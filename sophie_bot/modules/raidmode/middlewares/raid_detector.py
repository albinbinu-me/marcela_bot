from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import ChatMemberUpdated, InlineKeyboardButton, TelegramObject
from aiogram.utils.keyboard import InlineKeyboardBuilder

from sophie_bot.db.models import ChatModel
from sophie_bot.db.models.raidmode import RaidModeModel
from sophie_bot.modules.raidmode.callbacks import RaidModeToggleCB
from sophie_bot.modules.restrictions.utils.restrictions import mute_user
from sophie_bot.services.bot import bot
from sophie_bot.services.redis import aredis
from sophie_bot.utils.i18n import gettext as _
from sophie_bot.utils.logger import log


# Redis keys
_JOINS_KEY = "raidmode:joins:{chat_iid}"
_RAID_ACTIVE_KEY = "raidmode:active:{chat_iid}"
_RAID_MUTED_KEY = "raidmode:muted:{chat_iid}"  # SET of user_tids muted during raid
_JOINS_TTL_SECONDS = 600
# Raid-muted user entries expire after 24 h so stale data is cleaned up automatically
_RAID_MUTED_TTL_SECONDS = 86400


def _mute_duration(model: RaidModeModel) -> timedelta | None:
    """Return timedelta for mute duration, or None for indefinite."""
    return timedelta(minutes=model.auto_mute_minutes) if model.auto_mute_minutes > 0 else None


def _mute_duration_text(model: RaidModeModel) -> str:
    """Human-readable mute duration string."""
    if model.auto_mute_minutes <= 0:
        return _("indefinitely")
    if model.auto_mute_minutes < 60:
        return _("{n} minutes").format(n=model.auto_mute_minutes)
    hours = model.auto_mute_minutes // 60
    mins = model.auto_mute_minutes % 60
    if mins:
        return _("{h}h {m}m").format(h=hours, m=mins)
    return _("{h} hours").format(h=hours)


async def _notify_raid(chat_tid: int, chat: ChatModel, model: RaidModeModel, joins_count: int) -> None:
    """
    Send a group announcement and DM all admins about the detected raid.
    Called only once per raid window.
    """
    duration_text = _mute_duration_text(model)

    toggle_buttons = InlineKeyboardBuilder()
    toggle_buttons.row(
        InlineKeyboardButton(
            text=_("🔒 Keep Raid Mode ON"),
            callback_data=RaidModeToggleCB(chat_iid=str(chat.iid), enabled=True).pack(),
        ),
        InlineKeyboardButton(
            text=_("🔓 Disable Raid Mode"),
            callback_data=RaidModeToggleCB(chat_iid=str(chat.iid), enabled=False).pack(),
        ),
    )

    # --- 1. Group announcement ---
    group_text = (
        "🚨 <b>Raid Detected!</b>\n\n"
        "{joins} new members joined in <b>{window}s</b>.\n"
        "New joiners are now muted for <b>{duration}</b>.\n\n"
        "Admins have been notified. Use <code>/raidunmute</code> to lift all raid mutes."
    ).format(
        joins=joins_count,
        window=model.window_seconds,
        duration=duration_text,
    )

    try:
        await bot.send_message(
            chat_id=chat_tid, text=group_text, reply_markup=toggle_buttons.as_markup(), parse_mode="HTML"
        )
    except Exception as err:  # noqa: BLE001
        log.warning("RaidMode: failed to send group alert", err=err, chat=chat_tid)

    # --- 2. DM every admin ---
    admin_text = (
        "⚠️ <b>Raid Alert — {chat_name}</b>\n\n"
        "🔢 <b>{joins}</b> users joined in <b>{window}s</b>\n"
        "⏱ Mute duration: <b>{duration}</b>\n"
        "🚨 Raid Mode has been auto-triggered.\n\n"
        "• Use <b>Keep ON</b> to keep raid mode active.\n"
        "• Use <b>Disable</b> to stop muting new joiners.\n"
        "• Use <code>/raidunmute</code> in the group to lift all raid mutes at once."
    ).format(
        chat_name=chat.first_name_or_title,
        joins=joins_count,
        window=model.window_seconds,
        duration=duration_text,
    )

    try:
        admins = await bot.get_chat_administrators(chat_tid)
    except Exception as err:  # noqa: BLE001
        log.warning("RaidMode: could not fetch admins for DM", err=err, chat=chat_tid)
        return

    for admin in admins:
        if admin.user.is_bot:
            continue
        try:
            await bot.send_message(
                chat_id=admin.user.id,
                text=admin_text,
                reply_markup=toggle_buttons.as_markup(),
                parse_mode="HTML",
            )
        except TelegramForbiddenError:
            # Admin hasn't started the bot in PM — skip silently
            pass
        except Exception as err:  # noqa: BLE001
            log.warning("RaidMode: failed to DM admin", err=err, admin=admin.user.id)


