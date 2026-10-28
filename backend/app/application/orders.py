from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.context import TenantContext
from app.application.customers import CustomerService
from app.application.dto import OrderCreateCommand, OrderUpdateCommand, PaymentCommand, StatusChangeCommand
from app.application.subscriptions import SubscriptionService
from app.domain.clock import local_day_bounds, utcnow
from app.domain.enums import OrderStatus, UsageMetric
from app.domain.errors import ValidationError
from app.domain.order_rules import RESTOCK_STATUSES, assert_transition
from app.domain.phone import normalize_phone
from app.domain.pricing import ZERO, LineInput, calculate_totals, line_total, money, payment_status_for
from app.infrastructure.db.models import (
    Business,
    Order,
    OrderItem,
    OrderPayment,
    OrderStatusHistory,
    PaymentMethod,
)
from app.infrastructure.repositories.catalog import VariantRepository
from app.infrastructure.repositories.customers import CustomerRepository
from app.infrastructure.repositories.orders import OrderRepository

_STATUS_TIMESTAMPS = {
    OrderStatus.CONFIRMED: "confirmed_at",
    OrderStatus.SHIPPED: "shipped_at",
    OrderStatus.DELIVERED: "delivered_at",
    OrderStatus.CANCELLED: "cancelled_at",
    OrderStatus.RETURNED: "returned_at",
}


