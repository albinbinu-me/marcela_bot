from sophie_bot.db.models import ChatModel, WSUserModel
from sophie_bot.db.models.greetings import WelcomeMute
from sophie_bot.modules.restrictions.utils.restrictions import unmute_user
from sophie_bot.modules.utils_.admin import is_user_admin
from sophie_bot.modules.welcomesecurity.utils_.db_time_convert import (
    convert_timedelta_or_str,
)
from sophie_bot.modules.welcomesecurity.utils_.welcomemute import on_welcomemute


async def ws_on_user_passed(user: ChatModel, group: ChatModel, welcomemute: WelcomeMute) -> bool:
    """
    Called when the user successfully passes welcome security (captcha + rules).

    Steps:
    1. Skip if the user is an admin.
    2. Mark the WS record as passed=True FIRST — this stops LockMutedUsers and
       BanUnpassedUsers from acting on this user during the unmute window.
    3. Fully unmute the user — clears the captcha mute unconditionally.
    4. Delete the WS record from the database.
    5. If WelcomeMute is enabled, re-apply a partial time-limited restriction
       (text only, no media) for the configured duration.

    Returns True if the flow ran, False if skipped (admin).
    """

    # Guard: admins should never be in the WS queue, but be safe
    if await is_user_admin(chat=group.tid, user=user.tid):
        return False

    # Mark as passed BEFORE unmuting — prevents scheduler/middleware from re-acting
    # on this user while the unmute API call is in-flight
    await WSUserModel.mark_passed(user.iid, group.iid)

    # Always fully unmute — captcha completion = full access restored
    await unmute_user(chat_tid=group.tid, user_tid=user.tid)

    # Now safe to delete the record
    await WSUserModel.remove_user(user.iid, group.iid)

    # Optionally apply a post-captcha welcome_mute (media restriction only, text allowed)
    if welcomemute.enabled and welcomemute.time:
        await on_welcomemute(group.tid, user.tid, on_time=convert_timedelta_or_str(welcomemute.time))

    return True
