from typing import Any

from aiogram import flags
from aiogram.handlers import BaseHandler
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message

from sophie_bot.utils.i18n import gettext as _
from sophie_bot.utils.i18n import lazy_gettext as l_

from ..callbacks import (
    PrivacyMenuCallback,
    PrivacyPolicyCallback,
    PrivacyPolicySectionCallback,
    PrivacyRetrieveDataCallback,
    PrivacyDeleteDataCallback,
)


@flags.help(description=l_("Shows the privacy policy of the bot"))
class PrivacyMenu(BaseHandler[Message | CallbackQuery]):
    async def handle(self) -> Any:
        text = _("Select one of the options for more information about how the bot handles privacy")

        buttons = InlineKeyboardBuilder()

        buttons.row(InlineKeyboardButton(text=_("Privacy Policy"), callback_data=PrivacyPolicyCallback().pack()))

        buttons.row(
            InlineKeyboardButton(text=_("Retrieve Data"), callback_data=PrivacyRetrieveDataCallback().pack()),
            InlineKeyboardButton(text=_("Delete Data"), callback_data=PrivacyDeleteDataCallback().pack()),
        )

        buttons.row(InlineKeyboardButton(text=_("Cancel"), callback_data="go_to_start"))

        if isinstance(self.event, CallbackQuery):
            await self.event.message.edit_text(text, reply_markup=buttons.as_markup())  # type: ignore
        else:
            await self.event.reply(text, reply_markup=buttons.as_markup())


class PrivacyPolicyMenu(BaseHandler[Message | CallbackQuery]):
    async def handle(self) -> Any:
        text = _("Privacy Policy Overview:\nHere you can learn in detail about how we handle your data.")

        buttons = InlineKeyboardBuilder()

        sections = [
            (_("What we collect"), "collect"),
            (_("Why we collect it"), "why"),
            (_("What we do"), "do"),
            (_("What we don't do"), "dont"),
            (_("Right to process"), "process"),
        ]

        for name, sec_id in sections:
            buttons.row(
                InlineKeyboardButton(text=name, callback_data=PrivacyPolicySectionCallback(section=sec_id).pack())
            )

        buttons.row(InlineKeyboardButton(text=_("⬅️ Back"), callback_data=PrivacyMenuCallback().pack()))

        if isinstance(self.event, CallbackQuery):
            await self.event.message.edit_text(text, reply_markup=buttons.as_markup())  # type: ignore
        else:
            await self.event.reply(text, reply_markup=buttons.as_markup())


class PrivacyPolicySection(BaseHandler[Message | CallbackQuery]):
    async def handle(self) -> Any:
        callback_data: PrivacyPolicySectionCallback = self.data["callback_data"]
        section = callback_data.section

        section_texts = {
            "collect": _("We store basic profile information (User ID, First Name, Username, Language Code) and Group details (Chat ID, Title). We temporarily process messages in memory to enforce rules, but we do not store message contents long-term unless logged for moderation."),
            "why": _("This data is required to provide our moderation services, trace warnings, manage global federations, and remember individual chat settings without asking repeatedly."),
            "do": _("We use this data strictly to execute bot functions: analyzing incoming messages against your configured filters, keeping track of warning thresholds, automating welcomes/captchas, and verifying admin permissions."),
            "dont": _("We never monetize or sell your data. We do not read private messages outside of explicit bot commands, and group messages are only scanned momentarily by automated systems to enforce your chat's security settings."),
            "process": _("You retain full ownership of your data. You may request a complete export of all data associated with your User ID, or permanently delete your footprint from our database at any time using this menu."),
        }

        text = section_texts.get(section, _("Unknown section."))

        buttons = InlineKeyboardBuilder()
        buttons.row(InlineKeyboardButton(text=_("⬅️ Back"), callback_data=PrivacyPolicyCallback().pack()))

        if isinstance(self.event, CallbackQuery):
            await self.event.message.edit_text(text, reply_markup=buttons.as_markup())  # type: ignore
        else:
            await self.event.reply(text, reply_markup=buttons.as_markup())
