"""WhatsApp settings, sending, notifications, webhooks and inbox. Meta is mocked with respx."""

import json
from datetime import timedelta

import httpx
import pytest
import respx
from sqlalchemy import select, update

from app.domain.clock import utcnow
from app.infrastructure.db.models import (
    WebhookEvent,
    WhatsAppApiErrorLog,
    WhatsAppConversation,
    WhatsAppMessage,
)
from tests.conftest import (
    META_BASE,
    PHONE_NUMBER_ID,
    create_order,
    create_product,
    inbound_message_payload,
    post_webhook,
    sign,
    status_payload,
)

MESSAGES_URL = f"{META_BASE}/v21.0/{PHONE_NUMBER_ID}/messages"
PHONE_URL = f"{META_BASE}/v21.0/{PHONE_NUMBER_ID}"
CUSTOMER_PHONE = "+8801712345678"


def meta_ok(message_id="wamid.OUT1"):
    return httpx.Response(200, json={"messaging_product": "whatsapp",
                                     "contacts": [{"input": "8801712345678", "wa_id": "8801712345678"}],
                                     "messages": [{"id": message_id}]})


@pytest.fixture
def meta():
    with respx.mock(assert_all_called=False) as mock:
        mock.get(PHONE_URL).mock(return_value=httpx.Response(200, json={
            "display_phone_number": "+1 555-000-1111", "verified_name": "Test Number", "id": PHONE_NUMBER_ID}))
        yield mock


@pytest.fixture
def connected(api, meta):
    res = api.post("/api/whatsapp/settings/connect")
    assert res.status_code == 200, res.text
    assert res.json()["state"] == "connected"
    assert api.post("/api/whatsapp/test-recipients", json={"phone": "01712345678"}).status_code == 201
    return api


def read_status(db) -> str:
    status = db.scalar(select(WhatsAppMessage.status))
    db.rollback()  # end the read transaction; tests share one SQLite connection with the app
    return status


def customer_with_consent(api, phone="01712345678"):
    cid = api.post("/api/customers", json={"name": "Rahim", "phone": phone}).json()["id"]
    api.post(f"/api/customers/{cid}/consents", json={"status": "granted", "source": "facebook"})
    return cid


class TestSettings:
    def test_not_connected_by_default_and_token_masked(self, api):
        view = api.get("/api/whatsapp/settings").json()
        assert view["state"] == "not_connected" and view["connected"] is False
        masked = view["environment"]["access_token_masked"]
        assert "EAATESTTOKEN1234567890" not in json.dumps(view)
        assert masked.endswith("7890") and masked.startswith("*")

    def test_failed_check_is_not_connected(self, api):
        with respx.mock:
            respx.get(PHONE_URL).mock(return_value=httpx.Response(401, json={"error": {
                "message": "Error validating access token", "type": "OAuthException", "code": 190}}))
            view = api.post("/api/whatsapp/settings/connect").json()
        assert view["state"] == "check_failed" and view["connected"] is False
        assert view["recent_errors"][0]["error_kind"] == "auth"

    def test_phone_number_can_only_link_one_business(self, connected, make_api, meta):
        other = make_api("other@example.com", "Other")
        res = other.post("/api/whatsapp/settings/connect")
        assert res.status_code == 409 and res.json()["error"]["code"] == "phone_number_in_use"


