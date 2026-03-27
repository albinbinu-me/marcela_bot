from typing import Any, Optional

from aiogram import Router, flags
from aiogram.handlers import CallbackQueryHandler
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from stfu_tg import Doc, Section, Template, Title, Url

from sophie_bot.config import CONFIG
from sophie_bot.filters.chat_status import ChatTypeFilter
from sophie_bot.filters.cmd import CMDFilter
from sophie_bot.filters.message_status import NoArgs
from sophie_bot.modules.help.callbacks import (
    PMHelpModule,
    PMHelpModules,
    PMHelpStartUrlCallback,
    PMHelpQueryStartUrlCallback,
)
from sophie_bot.modules.help.utils.extract_info import HELP_MODULES, get_aliased_cmds
from sophie_bot.modules.help.utils.format_help import format_handlers, group_handlers, format_handler
from sophie_bot.utils.handlers import SophieMessageCallbackQueryHandler
from sophie_bot.utils.exception import SophieException
from sophie_bot.utils.i18n import gettext as _
from sophie_bot.utils.i18n import lazy_gettext as l_


@flags.help(description=l_("Shows help overview for all modules"))
class PMModulesList(SophieMessageCallbackQueryHandler):
    @classmethod
    def register(cls, router: Router):
        router.message.register(cls, PMHelpStartUrlCallback.filter(), ChatTypeFilter("private"))
        router.message.register(cls, CMDFilter("help"), ChatTypeFilter("private"), NoArgs(True))
        router.callback_query.register(cls, PMHelpModules.filter())

    async def handle(self) -> Any:
        callback_data: Optional[PMHelpModules] = self.data.get("callback_data", None)

        # Sort item by the module title
        modules = {k: v for k, v in sorted(HELP_MODULES.items(), key=lambda item: str(item[1].name)) if k != "ai"}
        # Put the featured module to the bottom
        if CONFIG.help_featured_module in HELP_MODULES:
            modules[CONFIG.help_featured_module] = HELP_MODULES[CONFIG.help_featured_module]

        buttons = InlineKeyboardBuilder()

        buttons.row(
            *(
                InlineKeyboardButton(
                    text=f"{module.icon} {module.name}",
                    callback_data=PMHelpModule(
                        module_name=module_name, back_to_start=bool(callback_data and callback_data.back_to_start)
                    ).pack(),
                )
                for module_name, module in modules.items()
                if not module.exclude_public
            ),
            width=2,
        )

        if callback_data and callback_data.back_to_start:
            buttons.row(InlineKeyboardButton(text=_("Back"), callback_data="go_to_start", style="primary"))

        doc = Doc(
            Title(_("Help")),
            _("There are 2 help sources, you can read the detailed wiki or get a quick commands by modules overview."),
            Url(_("📖 Wiki (detailed information)"), CONFIG.wiki_link),
        )

        if isinstance(self.event, CallbackQuery):
            await self.message.edit_text(str(doc), reply_markup=buttons.as_markup(), disable_web_page_preview=True)
        else:
            await self.event.reply(str(doc), reply_markup=buttons.as_markup(), disable_web_page_preview=True)


class PMModuleHelp(CallbackQueryHandler):
    async def handle(self) -> Any:
        callback_data: PMHelpModule = self.data["callback_data"]
        module_name = callback_data.module_name
        module = HELP_MODULES[module_name]

        if not module:
            await self.event.answer(_("Module not found"))
            return

        cmds = list(filter(lambda x: not x.only_op, module.handlers))

        doc = Doc(
            Title(Template("📖{name}", name=module.name)),
            Template(_("✨ What it does:")),
            f"{module.description}" if module.description else "",
            " ",
            Template(_("⚙️ Commands:")),
        )

        for section_title, handlers in group_handlers(cmds):
            doc += Section(format_handlers(handlers), title=section_title, indent=0)

        for a_mod_name, a_cmds in get_aliased_cmds(module_name).items():
            a_module = HELP_MODULES[a_mod_name]
            doc += Section(
                format_handlers(a_cmds),
                title=Template(
                    _("Aliased commands from {module}"), module=f"{a_module.icon} {a_module.name}"
                ).to_html(),
                indent=0,
            )

        if module.info:
            doc += " "
            doc += Template(_("💡 Tip:"))
            doc += module.info

        buttons = InlineKeyboardBuilder()

        if module.advertise_wiki_page:
            doc += " "
            doc += Url(_("📖 Look the module's wiki page for more information"), CONFIG.wiki_modules_link + module_name)
            buttons.row(InlineKeyboardButton(text=_("📖 Wiki page"), url=CONFIG.wiki_modules_link + module_name))

        buttons.row(
            InlineKeyboardButton(
                text=_("Back"),
                callback_data=PMHelpModules(back_to_start=callback_data.back_to_start).pack(),
                style="primary",
            )
        )

        if not self.event.message or not isinstance(self.event.message, Message):
            raise SophieException("Message not found or inaccessible")

        await self.event.message.edit_text(str(doc), reply_markup=buttons.as_markup(), disable_web_page_preview=True)


