from aiogram import Router
from stfu_tg import Doc

from sophie_bot.utils.i18n import LazyProxy
from sophie_bot.utils.i18n import lazy_gettext as l_

from .handlers.raidmode import RaidModeHandler, RaidModeToggleCallbackHandler, RaidMuteDurationHandler
from .handlers.raidmode_pm import RaidModePMHandler, RaidMuteDurationPMHandler
from .handlers.raidunmute import RaidUnmuteHandler
from .middlewares.raid_detector import RaidDetectorMiddleware

router = Router(name="raidmode")

__module_name__ = l_("Raid Mode")
__module_emoji__ = "🚨"
__module_description__ = l_("Automatically detect and stop member join floods (raids).")
__module_info__ = LazyProxy(
    lambda: Doc(
        l_(
            "Raid Mode monitors new member joins. When a flood of joins is detected within a short window, "
            "new joiners are automatically muted and admins are alerted.\n\n"
            "Commands:\n"
            "• /raidmode on|off — manually enable or disable Raid Mode\n"
            "• /raidmute <minutes> — set how long new joiners are muted (0 = indefinite)\n"
            "• /raidunmute — lift all mutes placed during the last raid at once"
        )
    )
)

__handlers__ = (
    RaidModeHandler,
    RaidMuteDurationHandler,
    RaidModePMHandler,
    RaidMuteDurationPMHandler,
    RaidModeToggleCallbackHandler,
    RaidUnmuteHandler,
)


async def __pre_setup__() -> None:
    # Attach the raid detector to chat_member events on the module router
    router.chat_member.outer_middleware(RaidDetectorMiddleware())
