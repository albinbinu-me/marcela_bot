from __future__ import annotations

from typing import Any, cast

from aiogram import flags
from aiogram.types import BufferedInputFile, CallbackQuery, InaccessibleMessage, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from stfu_tg import Bold, KeyValue, Section, Template

from sophie_bot.db.models.chat import ChatModel, ChatType
from sophie_bot.filters.cmd import CMDFilter
from sophie_bot.filters.user_status import IsOP
from sophie_bot.modules.op.callbacks import AllUsersListCB
from sophie_bot.utils.handlers import SophieCallbackQueryHandler, SophieMessageHandler
from sophie_bot.utils.i18n import gettext as _
from sophie_bot.utils.i18n import lazy_gettext as l_


@flags.help(
    description=l_("Shows bot user stats and allows generating a full user list."),
    example=l_("/allusers — shows total users, new in 48h, active in 48h, with a Make List button"),
)
class AllUsersHandler(SophieMessageHandler):
    @staticmethod
    def filters():
        return (CMDFilter(("allusers",)), IsOP(True))

    async def handle(self) -> Any:
        user_types = (ChatType.private,)
        total = await ChatModel.total_count(user_types)
        new_48h = await ChatModel.new_count_last_48h(user_types)
        active_48h = await ChatModel.active_count_last_48h(user_types)

        doc = Section(
            KeyValue(_("Total users"), Bold(str(total))),
            KeyValue(_("New in last 48h"), Bold(str(new_48h))),
            KeyValue(_("Active in last 48h"), Bold(str(active_48h))),
            title=_("Bot User Stats"),
        )

        buttons = InlineKeyboardBuilder()
        buttons.row(
            InlineKeyboardButton(
                text=f"📋 {_('Make List')}",
                callback_data=AllUsersListCB().pack(),
            )
        )

        await self.event.reply(str(doc), reply_markup=buttons.as_markup())


class AllUsersListHandler(SophieCallbackQueryHandler):
    @staticmethod
    def filters():
        return (AllUsersListCB.filter(), IsOP(True))

    async def handle(self) -> Any:
        if not self.event.message or isinstance(self.event.message, InaccessibleMessage):
            return

        await cast(CallbackQuery, self.event).answer(_("Generating list…"))

        users = await ChatModel.find(ChatModel.type == ChatType.private).to_list()

        lines = [f"Bot Users ({len(users)} total)\n"]
        for user in users:
            uid = user.tid
            fname = user.first_name_or_title or ""
            lname = user.last_name or ""
            name = f"{fname} {lname}".strip()
            uname_display = f"@{user.username}" if user.username else "no username"

            lines.append("-" * 28)
            lines.append(f"ID:       {uid}")
            lines.append(f"Name:     {name}")
            lines.append(f"Username: {uname_display}")
            lines.append("")

        text = "\n".join(lines)
        file = BufferedInputFile(text.encode("utf-8"), filename="allusers.txt")
        await cast(Message, self.event.message).answer_document(
            file,
            caption=Template(_("All Bot Users ({count})"), count=Bold(str(len(users)))).to_html(),
        )
