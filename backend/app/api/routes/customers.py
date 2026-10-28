from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import DbDep, Tenant
from app.api.schemas import ConsentOut, CustomerDetailOut, CustomerOut, DuplicateCheckOut, OrderSummaryOut, Page
from app.application.customers import CustomerService
from app.application.dto import ConsentCommand, CustomerCreateCommand, CustomerUpdateCommand
from app.domain.phone import normalize_phone

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=Page[CustomerOut])
def list_customers(
    ctx: Tenant, db: DbDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    items, total, stats = CustomerService(db, ctx).search(q=q, page=page, page_size=page_size)
    out = []
    for c in items:
        row = CustomerOut.model_validate(c)
        row.order_count, row.last_order_at = stats.get(c.id, (0, None))
        out.append(row)
    return Page(items=out, total=total, page=page, page_size=page_size)


@router.get("/check-duplicate", response_model=DuplicateCheckOut)
def check_duplicate(ctx: Tenant, db: DbDep, phone: Annotated[str, Query(min_length=3, max_length=30)]):
    duplicate = CustomerService(db, ctx).find_duplicate(phone)
    return DuplicateCheckOut(normalized_phone=normalize_phone(phone),
                             duplicate=CustomerOut.model_validate(duplicate) if duplicate else None)


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(cmd: CustomerCreateCommand, ctx: Tenant, db: DbDep):
    return CustomerService(db, ctx).create(cmd)


@router.get("/{customer_id}", response_model=CustomerDetailOut)
def get_customer(customer_id: int, ctx: Tenant, db: DbDep):
    detail = CustomerService(db, ctx).detail(customer_id)
    customer = CustomerOut.model_validate(detail["customer"])
    customer.order_count = len(detail["orders"])
    return CustomerDetailOut(
        customer=customer,
        orders=[OrderSummaryOut.model_validate(o) for o in detail["orders"]],
        consents=[ConsentOut.model_validate(c) for c in detail["consents"]],
        transactional_consent=detail["transactional_consent"],
        marketing_consent=detail["marketing_consent"],
    )


@router.patch("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, cmd: CustomerUpdateCommand, ctx: Tenant, db: DbDep):
    return CustomerService(db, ctx).update(customer_id, cmd)


@router.post("/{customer_id}/consents", response_model=ConsentOut, status_code=status.HTTP_201_CREATED)
def record_consent(customer_id: int, cmd: ConsentCommand, ctx: Tenant, db: DbDep):
    return CustomerService(db, ctx).record_consent(customer_id, cmd)
