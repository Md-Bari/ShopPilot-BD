from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import DbDep, IdempotencyKey, Messaging, SettingsDep, Tenant, rate_limit
from app.api.schemas import (
    MessageOut,
    NotificationPreviewOut,
    OrderDetailOut,
    OrderListItemOut,
    Page,
    SendResultOut,
)
from app.api.serializers import order_detail_out
from app.application.dto import (
    OrderCreateCommand,
    OrderNotificationCommand,
    OrderUpdateCommand,
    PaymentCommand,
    StatusChangeCommand,
)
from app.application.orders import OrderService
from app.application.whatsapp.notifications import OrderNotificationService
from app.domain.enums import NotificationKind, OrderStatus
from app.infrastructure.repositories.whatsapp import MessageRepository

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _service(db, ctx, settings) -> OrderService:
    return OrderService(db, ctx, enforce_limits=settings.enforce_subscription_limits)


def _detail(db, ctx, order) -> OrderDetailOut:
    return order_detail_out(order, MessageRepository(db, ctx.business_id).for_order(order.id))


@router.get("", response_model=Page[OrderListItemOut])
def list_orders(
    ctx: Tenant, db: DbDep, settings: SettingsDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    status_filter: Annotated[OrderStatus | None, Query(alias="status")] = None,
    customer_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    items, total = _service(db, ctx, settings).search(
        q=q, status=status_filter.value if status_filter else None, customer_id=customer_id,
        date_from=date_from, date_to=date_to, page=page, page_size=page_size)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=OrderDetailOut, status_code=status.HTTP_201_CREATED)
def create_order(cmd: OrderCreateCommand, ctx: Tenant, db: DbDep, settings: SettingsDep):
    return _detail(db, ctx, _service(db, ctx, settings).create(cmd))


@router.get("/{order_id}", response_model=OrderDetailOut)
def get_order(order_id: int, ctx: Tenant, db: DbDep, settings: SettingsDep):
    return _detail(db, ctx, _service(db, ctx, settings).get(order_id))


@router.patch("/{order_id}", response_model=OrderDetailOut)
def update_order(order_id: int, cmd: OrderUpdateCommand, ctx: Tenant, db: DbDep, settings: SettingsDep):
    return _detail(db, ctx, _service(db, ctx, settings).update(order_id, cmd))


@router.post("/{order_id}/status", response_model=OrderDetailOut)
def change_status(order_id: int, cmd: StatusChangeCommand, ctx: Tenant, db: DbDep, settings: SettingsDep):
    return _detail(db, ctx, _service(db, ctx, settings).change_status(order_id, cmd))


@router.post("/{order_id}/payments", response_model=OrderDetailOut)
def record_payment(order_id: int, cmd: PaymentCommand, ctx: Tenant, db: DbDep, settings: SettingsDep):
    return _detail(db, ctx, _service(db, ctx, settings).record_payment(order_id, cmd))


@router.get("/{order_id}/notifications/preview", response_model=NotificationPreviewOut)
def preview_notification(order_id: int, kind: NotificationKind, ctx: Tenant, db: DbDep, settings: SettingsDep,
                         messaging: Messaging, custom_text: Annotated[str | None, Query(max_length=4096)] = None):
    return OrderNotificationService(db, ctx, settings, messaging).preview(order_id, kind, custom_text)


@router.post("/{order_id}/notifications", response_model=SendResultOut,
             dependencies=[rate_limit("whatsapp-send", 30, 60)])
def send_notification(order_id: int, cmd: OrderNotificationCommand, ctx: Tenant, db: DbDep, settings: SettingsDep,
                      messaging: Messaging, idempotency_key: IdempotencyKey = None):
    outcome = OrderNotificationService(db, ctx, settings, messaging).send(order_id, cmd,
                                                                         idempotency_key=idempotency_key)
    return SendResultOut(replayed=outcome.replayed, message=MessageOut.model_validate(outcome.message))
