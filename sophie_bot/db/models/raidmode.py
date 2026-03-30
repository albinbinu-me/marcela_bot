from __future__ import annotations

from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field

from sophie_bot.db.models._link_type import Link
from sophie_bot.db.models.chat import ChatModel


class RaidModeModel(Document):
    chat: Link[ChatModel]

    enabled: bool = False
    # Threshold: how many joins within window_seconds trigger auto raid mode
    threshold: int = 15
    window_seconds: int = 60
    # When raid mode auto-activates, mute new joiners for this many minutes (0 = indefinite)
    auto_mute_minutes: int = 60

    class Settings:
        name = "raidmode"

    @staticmethod
    async def get_by_chat_iid(chat_iid: PydanticObjectId) -> "RaidModeModel":
        return await RaidModeModel.find_one(RaidModeModel.chat.id == chat_iid) or RaidModeModel(chat=chat_iid)

    async def set_enabled(self, enabled: bool) -> "RaidModeModel":
        self.enabled = enabled
        return await self.save()
