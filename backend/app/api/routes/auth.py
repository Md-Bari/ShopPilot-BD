import secrets

from fastapi import APIRouter, Request, Response, status

from app.api.deps import CSRF_COOKIE, SESSION_COOKIE, CurrentUser, DbDep, SettingsDep, rate_limit
from app.api.schemas import MeOut, OkOut
from app.api.serializers import me_out
from app.application.auth import AuthService
from app.application.dto import (
    LoginCommand,
    PasswordResetConfirmCommand,
    PasswordResetRequestCommand,
    RegisterCommand,
)
from app.core.config import Settings
from app.infrastructure.db.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _service(request: Request, db, settings) -> AuthService:
    return AuthService(db, settings, request.app.state.email_sender)


def _start_session(response: Response, settings: Settings, token: str) -> None:
    max_age = settings.access_token_ttl_minutes * 60
    response.set_cookie(SESSION_COOKIE, token, max_age=max_age, httponly=True, secure=settings.cookie_secure,
                        samesite="lax", path="/")
    response.set_cookie(CSRF_COOKIE, secrets.token_urlsafe(32), max_age=max_age, httponly=False,
                        secure=settings.cookie_secure, samesite="lax", path="/")


def _me(service: AuthService, user: User) -> MeOut:
    return me_out(service.get_user_with_memberships(user.id))


@router.post("/register", response_model=MeOut, status_code=status.HTTP_201_CREATED,
             dependencies=[rate_limit("register", 5, 60)])
def register(cmd: RegisterCommand, request: Request, response: Response, db: DbDep, settings: SettingsDep):
    service = _service(request, db, settings)
    user = service.register(email=cmd.email, password=cmd.password, full_name=cmd.full_name)
    _start_session(response, settings, service.issue_token(user))
    return _me(service, user)


@router.post("/login", response_model=MeOut, dependencies=[rate_limit("login", 10, 60)])
def login(cmd: LoginCommand, request: Request, response: Response, db: DbDep, settings: SettingsDep):
    service = _service(request, db, settings)
    user = service.authenticate(email=cmd.email, password=cmd.password)
    _start_session(response, settings, service.issue_token(user))
    return _me(service, user)


@router.post("/token", dependencies=[rate_limit("login", 10, 60)])
def token(cmd: LoginCommand, request: Request, db: DbDep, settings: SettingsDep):
    """Bearer token for API clients and scripts (no cookies, no CSRF)."""
    service = _service(request, db, settings)
    user = service.authenticate(email=cmd.email, password=cmd.password)
    return {"access_token": service.issue_token(user), "token_type": "bearer"}


@router.post("/logout", response_model=OkOut)
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return OkOut(message="Signed out.")


@router.get("/me", response_model=MeOut)
def me(user: CurrentUser, request: Request, db: DbDep, settings: SettingsDep):
    return _me(_service(request, db, settings), user)


@router.post("/password-reset/request", response_model=OkOut, status_code=status.HTTP_202_ACCEPTED,
             dependencies=[rate_limit("password-reset", 5, 300)])
def request_password_reset(cmd: PasswordResetRequestCommand, request: Request, db: DbDep, settings: SettingsDep):
    _service(request, db, settings).request_password_reset(cmd.email)
    return OkOut(message="If an account exists for this email, a reset link has been sent.")


@router.post("/password-reset/confirm", response_model=OkOut, dependencies=[rate_limit("password-reset", 10, 300)])
def confirm_password_reset(cmd: PasswordResetConfirmCommand, request: Request, db: DbDep, settings: SettingsDep):
    _service(request, db, settings).confirm_password_reset(token=cmd.token, new_password=cmd.new_password)
    return OkOut(message="Password updated. Please sign in.")
