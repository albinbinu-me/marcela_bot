from __future__ import annotations

from contextlib import suppress
from typing import Any, Optional

from aiogram import flags
from aiogram.dispatcher.event.handler import CallbackType
from aiogram.types import InlineKeyboardButton, Message, User
from aiogram.utils.keyboard import InlineKeyboardBuilder
from ass_tg.types import OptionalArg, TextArg
from ass_tg.types.base_abc import ArgFabric
from stfu_tg import Doc, Italic, KeyValue, Section, Template, Title, UserLink

from sophie_bot.args.users import SophieUserArg
from sophie_bot.config import CONFIG
from sophie_bot.db.models import ChatModel, RulesModel
from sophie_bot.filters.admin_rights import BotHasPermissions, UserRestricting
from sophie_bot.filters.cmd import CMDFilter
from sophie_bot.modules.logging.events import LogEvent
from sophie_bot.modules.logging.utils import log_event
from sophie_bot.modules.utils_.admin import is_user_admin
from sophie_bot.modules.utils_.common_try import common_try
from sophie_bot.modules.utils_.get_user import get_arg_or_reply_user, get_union_user
from sophie_bot.modules.utils_.message import is_real_reply
from sophie_bot.modules.warns.callbacks import DeleteWarnCallback
from sophie_bot.modules.warns.utils import warn_user
from sophie_bot.utils.handlers import SophieMessageHandler
from sophie_bot.utils.exception import SophieException
from sophie_bot.utils.i18n import gettext as _
from sophie_bot.utils.i18n import lazy_gettext as l_


def _build_warn_doc(
    target_user: ChatModel,
    admin_id: int,
    admin_name: str,
    current: int,
    limit: int,
    reason: Optional[str],
    punishment: Optional[str],
) -> Doc:
    doc = Doc(
        Title(_("⚠️ User warned")),
        KeyValue(_("User"), UserLink(target_user.tid, target_user.first_name_or_title)),
        KeyValue(_("By admin"), UserLink(admin_id, admin_name)),
        KeyValue(_("Warnings count"), f"{current}/{limit}"),
    )
    if reason:
        doc += Section(Italic(reason), title=_("Reason"))
    if punishment:
        doc += Section(Template(_("User has been {punishment} due to reaching max warns."), punishment=punishment))
    return doc


@flags.help(
    description=l_("Warns a user."),
    example=l_("/warn @user spamming — warn a user with a reason\n/warn (reply) — warn the replied user"),
)
@flags.disableable(name="warn")
class WarnHandler(SophieMessageHandler):
    @staticmethod
    def filters() -> tuple[CallbackType, ...]:
        return (
            CMDFilter("warn"),
            UserRestricting(can_restrict_members=True),
            BotHasPermissions(can_restrict_members=True),
        )

    @classmethod
    async def handler_args(cls, message: Message | None, data: dict) -> dict[str, ArgFabric]:
        args: dict[str, ArgFabric] = {}
        if not message or not is_real_reply(message):
            args["user"] = SophieUserArg(l_("User to warn"))
        args["reason"] = OptionalArg(TextArg(l_("Reason")))
        return args

    async def handle(self) -> Any:
        message: Message = self.event
        connection = self.connection
        admin_user: ChatModel = self.data["user_db"]
        reason: Optional[str] = self.data.get("reason")

        raw_user = get_arg_or_reply_user(message, self.data)

        if isinstance(raw_user, User):
            target_user = await ChatModel.get_by_tid(raw_user.id)
            if not target_user:
                await message.reply(_("User not found in database."))
                return
        else:
            target_user = raw_user

        if target_user.tid == CONFIG.bot_id:
            await message.reply(_("I cannot warn myself."))
            return

        if await is_user_admin(connection.db_model.iid, target_user.iid):
            await message.reply(_("I cannot warn an admin."))
            return

        if not message.from_user:
            return

        current, limit, punishment, warn = await warn_user(
            connection.db_model,
            target_user,
            admin_user,
            reason,
            trigger_message=message,
            action_context=self.data,
        )

        await log_event(
            connection.tid,
            message.from_user.id,
            LogEvent.WARN_ADDED,
            {"target_user_id": target_user.tid, "reason": reason, "current": current, "limit": limit},
        )

        doc = _build_warn_doc(target_user, message.from_user.id, message.from_user.first_name, current, limit, reason, punishment)

        builder = InlineKeyboardBuilder()
        if await RulesModel.get_rules(connection.db_model.iid):
            bot_username = (await self.bot.get_me()).username
            builder.row(
                InlineKeyboardButton(
                    text=f"🪧 {_('Rules')}",
                    url=f"https://t.me/{bot_username}?start=btn_rules_{connection.tid}",
                )
            )
        if not punishment and warn and warn.id:
            builder.row(
                InlineKeyboardButton(
                    text=f"🗑️ {_('Delete warn')}",
                    callback_data=DeleteWarnCallback(warn_iid=str(warn.id)).pack(),
                )
            )

        reply_markup = builder.as_markup()
        text = doc.to_html()

        async def send_message() -> Message:
            return await self.bot.send_message(
                chat_id=message.chat.id,
                text=text,
                reply_markup=reply_markup,
                message_thread_id=message.message_thread_id,
            )

        await common_try(message.reply(text, reply_markup=reply_markup), reply_not_found=send_message)


