"""MANUAL integration tests against the real Meta Graph API.

They are skipped unless RUN_META_LIVE_TESTS=1 and real credentials are in the environment:

    RUN_META_LIVE_TESTS=1 META_ACCESS_TOKEN=... META_PHONE_NUMBER_ID=... \
    META_TEST_RECIPIENT=8801XXXXXXXXX pytest tests/manual -s

The recipient must be registered as a test recipient in your Meta app. These tests send a
real `hello_world` template message.
"""

import os

import pytest

from app.application.ports import WhatsAppCredentials
from app.domain.enums import WhatsAppMode
from app.infrastructure.whatsapp.meta_client import MetaCloudApiClient
from app.infrastructure.whatsapp.payloads import build_template_payload

pytestmark = pytest.mark.skipif(os.environ.get("RUN_META_LIVE_TESTS") != "1",
                                reason="Live Meta tests are opt-in (RUN_META_LIVE_TESTS=1)")


@pytest.fixture
def creds() -> WhatsAppCredentials:
    return WhatsAppCredentials(
        access_token=os.environ["META_ACCESS_TOKEN"],
        phone_number_id=os.environ["META_PHONE_NUMBER_ID"],
        waba_id=os.environ.get("META_WABA_ID"),
        api_version=os.environ.get("META_GRAPH_API_VERSION", "v21.0"),
        base_url="https://graph.facebook.com",
        mode=WhatsAppMode.TEST,
    )


def test_phone_number_lookup(creds):
    info = MetaCloudApiClient().get_phone_number(creds)
    print(info)
    assert "display_phone_number" in info


def test_send_hello_world(creds):
    recipient = os.environ["META_TEST_RECIPIENT"]
    result = MetaCloudApiClient().send_message(creds, build_template_payload(recipient, "hello_world", "en_US"))
    print("message id:", result.message_id)
    assert result.message_id.startswith("wamid.")
