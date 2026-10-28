"""Processing of verified WhatsApp webhook payloads.

Each message/status item is processed exactly once, keyed by a WebhookEvent `event_key`.
Each item runs in its own savepoint so one bad item never drops the others.
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.clock import utcnow
from app.domain.enums import (
    ConsentPurpose,
    ConsentSource,
    ConsentStatus,
    CredentialSource,
    MessageDirection,
    MessageStatus,
    WebhookEventStatus,
)
from app.domain.messaging_policy import should_apply_status
from app.domain.phone import normalize_wa_id
from app.infrastructure.db.models import (
    Customer,
    CustomerCommunicationConsent,
    WebhookEvent,
    WhatsAppConfiguration,
    WhatsAppConversation,
    WhatsAppMessage,
)

log = logging.getLogger(__name__)

MAX_TEXT_LENGTH = 4096
OPT_OUT_KEYWORDS = {"STOP", "UNSUBSCRIBE", "বন্ধ"}
_STATUS_MAP = {
    "sent": MessageStatus.SENT,
    "delivered": MessageStatus.DELIVERED,
    "read": MessageStatus.READ,
    "failed": MessageStatus.FAILED,
}


def _parse_timestamp(value) -> datetime:
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return utcnow()


def _extract_content(msg: dict) -> tuple[str, str | None, dict]:
    """Return (type, text, safe_metadata). Media is never downloaded; location coordinates are not stored."""
    msg_type = str(msg.get("type") or "unknown")[:30]
    body = msg.get(msg_type) if isinstance(msg.get(msg_type), dict) else {}
    meta: dict = {}
    text = None
    if msg_type == "text":
        text = body.get("body")
    elif msg_type == "button":
        text = body.get("text")
    elif msg_type == "interactive":
        reply = body.get("button_reply") or body.get("list_reply") or {}
        text = reply.get("title")
        meta["interactive_type"] = body.get("type")
    elif msg_type in {"image", "video", "audio", "document", "sticker"}:
        text = body.get("caption")
        meta.update({"media_id": body.get("id"), "mime_type": body.get("mime_type")})
        if msg_type == "document":
            meta["filename"] = (body.get("filename") or "")[:120] or None
    elif msg_type == "reaction":
        text = body.get("emoji")
        meta["reacted_message_id"] = body.get("message_id")
    elif msg_type == "location":
        meta["note"] = "location shared (coordinates not stored)"
    if isinstance(text, str):
        text = text[:MAX_TEXT_LENGTH]
    else:
        text = None
    return msg_type, text, {k: v for k, v in meta.items() if v is not None}


class WebhookProcessor:
    def __init__(self, session: Session):
        self.session = session

    def process(self, payload: dict) -> dict:
        summary = {"processed": 0, "duplicates": 0, "ignored": 0, "failed": 0}
        if not isinstance(payload, dict) or payload.get("object") != "whatsapp_business_account":
            summary["ignored"] += 1
            return summary

        for entry in payload.get("entry") or []:
            for change in (entry or {}).get("changes") or []:
                if not isinstance(change, dict) or change.get("field") != "messages":
                    summary["ignored"] += 1
                    continue
                value = change.get("value") or {}
                phone_number_id = str((value.get("metadata") or {}).get("phone_number_id") or "")
                config = self.session.scalar(
                    select(WhatsAppConfiguration).where(WhatsAppConfiguration.phone_number_id == phone_number_id)
                ) if phone_number_id else None
                if config:
                    config.last_webhook_at = utcnow()
                contacts = {
                    str(c.get("wa_id")): (c.get("profile") or {}).get("name")
                    for c in value.get("contacts") or [] if isinstance(c, dict)
                }
                for msg in value.get("messages") or []:
                    key = f"message:{msg.get('id')}" if isinstance(msg, dict) and msg.get("id") else None
                    self._count(summary, self._run_once(key, "message", config, {"type": (msg or {}).get("type")},
                                                         lambda m=msg: self._handle_message(config, m, contacts)))
                for status in value.get("statuses") or []:
                    key = (f"status:{status.get('id')}:{status.get('status')}"
                           if isinstance(status, dict) and status.get("id") else None)
                    self._count(summary, self._run_once(key, "status", config,
                                                         {"status": (status or {}).get("status")},
                                                         lambda s=status: self._handle_status(config, s)))
                for error in value.get("errors") or []:
                    digest = hashlib.sha256(json.dumps(error, sort_keys=True).encode()).hexdigest()[:32]
                    self._count(summary, self._run_once(
                        f"error:{digest}", "error", config,
                        {"code": (error or {}).get("code"), "title": (error or {}).get("title")},
                        lambda: WebhookEventStatus.PROCESSED))
        self.session.commit()
        return summary

    @staticmethod
    def _count(summary: dict, outcome: str) -> None:
        summary[{"processed": "processed", "duplicate": "duplicates", "ignored": "ignored"}.get(outcome, "failed")] += 1

    def _run_once(self, event_key: str | None, event_type: str, config, summary_data: dict, handler) -> str:
        if not event_key:
            return "ignored"
        if self.session.scalar(select(WebhookEvent.id).where(WebhookEvent.event_key == event_key)):
            return "duplicate"
        business_id = config.business_id if config else None
        try:
            with self.session.begin_nested():
                event = WebhookEvent(event_key=event_key[:200], event_type=event_type, business_id=business_id,
                                     status=WebhookEventStatus.PROCESSED.value, summary=summary_data,
                                     received_at=utcnow())
                self.session.add(event)
                self.session.flush()  # unique event_key guards against concurrent duplicates
                outcome = handler()
                event.status = outcome.value
        except IntegrityError:
            return "duplicate"
        except Exception as exc:  # noqa: BLE001 - one bad item must not break the batch
            log.exception("Failed to process webhook item %s", event_key)
            with self.session.begin_nested():
                self.session.add(WebhookEvent(
                    event_key=f"failed:{uuid.uuid4().hex}", event_type=event_type, business_id=business_id,
                    status=WebhookEventStatus.FAILED.value, error=f"{event_key}: {exc}"[:2000],
                    summary=summary_data, received_at=utcnow()))
            return "failed"
        return "processed" if outcome == WebhookEventStatus.PROCESSED else "ignored"

    # --- handlers ----------------------------------------------------------------------------
    def _handle_message(self, config: WhatsAppConfiguration | None, msg: dict, contacts: dict) -> WebhookEventStatus:
        if config is None or not msg.get("from"):
            return WebhookEventStatus.IGNORED
        business_id = config.business_id
        phone = normalize_wa_id(msg["from"])
        sent_at = _parse_timestamp(msg.get("timestamp"))
        msg_type, text, meta = _extract_content(msg)

        customer = self.session.scalar(select(Customer).where(Customer.business_id == business_id,
                                                              Customer.phone == phone))
        conversation = self.session.scalar(select(WhatsAppConversation).where(
            WhatsAppConversation.business_id == business_id, WhatsAppConversation.wa_id == phone))
        if conversation is None:
            conversation = WhatsAppConversation(business_id=business_id, wa_id=phone, unread_count=0)
            self.session.add(conversation)
            self.session.flush()
        if customer and conversation.customer_id is None:
            conversation.customer_id = customer.id
        profile_name = contacts.get(str(msg["from"]))
        if profile_name:
            conversation.contact_name = str(profile_name)[:150]

        self.session.add(WhatsAppMessage(
            business_id=business_id, conversation_id=conversation.id,
            customer_id=customer.id if customer else None, direction=MessageDirection.INBOUND.value,
            wa_message_id=str(msg["id"])[:128], message_type=msg_type, text=text,
            status=MessageStatus.RECEIVED.value, wa_timestamp=sent_at, safe_metadata=meta or None,
        ))
        if conversation.last_inbound_at is None or sent_at > conversation.last_inbound_at:
            conversation.last_inbound_at = sent_at
        conversation.last_message_at = max(filter(None, [conversation.last_message_at, sent_at]))
        conversation.last_message_preview = (text or f"[{msg_type}]")[:200]
        conversation.unread_count = (conversation.unread_count or 0) + 1

        if customer and text and text.strip().upper() in OPT_OUT_KEYWORDS:
            for purpose in ConsentPurpose:
                self.session.add(CustomerCommunicationConsent(
                    business_id=business_id, customer_id=customer.id, channel="whatsapp", purpose=purpose.value,
                    status=ConsentStatus.REVOKED.value, source=ConsentSource.WHATSAPP.value,
                    note="Customer replied with an opt-out keyword", recorded_at=utcnow()))
        self.session.flush()
        return WebhookEventStatus.PROCESSED

    def _handle_status(self, config: WhatsAppConfiguration | None, status: dict) -> WebhookEventStatus:
        new_status = _STATUS_MAP.get(str(status.get("status")))
        if new_status is None:
            return WebhookEventStatus.IGNORED
        stmt = select(WhatsAppMessage).where(WhatsAppMessage.wa_message_id == str(status.get("id")))
        if config:
            stmt = stmt.where(WhatsAppMessage.business_id == config.business_id)
        message = self.session.scalar(stmt.with_for_update())
        if message is None or message.direction != MessageDirection.OUTBOUND.value:
            return WebhookEventStatus.IGNORED
        if not should_apply_status(MessageStatus(message.status), new_status):
            return WebhookEventStatus.IGNORED
        message.status = new_status.value
        message.status_updated_at = _parse_timestamp(status.get("timestamp"))
        if new_status == MessageStatus.FAILED:
            error = (status.get("errors") or [{}])[0] or {}
            message.error_code = str(error.get("code")) if error.get("code") is not None else None
            message.error_title = (error.get("title") or "")[:255] or None
            message.error_detail = ((error.get("error_data") or {}).get("details") or error.get("message") or "")[:2000] or None
        self.session.flush()
        return WebhookEventStatus.PROCESSED


def mark_webhook_verified(session: Session) -> None:
    session.execute(
        update(WhatsAppConfiguration)
        .where(WhatsAppConfiguration.credential_source == CredentialSource.ENVIRONMENT.value)
        .values(webhook_verified_at=utcnow())
    )
    session.commit()


def purge_old_webhook_events(session: Session, retention_days: int) -> int:
    cutoff = utcnow() - timedelta(days=retention_days)
    result = session.execute(delete(WebhookEvent).where(WebhookEvent.received_at < cutoff))
    session.commit()
    return result.rowcount or 0
