from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import CredentialSource, WhatsAppMode
from app.infrastructure.db.base import Base, CreatedAtMixin, JSONType, TimestampMixin


class WhatsAppConfiguration(TimestampMixin, Base):
    """Links a business to a WhatsApp phone number id. Secrets are never stored here in the MVP:
    `credential_source=environment` means the token comes from server environment variables."""

    __tablename__ = "whatsapp_configurations"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), unique=True)
    phone_number_id: Mapped[str] = mapped_column(String(64), unique=True)
    waba_id: Mapped[str | None] = mapped_column(String(64))
    display_phone_number: Mapped[str | None] = mapped_column(String(32))
    verified_name: Mapped[str | None] = mapped_column(String(150))
    mode: Mapped[str] = mapped_column(String(20), default=WhatsAppMode.TEST.value)
    credential_source: Mapped[str] = mapped_column(String(30), default=CredentialSource.ENVIRONMENT.value)
    is_enabled: Mapped[bool] = mapped_column(default=True)
    last_check_at: Mapped[datetime | None]
    last_check_ok: Mapped[bool | None]
    last_check_error: Mapped[str | None] = mapped_column(Text)
    webhook_verified_at: Mapped[datetime | None]
    last_webhook_at: Mapped[datetime | None]


class WhatsAppTestRecipient(CreatedAtMixin, Base):
    __tablename__ = "whatsapp_test_recipients"
    __table_args__ = (UniqueConstraint("business_id", "phone"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    phone: Mapped[str] = mapped_column(String(20))
    label: Mapped[str | None] = mapped_column(String(80))


class WhatsAppConversation(TimestampMixin, Base):
    __tablename__ = "whatsapp_conversations"
    __table_args__ = (
        UniqueConstraint("business_id", "wa_id"),
        Index("ix_wa_conversations_business_last", "business_id", "last_message_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), index=True)
    wa_id: Mapped[str] = mapped_column(String(32))  # E.164
    contact_name: Mapped[str | None] = mapped_column(String(150))
    last_inbound_at: Mapped[datetime | None]
    last_message_at: Mapped[datetime | None]
    last_message_preview: Mapped[str | None] = mapped_column(String(200))
    unread_count: Mapped[int] = mapped_column(default=0)


class WhatsAppMessage(CreatedAtMixin, Base):
    __tablename__ = "whatsapp_messages"
    __table_args__ = (
        UniqueConstraint("business_id", "idempotency_key"),
        Index("ix_wa_messages_conversation_created", "conversation_id", "created_at"),
        Index("ix_wa_messages_business_status", "business_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("whatsapp_conversations.id", ondelete="CASCADE"))
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), index=True)
    direction: Mapped[str] = mapped_column(String(10))
    wa_message_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(80))
    message_type: Mapped[str] = mapped_column(String(30))
    text: Mapped[str | None] = mapped_column(Text)
    template_name: Mapped[str | None] = mapped_column(String(120))
    template_language: Mapped[str | None] = mapped_column(String(15))
    notification_kind: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20))
    status_updated_at: Mapped[datetime | None]
    error_code: Mapped[str | None] = mapped_column(String(20))
    error_title: Mapped[str | None] = mapped_column(String(255))
    error_detail: Mapped[str | None] = mapped_column(Text)
    sent_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    wa_timestamp: Mapped[datetime | None]
    safe_metadata: Mapped[dict | None] = mapped_column(JSONType)

    conversation: Mapped[WhatsAppConversation] = relationship()


class WebhookEvent(Base):
    """One row per processed webhook item (message or status). `event_key` makes processing idempotent.
    Only a small, non-sensitive summary is kept; rows are purged after the retention period."""

    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_key: Mapped[str] = mapped_column(String(200), unique=True)
    event_type: Mapped[str] = mapped_column(String(30))
    business_id: Mapped[int | None] = mapped_column(ForeignKey("businesses.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    error: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[dict | None] = mapped_column(JSONType)
    received_at: Mapped[datetime] = mapped_column(index=True)


class WhatsAppApiErrorLog(CreatedAtMixin, Base):
    __tablename__ = "whatsapp_api_error_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    operation: Mapped[str] = mapped_column(String(50))
    http_status: Mapped[int | None]
    error_code: Mapped[str | None] = mapped_column(String(20))
    error_kind: Mapped[str | None] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(Text)
    fbtrace_id: Mapped[str | None] = mapped_column(String(64))
