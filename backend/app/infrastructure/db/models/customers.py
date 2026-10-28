from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base, TimestampMixin


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (
        # Normalized E.164 phone: one customer per number per business (duplicate detection).
        UniqueConstraint("business_id", "phone"),
        Index("ix_customers_business_name", "business_id", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(20), index=True)
    address: Mapped[str | None] = mapped_column(Text)
    area: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)

    consents: Mapped[list["CustomerCommunicationConsent"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan", order_by="CustomerCommunicationConsent.id"
    )


class CustomerCommunicationConsent(Base):
    """Append-only consent log. The latest row per (channel, purpose) is the current state."""

    __tablename__ = "customer_communication_consents"
    __table_args__ = (Index("ix_consents_lookup", "customer_id", "channel", "purpose", "recorded_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"))
    channel: Mapped[str] = mapped_column(String(20), default="whatsapp")
    purpose: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(30))
    note: Mapped[str | None] = mapped_column(String(255))
    recorded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    recorded_at: Mapped[datetime]

    customer: Mapped[Customer] = relationship(back_populates="consents")
