# Re-export from new location for backwards compatibility
# TODO: Update all imports to use sophie_bot.utils.handlers directly

from sophie_bot.utils.handlers import (
    SophieBaseHandler as MacelaBaseHandler,
    SophieCallbackQueryHandler as MacelaCallbackQueryHandler,
    SophieMessageCallbackQueryHandler as MacelaMessageCallbackQueryHandler,
    SophieMessageHandler as MacelaMessageHandler,
)

__all__ = [
    "MacelaBaseHandler",
    "MacelaCallbackQueryHandler",
    "MacelaMessageCallbackQueryHandler",
    "MacelaMessageHandler",
]
