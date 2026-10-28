"""Ports (interfaces) the application layer depends on. Infrastructure provides the adapters."""

from dataclasses import dataclass
from typing import Protocol

from app.domain.enums import WhatsAppMode


@dataclass(frozen=True)
class WhatsAppCredentials:
    access_token: str
    phone_number_id: str
    waba_id: str | None
    api_version: str
    base_url: str
    mode: WhatsAppMode


@dataclass(frozen=True)
class SendResult:
    message_id: str
    wa_id: str | None = None
    message_status: str | None = None


class MetaApiError(Exception):
    def __init__(
        self,
        *,
        http_status: int,
        code: int | None,
        kind: str,
        title: str,
        message: str,
        fbtrace_id: str | None = None,
    ):
        super().__init__(message)
        self.http_status = http_status
        self.code = code
        self.kind = kind  # auth | rate_limit | recipient | window_closed | template | other
        self.title = title
        self.message = message
        self.fbtrace_id = fbtrace_id


class MetaNetworkError(Exception):
    def __init__(self, message: str, *, timeout: bool):
        super().__init__(message)
        self.message = message
        self.timeout = timeout


class WhatsAppGateway(Protocol):
    def send_message(self, creds: WhatsAppCredentials, payload: dict) -> SendResult: ...

    def get_phone_number(self, creds: WhatsAppCredentials) -> dict: ...


class CredentialProvider(Protocol):
    def for_configuration(self, config) -> WhatsAppCredentials: ...

    def env_status(self) -> dict: ...


class EmailSender(Protocol):
    def send(self, *, to: str, subject: str, body: str) -> None: ...


class FileStorage(Protocol):
    def save(self, *, folder: str, filename: str, data: bytes) -> str:
        """Persist the file and return its relative path."""
        ...

    def delete(self, path: str) -> None: ...

    def url_for(self, path: str | None) -> str | None: ...
