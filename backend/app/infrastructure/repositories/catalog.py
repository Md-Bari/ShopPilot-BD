from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.domain.enums import ProductStatus
from app.infrastructure.db.models import Product, ProductVariant
from app.infrastructure.repositories.base import TenantRepository


class ProductRepository(TenantRepository[Product]):
    model = Product
    label = "Product"

    def _select(self):
        return super()._select().options(selectinload(Product.variants))

    def search(self, *, q: str | None, status: str | None, page: int, page_size: int):
        stmt = self._select()
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(or_(Product.name.ilike(like), Product.sku.ilike(like)))
        if status:
            stmt = stmt.where(Product.status == status)
        return self.paginate(stmt.order_by(Product.created_at.desc(), Product.id.desc()), page, page_size)

    def by_sku(self, sku: str) -> Product | None:
        return self.session.scalar(self._select().where(Product.sku == sku))

    def all(self) -> list[Product]:
        return list(self.session.scalars(self._select().order_by(Product.id)))


class VariantRepository(TenantRepository[ProductVariant]):
    model = ProductVariant
    label = "Product variant"

    def get_many_for_update(self, ids: list[int]) -> dict[int, ProductVariant]:
        stmt = (
            self._select()
            .where(ProductVariant.id.in_(ids))
            .options(selectinload(ProductVariant.product))
            .order_by(ProductVariant.id)  # consistent lock order avoids deadlocks
            .with_for_update()
        )
        return {v.id: v for v in self.session.scalars(stmt)}

    def low_stock(self, limit: int = 10) -> list[ProductVariant]:
        stmt = (
            self._select()
            .join(ProductVariant.product)
            .where(
                ProductVariant.is_active.is_(True),
                Product.status == ProductStatus.ACTIVE.value,
                ProductVariant.stock <= ProductVariant.low_stock_threshold,
            )
            .options(selectinload(ProductVariant.product))
            .order_by(ProductVariant.stock.asc(), ProductVariant.id)
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def sku_taken(self, sku: str, exclude_id: int | None = None) -> bool:
        stmt = select(ProductVariant.id).where(
            ProductVariant.business_id == self.business_id, ProductVariant.sku == sku
        )
        if exclude_id:
            stmt = stmt.where(ProductVariant.id != exclude_id)
        return self.session.scalar(stmt) is not None
