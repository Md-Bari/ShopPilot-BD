from sqlalchemy import update

from app.core.security import hash_password
from app.infrastructure.db.models import User


def make_admin(db, email="admin@example.com"):
    db.add(User(email=email, full_name="Admin", password_hash=hash_password("admin1234"), is_superuser=True))
    db.commit()


def test_trial_is_never_reported_as_paid(api):
    sub = api.get("/api/subscription").json()
    assert sub["status"] == "trial" and sub["is_paid"] is False
    assert sub["plan"]["code"] == "trial"
    assert {p["code"] for p in sub["plans"]} == {"starter", "growth"}
    assert sub["plans"][0]["price_bdt"] == "499.00"


def test_request_does_not_activate(api):
    sub = api.post("/api/subscription/request", json={"plan_code": "growth"}).json()
    assert sub["requested_plan"]["code"] == "growth"
    assert sub["plan"]["code"] == "trial" and sub["is_paid"] is False


def test_admin_activation(api, anon, db):
    make_admin(db)
    api.post("/api/subscription/request", json={"plan_code": "starter"})
    assert api.post(f"/api/admin/businesses/{api.business_id}/subscription/activate",
                    json={"plan_code": "starter", "payment_reference": "BKASH-1"}).status_code == 403

    anon.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin1234"})
    listing = anon.get("/api/admin/subscriptions").json()
    assert listing[0]["requested_plan_code"] == "starter"
    res = anon.post(f"/api/admin/businesses/{api.business_id}/subscription/activate",
                    json={"plan_code": "starter", "months": 1, "payment_reference": "BKASH-TRX-1"})
    assert res.status_code == 200, res.text
    sub = api.get("/api/subscription").json()
    assert sub["status"] == "active" and sub["is_paid"] is True and sub["plan"]["code"] == "starter"
    assert sub["requested_plan"] is None


def test_expired_trial_blocks_new_orders(api, db):
    from app.domain.clock import utcnow
    from app.infrastructure.db.models import BusinessSubscription

    db.execute(update(BusinessSubscription).values(current_period_end=utcnow()))
    db.commit()
    assert api.get("/api/subscription").json()["status"] == "expired"
    product = api.post("/api/products", json={"name": "P", "sku": "P", "price": "10", "stock": 5}).json()
    res = api.post("/api/orders", json={"new_customer": {"name": "R", "phone": "01712345678"},
                                         "items": [{"variant_id": product["variants"][0]["id"], "quantity": 1}]})
    assert res.status_code == 402
