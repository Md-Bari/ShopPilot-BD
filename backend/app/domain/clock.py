"""Time helpers. Store UTC; show business-facing dates in Asia/Dhaka."""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DHAKA = ZoneInfo("Asia/Dhaka")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def local_day_bounds(day: date, tz: ZoneInfo = DHAKA) -> tuple[datetime, datetime]:
    """UTC [start, end) for a calendar day in the business time zone."""
    start = datetime.combine(day, time.min, tzinfo=tz)
    return start.astimezone(timezone.utc), (start + timedelta(days=1)).astimezone(timezone.utc)


def local_today(tz: ZoneInfo = DHAKA) -> date:
    return utcnow().astimezone(tz).date()


def to_local_date(value: datetime, tz: ZoneInfo = DHAKA) -> date:
    return value.astimezone(tz).date()
