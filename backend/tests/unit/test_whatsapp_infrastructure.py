"""Payload construction, signature validation and the Meta HTTP client (mocked with respx)."""

import httpx
import pytest
import respx

from app.application.ports import MetaApiError, MetaNetworkError, WhatsAppCredentials
from app.application.whatsapp.templates import format_bdt, order_parameters, template_registry
from app.core.config import Settings
from app.domain.enums import NotificationKind, WhatsAppMode
from app.infrastructure.whatsapp.meta_client import MetaCloudApiClient, classify_error
from app.infrastructure.whatsapp.payloads import build_template_payload, build_text_payload
from app.infrastructure.whatsapp.signature import compute_signature, verify_signature

CREDS = WhatsAppCredentials(access_token="TOKEN", phone_number_id="123", waba_id=None, api_version="v21.0",
                            base_url="https://graph.example.com", mode=WhatsAppMode.TEST)
MESSAGES_URL = "https://graph.example.com/v21.0/123/messages"


def test_text_payload():
    assert build_text_payload("8801712345678", "Hello") == {
        "messaging_product": "whatsapp", "recipient_type": "individual", "to": "8801712345678",
        "type": "text", "text": {"preview_url": False, "body": "Hello"},
    }


def test_template_payload_with_and_without_parameters():
    payload = build_template_payload("8801712345678", "order_confirmation", "en", ["SP-1001", "1,250", "Shop"])
    assert payload["type"] == "template"
    assert payload["template"]["name"] == "order_confirmation"
    assert payload["template"]["language"] == {"code": "en"}
    assert payload["template"]["components"] == [{"type": "body", "parameters": [
        {"type": "text", "text": "SP-1001"}, {"type": "text", "text": "1,250"}, {"type": "text", "text": "Shop"}]}]
    assert "components" not in build_template_payload("1", "hello_world", "en_US")["template"]


def test_order_confirmation_text_uses_real_values():
    template = template_registry(Settings(_env_file=None))[NotificationKind.ORDER_CONFIRMED]
    params = order_parameters(NotificationKind.ORDER_CONFIRMED, order_number="SP-1001", total=1250,
                              amount_due=1250, business_name="us")
    assert template.render(params) == (
        "Assalamu Alaikum! Your order #SP-1001 has been confirmed. Total: ৳1,250. Thank you for shopping with us."
    )
    assert format_bdt(1250.5) == "1,250.50"


def test_signature():
    body = b'{"a":1}'
    header = compute_signature("secret", body)
    assert verify_signature("secret", body, header)
    assert not verify_signature("secret", body + b" ", header)
    assert not verify_signature("other", body, header)
    assert not verify_signature("secret", body, None)
    assert not verify_signature("", body, header)
    assert not verify_signature("secret", body, "md5=abc")


@respx.mock
def test_send_success_returns_message_id():
    route = respx.post(MESSAGES_URL).mock(return_value=httpx.Response(200, json={
        "messaging_product": "whatsapp", "contacts": [{"input": "880", "wa_id": "8801712345678"}],
        "messages": [{"id": "wamid.ABC", "message_status": "accepted"}]}))
    result = MetaCloudApiClient().send_message(CREDS, build_text_payload("8801712345678", "Hi"))
    assert result.message_id == "wamid.ABC"
    assert route.calls[0].request.headers["Authorization"] == "Bearer TOKEN"


@respx.mock
@pytest.mark.parametrize("status,code,kind", [
    (401, 190, "auth"),
    (400, 131030, "recipient"),
    (429, 130429, "rate_limit"),
    (400, 132001, "template"),
    (400, 131047, "window_closed"),
])
def test_meta_errors_are_classified(status, code, kind):
    respx.post(MESSAGES_URL).mock(return_value=httpx.Response(status, json={"error": {
        "message": "boom", "type": "OAuthException", "code": code,
        "error_data": {"details": "Detailed reason"}, "fbtrace_id": "TRACE"}}))
    with pytest.raises(MetaApiError) as exc:
        MetaCloudApiClient().send_message(CREDS, {})
    assert exc.value.kind == kind
    assert exc.value.message == "Detailed reason"
    assert exc.value.fbtrace_id == "TRACE"


@respx.mock
def test_timeout_raises_network_error_without_retry():
    route = respx.post(MESSAGES_URL).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(MetaNetworkError) as exc:
        MetaCloudApiClient().send_message(CREDS, {})
    assert exc.value.timeout is True
    assert route.call_count == 1


def test_classify_error_fallback():
    assert classify_error(500, None) == "other"
