from datetime import date, timedelta

from fastapi import APIRouter

from app.api.deps import DbDep, Tenant
from app.application.reports import ReportService
from app.domain.clock import local_today

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
def dashboard(ctx: Tenant, db: DbDep):
    return ReportService(db, ctx).dashboard()


@router.get("/reports/sales")
def sales_report(ctx: Tenant, db: DbDep, date_from: date | None = None, date_to: date | None = None):
    date_to = date_to or local_today()
    date_from = date_from or date_to - timedelta(days=29)
    return ReportService(db, ctx).sales_report(date_from, date_to)
