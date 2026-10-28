import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.context import TenantContext
from app.application.dto import TestRecipientCommand
from app.application.ports import CredentialProvider, MetaApiError, MetaNetworkError, WhatsAppGateway
from app.application.whatsapp.templates import template_registry
from app.core.config import Settings
from app.core.security import mask_secret
from app.domain.clock import utcnow
from app.domain.enums import MANAGER_ROLES, CredentialSource
from app.domain.errors import ConfigurationError, ConflictError
from app.domain.phone import normalize_phone
from app.infrastructure.db.models import WhatsAppApiErrorLog, WhatsAppConfiguration, WhatsAppTestRecipient
from app.infrastructure.repositories.whatsapp import (
    ApiErrorLogRepository,
    TestRecipientRepository,
    WhatsAppConfigRepository,
)

log = logging.getLogger(__name__)


def log_api_error(session: Session, business_id: int, operation: str, exc: Exception) -> None:
    """Persist an API failure for the settings page (no tokens or message bodies are stored)."""
    if isinstance(exc, MetaApiError):
        entry = WhatsAppApiErrorLog(business_id=business_id, operation=operation, http_status=exc.http_status,
                                    error_code=str(exc.code) if exc.code is not None else None,
                                    error_kind=exc.kind, message=exc.message[:2000], fbtrace_id=exc.fbtrace_id)
    else:
        entry = WhatsAppApiErrorLog(business_id=business_id, operation=operation, error_kind="network",
                                    message=str(getattr(exc, "message", exc))[:2000])
    session.add(entry)


class WhatsAppSettingsService:
    def __init__(self, session: Session, ctx: TenantContext, settings: Settings, gateway: WhatsAppGateway,
                 credentials: CredentialProvider):
        self.session = session
        self.ctx = ctx
        self.settings = settings
        self.gateway = gateway
        self.credentials = credentials
        self.configs = WhatsAppConfigRepository(session, ctx.business_id)
        self.recipients = TestRecipientRepository(session, ctx.business_id)

    def view(self) -> dict:
        config = self.configs.current()
        env = self.credentials.env_status()
        connected = bool(
            config and config.is_enabled and config.last_check_ok and self.settings.meta_env_credentials_present
        )
        if not config:
            state = "not_connected"
        elif connected:
            state = "connected"
        elif config.last_check_ok is False:
            state = "check_failed"
        else:
            state = "pending_check"
        return {
            "state": state,
            "connected": connected,
            "environment": {**env, "access_token_masked": mask_secret(self.settings.meta_access_token)},
            "configuration": config,
            "webhook": {
                "callback_path": "/webhooks/whatsapp/",
                "verify_token_configured": bool(self.settings.meta_verify_token),
                "app_secret_configured": bool(self.settings.meta_app_secret),
                "verified_at": config.webhook_verified_at if config else None,
                "last_event_at": config.last_webhook_at if config else None,
            },
            "templates": [
                {"kind": t.kind.value, "template_name": t.template_name or None, "language": t.language,
                 "configured": t.is_configured, "body": t.body}
                for t in template_registry(self.settings).values()
            ],
            "test_recipients": self.recipients.all(),
            "recent_errors": ApiErrorLogRepository(self.session, self.ctx.business_id).recent(10),
        }

    def connect_environment_number(self) -> WhatsAppConfiguration:
        self.ctx.require(*MANAGER_ROLES)
        if not self.settings.meta_env_credentials_present:
            raise ConfigurationError(
                "The server has no WhatsApp credentials. Set META_ACCESS_TOKEN and META_PHONE_NUMBER_ID."
            )
        existing = self.configs.current()
        if existing:
            return existing
        taken = self.session.scalar(select(WhatsAppConfiguration.business_id).where(
            WhatsAppConfiguration.phone_number_id == self.settings.meta_phone_number_id))
        if taken:
            raise ConflictError("This WhatsApp number is already linked to another business.",
                                code="phone_number_in_use")
        config = WhatsAppConfiguration(
            phone_number_id=self.settings.meta_phone_number_id, waba_id=self.settings.meta_waba_id or None,
            mode=self.settings.meta_mode, credential_source=CredentialSource.ENVIRONMENT.value,
        )
        self.configs.add(config)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("This WhatsApp number is already linked to another business.",
                                code="phone_number_in_use") from exc
        return config

    def disconnect(self) -> None:
        self.ctx.require(*MANAGER_ROLES)
        config = self.configs.current()
        if config:
            self.session.delete(config)
            self.session.commit()

    def check_connection(self) -> WhatsAppConfiguration:
        """Calls Meta to confirm the token and phone number id work. Only a success marks the business connected."""
        self.ctx.require(*MANAGER_ROLES)
        config = self.configs.current()
        if not config:
            raise ConfigurationError("Connect WhatsApp first.")
        config.last_check_at = utcnow()
        try:
            creds = self.credentials.for_configuration(config)
            info = self.gateway.get_phone_number(creds)
        except ConfigurationError as exc:
            config.last_check_ok, config.last_check_error = False, exc.message
        except (MetaApiError, MetaNetworkError) as exc:
            config.last_check_ok, config.last_check_error = False, exc.message
            log_api_error(self.session, self.ctx.business_id, "connection_check", exc)
        else:
            config.last_check_ok, config.last_check_error = True, None
            config.display_phone_number = info.get("display_phone_number")
            config.verified_name = info.get("verified_name")
        self.session.commit()
        return config

    def add_test_recipient(self, cmd: TestRecipientCommand) -> WhatsAppTestRecipient:
        self.ctx.require(*MANAGER_ROLES)
        phone = normalize_phone(cmd.phone)
        if phone in self.recipients.phones():
            raise ConflictError("This number is already an authorized test recipient.")
        recipient = WhatsAppTestRecipient(phone=phone, label=cmd.label)
        self.recipients.add(recipient)
        self.session.commit()
        return recipient

    def remove_test_recipient(self, recipient_id: int) -> None:
        self.ctx.require(*MANAGER_ROLES)
        recipient = self.recipients.get_or_raise(recipient_id)
        self.session.delete(recipient)
        self.session.commit()
