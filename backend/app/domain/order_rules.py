"""Order lifecycle rules."""

from app.domain.enums import OrderStatus
from app.domain.errors import ValidationError

S = OrderStatus

ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    S.PENDING: frozenset({S.CONFIRMED, S.CANCELLED}),
    S.CONFIRMED: frozenset({S.PROCESSING, S.SHIPPED, S.CANCELLED}),
    S.PROCESSING: frozenset({S.SHIPPED, S.CANCELLED}),
    S.SHIPPED: frozenset({S.DELIVERED, S.RETURNED}),
    S.DELIVERED: frozenset({S.RETURNED}),
    S.CANCELLED: frozenset(),
    S.RETURNED: frozenset(),
}

# Moving into these statuses puts reserved stock back on the shelf.
RESTOCK_STATUSES = frozenset({S.CANCELLED, S.RETURNED})

# Orders that count towards gross order value (placed and not cancelled).
GROSS_VALUE_EXCLUDED = frozenset({S.CANCELLED})


def allowed_next_statuses(current: OrderStatus) -> frozenset[OrderStatus]:
    return ALLOWED_TRANSITIONS[OrderStatus(current)]


def assert_transition(current: OrderStatus, target: OrderStatus) -> None:
    current, target = OrderStatus(current), OrderStatus(target)
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ValidationError(
            f"Cannot change order status from {current.value} to {target.value}.",
            code="invalid_status_transition",
            details={"allowed": sorted(s.value for s in ALLOWED_TRANSITIONS[current])},
        )
