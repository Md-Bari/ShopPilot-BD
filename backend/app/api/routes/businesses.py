from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbDep, SettingsDep, Tenant
from app.api.schemas import BusinessOut, MemberOut, OkOut, PaymentMethodOut
from app.application.businesses import BusinessService
from app.application.dto import (
    BusinessCreateCommand,
    BusinessUpdateCommand,
    MemberAddCommand,
    MemberRoleCommand,
    PaymentMethodCommand,
)

router = APIRouter(prefix="/api", tags=["business"])


def _member_out(m) -> MemberOut:
    return MemberOut(id=m.id, user_id=m.user_id, email=m.user.email, full_name=m.user.full_name, role=m.role)


@router.post("/businesses", response_model=BusinessOut, status_code=status.HTTP_201_CREATED)
def create_business(cmd: BusinessCreateCommand, user: CurrentUser, db: DbDep, settings: SettingsDep):
    return BusinessService(db).create(owner=user, name=cmd.name, phone=cmd.phone, address=cmd.address,
                                      enforce_limits=settings.enforce_subscription_limits)


@router.get("/business", response_model=BusinessOut)
def get_current_business(ctx: Tenant, db: DbDep):
    return BusinessService(db).get(ctx)


@router.patch("/business", response_model=BusinessOut)
def update_business(cmd: BusinessUpdateCommand, ctx: Tenant, db: DbDep):
    return BusinessService(db).update(ctx, cmd.model_dump(exclude_unset=True))


@router.get("/business/members", response_model=list[MemberOut])
def list_members(ctx: Tenant, db: DbDep):
    return [_member_out(m) for m in BusinessService(db).members(ctx)]


@router.post("/business/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def add_member(cmd: MemberAddCommand, ctx: Tenant, db: DbDep):
    return _member_out(BusinessService(db).add_member(ctx, email=cmd.email, role=cmd.role))


@router.patch("/business/members/{membership_id}", response_model=MemberOut)
def change_member_role(membership_id: int, cmd: MemberRoleCommand, ctx: Tenant, db: DbDep):
    return _member_out(BusinessService(db).change_member_role(ctx, membership_id, cmd.role))


@router.delete("/business/members/{membership_id}", response_model=OkOut)
def remove_member(membership_id: int, ctx: Tenant, db: DbDep):
    BusinessService(db).remove_member(ctx, membership_id)
    return OkOut()


@router.get("/business/payment-methods", response_model=list[PaymentMethodOut])
def list_payment_methods(ctx: Tenant, db: DbDep, active_only: bool = False):
    return BusinessService(db).payment_methods(ctx, active_only=active_only)


@router.put("/business/payment-methods", response_model=PaymentMethodOut)
def upsert_payment_method(cmd: PaymentMethodCommand, ctx: Tenant, db: DbDep):
    return BusinessService(db).upsert_payment_method(ctx, code=cmd.code, label=cmd.label, is_active=cmd.is_active)
