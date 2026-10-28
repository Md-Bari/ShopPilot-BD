"""Dashboard and reports.

Definitions (kept deliberately separate so a placed order is never shown as a sale):
- Gross order value: sum of totals of orders placed in the period, excluding cancelled orders.
- Collected revenue: money actually recorded as received (OrderPayment rows) in the period.
- Estimated profit: for orders delivered in the period, subtotal - discount - product cost.
  Returned orders are excluded. Delivery charges are treated as pass-through.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.context import TenantContext
from app.domain.clock import local_day_bounds, local_today, to_local_date, utcnow
from app.domain.enums import MessageStatus, OrderStatus
from app.domain.errors import ValidationError
from app.domain.pricing import ZERO, estimated_profit, money
from app.infrastructure.db.models import Order, OrderPayment
from app.infrastructure.repositories.catalog import VariantRepository
from app.infrastructure.repositories.orders import OrderRepository
from app.infrastructure.repositories.whatsapp import MessageRepository

MAX_REPORT_DAYS = 366


class ReportService:
    def __init__(self, session: Session, ctx: TenantContext):
        self.session = session
        self.ctx = ctx
        self.orders = OrderRepository(session, ctx.business_id)
        self.messages = MessageRepository(session, ctx.business_id)

    # --- building blocks ----------------------------------------------------------------------
    def _collected(self, start: datetime, end: datetime) -> object:
        value = self.session.scalar(
            select(func.coalesce(func.sum(OrderPayment.amount), 0)).where(
                OrderPayment.business_id == self.ctx.business_id,
                OrderPayment.created_at >= start, OrderPayment.created_at < end,
            )
        )
        return money(value or 0)

    def _profit(self, start: datetime, end: datetime) -> object:
        rows = self.session.execute(
            select(Order.subtotal, Order.discount, Order.cost_total).where(
                Order.business_id == self.ctx.business_id,
                Order.status == OrderStatus.DELIVERED.value,
                Order.delivered_at >= start, Order.delivered_at < end,
            )
        )
        return money(sum((estimated_profit(s, d, c) for s, d, c in rows), ZERO))

    def whatsapp_stats(self, days: int = 30) -> dict:
        counts = self.messages.outbound_status_counts(utcnow() - timedelta(days=days))
        total = sum(counts.values())
        delivered_or_read = counts.get(MessageStatus.DELIVERED.value, 0) + counts.get(MessageStatus.READ.value, 0)
        return {
            "period_days": days,
            "outbound_total": total,
            "by_status": counts,
            "inbound_total": self.messages.inbound_count(utcnow() - timedelta(days=days)),
            "delivery_rate": round(delivered_or_read / total, 3) if total else None,
        }

    # --- dashboard ----------------------------------------------------------------------------
    def dashboard(self) -> dict:
        today = local_today()
        day_start, day_end = local_day_bounds(today)
        month_start = local_day_bounds(today.replace(day=1))[0]
        recent_start = local_day_bounds(today - timedelta(days=29))[0]

        today_orders = self.orders.in_range(day_start, day_end)
        month_orders = self.orders.in_range(month_start, day_end)
        status_counts = dict(self.session.execute(
            select(Order.status, func.count(Order.id))
            .where(Order.business_id == self.ctx.business_id, Order.created_at >= recent_start)
            .group_by(Order.status)
        ).all())
        pending = self.session.scalar(select(func.count(Order.id)).where(
            Order.business_id == self.ctx.business_id, Order.status == OrderStatus.PENDING.value)) or 0

        low_stock = VariantRepository(self.session, self.ctx.business_id).low_stock(limit=10)

        activity = [
            {"type": "order", "at": o.created_at, "title": f"Order {o.order_number}",
             "subtitle": f"{o.customer.name} · ৳{o.total}", "order_id": o.id, "status": o.status}
            for o in self.orders.recent(8)
        ] + [
            {"type": "message", "at": m.created_at, "title": "WhatsApp message",
             "subtitle": (m.text or f"[{m.message_type}]")[:80], "conversation_id": m.conversation_id}
            for m in self.messages.recent_inbound(8)
        ]
        activity.sort(key=lambda a: a["at"], reverse=True)

        return {
            "date": today,
            "today": {
                "orders": len(today_orders),
                "gross_order_value": _gross(today_orders),
                "collected_revenue": self._collected(day_start, day_end),
            },
            "month_to_date": {
                "orders": len(month_orders),
                "gross_order_value": _gross(month_orders),
                "collected_revenue": self._collected(month_start, day_end),
                "estimated_profit": self._profit(month_start, day_end),
            },
            "pending_confirmations": pending,
            "last_30_days_status_counts": {s.value: status_counts.get(s.value, 0) for s in OrderStatus},
            "low_stock": [
                {"variant_id": v.id, "product_id": v.product_id, "product_name": v.product.name,
                 "variant_label": v.label, "stock": v.stock, "threshold": v.low_stock_threshold}
                for v in low_stock
            ],
            "recent_activity": activity[:10],
            "whatsapp": self.whatsapp_stats(),
        }

    # --- sales report -------------------------------------------------------------------------
    def sales_report(self, date_from: date, date_to: date) -> dict:
        if date_to < date_from:
            raise ValidationError("date_to must be on or after date_from.")
        if (date_to - date_from).days >= MAX_REPORT_DAYS:
            raise ValidationError(f"Reports can cover at most {MAX_REPORT_DAYS} days.")
        start, end = local_day_bounds(date_from)[0], local_day_bounds(date_to)[1]
        orders = self.orders.in_range(start, end)

        by_status: dict[str, dict] = {s.value: {"count": 0, "value": ZERO} for s in OrderStatus}
        daily: dict[date, dict] = {}
        day = date_from
        while day <= date_to:
            daily[day] = {"date": day, "orders": 0, "gross_order_value": ZERO, "collected_revenue": ZERO}
            day += timedelta(days=1)
        products: dict[str, dict] = defaultdict(lambda: {"quantity": 0, "value": ZERO})

        for order in orders:
            by_status[order.status]["count"] += 1
            by_status[order.status]["value"] += order.total
            bucket = daily[to_local_date(order.created_at)]
            bucket["orders"] += 1
            if order.status != OrderStatus.CANCELLED.value:
                bucket["gross_order_value"] += order.total
                for item in order.items:
                    key = item.product_name
                    products[key]["quantity"] += item.quantity
                    products[key]["value"] += item.line_total

        payments = self.session.execute(select(OrderPayment.created_at, OrderPayment.amount).where(
            OrderPayment.business_id == self.ctx.business_id,
            OrderPayment.created_at >= start, OrderPayment.created_at < end))
        for created_at, amount in payments:
            daily[to_local_date(created_at)]["collected_revenue"] += amount

        top_products = sorted(
            ({"product_name": name, "quantity": v["quantity"], "value": money(v["value"])} for name, v in products.items()),
            key=lambda p: p["quantity"], reverse=True,
        )[:10]

        return {
            "date_from": date_from,
            "date_to": date_to,
            "orders": len(orders),
            "gross_order_value": _gross(orders),
            "collected_revenue": self._collected(start, end),
            "estimated_profit": self._profit(start, end),
            "by_status": {k: {"count": v["count"], "value": money(v["value"])} for k, v in by_status.items()},
            "daily": [{**d, "gross_order_value": money(d["gross_order_value"]),
                       "collected_revenue": money(d["collected_revenue"])} for d in daily.values()],
            "top_products": top_products,
        }


def _gross(orders: list[Order]):
    return money(sum((o.total for o in orders if o.status != OrderStatus.CANCELLED.value), ZERO))
