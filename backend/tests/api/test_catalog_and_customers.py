import io

from tests.conftest import create_product

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class TestProducts:
    def test_create_with_variants_and_search(self, api):
        product = create_product(api, sku="KURTI-1", price="1200", variants=[
            {"size": "M", "color": "Red", "stock": 5}, {"size": "L", "color": "Red", "stock": 2, "price": "1300"}])
        assert product["total_stock"] == 7
        assert [v["label"] for v in product["variants"]] == ["M / Red", "L / Red"]
        assert product["variants"][1]["effective_price"] == "1300.00"

        assert api.get("/api/products", params={"q": "kurti"}).json()["total"] == 1
        assert api.get("/api/products", params={"q": "nothing"}).json()["total"] == 0

    def test_duplicate_sku_and_duplicate_variant(self, api):
        create_product(api, sku="DUP")
        res = api.post("/api/products", json={"name": "Other", "sku": "DUP", "price": "10"})
        assert res.status_code == 409
        res = api.post("/api/products", json={"name": "V", "sku": "V1", "price": "10",
                                               "variants": [{"size": "M"}, {"size": "m"}]})
        assert res.status_code == 422

    def test_update_archive_and_variant_management(self, api):
        product = create_product(api)
        pid = product["id"]
        assert api.patch(f"/api/products/{pid}", json={"price": "550"}).json()["price"] == "550.00"
        assert api.post(f"/api/products/{pid}/archive").json()["status"] == "archived"
        assert api.get("/api/products", params={"status": "active"}).json()["total"] == 0
        assert api.post(f"/api/products/{pid}/unarchive").json()["status"] == "active"

        variant = api.post(f"/api/products/{pid}/variants", json={"size": "XL", "stock": 4}).json()
        assert api.patch(f"/api/products/{pid}/variants/{variant['id']}", json={"stock": 9}).json()["stock"] == 9
        assert api.delete(f"/api/products/{pid}/variants/{variant['id']}").status_code == 200
        only = product["variants"][0]["id"]
        assert api.delete(f"/api/products/{pid}/variants/{only}").status_code == 422

    def test_negative_price_rejected(self, api):
        assert api.post("/api/products", json={"name": "N", "sku": "N", "price": "-1"}).status_code == 422

    def test_image_upload_validates_content(self, api):
        pid = create_product(api)["id"]
        res = api.post(f"/api/products/{pid}/image", files={"file": ("a.png", io.BytesIO(PNG_BYTES), "image/png")})
        assert res.status_code == 200
        assert res.json()["image_url"].startswith("/media/products/")
        fake = api.post(f"/api/products/{pid}/image",
                        files={"file": ("a.png", io.BytesIO(b"<script>alert(1)</script>"), "image/png")})
        assert fake.status_code == 422

    def test_csv_import_and_export(self, api):
        csv_text = (
            "name,sku,description,price,cost_price,status,variant_sku,size,color,variant_price,stock,low_stock_threshold\n"
            "Three Piece,TP-1,Cotton,1500,900,active,TP-1-M,M,Blue,,5,2\n"
            "Three Piece,TP-1,Cotton,1500,900,active,TP-1-L,L,Blue,1600,3,2\n"
            "Bad Row,BAD,,notanumber,,,,,,,1,\n"
        )
        res = api.post("/api/products/import", files={"file": ("p.csv", io.BytesIO(csv_text.encode()), "text/csv")})
        assert res.status_code == 200, res.text
        summary = res.json()
        assert summary["products_created"] == 1 and summary["variants_created"] == 2
        assert len(summary["errors"]) == 1 and summary["errors"][0]["row"] == 4

        export = api.get("/api/products/export.csv")
        assert export.status_code == 200
        assert "TP-1-L" in export.text and export.text.count("\n") == 3

        # Re-import updates instead of duplicating.
        res = api.post("/api/products/import", files={"file": ("p.csv", io.BytesIO(export.text.encode()), "text/csv")})
        assert res.json()["products_created"] == 0 and res.json()["variants_updated"] == 2


class TestCustomers:
    def test_duplicate_detection_uses_normalized_phone(self, api):
        res = api.post("/api/customers", json={"name": "Rahim", "phone": "01712-345678"})
        assert res.status_code == 201 and res.json()["phone"] == "+8801712345678"
        dup = api.post("/api/customers", json={"name": "Rahim 2", "phone": "+880 1712 345678"})
        assert dup.status_code == 409
        assert dup.json()["error"]["details"]["existing_customer_id"] == res.json()["id"]
        check = api.get("/api/customers/check-duplicate", params={"phone": "8801712345678"}).json()
        assert check["duplicate"]["id"] == res.json()["id"]

    def test_same_phone_allowed_in_different_businesses(self, api, make_api):
        assert api.post("/api/customers", json={"name": "A", "phone": "01712345678"}).status_code == 201
        other = make_api("b@example.com", "Shop B")
        assert other.post("/api/customers", json={"name": "A", "phone": "01712345678"}).status_code == 201

    def test_invalid_phone(self, api):
        res = api.post("/api/customers", json={"name": "A", "phone": "12345"})
        assert res.status_code == 422

    def test_consent_history(self, api):
        cid = api.post("/api/customers", json={"name": "A", "phone": "01712345678"}).json()["id"]
        api.post(f"/api/customers/{cid}/consents", json={"status": "granted", "source": "facebook"})
        api.post(f"/api/customers/{cid}/consents", json={"status": "revoked", "source": "phone_call"})
        detail = api.get(f"/api/customers/{cid}").json()
        assert detail["transactional_consent"] == "revoked"
        assert len(detail["consents"]) == 2
        assert detail["marketing_consent"] is None