@flags.help(exclude=True)
class PMHelpQuery(SophieMessageCallbackQueryHandler):
    @classmethod
    def register(cls, router: Router):
        router.message.register(cls, CMDFilter("help"), ChatTypeFilter("private"), ~NoArgs(True))
        router.message.register(cls, PMHelpQueryStartUrlCallback.filter(), ChatTypeFilter("private"))

    async def handle(self) -> Any:
        if "command_start" in self.data:
            query = self.data["command_start"].query.lower()
        else:
            command = self.data.get("command")
            if command and command.args:
                query = str(command.args).lower()
            else:
                text_str = self.message.text or ""
                parts = text_str.split(maxsplit=1)
                if len(parts) > 1:
                    query = parts[1].lower()
                else:
                    return await self.answer("Usage: /help <query>")

        # Remove emojis and strip whitespace
        import re

        query = re.sub(r"[^\w\s-]", "", query).strip()

        if query.startswith("/"):
            query = query[1:]

        for module_name, module in HELP_MODULES.items():
            if module_name.lower() == query or str(module.name).lower() == query:
                cmds = list(filter(lambda x: not x.only_op, module.handlers))

                doc = Doc(
                    Title(Template("📖 {name}", name=module.name)),
                    Template(_("✨ What it does:")),
                    f"{module.description}" if module.description else "",
                    " ",
                    Template(_("⚙️ Commands:")),
                )

                for section_title, handlers in group_handlers(cmds):
                    doc += Section(format_handlers(handlers), title=section_title, indent=0)

                for a_mod_name, a_cmds in get_aliased_cmds(module_name).items():
                    a_module = HELP_MODULES[a_mod_name]
                    doc += Section(
                        format_handlers(a_cmds),
                        title=Template(
                            _("Aliased commands from {module}"), module=f"{a_module.icon} {a_module.name}"
                        ).to_html(),
                        indent=0,
                    )

                if module.info:
                    doc += " "
                    doc += Template(_("💡 Tip:"))
                    doc += module.info

                buttons = InlineKeyboardBuilder()
                buttons.row(
                    InlineKeyboardButton(
                        text=_("Back"),
                        callback_data=PMHelpModules(back_to_start=True).pack(),
                        style="primary",
                    )
                )

                return await self.answer(str(doc), reply_markup=buttons.as_markup())

        from sophie_bot.modules.help.utils.extract_info import get_all_cmds

        matched_cmd = None
        for cmd in get_all_cmds():
            if query in cmd.cmds:
                matched_cmd = cmd
                break

        if matched_cmd:
            doc = Doc(
                Title(Template("📖 {cmd}", cmd=f"/{query}")),
                Template(_("✨ What it does:")),
                f"{matched_cmd.description}" if matched_cmd.description else Template(_("No description provided.")),
                " ",
                Template(_("⚙️ Usage:")),
                format_handler(matched_cmd, show_only_in_groups=True, show_disable_able=True),
            )

            buttons = InlineKeyboardBuilder()
            buttons.row(
                InlineKeyboardButton(
                    text=_("Back"),
                    callback_data=PMHelpModules(back_to_start=True).pack(),
                    style="primary",
                )
            )

            return await self.answer(str(doc), reply_markup=buttons.as_markup())

        error_doc = Template(_("{query} command not found refer /help to view all commands"), query=query)
        await self.answer(str(error_doc))
