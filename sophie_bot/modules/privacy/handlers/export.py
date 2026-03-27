from datetime import datetime
from types import ModuleType
from typing import Any

from aiogram import flags
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from beanie import PydanticObjectId
from ujson import dumps

from sophie_bot.middlewares.connections import ChatConnection
from sophie_bot.utils.i18n import gettext as _
from sophie_bot.utils.i18n import lazy_gettext as l_
from sophie_bot.services.redis import aredis
from aiogram.handlers import BaseHandler

VERSION = 6

EXPORTABLE_MODULES: list[ModuleType] = []


def text_to_buffered_file(text: str, filename: str = "data.txt") -> BufferedInputFile:
    return BufferedInputFile(text.encode(), filename=filename)


@flags.help(description=l_("Exports your data to a JSON file"))
class TriggerExport(BaseHandler[Message | CallbackQuery]):
    @staticmethod
    async def get_data(chat_iid: PydanticObjectId) -> list[dict[str, Any]]:
        return list(
            filter(
                None,
                [await module.__export__(chat_iid) for module in EXPORTABLE_MODULES if hasattr(module, "__export__")],
            )
        )

    async def handle(self) -> Any:
        connection: ChatConnection = self.data["connection"]
        user_id = connection.tid

        cooldown_key = f"export_cooldown:{user_id}"
        if await aredis.get(cooldown_key):
            text = _("You can only retrieve your data once every 48 hours. Please wait.")
            if isinstance(self.event, CallbackQuery):
                return await self.event.answer(text, show_alert=True)
            return await self.event.reply(text)

        if isinstance(self.event, CallbackQuery):
            await self.event.answer(_("Export is started, this may take a while."), show_alert=False)
        else:
            await self.event.reply(_("Export is started, this may take a while."))

        from sophie_bot.db.models.chat import UserInGroupModel
        from sophie_bot.config import CONFIG

        user = self.event.from_user
        if not user:
            return

        common_groups = []
        if connection.db_model:
            db_user_in_groups = await UserInGroupModel.find(
                UserInGroupModel.user.id == connection.db_model.iid, fetch_links=True
            ).to_list()
            common_groups = [g.group.tid for g in db_user_in_groups if g.group]

        now = datetime.now()
        data = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "userid": user.id,
            "generated_time": now.strftime("%H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "common_group_ids": common_groups,
            "is_owner": (user.id == CONFIG.owner_id),
        }

        modules_data = await self.get_data(connection.db_model.iid)

        for module_data in modules_data:
            data.update(module_data)

        jfile = text_to_buffered_file(dumps(data, indent=2), filename="user_data.txt")
        text = _("Export is done.")

        if isinstance(self.event, CallbackQuery):
            if isinstance(self.event.message, Message):
                await self.event.message.answer_document(jfile, caption=text)
        elif isinstance(self.event, Message):
            await self.event.reply_document(jfile, caption=text)

        await aredis.setex(cooldown_key, 172800, "1")


class TriggerDeleteData(BaseHandler[Message | CallbackQuery]):
    async def handle(self) -> Any:
        connection: ChatConnection = self.data["connection"]
        user_id = connection.tid

        cooldown_key = f"delete_cooldown:{user_id}"
        if await aredis.get(cooldown_key):
            text = _("You can only request data deletion once every 96 hours. Please wait.")
            if isinstance(self.event, CallbackQuery):
                return await self.event.answer(text, show_alert=True)
            return await self.event.reply(text)

        if hasattr(connection.db_model, "delete_chat"):
            await connection.db_model.delete_chat()
        else:
            await connection.db_model.delete()

        await aredis.setex(cooldown_key, 345600, "1")

        text = _("Your data has been successfully deleted from our backend.")
        if isinstance(self.event, CallbackQuery):
            return await self.event.answer(text, show_alert=True)
        return await self.event.reply(text)
