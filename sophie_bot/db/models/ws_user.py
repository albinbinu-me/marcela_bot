from datetime import datetime, timezone
from typing import Optional

from beanie import Document, PydanticObjectId, UpdateResponse
from beanie.odm.operators.update.general import Set

from sophie_bot.db.models import ChatModel
from sophie_bot.db.models._link_type import Link


class WSUserModel(Document):
    user: Link["ChatModel"]
    group: Link["ChatModel"]
    passed: bool = False
    is_join_request: bool = False
    added_at: datetime = datetime.now(timezone.utc)

    class Settings:
        name = "ws_users"

    @staticmethod
    async def ensure_user(user: "ChatModel", group: "ChatModel", is_join_request: bool) -> "WSUserModel":
        """
        Get or create the WS pending record for this user+group pair.
        If a record already exists with passed=True we do NOT overwrite it —
        the user has already completed captcha for this chat.
        """
        existing = await WSUserModel.find_one(
            WSUserModel.user.id == user.iid,
            WSUserModel.group.id == group.iid,
        )
        if existing:
            return existing
        new_record = WSUserModel(user=user, group=group, is_join_request=is_join_request)
        await new_record.insert()
        return new_record

    @staticmethod
    async def mark_passed(user_iid: PydanticObjectId, group_iid: PydanticObjectId) -> Optional["WSUserModel"]:
        """
        Mark the user as having passed captcha WITHOUT deleting the record immediately.
        This prevents a race condition where the scheduler or middleware re-processes
        the user before the record is cleaned up.
        """
        record = await WSUserModel.find_one(WSUserModel.user.id == user_iid, WSUserModel.group.id == group_iid)
        if record:
            record.passed = True
            await record.save()
        return record

    @staticmethod
    async def remove_user(user_iid: PydanticObjectId, group_iid: PydanticObjectId) -> Optional["WSUserModel"]:
        user_in_chat = await WSUserModel.find_one(WSUserModel.user.id == user_iid, WSUserModel.group.id == group_iid)
        if user_in_chat:
            await user_in_chat.delete()
        return user_in_chat

    @staticmethod
    async def is_user(user_iid: PydanticObjectId, group_iid: PydanticObjectId) -> Optional["WSUserModel"]:
        return await WSUserModel.find_one(WSUserModel.user.id == user_iid, WSUserModel.group.id == group_iid)
