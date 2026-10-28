"""Subscription plans, manual activation and plan-limit enforcement.

Prices are pilot hypotheses. Limits live on SubscriptionPlan rows, never in code paths.
"""

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.clock import DHAKA, utcnow
from app.domain.enums import SubscriptionStatus, UsageMetric
from app.domain.errors import NotFoundError, PlanLimitError, ValidationError
from app.infrastructure.db.models import BusinessSubscription, SubscriptionPlan, UsageRecord

DEFAULT_PLANS = [
    dict(code="trial", name="Free Trial", price_bdt=Decimal("0"), trial_days=14, monthly_order_limit=50,
         monthly_message_limit=100, is_public=False, sort_order=0),
    dict(code="starter", name="Starter", price_bdt=Decimal("499"), monthly_order_limit=300,
         monthly_message_limit=500, sort_order=1),
    dict(code="growth", name="Growth", price_bdt=Decimal("999"), monthly_order_limit=None,
         monthly_message_limit=2000, sort_order=2),
]

USABLE_STATUSES = {SubscriptionStatus.TRIAL.value, SubscriptionStatus.ACTIVE.value}


def ensure_default_plans(session: Session) -> None:
    existing = set(session.scalars(select(SubscriptionPlan.code)))
    for plan in DEFAULT_PLANS:
        if plan["code"] not in existing:
            session.add(SubscriptionPlan(**plan))
    session.flush()


def current_period(now=None) -> str:
    return (now or utcnow()).astimezone(DHAKA).strftime("%Y-%m")


def _limit_for(plan: SubscriptionPlan, metric: UsageMetric) -> int | None:
    return plan.monthly_order_limit if metric == UsageMetric.ORDERS else plan.monthly_message_limit


