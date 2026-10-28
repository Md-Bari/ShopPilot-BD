from app.application.ports import WhatsAppCredentials
from app.core.config import Settings
from app.domain.enums import CredentialSource, WhatsAppMode
from app.domain.errors import ConfigurationError
from app.infrastructure.db.models import WhatsAppConfiguration


class SettingsCredentialProvider:
    """MVP credential provider: the single test number configured in environment variables.

    A future `EncryptedCredentialProvider` can serve per-business tokens stored encrypted
    in the database, selected by `WhatsAppConfiguration.credential_source`.
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    def env_status(self) -> dict:
        s = self.settings
        return {
            "access_token_present": bool(s.meta_access_token),
            "phone_number_id": s.meta_phone_number_id or None,
            "waba_id": s.meta_waba_id or None,
            "app_secret_present": bool(s.meta_app_secret),
            "verify_token_present": bool(s.meta_verify_token),
            "api_version": s.meta_graph_api_version,
            "mode": s.meta_mode,
        }

    def for_configuration(self, config: WhatsAppConfiguration) -> WhatsAppCredentials:
        if config.credential_source != CredentialSource.ENVIRONMENT.value:
            raise ConfigurationError("Per-business WhatsApp credentials are not supported yet.")
        s = self.settings
        if not s.meta_env_credentials_present:
            raise ConfigurationError("META_ACCESS_TOKEN and META_PHONE_NUMBER_ID are not configured on the server.")
        if config.phone_number_id != s.meta_phone_number_id:
            raise ConfigurationError(
                "This business is linked to a phone number id that no longer matches the server configuration."
            )
        return WhatsAppCredentials(
            access_token=s.meta_access_token,
            phone_number_id=s.meta_phone_number_id,
            waba_id=s.meta_waba_id or None,
            api_version=s.meta_graph_api_version,
            base_url=s.meta_graph_base_url,
            mode=WhatsAppMode(s.meta_mode),
        )
