"""Seller-initiated order notifications: preview first, then an explicit send."""

from sqlalchemy.orm import Session

from app.application.context import TenantContext
from app.application.dto import OrderNotificationCommand, SendTemplateCommand, SendTextCommand
from app.application.whatsapp.messaging import MessagingService, SendOutcome
from app.application.whatsapp.templates import order_parameters, template_registry
from app.core.config import Settings
from app.domain.clock import utcnow
from app.domain.enums import NotificationKind, OrderStatus
from app.domain.errors import MessagingPolicyError
from app.domain.messaging_policy import (
    free_form_blockers,
    is_service_window_open,
    service_window_expires_at,
    template_blockers,
)
from app.infrastructure.db.models import Business
from app.infrastructure.repositories.orders import OrderRepository
from app.infrastructure.repositories.whatsapp import WhatsAppConfigRepository


class OrderNotificationService:
    def __init__(self, session: Session, ctx: TenantContext, settings: Settings, messaging: MessagingService):
        self.session = session
        self.ctx = ctx
        self.settings = settings
        self.messaging = messaging
        self.orders = OrderRepository(session, ctx.business_id)

    def preview(self, order_id: int, kind: NotificationKind, custom_text: str | None = None) -> dict:
        order = self.orders.get_or_raise(order_id)
        business = self.session.get(Business, self.ctx.business_id)
        recipient = self.messaging.resolve_recipient(customer_id=order.customer_id)
        config = WhatsAppConfigRepository(self.session, self.ctx.business_id).current()
        policy_ctx = self.messaging.policy_context(recipient, config)
        now = utcnow()
        blockers: list[str] = []
        if not config:
            blockers.append("WhatsApp is not connected for this business.")

        template = None
        parameters: list[str] = []
        if kind == NotificationKind.CUSTOM:
            channel, text = "text", (custom_text or "").strip()
            if not text:
                blockers.append("Write the message you want to send.")
        else:
            template = template_registry(self.settings)[kind]
            if OrderStatus(order.status) not in template.eligible_statuses:
                blockers.append(f"This notification does not match the order's current status ({order.status}).")
            parameters = order_parameters(kind, order_number=order.order_number, total=order.total,
                                          amount_due=order.total - order.amount_paid, business_name=business.name)
            text = template.render(parameters)
            channel = "template" if template.is_configured else "text"

        blockers += template_blockers(policy_ctx) if channel == "template" else free_form_blockers(policy_ctx, now)
        return {
            "kind": kind.value,
            "order_id": order.id,
            "order_number": order.order_number,
            "recipient_phone": recipient.phone,
            "recipient_name": order.customer.name,
            "channel": channel,
            "template_name": template.template_name if template and channel == "template" else None,
            "template_language": template.language if template and channel == "template" else None,
            "parameters": parameters,
            "text": text,
            "mode": policy_ctx.mode.value,
            "service_window_open": is_service_window_open(policy_ctx.last_inbound_at, now),
            "service_window_expires_at": service_window_expires_at(policy_ctx.last_inbound_at),
            "transactional_consent": policy_ctx.transactional_consent.value if policy_ctx.transactional_consent else None,
            "can_send": not blockers,
            "blockers": list(dict.fromkeys(blockers)),
        }

    def send(self, order_id: int, cmd: OrderNotificationCommand, *, idempotency_key: str | None) -> SendOutcome:
        preview = self.preview(order_id, cmd.kind, cmd.custom_text)
        if idempotency_key:
            existing = self.messaging.messages.by_idempotency_key(idempotency_key)
            if existing:
                return SendOutcome(existing, replayed=True)
        if not preview["can_send"]:
            raise MessagingPolicyError(preview["blockers"][0], details={"reasons": preview["blockers"]})

        order = self.orders.get_or_raise(order_id)
        if preview["channel"] == "template":
            return self.messaging.send_template(
                SendTemplateCommand(customer_id=order.customer_id, template_name=preview["template_name"],
                                    language=preview["template_language"], body_parameters=preview["parameters"],
                                    order_id=order.id),
                idempotency_key=idempotency_key, preview_text=preview["text"], notification_kind=cmd.kind.value,
            )
        return self.messaging.send_text(
            SendTextCommand(customer_id=order.customer_id, text=preview["text"], order_id=order.id),
            idempotency_key=idempotency_key, notification_kind=cmd.kind.value,
        )