async def record_raid_mute(chat_iid: str, user_tid: int) -> None:
    """Store the user's Telegram ID in the raid-muted Redis set for this chat."""
    key = _RAID_MUTED_KEY.format(chat_iid=chat_iid)
    await aredis.sadd(key, str(user_tid))
    await aredis.expire(key, _RAID_MUTED_TTL_SECONDS)


async def get_raid_muted_users(chat_iid: str) -> list[int]:
    """Return all Telegram user IDs that were muted by the raid detector for this chat."""
    key = _RAID_MUTED_KEY.format(chat_iid=chat_iid)
    raw = await aredis.smembers(key)
    return [int(uid) for uid in raw]


async def clear_raid_muted_users(chat_iid: str) -> None:
    """Remove the raid-muted set for this chat."""
    key = _RAID_MUTED_KEY.format(chat_iid=chat_iid)
    await aredis.delete(key)


class RaidDetectorMiddleware(BaseMiddleware):
    """
    Watches chat_member join events.
    When threshold is breached within the rolling window:
      - auto-mutes each new joiner (for auto_mute_minutes, or indefinitely if 0)
      - records each muted user in Redis (so /raidunmute can lift them all)
      - sends a group announcement
      - DMs all admins with a toggle button
    When raid_mode is already manually enabled:
      - mutes every new joiner silently with the configured duration
      - records each muted user in Redis
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, ChatMemberUpdated):
            return await handler(event, data)

        new_status = event.new_chat_member.status
        if new_status not in ("member", "restricted"):
            return await handler(event, data)

        user = event.new_chat_member.user
        if user.is_bot:
            return await handler(event, data)

        # CRITICAL: Only treat this as a join if the user was NOT already in the group.
        # When unmute_user() / restrict_chat_member() is called, Telegram fires a
        # ChatMemberUpdated with new_status="member". Without this check the bot would
        # re-mute the user immediately after unmuting them.
        # Real joins: old_status is "left" (voluntary) or "kicked" (was banned then unbanned).
        # Permission changes: old_status is "restricted" or "member" — skip those.
        old_status = event.old_chat_member.status
        if old_status not in ("left", "kicked"):
            return await handler(event, data)

        chat_tid = event.chat.id
        chat = await ChatModel.get_by_tid(chat_tid)
        if not chat:
            return await handler(event, data)

        model = await RaidModeModel.get_by_chat_iid(chat.iid)
        chat_iid_str = str(chat.iid)

        if model.enabled:
            # Manual raid mode — mute with configured duration and record
            await mute_user(chat_tid=chat_tid, user_tid=user.id, until_date=_mute_duration(model))
            await record_raid_mute(chat_iid_str, user.id)
            log.debug("RaidMode active: muted new joiner", chat=chat_tid, user=user.id)
            return await handler(event, data)

        # --- Auto-detection: sliding window ---
        join_key = _JOINS_KEY.format(chat_iid=chat_iid_str)
        active_key = _RAID_ACTIVE_KEY.format(chat_iid=chat_iid_str)
        now_ts = datetime.now(timezone.utc).timestamp()

        await aredis.rpush(join_key, str(now_ts))
        await aredis.expire(join_key, _JOINS_TTL_SECONDS)

        window_start = now_ts - model.window_seconds
        raw_timestamps = await aredis.lrange(join_key, 0, -1)
        recent = [ts for ts in raw_timestamps if float(ts) >= window_start]

        if len(recent) != len(raw_timestamps):
            await aredis.delete(join_key)
            if recent:
                await aredis.rpush(join_key, *recent)
                await aredis.expire(join_key, _JOINS_TTL_SECONDS)

        if len(recent) >= model.threshold:
            # Mute and record so they can be bulk-unmuted later
            await mute_user(chat_tid=chat_tid, user_tid=user.id, until_date=_mute_duration(model))
            await record_raid_mute(chat_iid_str, user.id)
            log.warning("RaidMode auto-triggered", chat=chat_tid, joins_in_window=len(recent))

            # Announce group + DM admins — only once per raid window
            already_alerted = await aredis.get(active_key)
            if not already_alerted:
                await aredis.set(active_key, "1", ex=model.window_seconds * 2)
                await _notify_raid(chat_tid, chat, model, len(recent))

        return await handler(event, data)
