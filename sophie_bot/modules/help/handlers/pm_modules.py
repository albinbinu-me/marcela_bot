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
    PMHelpCommandExample,
    PMHelpModuleExamples,
)
from sophie_bot.modules.help.utils.extract_info import HELP_MODULES, get_aliased_cmds, get_all_cmds
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

        # Show Examples button if any command in this module has an example
        if any(h.example for h in cmds):
            buttons.row(
                InlineKeyboardButton(
                    text=_("💡 Show Examples"),
                    callback_data=PMHelpModuleExamples(module_name=module_name).pack(),
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
                        text=_("⬅️ Back"),
                        callback_data=PMHelpModules(back_to_start=True).pack(),
                    ),
                    InlineKeyboardButton(
                        text=_("📋 Help Menu"),
                        callback_data=PMHelpModules(back_to_start=False).pack(),
                    ),
                )
                # Show Examples button if any command has an example
                if any(h.example for h in cmds):
                    buttons.row(
                        InlineKeyboardButton(
                            text=_("💡 Show Examples"),
                            callback_data=PMHelpModuleExamples(module_name=module_name).pack(),
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

            # Find which module this command belongs to
            owner_module_name: Optional[str] = None
            for mod_name, mod in HELP_MODULES.items():
                if any(matched_cmd is h for h in mod.handlers):
                    owner_module_name = mod_name
                    break

            buttons = InlineKeyboardBuilder()
            buttons.row(
                InlineKeyboardButton(
                    text=_("⬅️ Back"),
                    callback_data=PMHelpModules(back_to_start=True).pack(),
                ),
                InlineKeyboardButton(
                    text=_("📋 Help Menu"),
                    callback_data=PMHelpModules(back_to_start=False).pack(),
                ),
            )
            if owner_module_name:
                buttons.row(
                    InlineKeyboardButton(
                        text=_("🔍 Explore Module"),
                        callback_data=PMHelpModule(
                            module_name=owner_module_name, back_to_start=False
                        ).pack(),
                    )
                )
            if matched_cmd.example:
                buttons.row(
                    InlineKeyboardButton(
                        text=_("💡 Show Example"),
                        callback_data=PMHelpCommandExample(cmd=matched_cmd.cmds[0]).pack(),
                    )
                )

            return await self.answer(str(doc), reply_markup=buttons.as_markup())

        error_doc = Template(_("{query} command not found refer /help to view all commands"), query=query)
        await self.answer(str(error_doc))


@flags.help(exclude=True)
class PMCommandExampleHandler(CallbackQueryHandler):
    """Shows the usage example for a specific command when the 💡 Show Example button is tapped."""

    @classmethod
    def register(cls, router: Router):
        router.callback_query.register(cls, PMHelpCommandExample.filter())

    async def handle(self) -> Any:
        cb: PMHelpCommandExample = self.data["callback_data"]
        cmd_name = cb.cmd

        matched = next((h for h in get_all_cmds() if cmd_name in h.cmds), None)

        if not matched or not matched.example:
            await self.event.answer(_("No example available for this command."), show_alert=True)
            return

        example_text = Doc(
            Title(Template(_("💡 Example: /{cmd}"), cmd=cmd_name)),
            str(matched.example),
        )

        await self.event.answer()
        if self.event.message and isinstance(self.event.message, Message):
            await self.event.message.answer(str(example_text))


@flags.help(exclude=True)
class PMModuleExamplesHandler(CallbackQueryHandler):
    """Shows all command examples for a module when the 💡 Show Examples button is tapped."""

    @classmethod
    def register(cls, router: Router):
        router.callback_query.register(cls, PMHelpModuleExamples.filter())

    async def handle(self) -> Any:
        cb: PMHelpModuleExamples = self.data["callback_data"]
        module = HELP_MODULES.get(cb.module_name)

        if not module:
            await self.event.answer(_("Module not found."), show_alert=True)
            return

        cmds_with_examples = [h for h in module.handlers if not h.only_op and h.example]

        if not cmds_with_examples:
            await self.event.answer(_("No examples available for this module."), show_alert=True)
            return

        doc = Doc(Title(Template(_("💡 Examples — {name}"), name=module.name)))
        for handler in cmds_with_examples:
            primary = handler.cmds[0]
            doc += Section(
                str(handler.example),
                title=f"/{primary}",
            )

        # Button to go back to this module's help
        buttons = InlineKeyboardBuilder()
        buttons.row(
            InlineKeyboardButton(
                text=_("⬅️ Back to module"),
                callback_data=PMHelpModule(module_name=cb.module_name, back_to_start=False).pack(),
            )
        )

        await self.event.answer()
        if self.event.message and isinstance(self.event.message, Message):
            await self.event.message.answer(str(doc), reply_markup=buttons.as_markup())
