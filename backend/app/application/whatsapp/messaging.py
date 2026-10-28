"""Outbound WhatsApp messaging.

Deduplication strategy: every send is stored as a `pending` row keyed by
(business_id, idempotency_key) *before* calling Meta. A repeated request with the same key
returns the stored message instead of sending again. Sends are never retried automatically;
a timeout leaves the message in `unknown` status until a webhook status update resolves it.
"""

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.context import TenantContext
from app.application.dto import SendTemplateCommand, SendTextCommand
from app.application.ports import CredentialProvider, MetaApiError, MetaNetworkError, WhatsAppGateway
from app.application.subscriptions import SubscriptionService
from app.application.whatsapp.configuration import log_api_error
from app.domain.clock import utcnow
from app.domain.enums import ConsentPurpose, MessageDirection, MessageStatus, UsageMetric, WhatsAppMode
from app.domain.errors import (
    ConfigurationError,
    ExternalServiceError,
    MessagingPolicyError,
    NotFoundError,
    RateLimitedError,
    ValidationError,
)
from app.domain.messaging_policy import MessagingContext, free_form_blockers, template_blockers
from app.domain.phone import normalize_phone, to_wa_id
from app.infrastructure.db.models import Customer, WhatsAppConfiguration, WhatsAppConversation, WhatsAppMessage
from app.infrastructure.repositories.customers import ConsentRepository, CustomerRepository
from app.infrastructure.repositories.orders import OrderRepository
from app.infrastructure.repositories.whatsapp import (
    ConversationRepository,
    MessageRepository,
    TestRecipientRepository,
    WhatsAppConfigRepository,
)
from app.infrastructure.whatsapp.payloads import build_template_payload, build_text_payload

log = logging.getLogger(__name__)


@dataclass
class Recipient:
    phone: str
    customer: Customer | None
    conversation: WhatsAppConversation | None


@dataclass
class SendOutcome:
    message: WhatsAppMessage
    replayed: bool = False


