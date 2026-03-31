from __future__ import annotations

from typing import Any

from aiogram import flags
from aiogram.dispatcher.event.handler import CallbackType
from ass_tg.types import BooleanArg
from stfu_tg import Bold, Doc, Italic, KeyValue, Section, Template

from sophie_bot.db.models.private_rules import PrivateRulesModel
from sophie_bot.filters.admin_rights import UserRestricting
from sophie_bot.filters.chat_status import ChatTypeFilter
from sophie_bot.filters.cmd import CMDFilter
from sophie_bot.filters.message_status import HasArgs
from sophie_bot.middlewares.connections import ChatConnection
from sophie_bot.utils.exception import SophieException
from sophie_bot.utils.handlers import SophieMessageHandler
from sophie_bot.utils.i18n import gettext as _
from sophie_bot.utils.i18n import lazy_gettext as l_


@flags.help(
    description=l_("Show current state of Private Rules"),
    example=l_("/privaterules — check if private rules mode is enabled or disabled"),
)
class PrivateRulesStatus(SophieMessageHandler):
    @staticmethod
    def filters() -> tuple[CallbackType, ...]:
        return CMDFilter(("privaterules", "privatrules")), ~ChatTypeFilter("private"), ~HasArgs(True)

    async def handle(self) -> Any:
        connection: ChatConnection = self.data["connection"]

        if not connection.db_model:
            raise SophieException("Chat has no database model saved.")

        state = await PrivateRulesModel.get_state(connection.db_model.iid)

        doc = Doc(
            Section(
                KeyValue(_("Chat"), connection.title),
                KeyValue(_("Current state"), _("Enabled") if state else _("Disabled")),
                title=_("Private Rules"),
            ),
            Template(_("Use '{cmd}' to change it."), cmd=Italic("/privaterules (on / off)")),
        )

        await self.event.reply(str(doc), disable_web_page_preview=True)


@flags.args(new_state=BooleanArg(l_("New state")))
@flags.help(
    description=l_("Control Private Rules — when enabled, /rules sends a PM button instead of showing inline"),
    example=l_(
        "/privaterules on — enable private rules mode\n/privaterules off — disable private rules mode (default)"
    ),
)
class PrivateRulesControl(SophieMessageHandler):
    @staticmethod
    def filters() -> tuple[CallbackType, ...]:
        return (
            CMDFilter(("privaterules", "privatrules")),
            ~ChatTypeFilter("private"),
            HasArgs(True),
            UserRestricting(admin=True),
        )

    async def handle(self) -> Any:
        new_state: bool = self.data["new_state"]
        connection: ChatConnection = self.data["connection"]

        if not connection.db_model:
            raise SophieException("Chat has no database model saved.")

        await PrivateRulesModel.set_state(connection.db_model.iid, new_state)

        status_text = _("enabled") if new_state else _("disabled")

        doc = Doc(
            Bold(
                Template(
                    _("Private Rules have been {status} in {chat}."),
                    status=status_text.lower(),
                    chat=connection.title,
                )
            )
        )

        await self.event.reply(str(doc), disable_web_page_preview=True)