class SubscriptionService:
    def __init__(self, session: Session, business_id: int, *, enforce: bool = True):
        self.session = session
        self.business_id = business_id
        self.enforce = enforce

    # --- queries -----------------------------------------------------------------------------
    def plans(self) -> list[SubscriptionPlan]:
        stmt = select(SubscriptionPlan).where(SubscriptionPlan.is_active.is_(True)).order_by(SubscriptionPlan.sort_order)
        return list(self.session.scalars(stmt))

    def current(self) -> BusinessSubscription | None:
        return self.session.scalar(
            select(BusinessSubscription)
            .where(BusinessSubscription.business_id == self.business_id)
            .options(selectinload(BusinessSubscription.plan), selectinload(BusinessSubscription.requested_plan))
        )

    def effective_status(self, sub: BusinessSubscription | None) -> SubscriptionStatus | None:
        if sub is None:
            return None
        if sub.status in USABLE_STATUSES and sub.current_period_end <= utcnow():
            return SubscriptionStatus.EXPIRED
        return SubscriptionStatus(sub.status)

    def usage(self) -> dict[str, int]:
        rows = self.session.scalars(
            select(UsageRecord).where(UsageRecord.business_id == self.business_id, UsageRecord.period == current_period())
        )
        return {r.metric: r.quantity for r in rows}

    # --- commands ----------------------------------------------------------------------------
    def start_trial(self) -> BusinessSubscription:
        ensure_default_plans(self.session)
        plan = self.session.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == "trial"))
        now = utcnow()
        sub = BusinessSubscription(
            business_id=self.business_id,
            plan_id=plan.id,
            status=SubscriptionStatus.TRIAL.value,
            current_period_start=now,
            current_period_end=now + timedelta(days=plan.trial_days or 14),
        )
        self.session.add(sub)
        return sub

    def request_plan(self, plan_code: str) -> BusinessSubscription:
        """Seller asks to upgrade; nothing is marked paid until an admin activates it."""
        plan = self._plan(plan_code)
        if plan.price_bdt <= 0:
            raise ValidationError("This plan cannot be requested.")
        sub = self._current_or_raise()
        sub.requested_plan_id = plan.id
        if self.effective_status(sub) not in (SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE):
            sub.status = SubscriptionStatus.PENDING_PAYMENT.value
        self.session.commit()
        self.session.refresh(sub)
        return sub

    def activate(self, *, plan_code: str, months: int, payment_reference: str, admin_user_id: int,
                 notes: str | None = None) -> BusinessSubscription:
        """Admin-only: record a verified manual payment (bKash/Nagad/bank) and activate the plan."""
        if months < 1 or months > 12:
            raise ValidationError("Months must be between 1 and 12.")
        if not payment_reference.strip():
            raise ValidationError("A payment reference is required to activate a paid plan.")
        plan = self._plan(plan_code)
        sub = self._current_or_raise()
        now = utcnow()
        # Renewing the same active plan extends it; anything else starts a fresh period today.
        extending = (sub.status == SubscriptionStatus.ACTIVE.value and sub.plan_id == plan.id
                     and sub.current_period_end > now)
        if extending:
            period_base = sub.current_period_end
        else:
            period_base = now
            sub.current_period_start = now
        sub.plan_id = plan.id
        sub.requested_plan_id = None
        sub.status = SubscriptionStatus.ACTIVE.value
        sub.current_period_end = period_base + timedelta(days=plan.billing_period_days * months)
        sub.payment_reference = payment_reference.strip()
        sub.activated_by_user_id = admin_user_id
        sub.notes = notes
        self.session.commit()
        self.session.refresh(sub)
        return sub

    def check_and_record(self, metric: UsageMetric, quantity: int = 1) -> None:
        """Check the plan limit and record usage in the caller's transaction."""
        record = self._usage_record(metric, for_update=True)
        self._ensure_within_limit(metric, (record.quantity if record else 0) + quantity)
        self._add_usage(record, metric, quantity)

    def ensure_within_limit(self, metric: UsageMetric, quantity: int = 1) -> None:
        record = self._usage_record(metric)
        self._ensure_within_limit(metric, (record.quantity if record else 0) + quantity)

    def record_usage(self, metric: UsageMetric, quantity: int = 1) -> None:
        self._add_usage(self._usage_record(metric, for_update=True), metric, quantity)

    def _usage_record(self, metric: UsageMetric, for_update: bool = False) -> UsageRecord | None:
        stmt = select(UsageRecord).where(UsageRecord.business_id == self.business_id,
                                         UsageRecord.metric == metric.value, UsageRecord.period == current_period())
        return self.session.scalar(stmt.with_for_update() if for_update else stmt)

    def _ensure_within_limit(self, metric: UsageMetric, total_after: int) -> None:
        if not self.enforce:
            return
        sub = self.current()
        status = self.effective_status(sub)
        if status not in (SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE):
            raise PlanLimitError(
                "Your subscription is not active. Please renew from the Subscription page.",
                details={"status": status.value if status else None},
            )
        limit = _limit_for(sub.plan, metric)
        if limit is not None and total_after > limit:
            raise PlanLimitError(
                f"Monthly {metric.value.replace('_', ' ')} limit ({limit}) reached for the {sub.plan.name} plan.",
                details={"metric": metric.value, "limit": limit},
            )

    def _add_usage(self, record: UsageRecord | None, metric: UsageMetric, quantity: int) -> None:
        if record is None:
            self.session.add(UsageRecord(business_id=self.business_id, metric=metric.value,
                                         period=current_period(), quantity=quantity))
        else:
            record.quantity += quantity
        self.session.flush()

    def _plan(self, code: str) -> SubscriptionPlan:
        plan = self.session.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == code,
                                                                  SubscriptionPlan.is_active.is_(True)))
        if not plan:
            raise NotFoundError("Plan not found.")
        return plan

    def _current_or_raise(self) -> BusinessSubscription:
        sub = self.current()
        if not sub:
            raise NotFoundError("This business has no subscription record.")
        return sub
