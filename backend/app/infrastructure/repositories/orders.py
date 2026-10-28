from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.infrastructure.db.models import Customer, Order, OrderStatusHistory
from app.infrastructure.repositories.base import TenantRepository


class OrderRepository(TenantRepository[Order]):
    model = Order
    label = "Order"

    def _select(self):
        return super()._select().options(selectinload(Order.customer))

    def get_detailed(self, order_id: int) -> Order | None:
        stmt = (
            self._select()
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items),
                selectinload(Order.payments),
                selectinload(Order.status_history).selectinload(OrderStatusHistory.changed_by),
            )
        )
        return self.session.scalar(stmt)

    def search(
        self,
        *,
        q: str | None,
        status: str | None,
        customer_id: int | None,
        created_from: datetime | None,
        created_to: datetime | None,
        page: int,
        page_size: int,
    ):
        stmt = self._select()
        if q:
            like = f"%{q.strip()}%"
            digits = "".join(ch for ch in q if ch.isdigit()).lstrip("0")
            conditions = [Order.order_number.ilike(like), Customer.name.ilike(like)]
            if digits:
                conditions.append(Customer.phone.like(f"%{digits}%"))
            stmt = stmt.join(Order.customer).where(or_(*conditions))
        if status:
            stmt = stmt.where(Order.status == status)
        if customer_id:
            stmt = stmt.where(Order.customer_id == customer_id)
        if created_from:
            stmt = stmt.where(Order.created_at >= created_from)
        if created_to:
            stmt = stmt.where(Order.created_at < created_to)
        return self.paginate(stmt.order_by(Order.created_at.desc(), Order.id.desc()), page, page_size)

    def in_range(self, start: datetime, end: datetime) -> list[Order]:
        stmt = (
            select(Order)
            .where(Order.business_id == self.business_id, Order.created_at >= start, Order.created_at < end)
            .options(selectinload(Order.items))
        )
        return list(self.session.scalars(stmt))

    def recent(self, limit: int) -> list[Order]:
        return list(self.session.scalars(self._select().order_by(Order.created_at.desc(), Order.id.desc()).limit(limit)))

    def for_customer(self, customer_id: int, limit: int = 50) -> list[Order]:
        stmt = self._select().where(Order.customer_id == customer_id).order_by(Order.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt))