class TestSending:
    def test_requires_connection(self, api):
        customer_with_consent(api)
        res = api.post("/api/whatsapp/messages/send-template/", json={
            "to": CUSTOMER_PHONE, "template_name": "hello_world", "language": "en_US"})
        assert res.status_code == 409 and res.json()["error"]["code"] == "not_configured"

    def test_template_send_success(self, connected, meta, db):
        customer_with_consent(connected)
        route = meta.post(MESSAGES_URL).mock(return_value=meta_ok())
        res = connected.post("/api/whatsapp/messages/send-template/", json={
            "to": "01712345678", "template_name": "hello_world", "language": "en_US"},
            headers={"Idempotency-Key": "key-1"})
        assert res.status_code == 200, res.text
        assert res.json()["message"]["status"] == "accepted"
        sent = json.loads(route.calls[0].request.content)
        assert sent["to"] == "8801712345678" and sent["template"]["name"] == "hello_world"
        assert db.scalar(select(WhatsAppMessage.wa_message_id)) == "wamid.OUT1"

    def test_idempotency_key_prevents_duplicate_send(self, connected, meta):
        customer_with_consent(connected)
        route = meta.post(MESSAGES_URL).mock(return_value=meta_ok())
        body = {"to": CUSTOMER_PHONE, "template_name": "hello_world", "language": "en_US"}
        first = connected.post("/api/whatsapp/messages/send-template/", json=body, headers={"Idempotency-Key": "same"})
        second = connected.post("/api/whatsapp/messages/send-template/", json=body, headers={"Idempotency-Key": "same"})
        assert first.json()["replayed"] is False and second.json()["replayed"] is True
        assert first.json()["message"]["id"] == second.json()["message"]["id"]
        assert route.call_count == 1

    def test_template_requires_consent(self, connected, meta):
        connected.post("/api/customers", json={"name": "No Consent", "phone": "01712345678"})
        route = meta.post(MESSAGES_URL).mock(return_value=meta_ok())
        res = connected.post("/api/whatsapp/messages/send-template/", json={
            "to": CUSTOMER_PHONE, "template_name": "hello_world"})
        assert res.status_code == 422 and res.json()["error"]["code"] == "messaging_policy_violation"
        assert route.call_count == 0

    def test_free_text_blocked_outside_service_window(self, connected, meta):
        customer_with_consent(connected)
        route = meta.post(MESSAGES_URL).mock(return_value=meta_ok())
        res = connected.post("/api/whatsapp/messages/send/", json={"to": CUSTOMER_PHONE, "text": "Hello"})
        assert res.status_code == 422 and "24-hour" in res.json()["error"]["message"]
        assert route.call_count == 0

    def test_free_text_allowed_inside_window(self, connected, meta):
        customer_with_consent(connected)
        assert post_webhook(connected, inbound_message_payload()).status_code == 200
        meta.post(MESSAGES_URL).mock(return_value=meta_ok())
        res = connected.post("/api/whatsapp/messages/send/", json={"to": CUSTOMER_PHONE, "text": "Yes, available!"})
        assert res.status_code == 200, res.text

    def test_test_mode_recipient_restriction(self, connected, meta):
        customer_with_consent(connected, phone="01812345678")  # not an authorized test recipient
        route = meta.post(MESSAGES_URL).mock(return_value=meta_ok())
        res = connected.post("/api/whatsapp/messages/send-template/", json={
            "to": "01812345678", "template_name": "hello_world"})
        assert res.status_code == 422 and "Test mode" in res.json()["error"]["message"]
        assert route.call_count == 0

    def test_unknown_recipient_rejected(self, connected, meta):
        res = connected.post("/api/whatsapp/messages/send-template/", json={
            "to": "01912345678", "template_name": "hello_world"})
        assert res.status_code == 404 and res.json()["error"]["code"] == "unknown_recipient"

    def test_cannot_message_other_tenants_customer(self, connected, make_api, meta):
        cid = customer_with_consent(connected)
        other = make_api("other@example.com", "Other")
        res = other.post("/api/whatsapp/messages/send-template/", json={"customer_id": cid,
                                                                        "template_name": "hello_world"})
        assert res.status_code == 404

    def test_meta_auth_error_marks_failed_and_logs(self, connected, meta, db):
        customer_with_consent(connected)
        meta.post(MESSAGES_URL).mock(return_value=httpx.Response(401, json={"error": {
            "message": "Invalid OAuth access token.", "type": "OAuthException", "code": 190, "fbtrace_id": "T1"}}))
        res = connected.post("/api/whatsapp/messages/send-template/", json={
            "to": CUSTOMER_PHONE, "template_name": "hello_world"})
        assert res.status_code == 502 and res.json()["error"]["code"] == "meta_auth"
        message = db.scalar(select(WhatsAppMessage))
        assert message.status == "failed" and message.error_code == "190"
        assert db.scalar(select(WhatsAppApiErrorLog.error_kind).where(
            WhatsAppApiErrorLog.operation == "send_message")) == "auth"

    def test_meta_rate_limit_maps_to_429(self, connected, meta):
        customer_with_consent(connected)
        meta.post(MESSAGES_URL).mock(return_value=httpx.Response(429, json={"error": {
            "message": "Too many messages", "code": 130429}}))
        res = connected.post("/api/whatsapp/messages/send-template/", json={
            "to": CUSTOMER_PHONE, "template_name": "hello_world"})
        assert res.status_code == 429

    def test_timeout_marks_unknown_without_retry(self, connected, meta, db):
        customer_with_consent(connected)
        route = meta.post(MESSAGES_URL).mock(side_effect=httpx.ReadTimeout("slow"))
        res = connected.post("/api/whatsapp/messages/send-template/", json={
            "to": CUSTOMER_PHONE, "template_name": "hello_world"})
        assert res.status_code == 502 and res.json()["error"]["code"] == "delivery_unknown"
        assert route.call_count == 1
        assert db.scalar(select(WhatsAppMessage.status)) == "unknown"


