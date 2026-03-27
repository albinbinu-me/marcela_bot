from __future__ import annotations

from aiogram.types import BufferedInputFile

from sophie_bot.db.models.chat import ChatModel, ChatType
from sophie_bot.filters.cmd import CMDFilter
from sophie_bot.filters.user_status import IsOP
from sophie_bot.utils.handlers import SophieMessageHandler


class AllUsersHandler(SophieMessageHandler):
    @staticmethod
    def filters():
        return (CMDFilter(("allusers",)), IsOP(True))

    async def handle(self):
        users = await ChatModel.find(ChatModel.type == ChatType.private).to_list()

        text = "Bot Users:\n\n"
        for user in users:
            uid = user.tid
            fname = user.first_name_or_title or ""
            lname = user.last_name or ""
            name = f"{fname} {lname}".strip()
            uname_display = f"@{user.username}" if user.username else "no username"

            text += f"{'-' * 28}\n"
            text += f"id: {uid}\n"
            text += f"Name: {name}\n"
            text += f"Username: {uname_display}\n"

        if len(text) > 4000:
            file = BufferedInputFile(text.encode("utf-8"), filename="allusers.txt")
            await self.event.answer_document(file, caption=f"All Bot Users ({len(users)})")
        else:
            await self.event.reply(text)
