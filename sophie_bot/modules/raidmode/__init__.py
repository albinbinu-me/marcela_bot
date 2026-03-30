from aiogram import Router
from stfu_tg import Doc

from sophie_bot.utils.i18n import LazyProxy
from sophie_bot.utils.i18n import lazy_gettext as l_

from .handlers.raidmode import RaidModeHandler, RaidModeToggleCallbackHandler, RaidMuteDurationHandler
from .middlewares.raid_detector import RaidDetectorMiddleware

router = Router(name="raidmode")

__module_name__ = l_("Raid Mode")
__module_emoji__ = "🚨"
__module_description__ = l_("Automatically detect and stop member join floods (raids).")
__module_info__ = LazyProxy(
    lambda: Doc(
        l_(
            "Raid Mode monitors new member joins. When a flood of joins is detected within a short window, "
            "new joiners are automatically muted and admins are alerted. "
            "You can also manually enable Raid Mode with /raidmode on to block all new joiners until you disable it."
        )
    )
)

__handlers__ = (
    RaidModeHandler,
    RaidMuteDurationHandler,
    RaidModeToggleCallbackHandler,
)


async def __pre_setup__() -> None:
    # Attach the raid detector to chat_member events on the module router
    router.chat_member.outer_middleware(RaidDetectorMiddleware())
