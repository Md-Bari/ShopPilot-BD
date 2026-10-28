"""WhatsApp messaging rules, kept free of I/O so they are easy to test.

- Free-form text may only be sent inside the 24h customer-service window,
  i.e. within 24h of the customer's last inbound message.
- Business-initiated template messages require the customer's recorded opt-in.
- An explicit opt-out blocks every outbound message.
- In test mode, only authorized test recipients can be messaged.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.domain.enums import ConsentStatus, MessageStatus, WhatsAppMode

SERVICE_WINDOW = timedelta(hours=24)


def is_service_window_open(last_inbound_at: datetime | None, now: datetime) -> bool:
    return last_inbound_at is not None and now - last_inbound_at < SERVICE_WINDOW


def service_window_expires_at(last_inbound_at: datetime | None) -> datetime | None:
    return last_inbound_at + SERVICE_WINDOW if last_inbound_at else None


@dataclass(frozen=True)
class MessagingContext:
    mode: WhatsAppMode
    recipient: str  # E.164
    test_recipients: frozenset[str] = field(default_factory=frozenset)
    transactional_consent: ConsentStatus | None = None
    last_inbound_at: datetime | None = None


def _common_blockers(ctx: MessagingContext) -> list[str]:
    reasons = []
    if ctx.mode == WhatsAppMode.TEST and ctx.recipient not in ctx.test_recipients:
        reasons.append(
            "Test mode: this number is not an authorized test recipient. Add it in WhatsApp Settings "
            "and in your Meta app's allowed recipient list."
        )
    if ctx.transactional_consent == ConsentStatus.REVOKED:
        reasons.append("The customer has opted out of WhatsApp messages.")
    return reasons


def free_form_blockers(ctx: MessagingContext, now: datetime) -> list[str]:
    reasons = _common_blockers(ctx)
    if not is_service_window_open(ctx.last_inbound_at, now):
        reasons.append(
            "The 24-hour customer service window is closed. Free-form messages are only allowed within "
            "24 hours of the customer's last message; use an approved template instead."
        )
    return reasons


def template_blockers(ctx: MessagingContext) -> list[str]:
    reasons = _common_blockers(ctx)
    if ctx.transactional_consent is None:
        reasons.append("No WhatsApp opt-in is recorded for this customer. Record their consent first.")
    return reasons


_STATUS_RANK = {
    MessageStatus.PENDING: 0,
    MessageStatus.UNKNOWN: 0,
    MessageStatus.ACCEPTED: 1,
    MessageStatus.SENT: 2,
    MessageStatus.DELIVERED: 3,
    MessageStatus.READ: 4,
}


def should_apply_status(current: MessageStatus, new: MessageStatus) -> bool:
    """Status webhooks can arrive out of order; only move forward, never backwards."""
    current, new = MessageStatus(current), MessageStatus(new)
    if current == new or current == MessageStatus.FAILED:
        return False
    if new == MessageStatus.FAILED:
        return current not in (MessageStatus.DELIVERED, MessageStatus.READ)
    if new not in _STATUS_RANK:
        return False
    return _STATUS_RANK[new] > _STATUS_RANK.get(current, -1)
