"""Test fixtures. No test here talks to Meta: all Graph API calls are mocked with respx.

By default tests use in-memory SQLite. Set TEST_DATABASE_URL to run them against PostgreSQL
(the docker-compose `backend-tests` service does this).
"""

import hashlib
import hmac
import json
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.infrastructure.db.base import Base
from app.main import create_app

META_BASE = "https://graph.test.facebook.com"
APP_SECRET = "test-app-secret"
VERIFY_TOKEN = "test-verify-token"
PHONE_NUMBER_ID = "111222333444"


class CapturingEmailSender:
    def __init__(self):
        self.sent: list[dict] = []

    def send(self, *, to: str, subject: str, body: str) -> None:
        self.sent.append({"to": to, "subject": subject, "body": body})


def _make_engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        engine = create_engine(url)
        Base.metadata.drop_all(engine)
        return engine
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    # Make pysqlite honour SAVEPOINTs and foreign keys, like PostgreSQL.
    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection, _):
        dbapi_connection.isolation_level = None
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    @event.listens_for(engine, "begin")
    def _on_begin(conn):
        conn.exec_driver_sql("BEGIN")

    return engine


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        secret_key="test-secret-key-0123456789-abcdefghij",
        database_url="sqlite://",
        media_dir=str(tmp_path / "media"),
        meta_access_token="EAATESTTOKEN1234567890",
        meta_phone_number_id=PHONE_NUMBER_ID,
        meta_waba_id="999888777",
        meta_app_secret=APP_SECRET,
        meta_verify_token=VERIFY_TOKEN,
        meta_graph_api_version="v21.0",
        meta_graph_base_url=META_BASE,
        meta_mode="test",
    )


@pytest.fixture
def engine():
    engine = _make_engine()
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def email_sender():
    return CapturingEmailSender()


@pytest.fixture
def app(settings, engine, email_sender):
    return create_app(settings, engine=engine, email_sender=email_sender)


@pytest.fixture
def db(app):
    session = app.state.session_factory()
    yield session
    session.close()


class Api:
    """TestClient wrapper that sends the CSRF header and the active business id."""

    def __init__(self, client: TestClient):
        self.client = client
        self.business_id: int | None = None

    def _headers(self, extra: dict | None = None) -> dict:
        headers = {}
        csrf = self.client.cookies.get("sp_csrf")
        if csrf:
            headers["X-CSRF-Token"] = csrf
        if self.business_id:
            headers["X-Business-Id"] = str(self.business_id)
        headers.update(extra or {})
        return headers

    def get(self, url, **kw):
        return self.client.get(url, headers=self._headers(kw.pop("headers", None)), **kw)

    def post(self, url, **kw):
        return self.client.post(url, headers=self._headers(kw.pop("headers", None)), **kw)

    def patch(self, url, **kw):
        return self.client.patch(url, headers=self._headers(kw.pop("headers", None)), **kw)

    def put(self, url, **kw):
        return self.client.put(url, headers=self._headers(kw.pop("headers", None)), **kw)

    def delete(self, url, **kw):
        return self.client.delete(url, headers=self._headers(kw.pop("headers", None)), **kw)


def register(api: Api, email: str, business_name: str | None = "Dhaka Boutique", password: str = "secret123"):
    res = api.post("/api/auth/register", json={"email": email, "password": password, "full_name": "Test Seller"})
    assert res.status_code == 201, res.text
    if business_name:
        res = api.post("/api/businesses", json={"name": business_name})
        assert res.status_code == 201, res.text
        api.business_id = res.json()["id"]
    return api


@pytest.fixture
def make_api(app):
    clients = []

    def factory(email: str | None = None, business_name: str | None = "Dhaka Boutique") -> Api:
        client = TestClient(app)
        clients.append(client)
        return register(Api(client), email or f"seller-{uuid.uuid4().hex[:8]}@example.com", business_name)

    yield factory
    for client in clients:
        client.close()


@pytest.fixture
def api(make_api) -> Api:
    return make_api("owner@example.com")


@pytest.fixture
def anon(app):
    with TestClient(app) as client:
        yield Api(client)


# --- domain helpers -------------------------------------------------------------------------------
def create_product(api: Api, sku="TSHIRT-1", price="500", stock=10, cost_price="300", variants=None) -> dict:
    body = {"name": f"Product {sku}", "sku": sku, "price": price, "cost_price": cost_price, "stock": stock}
    if variants is not None:
        body["variants"] = variants
    res = api.post("/api/products", json=body)
    assert res.status_code == 201, res.text
    return res.json()


def create_order(api: Api, variant_id: int, quantity=1, phone="01712345678", **extra) -> dict:
    body = {
        "new_customer": {"name": "Rahim", "phone": phone, "address": "Mirpur, Dhaka"},
        "items": [{"variant_id": variant_id, "quantity": quantity}],
        "delivery_charge": "60",
        "discount": "0",
        **extra,
    }
    res = api.post("/api/orders", json=body)
    assert res.status_code == 201, res.text
    return res.json()


def sign(body: bytes, secret: str = APP_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def post_webhook(client_api: Api, payload: dict, secret: str = APP_SECRET):
    body = json.dumps(payload).encode()
    return client_api.client.post("/webhooks/whatsapp/", content=body,
                                  headers={"Content-Type": "application/json", "X-Hub-Signature-256": sign(body, secret)})


def inbound_message_payload(wa_from="8801712345678", msg_id="wamid.IN1", text="Hi, is this available?",
                            timestamp=None, phone_number_id=PHONE_NUMBER_ID) -> dict:
    import time

    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WABA",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "15550001111", "phone_number_id": phone_number_id},
                    "contacts": [{"profile": {"name": "Rahim"}, "wa_id": wa_from}],
                    "messages": [{"from": wa_from, "id": msg_id, "timestamp": str(timestamp or int(time.time())),
                                  "type": "text", "text": {"body": text}}],
                },
            }],
        }],
    }


def status_payload(wa_message_id: str, status: str, timestamp: int = 1_760_000_000, errors=None) -> dict:
    item = {"id": wa_message_id, "status": status, "timestamp": str(timestamp), "recipient_id": "8801712345678"}
    if errors:
        item["errors"] = errors
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "WABA", "changes": [{"field": "messages", "value": {
            "messaging_product": "whatsapp",
            "metadata": {"phone_number_id": PHONE_NUMBER_ID},
            "statuses": [item],
        }}]}],
    }
