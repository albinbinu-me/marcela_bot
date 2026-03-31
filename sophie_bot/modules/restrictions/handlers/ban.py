from __future__ import annotations

from contextlib import suppress
from datetime import timedelta
from typing import Any, Optional

from aiogram import flags
from aiogram.dispatcher.event.handler import CallbackType
from aiogram.types import Message
from ass_tg.types import ActionTimeArg, OptionalArg, TextArg
from ass_tg.types.base_abc import ArgFabric
from babel.dates import format_timedelta
from stfu_tg import KeyValue, Section, Template, UserLink

from sophie_bot.args.users import SophieUserArg
from sophie_bot.config import CONFIG
from sophie_bot.filters.admin_rights import BotHasPermissions, UserRestricting
from sophie_bot.filters.cmd import CMDFilter
from sophie_bot.modules.logging.events import LogEvent
from sophie_bot.modules.logging.utils import log_event
from sophie_bot.modules.utils_.admin import is_user_admin
from sophie_bot.modules.restrictions.utils.restrictions import ban_user
from sophie_bot.utils.federation_ban_check import FederationBanInfo, get_user_federation_ban_info
from sophie_bot.utils.handlers import SophieMessageHandler
from sophie_bot.modules.utils_.get_user import get_arg_or_reply_user, get_union_user
from sophie_bot.modules.utils_.message import is_real_reply
from sophie_bot.utils.exception import SophieException
from sophie_bot.utils.i18n import gettext as _
from sophie_bot.utils.i18n import lazy_gettext as l_


def _build_ban_doc(
    title: str,
    connection_title: str,
    user_id: int,
    user_name: str,
    admin_id: int,
    admin_name: str,
    reason: Optional[str],
    duration: Optional[timedelta] = None,
    locale: str = "en",
    fed_info: Optional[FederationBanInfo] = None,
) -> Section:
    doc = Section(
        KeyValue(_("Chat"), connection_title),
        KeyValue(_("User"), UserLink(user_id, user_name)),
        KeyValue(_("Banned by"), UserLink(admin_id, admin_name)),
        KeyValue(_("Duration"), format_timedelta(duration, locale=locale)) if duration else None,
        KeyValue(_("Reason"), reason) if reason else None,
        KeyValue(
            _("Notice"),
            Template(
                _("The user is already banned in the current federation: {fed_name} ({fed_id})."),
                fed_name=fed_info.fed_name,
                fed_id=fed_info.fed_id,
            ),
        )
        if fed_info and fed_info.scope == "current"
        else None,
        KeyValue(
            _("Notice"),
            Template(
                _("The user is already banned in a subscribed federation: {fed_name} ({fed_id})."),
                fed_name=fed_info.fed_name,
                fed_id=fed_info.fed_id,
            ),
        )
        if fed_info and fed_info.scope == "subscribed"
        else None,
        title=title,
    )
    return doc


@flags.help(
    description=l_("Bans the user from the chat."),
    example=l_("/ban @user — ban permanently\n/ban @user 2h — ban for 2 hours"),
)
class BanUserHandler(SophieMessageHandler):
    @staticmethod
    def filters() -> tuple[CallbackType, ...]:
        return (
            CMDFilter("ban"),
            UserRestricting(can_restrict_members=True),
            BotHasPermissions(can_restrict_members=True),
        )

    @classmethod
    async def handler_args(cls, message: Message | None, data: dict) -> dict[str, ArgFabric]:
        args: dict[str, ArgFabric] = {}
        if not message or not is_real_reply(message):
            args["user"] = SophieUserArg(l_("User"))
        args["reason"] = OptionalArg(TextArg(l_("Reason")))
        return args

    async def handle(self) -> Any:
        connection = self.connection

        if not self.event.from_user:
            raise SophieException("No from_user")

        user = get_union_user(get_arg_or_reply_user(self.event, self.data))

        if user.chat_id == CONFIG.bot_id:
            return await self.event.reply(_("I cannot ban myself."))
        if self.event.from_user and user.chat_id == self.event.from_user.id:
            return await self.event.reply(_("You cannot ban yourself."))
        if await is_user_admin(connection.tid, user.chat_id):
            return await self.event.reply(_("I cannot ban an admin."))

        fed_info = await get_user_federation_ban_info(connection.db_model.iid, user.chat_id)

        if not await ban_user(connection.tid, user.chat_id):
            return await self.event.reply(_("Failed to ban the user. Make sure I have the right permissions."))

        reason = self.data.get("reason")
        await log_event(
            connection.tid,
            self.event.from_user.id,
            LogEvent.USER_BANNED,
            {"target_user_id": user.chat_id, "reason": reason},
        )

        doc = _build_ban_doc(
            _("User banned"),
            connection.title,
            user.chat_id,
            user.first_name,
            self.event.from_user.id,
            self.event.from_user.first_name,
            reason,
            fed_info=fed_info,
        )
        await self.event.reply(str(doc))


