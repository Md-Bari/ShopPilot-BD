from enum import StrEnum


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    STAFF = "staff"


MANAGER_ROLES = (Role.OWNER, Role.ADMIN)
ALL_ROLES = (Role.OWNER, Role.ADMIN, Role.STAFF)


class ProductStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class OrderStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class PaymentStatus(StrEnum):
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"


class MessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageStatus(StrEnum):
    PENDING = "pending"  # stored locally, request to Meta not yet answered
    ACCEPTED = "accepted"  # Meta accepted the request and returned a message id
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    UNKNOWN = "unknown"  # network timeout: Meta may or may not have sent it
    RECEIVED = "received"  # inbound messages


class ConsentPurpose(StrEnum):
    TRANSACTIONAL = "transactional"  # order updates
    MARKETING = "marketing"


class ConsentStatus(StrEnum):
    GRANTED = "granted"
    REVOKED = "revoked"


class ConsentSource(StrEnum):
    IN_PERSON = "in_person"
    PHONE_CALL = "phone_call"
    WHATSAPP = "whatsapp"
    FACEBOOK = "facebook"
    WEBSITE = "website"
    OTHER = "other"


class WhatsAppMode(StrEnum):
    TEST = "test"
    PRODUCTION = "production"


class CredentialSource(StrEnum):
    ENVIRONMENT = "environment"
    # Future phase: per-business encrypted credentials stored in the database.
    ENCRYPTED_DATABASE = "encrypted_database"


class NotificationKind(StrEnum):
    ORDER_CONFIRMED = "order_confirmed"
    ORDER_SHIPPED = "order_shipped"
    ORDER_DELIVERED = "order_delivered"
    CUSTOM = "custom"


class SubscriptionStatus(StrEnum):
    TRIAL = "trial"
    PENDING_PAYMENT = "pending_payment"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class UsageMetric(StrEnum):
    ORDERS = "orders"
    WHATSAPP_MESSAGES = "whatsapp_messages"


class WebhookEventStatus(StrEnum):
    PROCESSED = "processed"
    IGNORED = "ignored"
    FAILED = "failed"
