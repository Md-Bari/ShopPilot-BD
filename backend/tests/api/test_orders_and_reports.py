from sqlalchemy import update

from app.infrastructure.db.models import SubscriptionPlan
from tests.conftest import create_order, create_product


def _variant(api, stock=10, price="650", sku="TSHIRT-1"):
    return create_product(api, sku=sku, price=price, stock=stock, cost_price="400")["variants"][0]


class TestOrders:
    def test_create_calculates_totals_and_reserves_stock(self, api):
        variant = _variant(api)
        order = create_order(api, variant["id"], quantity=2, discount="100")
        assert order["order_number"] == "SP-1001"
        assert order["subtotal"] == "1300.00"
        assert order["delivery_charge"] == "60.00"
        assert order["total"] == "1260.00"
        assert order["status"] == "pending" and order["payment_status"] == "unpaid"
        assert order["status_history"][0]["to_status"] == "pending"
        assert order["status_history"][0]["changed_by_name"] == "Test Seller"
        assert order["customer"]["phone"] == "+8801712345678"
        product = api.get("/api/products").json()["items"][0]
        assert product["total_stock"] == 8

        second = create_order(api, variant["id"], phone="+8801712345678")
        assert second["order_number"] == "SP-1002"
        assert second["customer"]["id"] == order["customer"]["id"]  # duplicate customer reused

    def test_insufficient_stock_rolls_back(self, api):
        variant = _variant(api, stock=1)
        res = api.post("/api/orders", json={"new_customer": {"name": "R", "phone": "01712345678"},
                                             "items": [{"variant_id": variant["id"], "quantity": 2}]})
        assert res.status_code == 422 and res.json()["error"]["code"] == "insufficient_stock"
        assert api.get("/api/customers").json()["total"] == 0  # customer creation rolled back too
        assert api.get("/api/products").json()["items"][0]["total_stock"] == 1

    def test_unknown_payment_method(self, api):
        variant = _variant(api)
        res = api.post("/api/orders", json={"new_customer": {"name": "R", "phone": "01712345678"},
                                             "items": [{"variant_id": variant["id"], "quantity": 1}],
                                             "payment_method_code": "bitcoin"})
        assert res.status_code == 422

    def test_status_flow_history_and_restock(self, api):
        variant = _variant(api, stock=5)
        order = create_order(api, variant["id"], quantity=3)
        oid = order["id"]
        res = api.post(f"/api/orders/{oid}/status", json={"status": "delivered"})
        assert res.status_code == 422 and res.json()["error"]["code"] == "invalid_status_transition"

        res = api.post(f"/api/orders/{oid}/status", json={"status": "confirmed", "note": "Called customer"})
        assert res.json()["status"] == "confirmed" and res.json()["confirmed_at"]
        res = api.post(f"/api/orders/{oid}/status", json={"status": "cancelled"})
        body = res.json()
        assert [h["to_status"] for h in body["status_history"]] == ["pending", "confirmed", "cancelled"]
        assert body["status_history"][1]["note"] == "Called customer"
        assert body["allowed_next_statuses"] == []
        assert api.get("/api/products").json()["items"][0]["total_stock"] == 5

    def test_payments(self, api):
        variant = _variant(api, price="1000")
        order = create_order(api, variant["id"])  # total 1060
        oid = order["id"]
        res = api.post(f"/api/orders/{oid}/payments", json={"amount": "500", "method_code": "bkash",
                                                             "reference": "TRX1"})
        assert res.json()["payment_status"] == "partial" and res.json()["amount_paid"] == "500.00"
        assert api.post(f"/api/orders/{oid}/payments", json={"amount": "600"}).status_code == 422
        assert api.post(f"/api/orders/{oid}/payments", json={"amount": "560"}).json()["payment_status"] == "paid"

    def test_search_and_filters(self, api):
        variant = _variant(api)
        create_order(api, variant["id"], phone="01712345678")
        o2 = create_order(api, variant["id"], phone="01812345678",
                          new_customer={"name": "Karim", "phone": "01812345678"})
        api.post(f"/api/orders/{o2['id']}/status", json={"status": "confirmed"})
        assert api.get("/api/orders", params={"status": "confirmed"}).json()["total"] == 1
        assert api.get("/api/orders", params={"q": "Karim"}).json()["total"] == 1
        assert api.get("/api/orders", params={"q": "SP-1001"}).json()["total"] == 1
        assert api.get("/api/orders", params={"q": "01812"}).json()["total"] == 1
        assert api.get("/api/orders", params={"date_from": "2000-01-01", "date_to": "2000-01-02"}).json()["total"] == 0

    def test_plan_order_limit_is_enforced(self, api, db):
        db.execute(update(SubscriptionPlan).where(SubscriptionPlan.code == "trial").values(monthly_order_limit=1))
        db.commit()
        variant = _variant(api)
        first = create_order(api, variant["id"])
        res = api.post("/api/orders", json={"customer_id": first["customer"]["id"],
                                             "items": [{"variant_id": variant["id"], "quantity": 1}]})
        assert res.status_code == 402 and res.json()["error"]["code"] == "plan_limit_exceeded"


class TestDashboard:
    def test_gross_value_is_not_revenue(self, api):
        variant = _variant(api, price="1000")
        delivered = create_order(api, variant["id"])  # total 1060
        cancelled = create_order(api, variant["id"])
        for status in ("confirmed", "shipped", "delivered"):
            api.post(f"/api/orders/{delivered['id']}/status", json={"status": status})
        api.post(f"/api/orders/{delivered['id']}/payments", json={"amount": "1060"})
        api.post(f"/api/orders/{cancelled['id']}/status", json={"status": "cancelled"})

        data = api.get("/api/dashboard").json()
        assert data["today"]["orders"] == 2
        assert float(data["today"]["gross_order_value"]) == 1060  # cancelled excluded
        assert float(data["today"]["collected_revenue"]) == 1060
        assert float(data["month_to_date"]["estimated_profit"]) == 600  # 1000 - 400 cost, delivery excluded
        assert data["last_30_days_status_counts"]["cancelled"] == 1
        assert data["pending_confirmations"] == 0

        report = api.get("/api/reports/sales").json()
        assert report["orders"] == 2
        assert report["by_status"]["delivered"]["count"] == 1
        assert report["top_products"][0]["quantity"] == 1
        assert len(report["daily"]) == 30

    def test_low_stock(self, api):
        create_product(api, sku="LOW", stock=1)
        low = api.get("/api/dashboard").json()["low_stock"]
        assert low and low[0]["stock"] == 1
