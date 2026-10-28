"""Tenant-scoped repository base.

Every query goes through `_select()`, which always filters by the tenant's business_id.
This is the single place tenant isolation is enforced at the data-access level.
"""

from typing import Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.errors import NotFoundError

T = TypeVar("T")


class TenantRepository(Generic[T]):
    model: type[T]
    label: str = "Record"

    def __init__(self, session: Session, business_id: int):
        self.session = session
        self.business_id = business_id

    def _select(self) -> Select:
        return select(self.model).where(self.model.business_id == self.business_id)

    def get(self, entity_id: int, *, for_update: bool = False) -> T | None:
        stmt = self._select().where(self.model.id == entity_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.session.scalar(stmt)

    def get_or_raise(self, entity_id: int, *, for_update: bool = False) -> T:
        entity = self.get(entity_id, for_update=for_update)
        if entity is None:
            raise NotFoundError(f"{self.label} not found.")
        return entity

    def add(self, entity: T) -> T:
        entity.business_id = self.business_id
        self.session.add(entity)
        return entity

    def paginate(self, stmt: Select, page: int, page_size: int) -> tuple[list[T], int]:
        total = self.session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
        items = list(self.session.scalars(stmt.limit(page_size).offset((page - 1) * page_size)).unique())
        return items, total
