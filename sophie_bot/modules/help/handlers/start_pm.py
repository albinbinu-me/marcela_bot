from typing import Any

from aiogram import F, Router, flags
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions

from sophie_bot.config import CONFIG
from sophie_bot.filters.chat_status import ChatTypeFilter
from sophie_bot.filters.cmd import CMDFilter
from sophie_bot.filters.message_status import NoArgs
from sophie_bot.modules.help.callbacks import PMHelpModules
from sophie_bot.modules.privacy import PrivacyMenuCallback
from sophie_bot.utils.handlers import SophieMessageCallbackQueryHandler
from sophie_bot.utils.i18n import gettext as _


@flags.help(exclude=True)
class StartPMHandler(SophieMessageCallbackQueryHandler):
    @classmethod
    def register(cls, router: Router):
        router.message.register(cls, CMDFilter("start"), ChatTypeFilter("private"), NoArgs(True))
        router.callback_query.register(cls, ChatTypeFilter("private"), F.data == "go_to_start")

    async def handle(self) -> Any:
        state: FSMContext = self.state
        await state.clear()

        bot_name = CONFIG.bot_name

        text = (
            f"<b>👋 Welcome to {bot_name}!</b>\n\n"
            f"I'm an advanced group management bot designed to keep your community safe, organised, and running smoothly.\n\n"
            f"<b>⚡ Key Features</b>\n"
            f"  • 🚨 Anti-Raid &amp; Anti-Flood protection\n"
            f"  • ⚠️ Smart warning system\n"
            f"  • 🔒 Message locks &amp; filters\n"
            f"  • 🛡️ Captcha &amp; welcome security\n"
            f"  • 📌 Pin management\n"
            f"  • 🌐 Multi-language support\n\n"
            f"Use the buttons below to get started."
        )

        buttons = InlineKeyboardMarkup(
            inline_keyboard=[
                # Primary CTA — full width
                [
                    InlineKeyboardButton(
                        text=_("➕ Add me to your group"),
                        url=f"https://telegram.me/{CONFIG.username}?startgroup=true",
                    )
                ],
                # Navigation row
                [
                    InlineKeyboardButton(
                        text=_("📖 Help & Commands"),
                        callback_data=PMHelpModules(back_to_start=True).pack(),
                    ),
                    InlineKeyboardButton(
                        text=_("🌐 Language"),
                        callback_data="lang_btn",
                    ),
                ],
                # News channel + Privacy row
                [
                    InlineKeyboardButton(
                        text=_("📢 News Channel"),
                        url=CONFIG.news_channel,
                    ),
                    InlineKeyboardButton(
                        text=_("🔐 Privacy"),
                        callback_data=PrivacyMenuCallback(back_to_start=True).pack(),
                    ),
                ],
            ]
        )

        await self.answer(
            text,
            reply_markup=buttons,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
