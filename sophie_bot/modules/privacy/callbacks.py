from aiogram.filters.callback_data import CallbackData


class PrivacyMenuCallback(CallbackData, prefix="privacy"):
    back_to_start: bool = False


class PrivacyPolicyCallback(CallbackData, prefix="privacy_policy"):
    pass


class PrivacyPolicySectionCallback(CallbackData, prefix="privacy_section"):
    section: str


class PrivacyRetrieveDataCallback(CallbackData, prefix="privacy_retrieve"):
    pass


class PrivacyDeleteDataCallback(CallbackData, prefix="privacy_delete"):
    pass