class MessagingService:
    def __init__(self, session: Session, ctx: TenantContext, gateway: WhatsAppGateway,
                 credentials: CredentialProvider, *, enforce_limits: bool = True):
        self.session = session
        self.ctx = ctx
        self.gateway = gateway
        self.credentials = credentials
        self.customers = CustomerRepository(session, ctx.business_id)
        self.conversations = ConversationRepository(session, ctx.business_id)
        self.messages = MessageRepository(session, ctx.business_id)
        self.subscriptions = SubscriptionService(session, ctx.business_id, enforce=enforce_limits)

    # --- recipients & policy ------------------------------------------------------------------
    def resolve_recipient(self, *, to: str | None = None, customer_id: int | None = None,
                          conversation_id: int | None = None) -> Recipient:
        """The recipient must be a customer or an existing conversation of *this* business."""
        if conversation_id:
            conversation = self.conversations.get_or_raise(conversation_id)
            customer = self.customers.get(conversation.customer_id) if conversation.customer_id else None
            return Recipient(conversation.wa_id, customer or self.customers.by_phone(conversation.wa_id), conversation)
        if customer_id:
            customer = self.customers.get_or_raise(customer_id)
            if to and normalize_phone(to) != customer.phone:
                raise ValidationError("The phone number does not match the selected customer.")
            return Recipient(customer.phone, customer, self.conversations.by_wa_id(customer.phone))
        if to:
            phone = normalize_phone(to)
            customer = self.customers.by_phone(phone)
            conversation = self.conversations.by_wa_id(phone)
            if not customer and not conversation:
                raise NotFoundError("This number is not a customer or contact of your business.",
                                    code="unknown_recipient")
            return Recipient(phone, customer, conversation)
        raise ValidationError("A recipient (to, customer_id or conversation_id) is required.")

    def active_configuration(self) -> WhatsAppConfiguration:
        config = WhatsAppConfigRepository(self.session, self.ctx.business_id).current()
        if not config or not config.is_enabled:
            raise ConfigurationError("WhatsApp is not connected for this business. Open WhatsApp Settings.")
        return config

    def policy_context(self, recipient: Recipient, config: WhatsAppConfiguration | None = None) -> MessagingContext:
        config = config or WhatsAppConfigRepository(self.session, self.ctx.business_id).current()
        consent = (ConsentRepository(self.session, self.ctx.business_id)
                   .current_status(recipient.customer.id, ConsentPurpose.TRANSACTIONAL.value)
                   if recipient.customer else None)
        return MessagingContext(
            mode=WhatsAppMode(config.mode) if config else WhatsAppMode.TEST,
            recipient=recipient.phone,
            test_recipients=TestRecipientRepository(self.session, self.ctx.business_id).phones(),
            transactional_consent=consent,
            last_inbound_at=recipient.conversation.last_inbound_at if recipient.conversation else None,
        )

    # --- sending ------------------------------------------------------------------------------
    def send_text(self, cmd: SendTextCommand, *, idempotency_key: str | None = None,
                  notification_kind: str | None = None) -> SendOutcome:
        recipient = self.resolve_recipient(to=cmd.to, customer_id=cmd.customer_id,
                                           conversation_id=cmd.conversation_id)
        return self._send(
            recipient=recipient,
            idempotency_key=idempotency_key,
            blockers=lambda ctx: free_form_blockers(ctx, utcnow()),
            payload=build_text_payload(to_wa_id(recipient.phone), cmd.text),
            fields=dict(message_type="text", text=cmd.text, order_id=self._order_id(cmd.order_id),
                        notification_kind=notification_kind),
        )

    def send_template(self, cmd: SendTemplateCommand, *, idempotency_key: str | None = None,
                      preview_text: str | None = None, notification_kind: str | None = None) -> SendOutcome:
        recipient = self.resolve_recipient(to=cmd.to, customer_id=cmd.customer_id)
        return self._send(
            recipient=recipient,
            idempotency_key=idempotency_key,
            blockers=template_blockers,
            payload=build_template_payload(to_wa_id(recipient.phone), cmd.template_name, cmd.language,
                                           cmd.body_parameters),
            fields=dict(message_type="template", template_name=cmd.template_name, template_language=cmd.language,
                        text=preview_text, order_id=self._order_id(cmd.order_id),
                        notification_kind=notification_kind,
                        safe_metadata={"parameter_count": len(cmd.body_parameters)}),
        )

    def _send(self, *, recipient: Recipient, idempotency_key: str | None, blockers, payload: dict,
              fields: dict) -> SendOutcome:
        if idempotency_key:
            existing = self.messages.by_idempotency_key(idempotency_key)
            if existing:
                return SendOutcome(existing, replayed=True)

        config = self.active_configuration()
        creds = self.credentials.for_configuration(config)
        reasons = blockers(self.policy_context(recipient, config))
        if reasons:
            raise MessagingPolicyError(reasons[0], details={"reasons": reasons})
        self.subscriptions.ensure_within_limit(UsageMetric.WHATSAPP_MESSAGES)

        message, created = self._store_pending(recipient, idempotency_key or f"auto-{uuid.uuid4()}", fields)
        if not created:
            return SendOutcome(message, replayed=True)

        try:
            result = self.gateway.send_message(creds, payload)
        except MetaApiError as exc:
            message.status = MessageStatus.FAILED.value
            message.error_code = str(exc.code) if exc.code is not None else None
            message.error_title = exc.title[:255]
            message.error_detail = exc.message[:2000]
            message.status_updated_at = utcnow()
            log_api_error(self.session, self.ctx.business_id, "send_message", exc)
            self.session.commit()
            error_cls = RateLimitedError if exc.kind == "rate_limit" else ExternalServiceError
            raise error_cls(f"WhatsApp rejected the message: {exc.message}",
                            code=f"meta_{exc.kind}",
                            details={"message_id": message.id, "meta_code": exc.code}) from exc
        except MetaNetworkError as exc:
            message.status = MessageStatus.UNKNOWN.value
            message.error_detail = exc.message
            message.status_updated_at = utcnow()
            log_api_error(self.session, self.ctx.business_id, "send_message", exc)
            self.session.commit()
            raise ExternalServiceError(
                "Could not confirm the message was sent. Wait for a status update before resending.",
                code="delivery_unknown", details={"message_id": message.id},
            ) from exc

        now = utcnow()
        message.wa_message_id = result.message_id
        message.status = MessageStatus.ACCEPTED.value
        message.status_updated_at = now
        conversation = message.conversation
        conversation.last_message_at = now
        conversation.last_message_preview = (fields.get("text") or f"[{fields['message_type']}]")[:200]
        self.subscriptions.record_usage(UsageMetric.WHATSAPP_MESSAGES)
        self.session.commit()
        return SendOutcome(message)

    def _store_pending(self, recipient: Recipient, idempotency_key: str,
                       fields: dict) -> tuple[WhatsAppMessage, bool]:
        """Persist the outbound row before calling Meta. Returns (message, created)."""
        conversation = recipient.conversation or self._create_conversation(recipient)
        message = WhatsAppMessage(
            conversation_id=conversation.id, customer_id=recipient.customer.id if recipient.customer else None,
            direction=MessageDirection.OUTBOUND.value, idempotency_key=idempotency_key,
            status=MessageStatus.PENDING.value, sent_by_user_id=self.ctx.user_id, **fields,
        )
        self.messages.add(message)
        try:
            self.session.commit()
        except IntegrityError:
            # A concurrent request with the same idempotency key won the race.
            self.session.rollback()
            existing = self.messages.by_idempotency_key(idempotency_key)
            if existing is None:
                raise
            return existing, False
        message.conversation = conversation
        return message, True

    def _create_conversation(self, recipient: Recipient) -> WhatsAppConversation:
        conversation = WhatsAppConversation(
            wa_id=recipient.phone, customer_id=recipient.customer.id if recipient.customer else None,
            contact_name=recipient.customer.name if recipient.customer else None,
        )
        self.conversations.add(conversation)
        self.session.flush()
        recipient.conversation = conversation
        return conversation

    def _order_id(self, order_id: int | None) -> int | None:
        if order_id is None:
            return None
        return OrderRepository(self.session, self.ctx.business_id).get_or_raise(order_id).id
