from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class RaidModeToggleCB(CallbackData, prefix="raidmode_toggle"):
    chat_iid: str
    enabled: bool