class TestOrderNotifications:
    def _order(self, api, status=None):
        variant = create_product(api, price="1190")["variants"][0]
        order = create_order(api, variant["id"])  # total 1250
        for s in status or []:
            api.post(f"/api/orders/{order['id']}/status", json={"status": s})
        return order

    def test_preview_uses_real_order_data(self, connected, meta):
        order = self._order(connected, ["confirmed"])
        cid = order["customer"]["id"]
        preview = connected.get(f"/api/orders/{order['id']}/notifications/preview",
                                params={"kind": "order_confirmed"}).json()
        assert preview["text"] == ("Assalamu Alaikum! Your order #SP-1001 has been confirmed. Total: ৳1,250. "
                                   "Thank you for shopping with Dhaka Boutique.")
        assert preview["channel"] == "template" and preview["template_name"] == "order_confirmation"
        assert preview["can_send"] is False  # no consent yet
        connected.post(f"/api/customers/{cid}/consents", json={"status": "granted", "source": "in_person"})
        preview = connected.get(f"/api/orders/{order['id']}/notifications/preview",
                                params={"kind": "order_confirmed"}).json()
        assert preview["can_send"] is True, preview["blockers"]

    def test_notification_must_match_order_status(self, connected, meta):
        order = self._order(connected)  # still pending
        preview = connected.get(f"/api/orders/{order['id']}/notifications/preview",
                                params={"kind": "order_shipped"}).json()
        assert any("current status" in b for b in preview["blockers"])

    def test_send_confirmation_links_message_to_order(self, connected, meta):
        order = self._order(connected, ["confirmed"])
        connected.post(f"/api/customers/{order['customer']['id']}/consents",
                       json={"status": "granted", "source": "in_person"})
        route = meta.post(MESSAGES_URL).mock(return_value=meta_ok("wamid.ORDER"))
        res = connected.post(f"/api/orders/{order['id']}/notifications", json={"kind": "order_confirmed"},
                             headers={"Idempotency-Key": "order-1-confirm"})
        assert res.status_code == 200, res.text
        params = json.loads(route.calls[0].request.content)["template"]["components"][0]["parameters"]
        assert [p["text"] for p in params] == ["SP-1001", "1,250", "Dhaka Boutique"]
        detail = connected.get(f"/api/orders/{order['id']}").json()
        assert detail["messages"][0]["notification_kind"] == "order_confirmed"

    def test_custom_message_requires_service_window(self, connected, meta):
        order = self._order(connected)
        res = connected.post(f"/api/orders/{order['id']}/notifications",
                             json={"kind": "custom", "custom_text": "Your parcel is ready"})
        assert res.status_code == 422


