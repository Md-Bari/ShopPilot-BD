"""Import every model so Base.metadata is complete (used by Alembic and tests)."""

from app.infrastructure.db.models.billing import BusinessSubscription, SubscriptionPlan, UsageRecord
from app.infrastructure.db.models.catalog import Product, ProductVariant
from app.infrastructure.db.models.customers import Customer, CustomerCommunicationConsent
from app.infrastructure.db.models.identity import Business, Membership, PasswordResetToken, PaymentMethod, User
from app.infrastructure.db.models.orders import Order, OrderItem, OrderPayment, OrderStatusHistory
from app.infrastructure.db.models.whatsapp import (
    WebhookEvent,
    WhatsAppApiErrorLog,
    WhatsAppConfiguration,
    WhatsAppConversation,
    WhatsAppMessage,
    WhatsAppTestRecipient,
)

__all__ = [
    "Business",
    "BusinessSubscription",
    "Customer",
    "CustomerCommunicationConsent",
    "Membership",
    "Order",
    "OrderItem",
    "OrderPayment",
    "OrderStatusHistory",
    "PasswordResetToken",
    "PaymentMethod",
    "Product",
    "ProductVariant",
    "SubscriptionPlan",
    "UsageRecord",
    "User",
    "WebhookEvent",
    "WhatsAppApiErrorLog",
    "WhatsAppConfiguration",
    "WhatsAppConversation",
    "WhatsAppMessage",
    "WhatsAppTestRecipient",
]
