from typing import Any

from aiogram import flags
from aiogram.dispatcher.event.handler import CallbackType
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from sophie_bot.filters.chat_status import ChatTypeFilter
from sophie_bot.filters.cmd import CMDFilter
from sophie_bot.modules.help.callbacks import PMHelpStartUrlCallback
from sophie_bot.utils.handlers import SophieMessageHandler
from sophie_bot.utils.i18n import gettext as _
from sophie_bot.utils.i18n import lazy_gettext as l_


@flags.disableable(name="help")
@flags.help(description=l_("Shows the help message"))
class HelpGroupHandler(SophieMessageHandler):
    @staticmethod
    def filters() -> tuple[CallbackType, ...]:
        return CMDFilter("help"), ~ChatTypeFilter("private")

    async def handle(self) -> Any:
        text_str = self.event.text or ""
        args = text_str.split(maxsplit=1)
        buttons = InlineKeyboardBuilder()

        if len(args) > 1:
            query = args[1].lower().strip()
            if query.startswith("/"):
                query = query[1:]
                
            from sophie_bot.modules.help.utils.extract_info import HELP_MODULES, get_all_cmds
            from stfu_tg import Template

            found = False
            for module_name, module in HELP_MODULES.items():
                if module_name.lower() == query or str(module.name).lower() == query:
                    found = True
                    break
            if not found:
                for cmd in get_all_cmds():
                    if query in cmd.cmds:
                        found = True
                        break

            if found:
                text = Template(_("Contact me for help in PM to view help for {query}."), query=query)
                from sophie_bot.modules.help.callbacks import PMHelpQueryStartUrlCallback
                cb_url = PMHelpQueryStartUrlCallback(query=query).pack()
            else:
                text = Template(_("{query} command not found refer help to view all commands"), query=query)
                cb_url = PMHelpStartUrlCallback().pack()

            buttons.add(
                InlineKeyboardButton(
                    text=_("Contact me for help in PM"), url=cb_url
                )
            )
        else:
            text = _("Contact me for help in PM")
            buttons.add(InlineKeyboardButton(text=_("Contact me for help in PM"), url=PMHelpStartUrlCallback().pack()))

        await self.event.reply(str(text), reply_markup=buttons.as_markup())
