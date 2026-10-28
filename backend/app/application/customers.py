from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.context import TenantContext
from app.application.dto import ConsentCommand, CustomerCreateCommand, CustomerUpdateCommand
from app.domain.clock import utcnow
from app.domain.enums import ConsentPurpose
from app.domain.errors import ConflictError
from app.domain.phone import normalize_phone
from app.infrastructure.db.models import Customer, CustomerCommunicationConsent
from app.infrastructure.repositories.customers import ConsentRepository, CustomerRepository
from app.infrastructure.repositories.orders import OrderRepository
from app.infrastructure.repositories.whatsapp import ConversationRepository


def duplicate_error(existing: Customer) -> ConflictError:
    return ConflictError(
        "A customer with this phone number already exists.",
        code="duplicate_customer",
        details={"existing_customer_id": existing.id, "existing_customer_name": existing.name},
    )


class CustomerService:
    def __init__(self, session: Session, ctx: TenantContext):
        self.session = session
        self.ctx = ctx
        self.customers = CustomerRepository(session, ctx.business_id)
        self.consents = ConsentRepository(session, ctx.business_id)

    def search(self, *, q: str | None = None, page: int = 1, page_size: int = 20):
        items, total = self.customers.search(q=q, page=page, page_size=page_size)
        stats = self.customers.order_stats([c.id for c in items])
        return items, total, stats

    def get(self, customer_id: int) -> Customer:
        return self.customers.get_or_raise(customer_id)

    def find_duplicate(self, phone: str) -> Customer | None:
        return self.customers.by_phone(normalize_phone(phone))

    def create(self, cmd: CustomerCreateCommand, *, commit: bool = True) -> Customer:
        phone = normalize_phone(cmd.phone)
        existing = self.customers.by_phone(phone)
        if existing:
            raise duplicate_error(existing)
        customer = Customer(name=cmd.name, phone=phone, address=cmd.address, area=cmd.area, notes=cmd.notes)
        self.customers.add(customer)
        self._link_conversation(customer)
        if commit:
            self._commit(phone)
        else:
            self.session.flush()
        return customer

    def update(self, customer_id: int, cmd: CustomerUpdateCommand) -> Customer:
        customer = self.get(customer_id)
        changes = cmd.model_dump(exclude_unset=True)
        if "phone" in changes:
            changes["phone"] = normalize_phone(changes["phone"])
            existing = self.customers.by_phone(changes["phone"])
            if existing and existing.id != customer.id:
                raise duplicate_error(existing)
        for key, value in changes.items():
            setattr(customer, key, value)
        self._commit(customer.phone)
        return customer

    def detail(self, customer_id: int) -> dict:
        customer = self.get(customer_id)
        orders = OrderRepository(self.session, self.ctx.business_id).for_customer(customer.id)
        return {
            "customer": customer,
            "orders": orders,
            "consents": self.consents.history(customer.id),
            "transactional_consent": self.consents.current_status(customer.id, ConsentPurpose.TRANSACTIONAL.value),
            "marketing_consent": self.consents.current_status(customer.id, ConsentPurpose.MARKETING.value),
        }

    def record_consent(self, customer_id: int, cmd: ConsentCommand) -> CustomerCommunicationConsent:
        customer = self.get(customer_id)
        record = CustomerCommunicationConsent(
            customer_id=customer.id, channel="whatsapp", purpose=cmd.purpose.value, status=cmd.status.value,
            source=cmd.source.value, note=cmd.note, recorded_by_user_id=self.ctx.user_id, recorded_at=utcnow(),
        )
        self.consents.add(record)
        self.session.commit()
        return record

    def _link_conversation(self, customer: Customer) -> None:
        conversation = ConversationRepository(self.session, self.ctx.business_id).by_wa_id(customer.phone)
        if conversation and conversation.customer_id is None:
            self.session.flush()
            conversation.customer_id = customer.id

    def _commit(self, phone: str) -> None:
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            existing = self.customers.by_phone(phone)
            if existing:
                raise duplicate_error(existing) from exc
            raise ConflictError("Could not save customer.") from exc
