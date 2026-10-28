from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import ProductStatus
from app.infrastructure.db.base import Base, TimestampMixin


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("business_id", "sku"),
        Index("ix_products_business_status", "business_id", "status"),
        Index("ix_products_business_name", "business_id", "name"),
        CheckConstraint("price >= 0", name="price_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    sku: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal]
    cost_price: Mapped[Decimal | None]
    status: Mapped[str] = mapped_column(String(20), default=ProductStatus.ACTIVE.value)
    image_path: Mapped[str | None] = mapped_column(String(500))

    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductVariant.id"
    )


class ProductVariant(TimestampMixin, Base):
    """Size/colour combination that carries stock. Products without options have one default variant."""

    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("product_id", "size", "color"),
        UniqueConstraint("business_id", "sku"),
        CheckConstraint("stock >= 0", name="stock_non_negative"),
        Index("ix_product_variants_business_stock", "business_id", "stock"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    sku: Mapped[str | None] = mapped_column(String(64))
    size: Mapped[str] = mapped_column(String(30), default="")
    color: Mapped[str] = mapped_column(String(40), default="")
    price: Mapped[Decimal | None]  # overrides product price when set
    stock: Mapped[int] = mapped_column(default=0)
    low_stock_threshold: Mapped[int] = mapped_column(default=3)
    is_active: Mapped[bool] = mapped_column(default=True)

    product: Mapped[Product] = relationship(back_populates="variants")

    @property
    def label(self) -> str:
        parts = [p for p in (self.size, self.color) if p]
        return " / ".join(parts) if parts else "Default"

    @property
    def effective_price(self) -> Decimal:
        return self.price if self.price is not None else self.product.price
