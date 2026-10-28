from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base, TimestampMixin


class SubscriptionPlan(TimestampMixin, Base):
    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    price_bdt: Mapped[Decimal]
    billing_period_days: Mapped[int] = mapped_column(default=30)
    trial_days: Mapped[int] = mapped_column(default=0)
    # NULL means unlimited.
    monthly_order_limit: Mapped[int | None]
    monthly_message_limit: Mapped[int | None]
    is_public: Mapped[bool] = mapped_column(default=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(default=0)


class BusinessSubscription(TimestampMixin, Base):
    """The current subscription of a business. Activation is manual (admin) in the MVP."""

    __tablename__ = "business_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), unique=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("subscription_plans.id"))
    requested_plan_id: Mapped[int | None] = mapped_column(ForeignKey("subscription_plans.id"))
    status: Mapped[str] = mapped_column(String(20))
    current_period_start: Mapped[datetime]
    current_period_end: Mapped[datetime]
    payment_reference: Mapped[str | None] = mapped_column(String(120))
    activated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    notes: Mapped[str | None] = mapped_column(Text)

    plan: Mapped[SubscriptionPlan] = relationship(foreign_keys=[plan_id])
    requested_plan: Mapped[SubscriptionPlan | None] = relationship(foreign_keys=[requested_plan_id])


class UsageRecord(TimestampMixin, Base):
    __tablename__ = "usage_records"
    __table_args__ = (UniqueConstraint("business_id", "metric", "period"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    metric: Mapped[str] = mapped_column(String(40))
    period: Mapped[str] = mapped_column(String(7))  # YYYY-MM (Asia/Dhaka)
    quantity: Mapped[int] = mapped_column(default=0)
