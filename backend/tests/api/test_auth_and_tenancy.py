from tests.conftest import create_order, create_product


class TestAuth:
    def test_register_login_me_logout(self, anon):
        res = anon.post("/api/auth/register", json={"email": "New@Example.com", "password": "secret123",
                                                     "full_name": "New Seller"})
        assert res.status_code == 201
        assert res.json()["user"]["email"] == "new@example.com"
        assert "sp_session" in anon.client.cookies

        me = anon.get("/api/auth/me")
        assert me.status_code == 200 and me.json()["memberships"] == []

        assert anon.post("/api/auth/logout").status_code == 200
        anon.client.cookies.clear()
        assert anon.get("/api/auth/me").status_code == 401

        res = anon.post("/api/auth/login", json={"email": "new@example.com", "password": "secret123"})
        assert res.status_code == 200
        assert anon.get("/api/auth/me").status_code == 200

    def test_duplicate_email_and_weak_password(self, anon):
        body = {"email": "a@example.com", "password": "secret123", "full_name": "A Seller"}
        assert anon.post("/api/auth/register", json=body).status_code == 201
        res = anon.post("/api/auth/register", json=body)
        assert res.status_code == 409 and res.json()["error"]["code"] == "email_taken"
        weak = anon.post("/api/auth/register", json={**body, "email": "b@example.com", "password": "abcdefgh"})
        assert weak.status_code == 422

    def test_wrong_password_is_generic(self, api, anon):
        res = anon.post("/api/auth/login", json={"email": "owner@example.com", "password": "wrongpass1"})
        assert res.status_code == 401
        assert res.json()["error"]["message"] == "Invalid email or password."
        res = anon.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrongpass1"})
        assert res.json()["error"]["message"] == "Invalid email or password."

    def test_csrf_required_for_cookie_sessions(self, api):
        res = api.client.post("/api/products", json={"name": "X", "sku": "X", "price": "1"},
                              headers={"X-Business-Id": str(api.business_id)})
        assert res.status_code == 403
        res = api.client.post("/api/products", json={"name": "X", "sku": "X", "price": "1"},
                              headers={"X-Business-Id": str(api.business_id), "X-CSRF-Token": "wrong"})
        assert res.status_code == 403

    def test_bearer_token_skips_csrf(self, api, anon):
        token = anon.post("/api/auth/token", json={"email": "owner@example.com", "password": "secret123"}).json()
        res = anon.client.post("/api/products", json={"name": "Y", "sku": "Y", "price": "1"},
                               headers={"Authorization": f"Bearer {token['access_token']}",
                                        "X-Business-Id": str(api.business_id)})
        assert res.status_code == 201

    def test_password_reset_flow_invalidates_sessions(self, api, anon, email_sender):
        res = anon.post("/api/auth/password-reset/request", json={"email": "owner@example.com"})
        assert res.status_code == 202
        # Unknown emails get the same response and no email.
        assert anon.post("/api/auth/password-reset/request", json={"email": "x@example.com"}).status_code == 202
        assert len(email_sender.sent) == 1
        token = email_sender.sent[0]["body"].split("token=")[1].split()[0]

        res = anon.post("/api/auth/password-reset/confirm", json={"token": token, "new_password": "newpass123"})
        assert res.status_code == 200
        # Old session is no longer valid; the token is single-use.
        assert api.get("/api/auth/me").status_code == 401
        again = anon.post("/api/auth/password-reset/confirm", json={"token": token, "new_password": "other123x"})
        assert again.status_code == 422
        login = anon.post("/api/auth/login", json={"email": "owner@example.com", "password": "newpass123"})
        assert login.status_code == 200

    def test_login_rate_limited(self, anon):
        codes = [anon.post("/api/auth/login", json={"email": "z@example.com", "password": "nope12345"}).status_code
                 for _ in range(12)]
        assert codes[-1] == 429


class TestTenantIsolation:
    def test_other_business_data_is_invisible(self, api, make_api):
        product = create_product(api)
        order = create_order(api, product["variants"][0]["id"])
        other = make_api("other@example.com", "Other Shop")

        assert other.get(f"/api/products/{product['id']}").status_code == 404
        assert other.get(f"/api/orders/{order['id']}").status_code == 404
        assert other.get(f"/api/customers/{order['customer']['id']}").status_code == 404
        assert other.get("/api/products").json()["total"] == 0
        assert other.get("/api/orders").json()["total"] == 0
        # Cannot order another tenant's variant either.
        res = other.post("/api/orders", json={
            "new_customer": {"name": "Karim", "phone": "01812345678"},
            "items": [{"variant_id": product["variants"][0]["id"], "quantity": 1}]})
        assert res.status_code == 422
        assert other.patch(f"/api/products/{product['id']}", json={"name": "hacked"}).status_code == 404

    def test_header_spoofing_is_rejected(self, api, make_api):
        other = make_api("spoof@example.com", "Spoof Shop")
        other.business_id = api.business_id  # claims to act for someone else's business
        assert other.get("/api/products").status_code == 404

    def test_business_header_required(self, api):
        api.business_id = None
        assert api.get("/api/products").status_code == 400

    def test_staff_cannot_change_business_settings(self, api, make_api):
        staff = make_api("staff@example.com", business_name=None)
        assert api.post("/api/business/members", json={"email": "staff@example.com", "role": "staff"}).status_code == 201
        staff.business_id = api.business_id
        assert staff.get("/api/products").status_code == 200
        assert staff.patch("/api/business", json={"name": "Renamed"}).status_code == 403
        assert staff.post("/api/whatsapp/settings/connect").status_code == 403