class TestWebhooks:
    def test_verification(self, anon):
        ok = anon.client.get("/webhooks/whatsapp/", params={"hub.mode": "subscribe", "hub.verify_token":
                                                             "test-verify-token", "hub.challenge": "12345"})
        assert ok.status_code == 200 and ok.text == "12345"
        bad = anon.client.get("/webhooks/whatsapp/", params={"hub.mode": "subscribe", "hub.verify_token": "wrong",
                                                              "hub.challenge": "12345"})
        assert bad.status_code == 403

    def test_invalid_signature_rejected(self, connected, db):
        body = json.dumps(inbound_message_payload()).encode()
        res = connected.client.post("/webhooks/whatsapp/", content=body,
                                    headers={"X-Hub-Signature-256": sign(body, "wrong-secret")})
        assert res.status_code == 401
        res = connected.client.post("/webhooks/whatsapp/", content=body)
        assert res.status_code == 401
        assert db.scalar(select(WhatsAppMessage)) is None

    def test_malformed_payload(self, connected):
        body = b"{not json"
        res = connected.client.post("/webhooks/whatsapp/", content=body, headers={"X-Hub-Signature-256": sign(body)})
        assert res.status_code == 400
        weird = {"object": "whatsapp_business_account", "entry": [{"changes": [{"field": "messages",
                                                                                 "value": {"messages": [{}]}}]}]}
        assert post_webhook(connected, weird).status_code == 200

    def test_incoming_message_creates_conversation(self, connected, db):
        cid = customer_with_consent(connected)
        res = post_webhook(connected, inbound_message_payload(text="Price koto?"))
        assert res.status_code == 200 and res.json()["processed"] == 1
        conversations = connected.get("/api/whatsapp/conversations").json()
        assert conversations["total"] == 1
        conv = conversations["items"][0]
        assert conv["customer_id"] == cid and conv["unread_count"] == 1 and conv["service_window_open"]
        detail = connected.get(f"/api/whatsapp/conversations/{conv['id']}").json()
        assert detail["messages"][0]["text"] == "Price koto?"
        assert detail["can_reply"] is True
        assert connected.get("/api/whatsapp/conversations").json()["items"][0]["unread_count"] == 0
        # Raw message text is not kept in the webhook event log.
        assert "Price koto" not in json.dumps(db.scalar(select(WebhookEvent.summary)))

    def test_duplicate_webhook_is_processed_once(self, connected, db):
        payload = inbound_message_payload(msg_id="wamid.DUP")
        assert post_webhook(connected, payload).json()["processed"] == 1
        second = post_webhook(connected, payload).json()
        assert second["duplicates"] == 1 and second["processed"] == 0
        assert len(db.scalars(select(WhatsAppMessage)).all()) == 1
        assert db.scalar(select(WhatsAppConversation.unread_count)) == 1

    def test_unknown_phone_number_id_is_ignored(self, connected, db):
        res = post_webhook(connected, inbound_message_payload(phone_number_id="000"))
        assert res.json()["ignored"] == 1
        assert db.scalar(select(WhatsAppMessage)) is None

    def test_reply_inside_window(self, connected, meta):
        customer_with_consent(connected)
        post_webhook(connected, inbound_message_payload())
        conv_id = connected.get("/api/whatsapp/conversations").json()["items"][0]["id"]
        meta.post(MESSAGES_URL).mock(return_value=meta_ok("wamid.REPLY"))
        res = connected.post(f"/api/whatsapp/conversations/{conv_id}/reply", json={"text": "Ji, available."})
        assert res.status_code == 200 and res.json()["message"]["direction"] == "outbound"

    def test_reply_blocked_after_window(self, connected, meta, db):
        customer_with_consent(connected)
        post_webhook(connected, inbound_message_payload())
        db.execute(update(WhatsAppConversation).values(last_inbound_at=utcnow() - timedelta(hours=30)))
        db.commit()
        conv_id = connected.get("/api/whatsapp/conversations").json()["items"][0]["id"]
        detail = connected.get(f"/api/whatsapp/conversations/{conv_id}").json()
        assert detail["can_reply"] is False
        assert connected.post(f"/api/whatsapp/conversations/{conv_id}/reply", json={"text": "hi"}).status_code == 422

    def test_status_updates_move_forward_only(self, connected, meta, db):
        customer_with_consent(connected)
        meta.post(MESSAGES_URL).mock(return_value=meta_ok("wamid.S1"))
        connected.post("/api/whatsapp/messages/send-template/", json={"to": CUSTOMER_PHONE,
                                                                      "template_name": "hello_world"})
        post_webhook(connected, status_payload("wamid.S1", "delivered"))
        post_webhook(connected, status_payload("wamid.S1", "sent"))  # late, out of order
        assert read_status(db) == "delivered"
        post_webhook(connected, status_payload("wamid.S1", "read"))
        assert read_status(db) == "read"
        stats = connected.get("/api/whatsapp/stats").json()
        assert stats["by_status"] == {"read": 1} and stats["delivery_rate"] == 1.0

    def test_failed_status_records_error(self, connected, meta, db):
        customer_with_consent(connected)
        meta.post(MESSAGES_URL).mock(return_value=meta_ok("wamid.F1"))
        connected.post("/api/whatsapp/messages/send-template/", json={"to": CUSTOMER_PHONE,
                                                                      "template_name": "hello_world"})
        post_webhook(connected, status_payload("wamid.F1", "failed", errors=[{
            "code": 131026, "title": "Message undeliverable", "error_data": {"details": "Not on WhatsApp"}}]))
        db.rollback()  # end the read transaction so the shared test connection is free
        message = db.scalar(select(WhatsAppMessage))
        assert message.status == "failed" and message.error_code == "131026"
        assert message.error_detail == "Not on WhatsApp"

    def test_opt_out_keyword_revokes_consent(self, connected):
        cid = customer_with_consent(connected)
        post_webhook(connected, inbound_message_payload(text="STOP"))
        assert connected.get(f"/api/customers/{cid}").json()["transactional_consent"] == "revoked"
