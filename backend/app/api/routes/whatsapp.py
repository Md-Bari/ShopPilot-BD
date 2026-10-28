from typing import Annotated

from fastapi import APIRouter, Query, Request, status

from app.api.deps import DbDep, IdempotencyKey, Messaging, SettingsDep, Tenant, rate_limit
from app.api.schemas import (
    ConversationDetailOut,
    ConversationOut,
    MessageOut,
    OkOut,
    OrderCustomerOut,
    Page,
    SendResultOut,
    TestRecipientOut,
    WhatsAppSettingsOut,
)
from app.api.serializers import conversation_out
from app.application.dto import ReplyCommand, SendTemplateCommand, SendTextCommand, TestRecipientCommand
from app.application.reports import ReportService
from app.application.whatsapp.configuration import WhatsAppSettingsService
from app.application.whatsapp.inbox import InboxService
from app.application.whatsapp.messaging import SendOutcome

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])
send_limit = rate_limit("whatsapp-send", 30, 60)


def _settings_service(request: Request, db, ctx, settings) -> WhatsAppSettingsService:
    return WhatsAppSettingsService(db, ctx, settings, request.app.state.whatsapp_gateway,
                                   request.app.state.credential_provider)


def _send_out(outcome: SendOutcome) -> SendResultOut:
    return SendResultOut(replayed=outcome.replayed, message=MessageOut.model_validate(outcome.message))


# --- settings -------------------------------------------------------------------------------------
@router.get("/settings", response_model=WhatsAppSettingsOut)
def get_settings_view(request: Request, ctx: Tenant, db: DbDep, settings: SettingsDep):
    return _settings_service(request, db, ctx, settings).view()


@router.post("/settings/connect", response_model=WhatsAppSettingsOut)
def connect(request: Request, ctx: Tenant, db: DbDep, settings: SettingsDep):
    service = _settings_service(request, db, ctx, settings)
    service.connect_environment_number()
    service.check_connection()
    return service.view()


@router.post("/settings/check", response_model=WhatsAppSettingsOut)
def check(request: Request, ctx: Tenant, db: DbDep, settings: SettingsDep):
    service = _settings_service(request, db, ctx, settings)
    service.check_connection()
    return service.view()


@router.post("/settings/disconnect", response_model=WhatsAppSettingsOut)
def disconnect(request: Request, ctx: Tenant, db: DbDep, settings: SettingsDep):
    service = _settings_service(request, db, ctx, settings)
    service.disconnect()
    return service.view()


@router.post("/test-recipients", response_model=TestRecipientOut, status_code=status.HTTP_201_CREATED)
def add_test_recipient(cmd: TestRecipientCommand, request: Request, ctx: Tenant, db: DbDep, settings: SettingsDep):
    return _settings_service(request, db, ctx, settings).add_test_recipient(cmd)


@router.delete("/test-recipients/{recipient_id}", response_model=OkOut)
def remove_test_recipient(recipient_id: int, request: Request, ctx: Tenant, db: DbDep, settings: SettingsDep):
    _settings_service(request, db, ctx, settings).remove_test_recipient(recipient_id)
    return OkOut()


@router.get("/stats")
def stats(ctx: Tenant, db: DbDep, days: Annotated[int, Query(ge=1, le=365)] = 30):
    return ReportService(db, ctx).whatsapp_stats(days)


# --- sending --------------------------------------------------------------------------------------
@router.post("/messages/send/", response_model=SendResultOut, dependencies=[send_limit])
@router.post("/messages/send", response_model=SendResultOut, dependencies=[send_limit], include_in_schema=False)
def send_text(cmd: SendTextCommand, messaging: Messaging, idempotency_key: IdempotencyKey = None):
    return _send_out(messaging.send_text(cmd, idempotency_key=idempotency_key))


@router.post("/messages/send-template/", response_model=SendResultOut, dependencies=[send_limit])
@router.post("/messages/send-template", response_model=SendResultOut, dependencies=[send_limit],
             include_in_schema=False)
def send_template(cmd: SendTemplateCommand, messaging: Messaging, idempotency_key: IdempotencyKey = None):
    return _send_out(messaging.send_template(cmd, idempotency_key=idempotency_key))


# --- inbox ----------------------------------------------------------------------------------------
@router.get("/conversations", response_model=Page[ConversationOut])
def list_conversations(
    ctx: Tenant, db: DbDep, messaging: Messaging,
    unread_only: bool = False,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 30,
):
    rows, total = InboxService(db, ctx, messaging).list(page=page, page_size=page_size, unread_only=unread_only)
    items = [conversation_out(r["conversation"], customer_name=r["customer_name"],
                              service_window_open=r["service_window_open"]) for r in rows]
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(conversation_id: int, ctx: Tenant, db: DbDep, messaging: Messaging):
    detail = InboxService(db, ctx, messaging).open(conversation_id)
    customer = detail["customer"]
    return ConversationDetailOut(
        conversation=conversation_out(detail["conversation"], customer_name=customer.name if customer else None,
                                      service_window_open=detail["service_window_open"]),
        customer=OrderCustomerOut.model_validate(customer) if customer else None,
        messages=[MessageOut.model_validate(m) for m in detail["messages"]],
        service_window_expires_at=detail["service_window_expires_at"],
        can_reply=detail["can_reply"],
        reply_blockers=detail["reply_blockers"],
    )


@router.post("/conversations/{conversation_id}/reply", response_model=SendResultOut, dependencies=[send_limit])
def reply(conversation_id: int, cmd: ReplyCommand, ctx: Tenant, db: DbDep, messaging: Messaging,
          idempotency_key: IdempotencyKey = None):
    return _send_out(InboxService(db, ctx, messaging).reply(conversation_id, cmd, idempotency_key=idempotency_key))
