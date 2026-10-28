"""HTTP client for the Meta WhatsApp Cloud API.

This adapter implements the `WhatsAppGateway` port. It never retries sends:
a retried POST to /messages can deliver the same message twice.
"""

import logging
from dataclasses import dataclass

import httpx

from app.application.ports import MetaApiError, MetaNetworkError, SendResult, WhatsAppCredentials

log = logging.getLogger(__name__)

_AUTH_CODES = {190, 102, 10, 200}
_RATE_LIMIT_CODES = {4, 80007, 130429, 131048, 131056}
_RECIPIENT_CODES = {131030, 131026, 131021}
_WINDOW_CODES = {131047}


def classify_error(http_status: int, code: int | None) -> str:
    if code in _AUTH_CODES or http_status == 401:
        return "auth"
    if code in _RATE_LIMIT_CODES or http_status == 429:
        return "rate_limit"
    if code in _RECIPIENT_CODES:
        return "recipient"
    if code in _WINDOW_CODES:
        return "window_closed"
    if code is not None and 132000 <= code < 133000:
        return "template"
    return "other"


def _parse_error(response: httpx.Response) -> MetaApiError:
    try:
        error = response.json().get("error", {})
    except ValueError:
        error = {}
    code = error.get("code")
    details = (error.get("error_data") or {}).get("details")
    return MetaApiError(
        http_status=response.status_code,
        code=code,
        kind=classify_error(response.status_code, code),
        title=error.get("type") or "MetaApiError",
        message=details or error.get("message") or f"HTTP {response.status_code} from Meta",
        fbtrace_id=error.get("fbtrace_id"),
    )


@dataclass
class MetaCloudApiClient:
    timeout_seconds: float = 10.0
    transport: httpx.BaseTransport | None = None  # injectable for tests

    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=self.timeout_seconds, transport=self.transport)

    @staticmethod
    def _url(creds: WhatsAppCredentials, path: str) -> str:
        return f"{creds.base_url.rstrip('/')}/{creds.api_version}/{path}"

    def _request(self, method: str, creds: WhatsAppCredentials, path: str, **kwargs) -> dict:
        headers = {"Authorization": f"Bearer {creds.access_token}"}
        try:
            with self._client() as client:
                response = client.request(method, self._url(creds, path), headers=headers, **kwargs)
        except httpx.TimeoutException as exc:
            raise MetaNetworkError("Timed out waiting for Meta.", timeout=True) from exc
        except httpx.HTTPError as exc:
            raise MetaNetworkError(f"Could not reach Meta: {exc.__class__.__name__}", timeout=False) from exc

        if response.status_code >= 400:
            error = _parse_error(response)
            log.warning("Meta API error op=%s status=%s code=%s kind=%s", path, error.http_status, error.code, error.kind)
            raise error
        try:
            return response.json()
        except ValueError as exc:
            raise MetaNetworkError("Meta returned an unreadable response.", timeout=False) from exc

    def send_message(self, creds: WhatsAppCredentials, payload: dict) -> SendResult:
        data = self._request("POST", creds, f"{creds.phone_number_id}/messages", json=payload)
        messages = data.get("messages") or []
        if not messages or "id" not in messages[0]:
            raise MetaNetworkError("Meta response did not include a message id.", timeout=False)
        contacts = data.get("contacts") or [{}]
        return SendResult(
            message_id=messages[0]["id"],
            wa_id=contacts[0].get("wa_id"),
            message_status=messages[0].get("message_status"),
        )

    def get_phone_number(self, creds: WhatsAppCredentials) -> dict:
        return self._request(
            "GET",
            creds,
            creds.phone_number_id,
            params={"fields": "display_phone_number,verified_name,quality_rating,code_verification_status"},
        )
