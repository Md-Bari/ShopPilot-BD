"""Order money calculations. All values are Decimal rounded to 2 places."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.domain.enums import PaymentStatus
from app.domain.errors import ValidationError

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class LineInput:
    unit_price: Decimal
    quantity: int
    unit_cost: Decimal = ZERO


@dataclass(frozen=True)
class OrderTotals:
    subtotal: Decimal
    delivery_charge: Decimal
    discount: Decimal
    total: Decimal
    cost_total: Decimal


def line_total(line: LineInput) -> Decimal:
    return money(line.unit_price * line.quantity)


def calculate_totals(lines: list[LineInput], delivery_charge: Decimal, discount: Decimal) -> OrderTotals:
    if not lines:
        raise ValidationError("An order needs at least one item.")
    for line in lines:
        if line.quantity <= 0:
            raise ValidationError("Quantity must be at least 1.")
        if line.unit_price < 0 or line.unit_cost < 0:
            raise ValidationError("Prices cannot be negative.")
    delivery_charge = money(delivery_charge)
    discount = money(discount)
    if delivery_charge < 0 or discount < 0:
        raise ValidationError("Delivery charge and discount cannot be negative.")

    subtotal = money(sum((line_total(line) for line in lines), ZERO))
    if discount > subtotal:
        raise ValidationError("Discount cannot exceed the subtotal.")
    cost_total = money(sum((line.unit_cost * line.quantity for line in lines), ZERO))
    total = money(subtotal + delivery_charge - discount)
    return OrderTotals(subtotal, delivery_charge, discount, total, cost_total)


def payment_status_for(total: Decimal, amount_paid: Decimal) -> PaymentStatus:
    if amount_paid <= 0:
        return PaymentStatus.UNPAID
    if amount_paid >= total:
        return PaymentStatus.PAID
    return PaymentStatus.PARTIAL


def estimated_profit(subtotal: Decimal, discount: Decimal, cost_total: Decimal) -> Decimal:
    """Product margin of an order. Delivery charges are treated as pass-through to the courier."""
    return money(subtotal - discount - cost_total)
