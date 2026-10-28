import re
import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.application.context import TenantContext
from app.application.subscriptions import SubscriptionService
from app.domain.enums import MANAGER_ROLES, Role
from app.domain.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.domain.phone import normalize_phone
from app.infrastructure.db.models import Business, Membership, PaymentMethod, User

DEFAULT_PAYMENT_METHODS = [
    ("cod", "Cash on Delivery"),
    ("bkash", "bKash"),
    ("nagad", "Nagad"),
    ("bank", "Bank Transfer"),
]

EDITABLE_FIELDS = {"name", "phone", "email", "address", "facebook_page_url", "order_prefix", "default_delivery_charge"}


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:150] or "shop"
    return f"{base}-{secrets.token_hex(3)}"


class BusinessService:
    def __init__(self, session: Session):
        self.session = session

    def create(self, *, owner: User, name: str, phone: str | None = None, address: str | None = None,
               enforce_limits: bool = True) -> Business:
        if not name.strip():
            raise ValidationError("Business name is required.")
        business = Business(
            name=name.strip(),
            slug=_slugify(name),
            phone=normalize_phone(phone) if phone else None,
            address=address,
        )
        self.session.add(business)
        self.session.flush()
        self.session.add(Membership(user_id=owner.id, business_id=business.id, role=Role.OWNER.value))
        for order, (code, label) in enumerate(DEFAULT_PAYMENT_METHODS):
            self.session.add(PaymentMethod(business_id=business.id, code=code, label=label, sort_order=order))
        SubscriptionService(self.session, business.id, enforce=enforce_limits).start_trial()
        self.session.commit()
        return business

    def membership(self, user_id: int, business_id: int) -> Membership | None:
        return self.session.scalar(
            select(Membership)
            .join(Business)
            .where(Membership.user_id == user_id, Membership.business_id == business_id, Business.is_active.is_(True))
        )

    # --- tenant-scoped operations ---------------------------------------------------------------
    def get(self, ctx: TenantContext) -> Business:
        return self.session.get(Business, ctx.business_id)

    def update(self, ctx: TenantContext, changes: dict) -> Business:
        ctx.require(*MANAGER_ROLES)
        business = self.get(ctx)
        unknown = set(changes) - EDITABLE_FIELDS
        if unknown:
            raise ValidationError(f"Unknown fields: {', '.join(sorted(unknown))}")
        if "phone" in changes and changes["phone"]:
            changes["phone"] = normalize_phone(changes["phone"])
        if "order_prefix" in changes:
            prefix = (changes["order_prefix"] or "").strip().upper()
            if not re.fullmatch(r"[A-Z0-9]{1,10}", prefix):
                raise ValidationError("Order prefix must be 1-10 letters or digits.")
            changes["order_prefix"] = prefix
        for key, value in changes.items():
            setattr(business, key, value)
        self.session.commit()
        return business

    def members(self, ctx: TenantContext) -> list[Membership]:
        return list(
            self.session.scalars(
                select(Membership)
                .where(Membership.business_id == ctx.business_id)
                .options(selectinload(Membership.user))
                .order_by(Membership.id)
            )
        )

    def add_member(self, ctx: TenantContext, *, email: str, role: Role) -> Membership:
        """Adds an existing user account to this business (invitation emails are a later phase)."""
        ctx.require(*MANAGER_ROLES)
        if role == Role.OWNER and ctx.role != Role.OWNER:
            raise PermissionDeniedError("Only an owner can add another owner.")
        user = self.session.scalar(select(User).where(User.email == email.strip().lower()))
        if not user:
            raise NotFoundError("No account exists with this email. Ask them to register first.")
        if self.membership(user.id, ctx.business_id):
            raise ConflictError("This user is already a member.")
        membership = Membership(user_id=user.id, business_id=ctx.business_id, role=role.value)
        self.session.add(membership)
        self.session.commit()
        self.session.refresh(membership, ["user"])
        return membership

    def change_member_role(self, ctx: TenantContext, membership_id: int, role: Role) -> Membership:
        ctx.require(Role.OWNER)
        membership = self._member(ctx, membership_id)
        if membership.role == Role.OWNER.value and role != Role.OWNER:
            self._ensure_not_last_owner(ctx)
        membership.role = role.value
        self.session.commit()
        return membership

    def remove_member(self, ctx: TenantContext, membership_id: int) -> None:
        ctx.require(*MANAGER_ROLES)
        membership = self._member(ctx, membership_id)
        if membership.role == Role.OWNER.value:
            if ctx.role != Role.OWNER:
                raise PermissionDeniedError("Only an owner can remove an owner.")
            self._ensure_not_last_owner(ctx)
        self.session.delete(membership)
        self.session.commit()

    def _member(self, ctx: TenantContext, membership_id: int) -> Membership:
        membership = self.session.scalar(
            select(Membership)
            .where(Membership.id == membership_id, Membership.business_id == ctx.business_id)
            .options(selectinload(Membership.user))
        )
        if not membership:
            raise NotFoundError("Member not found.")
        return membership

    def _ensure_not_last_owner(self, ctx: TenantContext) -> None:
        owners = self.session.scalar(
            select(func.count(Membership.id)).where(
                Membership.business_id == ctx.business_id, Membership.role == Role.OWNER.value
            )
        )
        if owners <= 1:
            raise ValidationError("A business must keep at least one owner.")

    # --- payment methods ------------------------------------------------------------------------
    def payment_methods(self, ctx: TenantContext, active_only: bool = False) -> list[PaymentMethod]:
        stmt = select(PaymentMethod).where(PaymentMethod.business_id == ctx.business_id)
        if active_only:
            stmt = stmt.where(PaymentMethod.is_active.is_(True))
        return list(self.session.scalars(stmt.order_by(PaymentMethod.sort_order, PaymentMethod.id)))

    def upsert_payment_method(self, ctx: TenantContext, *, code: str, label: str, is_active: bool) -> PaymentMethod:
        ctx.require(*MANAGER_ROLES)
        code = code.strip().lower()
        if not re.fullmatch(r"[a-z0-9_]{2,30}", code):
            raise ValidationError("Code must be 2-30 lowercase letters, digits or underscores.")
        method = self.session.scalar(
            select(PaymentMethod).where(PaymentMethod.business_id == ctx.business_id, PaymentMethod.code == code)
        )
        if method is None:
            count = len(self.payment_methods(ctx))
            method = PaymentMethod(business_id=ctx.business_id, code=code, sort_order=count)
            self.session.add(method)
        method.label = label.strip()
        method.is_active = is_active
        self.session.commit()
        return method
