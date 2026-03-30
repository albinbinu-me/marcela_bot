from aiogram.filters.callback_data import CallbackData

from sophie_bot.filters.command_start import CmdStart


class PMHelpModule(CallbackData, prefix="pmhelpmod"):
    module_name: str
    back_to_start: bool = False


class PMHelpModules(CallbackData, prefix="pmhelpback"):
    back_to_start: bool = False


class PMHelpStartUrlCallback(CmdStart, prefix="help"):
    pass


class PMHelpQueryStartUrlCallback(CmdStart, prefix="helpq"):
    query: str


class PMHelpCommandExample(CallbackData, prefix="pmhelpexample"):
    cmd: str  # primary command name, used to look up the handler


class PMHelpModuleExamples(CallbackData, prefix="pmhelpmodex"):
    module_name: str  # show all examples for all commands in this module
