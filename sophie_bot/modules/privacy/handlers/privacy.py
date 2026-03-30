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
        text = (
            "<b>🔐 Privacy Centre</b>\n\n"
            "We take your privacy seriously. Choose an option below to learn how we handle your data, "
            "retrieve a copy, or permanently delete it.\n\n"
            "<i>Your data, your control.</i>"
        )

        buttons = InlineKeyboardBuilder()

        # Policy — full width
        buttons.row(
            InlineKeyboardButton(
                text=_("📄 Privacy Policy"),
                callback_data=PrivacyPolicyCallback().pack(),
            )
        )

        # Data actions — two distinct styled buttons side by side
        buttons.row(
            InlineKeyboardButton(
                text=_("📥 Retrieve My Data"),
                callback_data=PrivacyRetrieveDataCallback().pack(),
            ),
            InlineKeyboardButton(
                text=_("🗑 Delete My Data"),
                callback_data=PrivacyDeleteDataCallback().pack(),
            ),
        )

        # Back to start
        buttons.row(
            InlineKeyboardButton(
                text=_("← Back to Start"),
                callback_data="go_to_start",
            )
        )

        if isinstance(self.event, CallbackQuery):
            await self.event.message.edit_text(text, reply_markup=buttons.as_markup(), parse_mode="HTML")  # type: ignore
        else:
            await self.event.reply(text, reply_markup=buttons.as_markup(), parse_mode="HTML")


class PrivacyPolicyMenu(BaseHandler[Message | CallbackQuery]):
    async def handle(self) -> Any:
        text = (
            "<b>📄 Privacy Policy</b>\n\n"
            "Select a section below to read our full privacy policy. "
            "We believe in complete transparency about the data we collect and how it is used."
        )

        buttons = InlineKeyboardBuilder()

        sections = [
            (_("📦 What we collect"), "collect"),
            (_("🎯 Why we collect it"), "why"),
            (_("✅ What we do with it"), "do"),
            (_("🚫 What we don't do"), "dont"),
            (_("⚖️ Your right to process"), "process"),
        ]

        # 2-column grid
        row = []
        for name, sec_id in sections:
            row.append(InlineKeyboardButton(text=name, callback_data=PrivacyPolicySectionCallback(section=sec_id).pack()))
            if len(row) == 2:
                buttons.row(*row)
                row = []
        if row:
            buttons.row(*row)

        buttons.row(
            InlineKeyboardButton(
                text=_("← Back"),
                callback_data=PrivacyMenuCallback().pack(),
            )
        )

        if isinstance(self.event, CallbackQuery):
            await self.event.message.edit_text(text, reply_markup=buttons.as_markup(), parse_mode="HTML")  # type: ignore
        else:
            await self.event.reply(text, reply_markup=buttons.as_markup(), parse_mode="HTML")


class PrivacyPolicySection(BaseHandler[Message | CallbackQuery]):
    async def handle(self) -> Any:
        callback_data: PrivacyPolicySectionCallback = self.data["callback_data"]
        section = callback_data.section

        section_texts = {
            "collect": (
                "<b>📦 What We Collect</b>\n\n"
                "We store basic profile information — <b>User ID, First Name, Username, Language Code</b> — "
                "and group details such as <b>Chat ID and Title</b>.\n\n"
                "We temporarily process messages in memory to enforce rules, but we do <b>not</b> store message contents long-term "
                "unless required for moderation logging."
            ),
            "why": (
                "<b>🎯 Why We Collect It</b>\n\n"
                "This data is required to provide our moderation services — including tracking warnings, "
                "managing global federations, and remembering individual chat settings without asking repeatedly."
            ),
            "do": (
                "<b>✅ What We Do With It</b>\n\n"
                "We use this data strictly to execute bot functions: analyzing incoming messages against your configured filters, "
                "tracking warning thresholds, automating welcomes and captchas, and verifying admin permissions."
            ),
            "dont": (
                "<b>🚫 What We Don't Do</b>\n\n"
                "We <b>never</b> sell or monetise your data. We do not read private messages outside of explicit bot commands. "
                "Group messages are only scanned momentarily by automated systems to enforce your chat's security settings."
            ),
            "process": (
                "<b>⚖️ Your Right to Process</b>\n\n"
                "You retain full ownership of your data. You may request a complete export of all data associated with your User ID, "
                "or permanently delete your footprint from our database at any time using the <b>Privacy Centre</b> menu."
            ),
        }

        text = section_texts.get(section, _("Unknown section."))

        buttons = InlineKeyboardBuilder()
        buttons.row(
            InlineKeyboardButton(
                text=_("← Back to Policy"),
                callback_data=PrivacyPolicyCallback().pack(),
            )
        )

        if isinstance(self.event, CallbackQuery):
            await self.event.message.edit_text(text, reply_markup=buttons.as_markup(), parse_mode="HTML")  # type: ignore
        else:
            await self.event.reply(text, reply_markup=buttons.as_markup(), parse_mode="HTML")
