from __future__ import annotations

from beanie import Document, PydanticObjectId

from sophie_bot.db.models._link_type import Link
from sophie_bot.db.models.chat import ChatModel


class PrivateRulesModel(Document):
    chat: Link[ChatModel]

    class Settings:
        name = "privaterules"

    @staticmethod
    async def get_state(chat_iid: PydanticObjectId) -> bool:
        return bool(await PrivateRulesModel.find_one(PrivateRulesModel.chat.id == chat_iid))

    @staticmethod
    async def set_state(chat_iid: PydanticObjectId, new_state: bool) -> None:
        model = await PrivateRulesModel.find_one(PrivateRulesModel.chat.id == chat_iid)
        if model and not new_state:
            await model.delete()
            return
        if model:
            return
        new_model = PrivateRulesModel(chat=chat_iid)
        await new_model.save()
