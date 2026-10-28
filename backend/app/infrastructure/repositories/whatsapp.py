from datetime import datetime

from sqlalchemy import func, select

from app.domain.enums import MessageDirection
from app.infrastructure.db.models import (
    WhatsAppApiErrorLog,
    WhatsAppConfiguration,
    WhatsAppConversation,
    WhatsAppMessage,
    WhatsAppTestRecipient,
)
from app.infrastructure.repositories.base import TenantRepository


class WhatsAppConfigRepository(TenantRepository[WhatsAppConfiguration]):
    model = WhatsAppConfiguration
    label = "WhatsApp configuration"

    def current(self) -> WhatsAppConfiguration | None:
        return self.session.scalar(self._select())


class TestRecipientRepository(TenantRepository[WhatsAppTestRecipient]):
    model = WhatsAppTestRecipient
    label = "Test recipient"

    def all(self) -> list[WhatsAppTestRecipient]:
        return list(self.session.scalars(self._select().order_by(WhatsAppTestRecipient.id)))

    def phones(self) -> frozenset[str]:
        return frozenset(r.phone for r in self.all())


class ConversationRepository(TenantRepository[WhatsAppConversation]):
    model = WhatsAppConversation
    label = "Conversation"

    def by_wa_id(self, wa_id: str) -> WhatsAppConversation | None:
        return self.session.scalar(self._select().where(WhatsAppConversation.wa_id == wa_id))

    def list(self, *, page: int, page_size: int, unread_only: bool = False):
        stmt = self._select()
        if unread_only:
            stmt = stmt.where(WhatsAppConversation.unread_count > 0)
        stmt = stmt.order_by(WhatsAppConversation.last_message_at.desc().nulls_last(), WhatsAppConversation.id.desc())
        return self.paginate(stmt, page, page_size)


class MessageRepository(TenantRepository[WhatsAppMessage]):
    model = WhatsAppMessage
    label = "Message"

    def by_idempotency_key(self, key: str) -> WhatsAppMessage | None:
        return self.session.scalar(self._select().where(WhatsAppMessage.idempotency_key == key))

    def for_conversation(self, conversation_id: int, limit: int = 200) -> list[WhatsAppMessage]:
        stmt = (
            self._select()
            .where(WhatsAppMessage.conversation_id == conversation_id)
            .order_by(WhatsAppMessage.created_at.desc(), WhatsAppMessage.id.desc())
            .limit(limit)
        )
        return list(reversed(list(self.session.scalars(stmt))))

    def for_order(self, order_id: int) -> list[WhatsAppMessage]:
        stmt = self._select().where(WhatsAppMessage.order_id == order_id).order_by(WhatsAppMessage.id)
        return list(self.session.scalars(stmt))

    def outbound_status_counts(self, since: datetime) -> dict[str, int]:
        rows = self.session.execute(
            select(WhatsAppMessage.status, func.count(WhatsAppMessage.id))
            .where(
                WhatsAppMessage.business_id == self.business_id,
                WhatsAppMessage.direction == MessageDirection.OUTBOUND.value,
                WhatsAppMessage.created_at >= since,
            )
            .group_by(WhatsAppMessage.status)
        )
        return {status: count for status, count in rows}

    def inbound_count(self, since: datetime) -> int:
        return self.session.scalar(
            select(func.count(WhatsAppMessage.id)).where(
                WhatsAppMessage.business_id == self.business_id,
                WhatsAppMessage.direction == MessageDirection.INBOUND.value,
                WhatsAppMessage.created_at >= since,
            )
        ) or 0

    def recent_inbound(self, limit: int) -> list[WhatsAppMessage]:
        stmt = (
            self._select()
            .where(WhatsAppMessage.direction == MessageDirection.INBOUND.value)
            .order_by(WhatsAppMessage.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt))


class ApiErrorLogRepository(TenantRepository[WhatsAppApiErrorLog]):
    model = WhatsAppApiErrorLog
    label = "API error"

    def recent(self, limit: int = 10) -> list[WhatsAppApiErrorLog]:
        stmt = self._select().order_by(WhatsAppApiErrorLog.created_at.desc(), WhatsAppApiErrorLog.id.desc()).limit(limit)
        return list(self.session.scalars(stmt))
