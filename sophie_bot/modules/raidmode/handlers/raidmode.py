from __future__ import annotations

from typing import Any

from aiogram import flags
from aiogram.dispatcher.event.handler import CallbackType
from aiogram.types import InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from ass_tg.types import IntArg, OptionalArg
from stfu_tg import Bold, KeyValue, Section, Template

from sophie_bot.db.models import ChatModel
from sophie_bot.db.models.raidmode import RaidModeModel
from sophie_bot.filters.admin_rights import BotHasPermissions, UserRestricting
from sophie_bot.filters.cmd import CMDFilter
from sophie_bot.modules.raidmode.callbacks import RaidModeToggleCB
from sophie_bot.modules.utils_.status_handler import StatusBoolHandlerABC
from sophie_bot.utils.handlers import SophieCallbackQueryHandler, SophieMessageHandler
from sophie_bot.utils.i18n import gettext as _
from sophie_bot.utils.i18n import lazy_gettext as l_


@flags.help(
    description=l_("Shows / changes the Raid Mode state. When enabled, new joiners are muted automatically."),
    example=l_("/raidmode on — enable raid mode\n/raidmode off — disable raid mode\n/raidmode — show current state"),
)
class RaidModeHandler(StatusBoolHandlerABC):
    header_text = l_("Raid Mode")
    change_command = "raidmode"

    @staticmethod
    def filters() -> tuple[CallbackType, ...]:
        return (
            CMDFilter(("raidmode", "raid")),
            UserRestricting(admin=True),
            BotHasPermissions(can_restrict_members=True),
        )

    async def get_status(self) -> bool:
        model = await RaidModeModel.get_by_chat_iid(self.connection.db_model.iid)
        return model.enabled

    async def set_status(self, new_status: bool) -> None:
        model = await RaidModeModel.get_by_chat_iid(self.connection.db_model.iid)
        await model.set_enabled(new_status)

    async def display_current_status(self):
        """Show current raid mode state with an inline toggle button for quick action."""
        model = await RaidModeModel.get_by_chat_iid(self.connection.db_model.iid)

        state_label = _("🔴 Enabled") if model.enabled else _("🟢 Disabled (auto-detect active)")
        duration_label = (
            _("indefinitely") if model.auto_mute_minutes <= 0 else _("{n} minutes").format(n=model.auto_mute_minutes)
        )

        text = (
            "<b>🚨 Raid Mode — {chat}</b>\n\n"
            "  Status:    <b>{state}</b>\n"
            "  Trigger:   <b>{threshold} joins within {window}s</b>\n"
            "  Mute for:  <b>{duration}</b>\n\n"
            "Use /raidmute &lt;minutes&gt; to change the mute duration.\n"
            "Use /raidunmute to lift all active raid mutes."
        ).format(
            chat=self.connection.title,
            state=state_label,
            threshold=model.threshold,
            window=model.window_seconds,
            duration=duration_label,
        )

        # Build quick-action button
        buttons = InlineKeyboardBuilder()
        if model.enabled:
            buttons.row(
                InlineKeyboardButton(
                    text=_("🔓 Disable Raid Mode"),
                    callback_data=RaidModeToggleCB(chat_iid=str(model.chat.ref.id), enabled=False).pack(),
                )
            )
        else:
            buttons.row(
                InlineKeyboardButton(
                    text=_("🔒 Enable Raid Mode"),
                    callback_data=RaidModeToggleCB(chat_iid=str(model.chat.ref.id), enabled=True).pack(),
                )
            )

        await self.event.reply(text, reply_markup=buttons.as_markup(), parse_mode="HTML")


@flags.help(
    description=l_("Sets how long (in minutes) new members are muted during a raid. Use 0 for indefinite."),
    example=l_(
        "/raidmute 30 — mute new joiners for 30 minutes\n/raidmute 0 — mute indefinitely\n/raidmute — show current duration"
    ),
)
class RaidMuteDurationHandler(SophieMessageHandler):
    @staticmethod
    def filters() -> tuple[CallbackType, ...]:
        return CMDFilter(("raidmute",)), UserRestricting(admin=True), BotHasPermissions(can_restrict_members=True)

    @classmethod
    async def handler_args(cls, message: Message | None, data: dict) -> dict:
        return {"minutes": OptionalArg(IntArg(l_("Mute duration in minutes (0 = indefinite)")))}

    async def handle(self) -> Any:
        minutes: int | None = (self.data.get("args") or {}).get("minutes")
        model = await RaidModeModel.get_by_chat_iid(self.connection.db_model.iid)

        if minutes is None:
            # Show current setting
            duration_label = (
                _("indefinitely")
                if model.auto_mute_minutes <= 0
                else _("{n} minutes").format(n=model.auto_mute_minutes)
            )
            doc = Section(
                KeyValue(_("Current mute duration"), Bold(duration_label)),
                KeyValue(_("Chat"), self.connection.title),
                title=_("Raid Mute Duration"),
            )
            doc += Template(_("Use '{cmd}' to change it."), cmd=Bold("/raidmute <minutes>"))
            return await self.event.reply(str(doc))

        if minutes < 0:
            return await self.event.reply(_("Duration cannot be negative. Use 0 for indefinite mute."))

        model.auto_mute_minutes = minutes
        await model.save()

        duration_label = _("indefinitely") if minutes == 0 else _("{n} minutes").format(n=minutes)
        doc = Section(
            _("Raid mute duration updated."),
            KeyValue(_("New duration"), Bold(duration_label)),
            KeyValue(_("Chat"), self.connection.title),
            title=_("Raid Mute Duration"),
        )
        await self.event.reply(str(doc))


class RaidModeToggleCallbackHandler(SophieCallbackQueryHandler):
    """Handles the inline Toggle button sent in admin raid alerts."""

    @staticmethod
    def filters() -> tuple[CallbackType, ...]:
        return (RaidModeToggleCB.filter(),)

    async def handle(self) -> Any:
        from beanie import PydanticObjectId

        cb: RaidModeToggleCB = self.callback_data
        chat = await ChatModel.get_by_iid(PydanticObjectId(cb.chat_iid))
        if not chat:
            await self.event.answer(_("Chat not found."), show_alert=True)
            return

        model = await RaidModeModel.get_by_chat_iid(chat.iid)
        await model.set_enabled(cb.enabled)

        label = _("enabled") if cb.enabled else _("disabled")
        await self.event.answer(
            Template(_("Raid Mode {label} for {chat}"), label=label, chat=chat.first_name_or_title).to_html(),
            show_alert=True,
        )

        # Flip the button
        buttons = InlineKeyboardBuilder()
        if cb.enabled:
            buttons.row(
                InlineKeyboardButton(
                    text=_("🔓 Disable Raid Mode"),
                    callback_data=RaidModeToggleCB(chat_iid=cb.chat_iid, enabled=False).pack(),
                )
            )
        else:
            buttons.row(
                InlineKeyboardButton(
                    text=_("🔒 Enable Raid Mode"),
                    callback_data=RaidModeToggleCB(chat_iid=cb.chat_iid, enabled=True).pack(),
                )
            )

        if self.event.message:
            from aiogram.types import Message as AiogramMessage

            if isinstance(self.event.message, AiogramMessage):
                await self.event.message.edit_reply_markup(reply_markup=buttons.as_markup())