@flags.help(
    description=l_("Warns a user silently (no public message). Optionally provide a reason."),
    example=l_(
        "/swarn @user spamming — silently warn with reason\n"
        "/swarn (reply) posting links — silently warn the replied user\n"
        "/swarn @user — silently warn with no reason"
    ),
)
@flags.disableable(name="swarn")
class SilentWarnHandler(WarnHandler):
    @staticmethod
    def filters() -> tuple[CallbackType, ...]:
        return (
            CMDFilter("swarn"),
            UserRestricting(can_restrict_members=True),
            BotHasPermissions(can_restrict_members=True),
        )

    async def handle(self) -> Any:
        message: Message = self.event
        connection = self.connection
        admin_user: ChatModel = self.data["user_db"]
        reason: Optional[str] = self.data.get("reason")

        # Delete the command message silently
        with suppress(Exception):
            await message.delete()

        raw_user = get_arg_or_reply_user(message, self.data)

        if isinstance(raw_user, User):
            target_user = await ChatModel.get_by_tid(raw_user.id)
            if not target_user:
                return
        else:
            target_user = raw_user

        if target_user.tid == CONFIG.bot_id:
            return

        if await is_user_admin(connection.db_model.iid, target_user.iid):
            return

        if not message.from_user:
            return

        current, limit, punishment, warn = await warn_user(
            connection.db_model,
            target_user,
            admin_user,
            reason,
            trigger_message=message,
            action_context=self.data,
        )

        await log_event(
            connection.tid,
            message.from_user.id,
            LogEvent.WARN_ADDED,
            {"target_user_id": target_user.tid, "reason": reason, "current": current, "limit": limit},
        )

        # DM the acting admin so they get confirmation + reason summary
        doc = _build_warn_doc(target_user, message.from_user.id, message.from_user.first_name, current, limit, reason, punishment)
        doc_text = _("🔇 <b>Silent warn applied</b>\n") + doc.to_html()
        with suppress(Exception):
            await self.bot.send_message(chat_id=message.from_user.id, text=doc_text, parse_mode="HTML")


@flags.help(
    description=l_("Deletes the replied message and warns the sender. Optionally provide a reason."),
    example=l_(
        "/dwarn (reply) — delete message and warn the sender\n"
        "/dwarn (reply) bad content — delete message, warn, and record reason"
    ),
)
@flags.disableable(name="dwarn")
class DeleteWarnHandler(WarnHandler):
    @staticmethod
    def filters() -> tuple[CallbackType, ...]:
        return (
            CMDFilter("dwarn"),
            UserRestricting(can_restrict_members=True),
            BotHasPermissions(can_restrict_members=True),
        )

    async def handle(self) -> Any:
        message: Message = self.event
        connection = self.connection
        admin_user: ChatModel = self.data["user_db"]
        reason: Optional[str] = self.data.get("reason")

        if not message.reply_to_message:
            return await message.reply(_("Reply to a message to perform warn."))

        raw_user = get_arg_or_reply_user(message, self.data)

        if isinstance(raw_user, User):
            target_user = await ChatModel.get_by_tid(raw_user.id)
            if not target_user:
                await message.reply(_("User not found in database."))
                return
        else:
            target_user = raw_user

        if target_user.tid == CONFIG.bot_id:
            await message.reply(_("I cannot warn myself."))
            return

        if await is_user_admin(connection.db_model.iid, target_user.iid):
            await message.reply(_("I cannot warn an admin."))
            return

        if not message.from_user:
            return

        # Delete the offending message first
        with suppress(Exception):
            await message.reply_to_message.delete()

        current, limit, punishment, warn = await warn_user(
            connection.db_model,
            target_user,
            admin_user,
            reason,
            trigger_message=message,
            action_context=self.data,
        )

        await log_event(
            connection.tid,
            message.from_user.id,
            LogEvent.WARN_ADDED,
            {"target_user_id": target_user.tid, "reason": reason, "current": current, "limit": limit},
        )

        # Always send the full warn doc (consistent with /warn)
        doc = _build_warn_doc(target_user, message.from_user.id, message.from_user.first_name, current, limit, reason, punishment)

        builder = InlineKeyboardBuilder()
        if await RulesModel.get_rules(connection.db_model.iid):
            bot_username = (await self.bot.get_me()).username
            builder.row(
                InlineKeyboardButton(
                    text=f"🪧 {_('Rules')}",
                    url=f"https://t.me/{bot_username}?start=btn_rules_{connection.tid}",
                )
            )
        if not punishment and warn and warn.id:
            builder.row(
                InlineKeyboardButton(
                    text=f"🗑️ {_('Delete warn')}",
                    callback_data=DeleteWarnCallback(warn_iid=str(warn.id)).pack(),
                )
            )

        reply_markup = builder.as_markup()
        text = doc.to_html()

        async def send_message() -> Message:
            return await self.bot.send_message(
                chat_id=message.chat.id,
                text=text,
                reply_markup=reply_markup,
                message_thread_id=message.message_thread_id,
            )

        await common_try(message.reply(text, reply_markup=reply_markup), reply_not_found=send_message)
