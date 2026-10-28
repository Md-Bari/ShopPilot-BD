"""Operational commands.

    python -m app.cli seed-plans
    python -m app.cli create-superuser --email admin@example.com --name "Admin" --password '...'
    python -m app.cli activate-subscription --business-id 1 --plan starter --months 1 --reference BKASH-TRX123
    python -m app.cli purge-webhook-events
"""

import argparse
import sys

from sqlalchemy import select

from app.application.subscriptions import SubscriptionService, ensure_default_plans
from app.application.whatsapp.webhooks import purge_old_webhook_events
from app.core.config import get_settings
from app.core.security import hash_password
from app.infrastructure.db.models import User
from app.infrastructure.db.session import build_engine, build_session_factory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="shoppilot")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed-plans")
    su = sub.add_parser("create-superuser")
    su.add_argument("--email", required=True)
    su.add_argument("--name", required=True)
    su.add_argument("--password", required=True)
    act = sub.add_parser("activate-subscription")
    act.add_argument("--business-id", type=int, required=True)
    act.add_argument("--plan", required=True)
    act.add_argument("--months", type=int, default=1)
    act.add_argument("--reference", required=True)
    sub.add_parser("purge-webhook-events")
    args = parser.parse_args(argv)

    settings = get_settings()
    session = build_session_factory(build_engine(settings.database_url))()
    try:
        if args.command == "seed-plans":
            ensure_default_plans(session)
            session.commit()
            print("Plans seeded.")
        elif args.command == "create-superuser":
            email = args.email.strip().lower()
            user = session.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(email=email, full_name=args.name, password_hash=hash_password(args.password))
                session.add(user)
            user.is_superuser = True
            session.commit()
            print(f"Superuser ready: {email}")
        elif args.command == "activate-subscription":
            admin = session.scalar(select(User).where(User.is_superuser.is_(True)))
            if admin is None:
                print("Create a superuser first.", file=sys.stderr)
                return 1
            result = SubscriptionService(session, args.business_id).activate(
                plan_code=args.plan, months=args.months, payment_reference=args.reference, admin_user_id=admin.id)
            print(f"Business {args.business_id}: {result.status} until {result.current_period_end:%Y-%m-%d}")
        elif args.command == "purge-webhook-events":
            count = purge_old_webhook_events(session, settings.webhook_event_retention_days)
            print(f"Deleted {count} webhook events older than {settings.webhook_event_retention_days} days.")
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
