from sqlalchemy.orm import Session

from app.application.context import TenantContext
from app.application.dto import ReplyCommand, SendTextCommand
from app.application.whatsapp.messaging import MessagingService, SendOutcome
from app.domain.clock import utcnow
from app.domain.messaging_policy import free_form_blockers, is_service_window_open, service_window_expires_at
from app.infrastructure.repositories.customers import CustomerRepository
from app.infrastructure.repositories.whatsapp import ConversationRepository, MessageRepository


class InboxService:
    def __init__(self, session: Session, ctx: TenantContext, messaging: MessagingService):
        self.session = session
        self.ctx = ctx
        self.messaging = messaging
        self.conversations = ConversationRepository(session, ctx.business_id)
        self.messages = MessageRepository(session, ctx.business_id)
        self.customers = CustomerRepository(session, ctx.business_id)

    def list(self, *, page: int = 1, page_size: int = 30, unread_only: bool = False):
        items, total = self.conversations.list(page=page, page_size=page_size, unread_only=unread_only)
        names = {c.id: c.name for c in (self.customers.get(i.customer_id) for i in items if i.customer_id) if c}
        now = utcnow()
        rows = [
            {"conversation": c, "customer_name": names.get(c.customer_id),
             "service_window_open": is_service_window_open(c.last_inbound_at, now)}
            for c in items
        ]
        return rows, total

    def open(self, conversation_id: int) -> dict:
        conversation = self.conversations.get_or_raise(conversation_id)
        if conversation.unread_count:
            conversation.unread_count = 0
            self.session.commit()
        recipient = self.messaging.resolve_recipient(conversation_id=conversation.id)
        reasons = free_form_blockers(self.messaging.policy_context(recipient), utcnow())
        return {
            "conversation": conversation,
            "customer": recipient.customer,
            "messages": self.messages.for_conversation(conversation.id),
            "service_window_open": is_service_window_open(conversation.last_inbound_at, utcnow()),
            "service_window_expires_at": service_window_expires_at(conversation.last_inbound_at),
            "can_reply": not reasons,
            "reply_blockers": reasons,
        }

    def reply(self, conversation_id: int, cmd: ReplyCommand, *, idempotency_key: str | None) -> SendOutcome:
        return self.messaging.send_text(SendTextCommand(conversation_id=conversation_id, text=cmd.text),
                                        idempotency_key=idempotency_key)
