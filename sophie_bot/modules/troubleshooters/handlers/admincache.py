from typing import Any

from aiogram import flags

from sophie_bot.db.models.chat import ChatType
from sophie_bot.filters.admin_rights import UserRestricting
from sophie_bot.db.models.chat_admin import ChatAdminModel
from sophie_bot.filters.cmd import CMDFilter
from sophie_bot.services.redis import aredis
from sophie_bot.utils.handlers import SophieMessageHandler
from sophie_bot.modules.utils_.chat_member import update_chat_members
from sophie_bot.utils.i18n import gettext as _
from sophie_bot.utils.i18n import lazy_gettext as l_


@flags.help(description=l_("Reset admin rights cache, use if Macela didn't get the recently added admin"))
class ResetAdminCache(SophieMessageHandler):
    @staticmethod
    def filters():
        return (CMDFilter("admincache"), UserRestricting(admin=True))

    async def handle(self) -> Any:
        # TODO: Make a flag for connection middleware
        if self.connection.type == ChatType.private:
            return await self.event.reply(_("You can't use this command in private chats."))

        # Hard wipe MongoDB admin cache for this chat
        await ChatAdminModel.find(ChatAdminModel.chat.id == self.connection.db_model.iid).delete()

        # Hard wipe Redis cache keys containing admin permissions
        await aredis.delete(f"admincache:{self.connection.tid}")

        # Pull fresh admins and reconstruct the cache map
        await update_chat_members(self.connection.db_model)
        await self.event.reply(_("Admin rights cache has been reset."))
