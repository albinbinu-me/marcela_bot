from typing import Any

from aiogram import flags
from aiogram.dispatcher.event.handler import CallbackType
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from stfu_tg import Bold, Doc, Template

from sophie_bot.modules.connections.utils.connection import set_connected_chat
from sophie_bot.modules.connections.utils.constants import CONNECTION_DISCONNECT_TEXT
from sophie_bot.modules.rules.callbacks import PrivateRulesStartUrlCallback
from sophie_bot.middlewares.connections import ConnectionsMiddleware
from sophie_bot.utils.handlers import SophieMessageHandler
from sophie_bot.utils.i18n import gettext as _
from sophie_bot.modules.rules.handlers.get import GetRulesHandler


@flags.help(exclude=True)
class PrivateRulesConnectHandler(SophieMessageHandler):
    @staticmethod
    def filters() -> tuple[CallbackType, ...]:
        return (PrivateRulesStartUrlCallback.filter(),)

    async def handle(self) -> Any:
        if not self.event.from_user:
            return

        user_id = self.event.from_user.id
        command_start: PrivateRulesStartUrlCallback = self.data["command_start"]
        chat_id = command_start.chat_id

        # Connect to the chat
        await set_connected_chat(user_id, chat_id)
        if not (connection := await ConnectionsMiddleware.get_chat_from_db(chat_id, is_connected=True)):
            return await self.event.reply(
                _("Chat not found in the database. Please try to disconnect and connect again.")
            )

        self.data["connection"] = connection

        doc = Doc(
            Bold(Template(_("Connected to chat {chat_name} successfully!"), chat_name=connection.title)),
            Template(_("Use {command} to disconnect"), command="/disconnect"),
            _("⏳ This connection will last for 48 hours."),
        )

        markup = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=str(CONNECTION_DISCONNECT_TEXT))]], resize_keyboard=True
        )

        await self.event.reply(str(doc), reply_markup=markup)

        # Show rules
        return await GetRulesHandler(self.event, **self.data)
