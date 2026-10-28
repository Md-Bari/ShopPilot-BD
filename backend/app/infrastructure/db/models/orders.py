from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import OrderStatus, PaymentStatus
from app.infrastructure.db.base import Base, CreatedAtMixin, TimestampMixin
from app.infrastructure.db.models.customers import Customer
from app.infrastructure.db.models.identity import User


class Order(TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("business_id", "order_number"),
        Index("ix_orders_business_status", "business_id", "status"),
        Index("ix_orders_business_created", "business_id", "created_at"),
        CheckConstraint("total >= 0", name="total_non_negative"),
        CheckConstraint("amount_paid >= 0", name="amount_paid_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    order_number: Mapped[str] = mapped_column(String(30))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(20), default=OrderStatus.PENDING.value)
    payment_method_code: Mapped[str] = mapped_column(String(30), default="cod")
    payment_status: Mapped[str] = mapped_column(String(20), default=PaymentStatus.UNPAID.value)

    subtotal: Mapped[Decimal]
    delivery_charge: Mapped[Decimal]
    discount: Mapped[Decimal]
    total: Mapped[Decimal]
    cost_total: Mapped[Decimal]
    amount_paid: Mapped[Decimal] = mapped_column(default=Decimal("0.00"))

    shipping_address: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    confirmed_at: Mapped[datetime | None]
    shipped_at: Mapped[datetime | None]
    delivered_at: Mapped[datetime | None]
    cancelled_at: Mapped[datetime | None]
    returned_at: Mapped[datetime | None]

    customer: Mapped[Customer] = relationship()
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id"
    )
    status_history: Mapped[list["OrderStatusHistory"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderStatusHistory.id"
    )
    payments: Mapped[list["OrderPayment"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderPayment.id"
    )


class OrderItem(Base):
    """Snapshot of what was sold, so later product edits never change past orders."""

    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="quantity_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), index=True)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id", ondelete="SET NULL"), index=True)
    product_name: Mapped[str] = mapped_column(String(200))
    variant_label: Mapped[str] = mapped_column(String(80))
    sku: Mapped[str | None] = mapped_column(String(64))
    unit_price: Mapped[Decimal]
    unit_cost: Mapped[Decimal]
    quantity: Mapped[int]
    line_total: Mapped[Decimal]

    order: Mapped[Order] = relationship(back_populates="items")


class OrderStatusHistory(CreatedAtMixin, Base):
    __tablename__ = "order_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    changed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    note: Mapped[str | None] = mapped_column(String(500))

    order: Mapped[Order] = relationship(back_populates="status_history")
    changed_by: Mapped[User | None] = relationship()


class OrderPayment(CreatedAtMixin, Base):
    """Money actually collected. Collected revenue is the sum of these, not of order totals."""

    __tablename__ = "order_payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        Index("ix_order_payments_business_created", "business_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"))
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    amount: Mapped[Decimal]
    method_code: Mapped[str] = mapped_column(String(30))
    reference: Mapped[str | None] = mapped_column(String(120))
    recorded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    order: Mapped[Order] = relationship(back_populates="payments")
