from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.application.ports import EmailSender
from app.core.config import Settings
from app.core.security import create_access_token, generate_token, hash_password, sha256_hex, verify_password
from app.domain.clock import utcnow
from app.domain.errors import AuthenticationError, ConflictError, ValidationError
from app.infrastructure.db.models import Membership, PasswordResetToken, User

MIN_PASSWORD_LENGTH = 8


def _validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if password.isdigit() or password.isalpha():
        raise ValidationError("Password must contain both letters and numbers.")


class AuthService:
    def __init__(self, session: Session, settings: Settings, email_sender: EmailSender):
        self.session = session
        self.settings = settings
        self.email_sender = email_sender

    def issue_token(self, user: User) -> str:
        return create_access_token(
            user_id=user.id,
            token_version=user.token_version,
            secret=self.settings.secret_key,
            ttl_minutes=self.settings.access_token_ttl_minutes,
        )

    def register(self, *, email: str, password: str, full_name: str) -> User:
        email = email.strip().lower()
        _validate_password(password)
        if self.session.scalar(select(User.id).where(User.email == email)):
            raise ConflictError("An account with this email already exists.", code="email_taken")
        user = User(email=email, full_name=full_name.strip(), password_hash=hash_password(password))
        self.session.add(user)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("An account with this email already exists.", code="email_taken") from exc
        return user

    def authenticate(self, *, email: str, password: str) -> User:
        user = self.session.scalar(select(User).where(User.email == email.strip().lower()))
        # Same error for unknown email and wrong password to avoid account enumeration.
        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password.")
        if not user.is_active:
            raise AuthenticationError("This account is disabled.")
        return user

    def get_user_with_memberships(self, user_id: int) -> User | None:
        return self.session.scalar(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.memberships).selectinload(Membership.business))
        )

    def request_password_reset(self, email: str) -> str | None:
        """Always succeeds from the caller's point of view. Returns the raw token (for tests)."""
        user = self.session.scalar(select(User).where(User.email == email.strip().lower()))
        if not user or not user.is_active:
            return None
        raw = generate_token()
        self.session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=sha256_hex(raw),
                expires_at=utcnow() + timedelta(minutes=self.settings.password_reset_ttl_minutes),
            )
        )
        self.session.commit()
        link = f"{self.settings.frontend_url.rstrip('/')}/reset-password?token={raw}"
        self.email_sender.send(
            to=user.email,
            subject="Reset your ShopPilot BD password",
            body=f"Use this link within {self.settings.password_reset_ttl_minutes} minutes:\n{link}\n\n"
            "If you did not request this, ignore this email.",
        )
        return raw

    def confirm_password_reset(self, *, token: str, new_password: str) -> None:
        record = self.session.scalar(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == sha256_hex(token)).with_for_update()
        )
        if not record or record.used_at is not None or record.expires_at <= utcnow():
            raise ValidationError("This reset link is invalid or has expired.", code="invalid_reset_token")
        _validate_password(new_password)
        user = self.session.get(User, record.user_id)
        user.password_hash = hash_password(new_password)
        user.token_version += 1  # sign out every existing session
        record.used_at = utcnow()
        self.session.commit()
