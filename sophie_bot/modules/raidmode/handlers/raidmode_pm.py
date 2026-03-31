from typing import Any

from aiogram import flags
from aiogram.dispatcher.event.handler import CallbackType

from sophie_bot.filters.chat_status import ChatTypeFilter
from sophie_bot.filters.cmd import CMDFilter
from sophie_bot.middlewares.connections import ChatConnection
from sophie_bot.modules.connections.handlers.connect_dm import ConnectDMCmd
from sophie_bot.modules.raidmode.handlers.raidmode import RaidModeHandler, RaidMuteDurationHandler
from sophie_bot.modules.utils_.admin import is_user_admin
from sophie_bot.utils.i18n import gettext as _


@flags.help(exclude=True)
class RaidModePMHandler(RaidModeHandler):
    @staticmethod
    def filters() -> tuple[CallbackType, ...]:
        return CMDFilter(("raidmode", "raid")), ChatTypeFilter("private")

    async def handle(self) -> Any:
        connection: ChatConnection = self.data["connection"]

        if not connection.is_connected:
            cmd = ConnectDMCmd(self.event, **self.data)
            return await cmd.handle()

        user = self.data["user"]
        if not await is_user_admin(connection.db_model.iid, user.iid):
            return await self.event.reply(_("You must be an admin of the connected chat to configure Raid Mode."))

        return await super().handle()


@flags.help(exclude=True)
class RaidMuteDurationPMHandler(RaidMuteDurationHandler):
    @staticmethod
    def filters() -> tuple[CallbackType, ...]:
        return CMDFilter(("raidmute",)), ChatTypeFilter("private")

    async def handle(self) -> Any:
        connection: ChatConnection = self.data["connection"]

        if not connection.is_connected:
            cmd = ConnectDMCmd(self.event, **self.data)
            return await cmd.handle()

        user = self.data["user"]
        if not await is_user_admin(connection.db_model.iid, user.iid):
            return await self.event.reply(_("You must be an admin of the connected chat to configure Raid Mode."))

        return await super().handle()
