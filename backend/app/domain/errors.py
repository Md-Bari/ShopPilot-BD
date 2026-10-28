"""Domain errors. The API layer maps each class to an HTTP status code."""

from typing import Any


class DomainError(Exception):
    code = "domain_error"

    def __init__(self, message: str, *, code: str | None = None, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details or {}


class ValidationError(DomainError):
    code = "validation_error"


class NotFoundError(DomainError):
    code = "not_found"


class ConflictError(DomainError):
    code = "conflict"


class AuthenticationError(DomainError):
    code = "authentication_failed"


class PermissionDeniedError(DomainError):
    code = "permission_denied"


class PlanLimitError(DomainError):
    code = "plan_limit_exceeded"


class MessagingPolicyError(DomainError):
    """A WhatsApp send was blocked by consent, test-recipient or 24h-window rules."""

    code = "messaging_policy_violation"


class ConfigurationError(DomainError):
    code = "not_configured"


class ExternalServiceError(DomainError):
    code = "external_service_error"


class RateLimitedError(DomainError):
    code = "rate_limited"
