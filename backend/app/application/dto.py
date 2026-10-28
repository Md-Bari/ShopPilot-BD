"""Input commands for the use cases. The API layer uses these directly as request bodies,
so validation rules live in one place and the application layer does not import the API."""

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.domain.enums import ConsentPurpose, ConsentSource, ConsentStatus, NotificationKind, OrderStatus, Role

Str = Annotated[str, StringConstraints(strip_whitespace=True)]
NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
MoneyIn = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- auth -----------------------------------------------------------------------------------------
class RegisterCommand(Command):
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]
    full_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]


class LoginCommand(Command):
    email: EmailStr
    password: Annotated[str, Field(max_length=128)]


class PasswordResetRequestCommand(Command):
    email: EmailStr


class PasswordResetConfirmCommand(Command):
    token: Annotated[str, Field(min_length=10, max_length=200)]
    new_password: Annotated[str, Field(min_length=8, max_length=128)]


# --- business -------------------------------------------------------------------------------------
class BusinessCreateCommand(Command):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]
    phone: Str | None = None
    address: Annotated[str, StringConstraints(max_length=500)] | None = None


class BusinessUpdateCommand(Command):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)] | None = None
    phone: Str | None = None
    email: EmailStr | None = None
    address: Annotated[str, StringConstraints(max_length=500)] | None = None
    facebook_page_url: Annotated[str, StringConstraints(max_length=255)] | None = None
    order_prefix: Str | None = None
    default_delivery_charge: Annotated[int, Field(ge=0, le=100000)] | None = None


class MemberAddCommand(Command):
    email: EmailStr
    role: Role = Role.STAFF


class MemberRoleCommand(Command):
    role: Role


class PaymentMethodCommand(Command):
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=30)]
    label: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    is_active: bool = True


# --- catalog --------------------------------------------------------------------------------------
class VariantInput(Command):
    size: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] = ""
    color: Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)] = ""
    sku: Annotated[str, StringConstraints(strip_whitespace=True, max_length=64)] | None = None
    price: MoneyIn | None = None
    stock: Annotated[int, Field(ge=0, le=1_000_000)] = 0
    low_stock_threshold: Annotated[int, Field(ge=0, le=10_000)] = 3


class VariantUpdate(Command):
    size: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] | None = None
    color: Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)] | None = None
    sku: Annotated[str, StringConstraints(strip_whitespace=True, max_length=64)] | None = None
    price: MoneyIn | None = None
    stock: Annotated[int, Field(ge=0, le=1_000_000)] | None = None
    low_stock_threshold: Annotated[int, Field(ge=0, le=10_000)] | None = None
    is_active: bool | None = None


class ProductCreateCommand(Command):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    sku: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    description: Annotated[str, StringConstraints(max_length=5000)] | None = None
    price: MoneyIn
    cost_price: MoneyIn | None = None
    stock: Annotated[int, Field(ge=0, le=1_000_000)] = 0  # used when no variants are given
    variants: list[VariantInput] = Field(default_factory=list, max_length=100)


class ProductUpdateCommand(Command):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)] | None = None
    sku: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)] | None = None
    description: Annotated[str, StringConstraints(max_length=5000)] | None = None
    price: MoneyIn | None = None
    cost_price: MoneyIn | None = None


# --- customers ------------------------------------------------------------------------------------
class CustomerCreateCommand(Command):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
    phone: NonEmpty
    address: Annotated[str, StringConstraints(max_length=500)] | None = None
    area: Annotated[str, StringConstraints(max_length=100)] | None = None
    notes: Annotated[str, StringConstraints(max_length=1000)] | None = None


class CustomerUpdateCommand(Command):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)] | None = None
    phone: NonEmpty | None = None
    address: Annotated[str, StringConstraints(max_length=500)] | None = None
    area: Annotated[str, StringConstraints(max_length=100)] | None = None
    notes: Annotated[str, StringConstraints(max_length=1000)] | None = None


class ConsentCommand(Command):
    purpose: ConsentPurpose = ConsentPurpose.TRANSACTIONAL
    status: ConsentStatus
    source: ConsentSource
    note: Annotated[str, StringConstraints(max_length=255)] | None = None


# --- orders ---------------------------------------------------------------------------------------
class OrderItemInput(Command):
    variant_id: int
    quantity: Annotated[int, Field(ge=1, le=1000)]
    unit_price: MoneyIn | None = None  # optional negotiated price; defaults to catalog price


class NewCustomerInput(CustomerCreateCommand):
    pass


class OrderCreateCommand(Command):
    customer_id: int | None = None
    new_customer: NewCustomerInput | None = None
    items: list[OrderItemInput] = Field(min_length=1, max_length=50)
    delivery_charge: MoneyIn = Decimal("0")
    discount: MoneyIn = Decimal("0")
    payment_method_code: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] = "cod"
    shipping_address: Annotated[str, StringConstraints(max_length=500)] | None = None
    note: Annotated[str, StringConstraints(max_length=1000)] | None = None


class OrderUpdateCommand(Command):
    shipping_address: Annotated[str, StringConstraints(max_length=500)] | None = None
    note: Annotated[str, StringConstraints(max_length=1000)] | None = None


class StatusChangeCommand(Command):
    status: OrderStatus
    note: Annotated[str, StringConstraints(max_length=500)] | None = None


class PaymentCommand(Command):
    amount: Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
    method_code: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] | None = None
    reference: Annotated[str, StringConstraints(max_length=120)] | None = None


# --- whatsapp -------------------------------------------------------------------------------------
class SendTextCommand(Command):
    to: NonEmpty | None = None
    customer_id: int | None = None
    conversation_id: int | None = None
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4096)]
    order_id: int | None = None


class SendTemplateCommand(Command):
    to: NonEmpty | None = None
    customer_id: int | None = None
    template_name: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[a-z0-9_]{1,120}$")]
    language: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[a-zA-Z_]{2,15}$")] = "en"
    body_parameters: list[Annotated[str, StringConstraints(max_length=1024)]] = Field(default_factory=list, max_length=20)
    order_id: int | None = None


class ReplyCommand(Command):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4096)]


class OrderNotificationCommand(Command):
    kind: NotificationKind
    custom_text: Annotated[str, StringConstraints(strip_whitespace=True, max_length=4096)] | None = None


class TestRecipientCommand(Command):
    phone: NonEmpty
    label: Annotated[str, StringConstraints(max_length=80)] | None = None


# --- subscription ---------------------------------------------------------------------------------
class PlanRequestCommand(Command):
    plan_code: NonEmpty


class SubscriptionActivateCommand(Command):
    plan_code: NonEmpty
    months: Annotated[int, Field(ge=1, le=12)] = 1
    payment_reference: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
    notes: Annotated[str, StringConstraints(max_length=1000)] | None = None
