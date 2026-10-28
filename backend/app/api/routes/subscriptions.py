from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DbDep, SettingsDep, Tenant, get_superuser
from app.api.schemas import AdminSubscriptionOut, PlanOut, SubscriptionOut
from app.application.dto import PlanRequestCommand, SubscriptionActivateCommand
from app.application.subscriptions import SubscriptionService
from app.domain.enums import MANAGER_ROLES, SubscriptionStatus
from app.infrastructure.db.models import Business, BusinessSubscription, User

router = APIRouter(prefix="/api", tags=["subscription"])


def _subscription_out(service: SubscriptionService) -> SubscriptionOut:
    sub = service.current()
    status = service.effective_status(sub)
    return SubscriptionOut(
        status=status.value if status else None,
        # Only an admin-verified active paid plan counts as paid; trials and pending requests never do.
        is_paid=bool(sub and status == SubscriptionStatus.ACTIVE and sub.plan.price_bdt > 0),
        plan=PlanOut.model_validate(sub.plan) if sub else None,
        requested_plan=PlanOut.model_validate(sub.requested_plan) if sub and sub.requested_plan else None,
        current_period_start=sub.current_period_start if sub else None,
        current_period_end=sub.current_period_end if sub else None,
        payment_reference=sub.payment_reference if sub else None,
        usage=service.usage(),
        plans=[PlanOut.model_validate(p) for p in service.plans() if p.is_public],
    )


@router.get("/subscription", response_model=SubscriptionOut)
def get_subscription(ctx: Tenant, db: DbDep, settings: SettingsDep):
    return _subscription_out(SubscriptionService(db, ctx.business_id, enforce=settings.enforce_subscription_limits))


@router.post("/subscription/request", response_model=SubscriptionOut)
def request_plan(cmd: PlanRequestCommand, ctx: Tenant, db: DbDep, settings: SettingsDep):
    ctx.require(*MANAGER_ROLES)
    service = SubscriptionService(db, ctx.business_id, enforce=settings.enforce_subscription_limits)
    service.request_plan(cmd.plan_code)
    return _subscription_out(service)


# --- platform administrator -----------------------------------------------------------------------
Admin = Annotated[User, Depends(get_superuser)]


@router.get("/admin/subscriptions", response_model=list[AdminSubscriptionOut])
def admin_list_subscriptions(_: Admin, db: DbDep):
    rows = db.execute(
        select(BusinessSubscription, Business.name)
        .join(Business, Business.id == BusinessSubscription.business_id)
        .options(selectinload(BusinessSubscription.plan), selectinload(BusinessSubscription.requested_plan))
        .order_by(BusinessSubscription.updated_at.desc())
    )
    return [
        AdminSubscriptionOut(business_id=sub.business_id, business_name=name, status=sub.status,
                             plan_code=sub.plan.code,
                             requested_plan_code=sub.requested_plan.code if sub.requested_plan else None,
                             current_period_end=sub.current_period_end)
        for sub, name in rows
    ]


@router.post("/admin/businesses/{business_id}/subscription/activate", response_model=SubscriptionOut)
def admin_activate(business_id: int, cmd: SubscriptionActivateCommand, admin: Admin, db: DbDep):
    service = SubscriptionService(db, business_id)
    service.activate(plan_code=cmd.plan_code, months=cmd.months, payment_reference=cmd.payment_reference,
                     admin_user_id=admin.id, notes=cmd.notes)
    return _subscription_out(service)
