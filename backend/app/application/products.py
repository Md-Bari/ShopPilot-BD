import csv
import io
import uuid
from decimal import Decimal, InvalidOperation

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.context import TenantContext
from app.application.dto import ProductCreateCommand, ProductUpdateCommand, VariantInput, VariantUpdate
from app.application.ports import FileStorage
from app.domain.enums import ProductStatus
from app.domain.errors import ConflictError, ValidationError
from app.domain.pricing import money
from app.infrastructure.db.models import Product, ProductVariant
from app.infrastructure.repositories.catalog import ProductRepository, VariantRepository

CSV_COLUMNS = ["name", "sku", "description", "price", "cost_price", "status",
               "variant_sku", "size", "color", "variant_price", "stock", "low_stock_threshold"]
MAX_CSV_ROWS = 5000

_IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG\r\n\x1a\n": "png",
}


def detect_image_type(data: bytes) -> str | None:
    for signature, ext in _IMAGE_SIGNATURES.items():
        if data.startswith(signature):
            return ext
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


class ProductService:
    def __init__(self, session: Session, ctx: TenantContext, storage: FileStorage | None = None):
        self.session = session
        self.ctx = ctx
        self.products = ProductRepository(session, ctx.business_id)
        self.variants = VariantRepository(session, ctx.business_id)
        self.storage = storage

    # --- queries ------------------------------------------------------------------------------
    def search(self, *, q: str | None = None, status: str | None = None, page: int = 1, page_size: int = 20):
        return self.products.search(q=q, status=status, page=page, page_size=page_size)

    def get(self, product_id: int) -> Product:
        return self.products.get_or_raise(product_id)

    # --- commands -----------------------------------------------------------------------------
    def create(self, cmd: ProductCreateCommand) -> Product:
        if self.products.by_sku(cmd.sku):
            raise ConflictError(f"A product with SKU '{cmd.sku}' already exists.", code="duplicate_sku")
        product = Product(
            name=cmd.name, sku=cmd.sku, description=cmd.description,
            price=money(cmd.price), cost_price=money(cmd.cost_price) if cmd.cost_price is not None else None,
            status=ProductStatus.ACTIVE.value,
        )
        self.products.add(product)
        variants = cmd.variants or [VariantInput(stock=cmd.stock)]
        seen: set[tuple[str, str]] = set()
        for v in variants:
            key = (v.size.lower(), v.color.lower())
            if key in seen:
                raise ValidationError(f"Duplicate variant {v.size or '-'} / {v.color or '-'}.")
            seen.add(key)
            product.variants.append(self._new_variant(v))
        self._commit("A variant SKU is already used by another product.")
        return product

    def update(self, product_id: int, cmd: ProductUpdateCommand) -> Product:
        product = self.get(product_id)
        changes = cmd.model_dump(exclude_unset=True)
        if "sku" in changes and changes["sku"] != product.sku and self.products.by_sku(changes["sku"]):
            raise ConflictError(f"A product with SKU '{changes['sku']}' already exists.", code="duplicate_sku")
        for key in ("price", "cost_price"):
            if changes.get(key) is not None:
                changes[key] = money(changes[key])
        for key, value in changes.items():
            setattr(product, key, value)
        self._commit()
        return product

    def set_status(self, product_id: int, status: ProductStatus) -> Product:
        product = self.get(product_id)
        product.status = status.value
        self.session.commit()
        return product

    def add_variant(self, product_id: int, cmd: VariantInput) -> ProductVariant:
        product = self.get(product_id)
        variant = self._new_variant(cmd)
        product.variants.append(variant)
        self._commit("This size/colour combination or SKU already exists.")
        return variant

    def update_variant(self, product_id: int, variant_id: int, cmd: VariantUpdate) -> ProductVariant:
        variant = self._variant_of(product_id, variant_id)
        changes = cmd.model_dump(exclude_unset=True)
        if changes.get("price") is not None:
            changes["price"] = money(changes["price"])
        if changes.get("sku") == "":
            changes["sku"] = None
        for key, value in changes.items():
            setattr(variant, key, value)
        self._commit("This size/colour combination or SKU already exists.")
        return variant

    def delete_variant(self, product_id: int, variant_id: int) -> None:
        product = self.get(product_id)
        variant = self._variant_of(product_id, variant_id)
        if len(product.variants) <= 1:
            raise ValidationError("A product needs at least one variant. Archive the product instead.")
        # Past order items keep their snapshot (variant_id becomes NULL).
        product.variants.remove(variant)
        self.session.commit()

    def upload_image(self, product_id: int, data: bytes, max_bytes: int) -> Product:
        if self.storage is None:
            raise ValidationError("File storage is not configured.")
        if not data:
            raise ValidationError("The uploaded file is empty.")
        if len(data) > max_bytes:
            raise ValidationError(f"Images must be at most {max_bytes // (1024 * 1024)} MB.")
        ext = detect_image_type(data)
        if not ext:
            raise ValidationError("Only JPEG, PNG or WebP images are allowed.")
        product = self.get(product_id)
        old_path = product.image_path
        product.image_path = self.storage.save(
            folder=f"products/{self.ctx.business_id}", filename=f"{uuid.uuid4().hex}.{ext}", data=data
        )
        self.session.commit()
        if old_path:
            self.storage.delete(old_path)
        return product

    # --- CSV ----------------------------------------------------------------------------------
    def export_csv(self) -> str:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for product in self.products.all():
            for v in product.variants:
                writer.writerow({
                    "name": product.name, "sku": product.sku, "description": product.description or "",
                    "price": product.price, "cost_price": product.cost_price if product.cost_price is not None else "",
                    "status": product.status, "variant_sku": v.sku or "", "size": v.size, "color": v.color,
                    "variant_price": v.price if v.price is not None else "", "stock": v.stock,
                    "low_stock_threshold": v.low_stock_threshold,
                })
        return buffer.getvalue()

    def import_csv(self, text: str) -> dict:
        """Upsert products by SKU and variants by (size, colour). Invalid rows are skipped and reported."""
        reader = csv.DictReader(io.StringIO(text))
        missing = {"name", "sku", "price"} - set(reader.fieldnames or [])
        if missing:
            raise ValidationError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

        summary = {"products_created": 0, "products_updated": 0, "variants_created": 0,
                   "variants_updated": 0, "errors": []}
        touched: set[int] = set()
        for row_number, row in enumerate(reader, start=2):
            if row_number - 1 > MAX_CSV_ROWS:
                summary["errors"].append({"row": row_number, "message": f"Only {MAX_CSV_ROWS} rows are imported."})
                break
            try:
                with self.session.begin_nested():
                    self._import_row(row, summary, touched)
            except (ValidationError, IntegrityError, InvalidOperation, ValueError) as exc:
                message = exc.message if isinstance(exc, ValidationError) else "Invalid value or duplicate SKU."
                summary["errors"].append({"row": row_number, "message": message})
        self.session.commit()
        return summary

    def _import_row(self, row: dict, summary: dict, touched: set[int]) -> None:
        def text(key: str) -> str:
            return (row.get(key) or "").strip()

        def decimal_or_none(key: str) -> Decimal | None:
            raw = text(key)
            if not raw:
                return None
            value = money(Decimal(raw))
            if value < 0:
                raise ValidationError(f"{key} cannot be negative.")
            return value

        name, sku = text("name"), text("sku")
        if not name or not sku:
            raise ValidationError("name and sku are required.")
        price = decimal_or_none("price")
        if price is None:
            raise ValidationError("price is required.")
        status = text("status") or ProductStatus.ACTIVE.value
        if status not in {s.value for s in ProductStatus}:
            raise ValidationError("status must be active or archived.")

        product = self.products.by_sku(sku)
        if product is None:
            product = Product(name=name, sku=sku, price=price, status=status)
            self.products.add(product)
            self.session.flush()
            summary["products_created"] += 1
        elif product.id not in touched:
            summary["products_updated"] += 1
        touched.add(product.id)
        product.name, product.price, product.status = name, price, status
        product.description = text("description") or product.description
        cost = decimal_or_none("cost_price")
        if cost is not None:
            product.cost_price = cost

        size, color = text("size"), text("color")
        variant = next((v for v in product.variants if v.size.lower() == size.lower()
                        and v.color.lower() == color.lower()), None)
        if variant is None:
            variant = ProductVariant(business_id=self.ctx.business_id, size=size, color=color)
            product.variants.append(variant)
            summary["variants_created"] += 1
        else:
            summary["variants_updated"] += 1
        variant.sku = text("variant_sku") or variant.sku
        variant.price = decimal_or_none("variant_price")
        if text("stock"):
            stock = int(text("stock"))
            if stock < 0:
                raise ValidationError("stock cannot be negative.")
            variant.stock = stock
        if text("low_stock_threshold"):
            variant.low_stock_threshold = max(0, int(text("low_stock_threshold")))
        self.session.flush()

    # --- helpers ------------------------------------------------------------------------------
    def _new_variant(self, v: VariantInput) -> ProductVariant:
        return ProductVariant(
            business_id=self.ctx.business_id, size=v.size, color=v.color, sku=v.sku or None,
            price=money(v.price) if v.price is not None else None,
            stock=v.stock, low_stock_threshold=v.low_stock_threshold,
        )

    def _variant_of(self, product_id: int, variant_id: int) -> ProductVariant:
        variant = self.variants.get_or_raise(variant_id)
        if variant.product_id != product_id:
            raise ValidationError("Variant does not belong to this product.")
        return variant

    def _commit(self, conflict_message: str = "Duplicate value.") -> None:
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError(conflict_message) from exc
