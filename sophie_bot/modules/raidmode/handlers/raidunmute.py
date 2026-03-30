from __future__ import annotations

from typing import Any

from aiogram import flags
from aiogram.dispatcher.event.handler import CallbackType

from sophie_bot.filters.admin_rights import BotHasPermissions, UserRestricting
from sophie_bot.filters.cmd import CMDFilter
from sophie_bot.modules.raidmode.middlewares.raid_detector import (
    clear_raid_muted_users,
    get_raid_muted_users,
)
from sophie_bot.modules.restrictions.utils.restrictions import unmute_user
from sophie_bot.utils.handlers import SophieMessageHandler
from sophie_bot.utils.i18n import gettext as _
from sophie_bot.utils.i18n import lazy_gettext as l_


@flags.help(
    description=l_("Unmutes all users who were muted by the Raid Mode detector in this chat."),
    example=l_("/raidunmute — lift all raid mutes and let previously joined members speak"),
)
class RaidUnmuteHandler(SophieMessageHandler):
    @staticmethod
    def filters() -> tuple[CallbackType, ...]:
        return (
            CMDFilter(("raidunmute",)),
            UserRestricting(admin=True),
            BotHasPermissions(can_restrict_members=True),
        )

    async def handle(self) -> Any:
        chat = self.connection.db_model
        chat_iid_str = str(chat.iid)
        chat_tid = chat.tid

        muted_users = await get_raid_muted_users(chat_iid_str)

        if not muted_users:
            return await self.event.reply(_("ℹ️ No raid-muted users found for this chat."))

        success = 0
        failed = 0
        for user_tid in muted_users:
            result = await unmute_user(chat_tid=chat_tid, user_tid=user_tid)
            if result:
                success += 1
            else:
                failed += 1

        await clear_raid_muted_users(chat_iid_str)

        if failed:
            await self.event.reply(
                _("✅ Unmuted {success} user(s).\n⚠️ Failed for {failed} user(s) (they may have already left).").format(
                    success=success, failed=failed
                )
            )
        else:
            await self.event.reply(
                _("✅ Successfully unmuted all {count} raid-muted user(s).").format(count=success)
            )