class OrderService:
    def __init__(self, session: Session, ctx: TenantContext, *, enforce_limits: bool = True):
        self.session = session
        self.ctx = ctx
        self.orders = OrderRepository(session, ctx.business_id)
        self.variants = VariantRepository(session, ctx.business_id)
        self.customers = CustomerRepository(session, ctx.business_id)
        self.subscriptions = SubscriptionService(session, ctx.business_id, enforce=enforce_limits)

    # --- queries ------------------------------------------------------------------------------
    def search(self, *, q=None, status=None, customer_id=None, date_from: date | None = None,
               date_to: date | None = None, page=1, page_size=20):
        created_from = local_day_bounds(date_from)[0] if date_from else None
        created_to = local_day_bounds(date_to)[1] if date_to else None
        return self.orders.search(q=q, status=status, customer_id=customer_id, created_from=created_from,
                                  created_to=created_to, page=page, page_size=page_size)

    def get(self, order_id: int) -> Order:
        order = self.orders.get_detailed(order_id)
        if order is None:
            self.orders.get_or_raise(order_id)  # raises NotFoundError
        return order

    # --- commands -----------------------------------------------------------------------------
    def create(self, cmd: OrderCreateCommand) -> Order:
        """Creates the order, its items, the first history entry and reserves stock atomically."""
        try:
            order = self._create(cmd)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return self.get(order.id)

    def _create(self, cmd: OrderCreateCommand) -> Order:
        self.subscriptions.check_and_record(UsageMetric.ORDERS)
        customer = self._resolve_customer(cmd)
        payment_code = self._validate_payment_method(cmd.payment_method_code)

        variant_ids = [item.variant_id for item in cmd.items]
        if len(set(variant_ids)) != len(variant_ids):
            raise ValidationError("Each product variant can only appear once in an order.")
        variants = self.variants.get_many_for_update(variant_ids)

        lines: list[tuple[LineInput, OrderItem]] = []
        for item in cmd.items:
            variant = variants.get(item.variant_id)
            if variant is None:
                raise ValidationError(f"Product variant {item.variant_id} was not found.")
            product = variant.product
            if product.status != "active" or not variant.is_active:
                raise ValidationError(f"'{product.name}' is not available for sale.")
            if variant.stock < item.quantity:
                raise ValidationError(
                    f"Only {variant.stock} in stock for {product.name} ({variant.label}).",
                    code="insufficient_stock",
                    details={"variant_id": variant.id, "available": variant.stock},
                )
            unit_price = money(item.unit_price if item.unit_price is not None else variant.effective_price)
            unit_cost = money(product.cost_price or ZERO)
            line = LineInput(unit_price=unit_price, quantity=item.quantity, unit_cost=unit_cost)
            lines.append((line, OrderItem(
                product_id=product.id, variant_id=variant.id, product_name=product.name,
                variant_label=variant.label, sku=variant.sku or product.sku, unit_price=unit_price,
                unit_cost=unit_cost, quantity=item.quantity, line_total=line_total(line),
            )))
            variant.stock -= item.quantity

        totals = calculate_totals([line for line, _ in lines], cmd.delivery_charge, cmd.discount)

        business = self.session.scalar(select(Business).where(Business.id == self.ctx.business_id).with_for_update())
        order_number = f"{business.order_prefix}-{business.next_order_number}"
        business.next_order_number += 1

        order = Order(
            order_number=order_number, customer_id=customer.id, status=OrderStatus.PENDING.value,
            payment_method_code=payment_code, subtotal=totals.subtotal, delivery_charge=totals.delivery_charge,
            discount=totals.discount, total=totals.total, cost_total=totals.cost_total, amount_paid=ZERO,
            shipping_address=cmd.shipping_address or customer.address, note=cmd.note,
            created_by_user_id=self.ctx.user_id,
        )
        order.items = [item for _, item in lines]
        order.status_history = [OrderStatusHistory(from_status=None, to_status=OrderStatus.PENDING.value,
                                                   changed_by_user_id=self.ctx.user_id, note="Order created")]
        self.orders.add(order)
        self.session.flush()
        return order

    def update(self, order_id: int, cmd: OrderUpdateCommand) -> Order:
        order = self.orders.get_or_raise(order_id)
        for key, value in cmd.model_dump(exclude_unset=True).items():
            setattr(order, key, value)
        self.session.commit()
        return self.get(order.id)

    def change_status(self, order_id: int, cmd: StatusChangeCommand) -> Order:
        try:
            order = self.orders.get_or_raise(order_id, for_update=True)
            current = OrderStatus(order.status)
            assert_transition(current, cmd.status)
            if cmd.status in RESTOCK_STATUSES:
                self._restock(order)
            order.status = cmd.status.value
            if attr := _STATUS_TIMESTAMPS.get(cmd.status):
                setattr(order, attr, utcnow())
            self.session.add(OrderStatusHistory(order_id=order.id, from_status=current.value,
                                                to_status=cmd.status.value, changed_by_user_id=self.ctx.user_id,
                                                note=cmd.note))
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.expire_all()
        return self.get(order_id)

    def record_payment(self, order_id: int, cmd: PaymentCommand) -> Order:
        try:
            order = self.orders.get_or_raise(order_id, for_update=True)
            if order.status == OrderStatus.CANCELLED.value:
                raise ValidationError("Cannot record a payment on a cancelled order.")
            amount = money(cmd.amount)
            if order.amount_paid + amount > order.total:
                raise ValidationError(
                    f"Payment exceeds the amount due (৳{order.total - order.amount_paid}).", code="overpayment"
                )
            method = self._validate_payment_method(cmd.method_code or order.payment_method_code)
            self.session.add(OrderPayment(business_id=self.ctx.business_id, order_id=order.id, amount=amount,
                                          method_code=method, reference=cmd.reference,
                                          recorded_by_user_id=self.ctx.user_id))
            order.amount_paid = money(order.amount_paid + amount)
            order.payment_status = payment_status_for(order.total, order.amount_paid).value
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.expire_all()
        return self.get(order_id)

    # --- helpers ------------------------------------------------------------------------------
    def _restock(self, order: Order) -> None:
        ids = [item.variant_id for item in order.items if item.variant_id]
        variants = self.variants.get_many_for_update(ids) if ids else {}
        for item in order.items:
            if item.variant_id in variants:
                variants[item.variant_id].stock += item.quantity

    def _resolve_customer(self, cmd: OrderCreateCommand):
        if cmd.customer_id and cmd.new_customer:
            raise ValidationError("Provide either customer_id or new_customer, not both.")
        if cmd.customer_id:
            return self.customers.get_or_raise(cmd.customer_id)
        if cmd.new_customer:
            # Reuse the existing customer when the phone number is already known (duplicate detection).
            existing = self.customers.by_phone(normalize_phone(cmd.new_customer.phone))
            if existing:
                return existing
            return CustomerService(self.session, self.ctx).create(cmd.new_customer, commit=False)
        raise ValidationError("A customer is required.")

    def _validate_payment_method(self, code: str) -> str:
        method = self.session.scalar(select(PaymentMethod).where(
            PaymentMethod.business_id == self.ctx.business_id, PaymentMethod.code == code,
            PaymentMethod.is_active.is_(True)))
        if not method:
            raise ValidationError(f"Payment method '{code}' is not enabled for this business.")
        return method.code
