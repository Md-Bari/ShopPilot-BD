"""FastAPI dependencies: database session, authentication, CSRF, tenant resolution, rate limits
and service factories. This is the composition root for request-scoped objects."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.application.businesses import BusinessService
from app.application.context import TenantContext
from app.application.whatsapp.messaging import MessagingService
from app.core.config import Settings
from app.core.security import constant_time_equals, decode_access_token
from app.domain.enums import Role
from app.domain.errors import AuthenticationError, PermissionDeniedError, RateLimitedError
from app.infrastructure.db.models import Membership, User

SESSION_COOKIE = "sp_session"
CSRF_COOKIE = "sp_csrf"
CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Iterator[Session]:
    session: Session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[Session, Depends(get_db)]


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def rate_limit(scope: str, limit: int, window_seconds: int = 60):
    """Dependency factory limiting requests per client IP for a scope."""

    def dependency(request: Request) -> None:
        if not request.app.state.rate_limiter.hit(f"{scope}:{client_ip(request)}", limit, window_seconds):
            raise RateLimitedError("Too many requests. Please wait a moment and try again.")

    return Depends(dependency)


def get_current_user(request: Request, db: DbDep, settings: SettingsDep) -> User:
    token, from_cookie = None, False
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    elif request.cookies.get(SESSION_COOKIE):
        token, from_cookie = request.cookies[SESSION_COOKIE], True
    if not token:
        raise AuthenticationError("Authentication required.", code="not_authenticated")

    # Cookie sessions need a matching double-submit CSRF token on state-changing requests.
    if from_cookie and request.method not in SAFE_METHODS:
        cookie_token = request.cookies.get(CSRF_COOKIE, "")
        header_token = request.headers.get(CSRF_HEADER, "")
        if not cookie_token or not header_token or not constant_time_equals(cookie_token, header_token):
            raise HTTPException(status_code=403, detail="CSRF token missing or invalid.")

    payload = decode_access_token(token, settings.secret_key)
    if not payload:
        raise AuthenticationError("Your session has expired. Please sign in again.", code="not_authenticated")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active or user.token_version != payload.get("ver"):
        raise AuthenticationError("Your session has expired. Please sign in again.", code="not_authenticated")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_superuser(user: CurrentUser) -> User:
    if not user.is_superuser:
        raise PermissionDeniedError("Administrator access required.")
    return user


def get_tenant(
    user: CurrentUser,
    db: DbDep,
    x_business_id: Annotated[int | None, Header(alias="X-Business-Id")] = None,
) -> TenantContext:
    """Resolve the active business from the X-Business-Id header and verify membership server-side."""
    if x_business_id is None:
        raise HTTPException(status_code=400, detail="X-Business-Id header is required.")
    membership: Membership | None = BusinessService(db).membership(user.id, x_business_id)
    if membership is None:
        # 404 rather than 403 so business ids cannot be probed.
        raise HTTPException(status_code=404, detail="Business not found.")
    return TenantContext(user_id=user.id, business_id=x_business_id, role=Role(membership.role))


Tenant = Annotated[TenantContext, Depends(get_tenant)]


def get_messaging_service(request: Request, db: DbDep, ctx: Tenant, settings: SettingsDep) -> MessagingService:
    return MessagingService(db, ctx, request.app.state.whatsapp_gateway, request.app.state.credential_provider,
                            enforce_limits=settings.enforce_subscription_limits)


Messaging = Annotated[MessagingService, Depends(get_messaging_service)]
IdempotencyKey = Annotated[str | None, Header(alias="Idempotency-Key", max_length=80)]
