from sqlalchemy import func, or_, select

from app.domain.enums import ConsentStatus
from app.infrastructure.db.models import Customer, CustomerCommunicationConsent, Order
from app.infrastructure.repositories.base import TenantRepository


class CustomerRepository(TenantRepository[Customer]):
    model = Customer
    label = "Customer"

    def by_phone(self, phone_e164: str) -> Customer | None:
        return self.session.scalar(self._select().where(Customer.phone == phone_e164))

    def search(self, *, q: str | None, page: int, page_size: int):
        stmt = self._select()
        if q:
            like = f"%{q.strip()}%"
            digits = "".join(ch for ch in q if ch.isdigit())
            conditions = [Customer.name.ilike(like)]
            if digits:
                # Local numbers ("017...") are stored as +88017...; match on the trailing digits.
                conditions.append(Customer.phone.like(f"%{digits.lstrip('0')}%"))
            stmt = stmt.where(or_(*conditions))
        return self.paginate(stmt.order_by(Customer.created_at.desc(), Customer.id.desc()), page, page_size)

    def order_stats(self, customer_ids: list[int]) -> dict[int, tuple[int, object]]:
        if not customer_ids:
            return {}
        rows = self.session.execute(
            select(Order.customer_id, func.count(Order.id), func.max(Order.created_at))
            .where(Order.business_id == self.business_id, Order.customer_id.in_(customer_ids))
            .group_by(Order.customer_id)
        )
        return {cid: (count, last) for cid, count, last in rows}


class ConsentRepository(TenantRepository[CustomerCommunicationConsent]):
    model = CustomerCommunicationConsent
    label = "Consent record"

    def history(self, customer_id: int) -> list[CustomerCommunicationConsent]:
        stmt = (
            self._select()
            .where(CustomerCommunicationConsent.customer_id == customer_id)
            .order_by(CustomerCommunicationConsent.recorded_at.desc(), CustomerCommunicationConsent.id.desc())
        )
        return list(self.session.scalars(stmt))

    def current_status(self, customer_id: int, purpose: str, channel: str = "whatsapp") -> ConsentStatus | None:
        stmt = (
            self._select()
            .where(
                CustomerCommunicationConsent.customer_id == customer_id,
                CustomerCommunicationConsent.purpose == purpose,
                CustomerCommunicationConsent.channel == channel,
            )
            .order_by(CustomerCommunicationConsent.recorded_at.desc(), CustomerCommunicationConsent.id.desc())
            .limit(1)
        )
        latest = self.session.scalar(stmt)
        return ConsentStatus(latest.status) if latest else None
