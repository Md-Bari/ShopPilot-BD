"""Response models. Request bodies are the application-layer commands in app.application.dto."""

from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class OkOut(BaseModel):
    ok: bool = True
    message: str | None = None


# --- identity -------------------------------------------------------------------------------------
class UserOut(Out):
    id: int
    email: str
    full_name: str
    is_superuser: bool
    preferred_language: str


class MembershipOut(BaseModel):
    business_id: int
    business_name: str
    role: str


class MeOut(BaseModel):
    user: UserOut
    memberships: list[MembershipOut]


class BusinessOut(Out):
    id: int
    name: str
    slug: str
    phone: str | None
    email: str | None
    address: str | None
    facebook_page_url: str | None
    timezone: str
    currency: str
    order_prefix: str
    default_delivery_charge: int
    created_at: datetime


class MemberOut(BaseModel):
    id: int
    user_id: int
    email: str
    full_name: str
    role: str


class PaymentMethodOut(Out):
    id: int
    code: str
    label: str
    is_active: bool


# --- catalog --------------------------------------------------------------------------------------
class VariantOut(Out):
    id: int
    sku: str | None
    size: str
    color: str
    label: str
    price: Decimal | None
    effective_price: Decimal
    stock: int
    low_stock_threshold: int
    is_active: bool


class ProductOut(Out):
    id: int
    name: str
    sku: str
    description: str | None
    price: Decimal
    cost_price: Decimal | None
    status: str
    image_url: str | None = None
    total_stock: int = 0
    variants: list[VariantOut]
    created_at: datetime
    updated_at: datetime


class ImportSummaryOut(BaseModel):
    products_created: int
    products_updated: int
    variants_created: int
    variants_updated: int
    errors: list[dict]


# --- customers ------------------------------------------------------------------------------------
class CustomerOut(Out):
    id: int
    name: str
    phone: str
    address: str | None
    area: str | None
    notes: str | None
    created_at: datetime
    order_count: int = 0
    last_order_at: datetime | None = None


class ConsentOut(Out):
    id: int
    channel: str
    purpose: str
    status: str
    source: str
    note: str | None
    recorded_at: datetime


class OrderSummaryOut(Out):
    id: int
    order_number: str
    status: str
    payment_status: str
    total: Decimal
    amount_paid: Decimal
    created_at: datetime


class CustomerDetailOut(BaseModel):
    customer: CustomerOut
    orders: list[OrderSummaryOut]
    consents: list[ConsentOut]
    transactional_consent: str | None
    marketing_consent: str | None


class DuplicateCheckOut(BaseModel):
    normalized_phone: str
    duplicate: CustomerOut | None


# --- orders ---------------------------------------------------------------------------------------
class OrderCustomerOut(Out):
    id: int
    name: str
    phone: str


class OrderListItemOut(Out):
    id: int
    order_number: str
    status: str
    payment_status: str
    payment_method_code: str
    total: Decimal
    amount_paid: Decimal
    customer: OrderCustomerOut
    created_at: datetime


class OrderItemOut(Out):
    id: int
    product_id: int | None
    variant_id: int | None
    product_name: str
    variant_label: str
    sku: str | None
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class StatusHistoryOut(Out):
    id: int
    from_status: str | None
    to_status: str
    note: str | None
    changed_by_name: str | None = None
    created_at: datetime


class PaymentOut(Out):
    id: int
    amount: Decimal
    method_code: str
    reference: str | None
    created_at: datetime


class MessageOut(Out):
    id: int
    conversation_id: int
    order_id: int | None
    direction: str
    message_type: str
    text: str | None
    template_name: str | None
    notification_kind: str | None
    status: str
    status_updated_at: datetime | None
    error_code: str | None
    error_title: str | None
    error_detail: str | None
    safe_metadata: dict | None
    created_at: datetime


class OrderDetailOut(OrderListItemOut):
    subtotal: Decimal
    delivery_charge: Decimal
    discount: Decimal
    shipping_address: str | None
    note: str | None
    confirmed_at: datetime | None
    shipped_at: datetime | None
    delivered_at: datetime | None
    cancelled_at: datetime | None
    returned_at: datetime | None
    items: list[OrderItemOut]
    payments: list[PaymentOut]
    status_history: list[StatusHistoryOut] = Field(default_factory=list)
    allowed_next_statuses: list[str] = Field(default_factory=list)
    messages: list[MessageOut] = Field(default_factory=list)


# --- whatsapp -------------------------------------------------------------------------------------
class SendResultOut(BaseModel):
    replayed: bool
    message: MessageOut


class NotificationPreviewOut(BaseModel):
    kind: str
    order_id: int
    order_number: str
    recipient_phone: str
    recipient_name: str
    channel: str
    template_name: str | None
    template_language: str | None
    parameters: list[str]
    text: str
    mode: str
    service_window_open: bool
    service_window_expires_at: datetime | None
    transactional_consent: str | None
    can_send: bool
    blockers: list[str]


class ConversationOut(BaseModel):
    id: int
    wa_id: str
    contact_name: str | None
    customer_id: int | None
    customer_name: str | None
    last_message_at: datetime | None
    last_message_preview: str | None
    last_inbound_at: datetime | None
    unread_count: int
    service_window_open: bool


class ConversationDetailOut(BaseModel):
    conversation: ConversationOut
    customer: OrderCustomerOut | None
    messages: list[MessageOut]
    service_window_expires_at: datetime | None
    can_reply: bool
    reply_blockers: list[str]


class WhatsAppConfigOut(Out):
    phone_number_id: str
    waba_id: str | None
    display_phone_number: str | None
    verified_name: str | None
    mode: str
    credential_source: str
    is_enabled: bool
    last_check_at: datetime | None
    last_check_ok: bool | None
    last_check_error: str | None


class TestRecipientOut(Out):
    id: int
    phone: str
    label: str | None


class ApiErrorOut(Out):
    id: int
    operation: str
    http_status: int | None
    error_code: str | None
    error_kind: str | None
    message: str
    fbtrace_id: str | None
    created_at: datetime


class WhatsAppSettingsOut(BaseModel):
    state: str
    connected: bool
    environment: dict
    configuration: WhatsAppConfigOut | None
    webhook: dict
    templates: list[dict]
    test_recipients: list[TestRecipientOut]
    recent_errors: list[ApiErrorOut]


# --- subscription ---------------------------------------------------------------------------------
class PlanOut(Out):
    code: str
    name: str
    price_bdt: Decimal
    billing_period_days: int
    monthly_order_limit: int | None
    monthly_message_limit: int | None
    is_public: bool


class SubscriptionOut(BaseModel):
    status: str | None
    is_paid: bool
    plan: PlanOut | None
    requested_plan: PlanOut | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    payment_reference: str | None
    usage: dict[str, int]
    plans: list[PlanOut]


class AdminSubscriptionOut(BaseModel):
    business_id: int
    business_name: str
    status: str
    plan_code: str
    requested_plan_code: str | None
    current_period_end: datetime