@flags.help(
    description=l_("Temporarily bans the user from the chat."),
    example=l_("/tban @user 1d — ban for 1 day\n/tban @user 6h spam — ban replied user for 6 hours"),
)
class TempBanUserHandler(SophieMessageHandler):
    @staticmethod
    def filters() -> tuple[CallbackType, ...]:
        return (
            CMDFilter("tban"),
            UserRestricting(can_restrict_members=True),
            BotHasPermissions(can_restrict_members=True),
        )

    @classmethod
    async def handler_args(cls, message: Message | None, data: dict) -> dict[str, ArgFabric]:
        args: dict[str, ArgFabric] = {}
        if not message or not is_real_reply(message):
            args["user"] = SophieUserArg(l_("User"))
        args["time"] = ActionTimeArg(l_("Time (e.g., 2h, 7d, 2w)"))
        args["reason"] = OptionalArg(TextArg(l_("Reason")))
        return args

    async def handle(self) -> Any:
        connection = self.connection

        if not self.event.from_user:
            raise SophieException("No from_user")

        user = get_union_user(get_arg_or_reply_user(self.event, self.data))

        if user.chat_id == CONFIG.bot_id:
            return await self.event.reply(_("I cannot ban myself."))
        if self.event.from_user and user.chat_id == self.event.from_user.id:
            return await self.event.reply(_("You cannot ban yourself."))
        if await is_user_admin(connection.tid, user.chat_id):
            return await self.event.reply(_("I cannot ban an admin."))

        fed_info = await get_user_federation_ban_info(connection.db_model.iid, user.chat_id)
        until_date: timedelta = self.data["time"]

        if not await ban_user(connection.tid, user.chat_id, until_date=until_date):
            return await self.event.reply(_("Failed to ban the user. Make sure I have the right permissions."))

        reason = self.data.get("reason")
        await log_event(
            connection.tid,
            self.event.from_user.id,
            LogEvent.USER_BANNED,
            {"target_user_id": user.chat_id, "reason": reason, "duration": until_date.total_seconds()},
        )

        doc = _build_ban_doc(
            _("User temporarily banned"),
            connection.title,
            user.chat_id,
            user.first_name,
            self.event.from_user.id,
            self.event.from_user.first_name,
            reason,
            duration=until_date,
            locale=self.current_locale,
            fed_info=fed_info,
        )
        await self.event.reply(str(doc))


@flags.help(
    description=l_("Silently bans the user. No public message in group. Optionally provide a reason."),
    example=l_(
        "/sban @user — ban silently with no reason\n"
        "/sban @user spamming — silent ban with reason\n"
        "/sban (reply) flooding — silent ban the replied user"
    ),
)
class SilentBanUserHandler(BanUserHandler):
    @staticmethod
    def filters() -> tuple[CallbackType, ...]:
        return (
            CMDFilter("sban"),
            UserRestricting(can_restrict_members=True),
            BotHasPermissions(can_restrict_members=True),
        )

    async def handle(self) -> Any:
        connection = self.connection

        if not self.event.from_user:
            raise SophieException("No from_user")

        # Delete the command message so the group sees nothing
        with suppress(Exception):
            await self.event.delete()

        user = get_union_user(get_arg_or_reply_user(self.event, self.data))

        if user.chat_id == CONFIG.bot_id:
            return
        if self.event.from_user and user.chat_id == self.event.from_user.id:
            return
        if await is_user_admin(connection.tid, user.chat_id):
            return

        if not await ban_user(connection.tid, user.chat_id):
            return

        reason = self.data.get("reason")
        await log_event(
            connection.tid,
            self.event.from_user.id,
            LogEvent.USER_BANNED,
            {"target_user_id": user.chat_id, "reason": reason},
        )

        # DM the acting admin with action details
        doc = _build_ban_doc(
            _("🔇 Silent Ban Applied"),
            connection.title,
            user.chat_id,
            user.first_name,
            self.event.from_user.id,
            self.event.from_user.first_name,
            reason,
        )
        with suppress(Exception):
            await self.bot.send_message(chat_id=self.event.from_user.id, text=str(doc))


@flags.help(
    description=l_("Deletes the replied message and bans the sender. Optionally provide a reason."),
    example=l_(
        "/dban (reply) — delete message and ban the sender\n"
        "/dban (reply) scam link — delete message, ban, and record reason"
    ),
)
class DeleteBanUserHandler(BanUserHandler):
    @staticmethod
    def filters() -> tuple[CallbackType, ...]:
        return (
            CMDFilter("dban"),
            UserRestricting(can_restrict_members=True),
            BotHasPermissions(can_restrict_members=True),
        )

    async def handle(self) -> Any:
        connection = self.connection

        if not self.event.from_user:
            raise SophieException("No from_user")

        if not self.event.reply_to_message:
            return await self.event.reply(_("Reply to a message to perform ban."))

        user = get_union_user(get_arg_or_reply_user(self.event, self.data))

        if user.chat_id == CONFIG.bot_id:
            return await self.event.reply(_("I cannot ban myself."))
        if self.event.from_user and user.chat_id == self.event.from_user.id:
            return await self.event.reply(_("You cannot ban yourself."))
        if await is_user_admin(connection.tid, user.chat_id):
            return await self.event.reply(_("I cannot ban an admin."))

        # Delete the offending message first
        with suppress(Exception):
            await self.event.reply_to_message.delete()

        if not await ban_user(connection.tid, user.chat_id):
            return await self.event.reply(_("Failed to ban the user. Make sure I have the right permissions."))

        reason = self.data.get("reason")
        await log_event(
            connection.tid,
            self.event.from_user.id,
            LogEvent.USER_BANNED,
            {"target_user_id": user.chat_id, "reason": reason},
        )

        # Always show the full rich doc (same format as /ban)
        doc = _build_ban_doc(
            _("User banned"),
            connection.title,
            user.chat_id,
            user.first_name,
            self.event.from_user.id,
            self.event.from_user.first_name,
            reason,
        )
        await self.event.reply(str(doc))
