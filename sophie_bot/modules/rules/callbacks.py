from sophie_bot.filters.command_start import CmdStart


class PrivateRulesStartUrlCallback(CmdStart, prefix="pmrules"):
    chat_id: int
