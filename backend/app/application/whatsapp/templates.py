"""Order notification templates.

`body` mirrors the text of the template approved in WhatsApp Manager, so the seller sees an
accurate preview. Template names come from settings; an empty name means "not approved yet".
"""

from dataclasses import dataclass
from decimal import Decimal

from app.core.config import Settings
from app.domain.enums import NotificationKind, OrderStatus

S = OrderStatus


@dataclass(frozen=True)
class NotificationTemplate:
    kind: NotificationKind
    template_name: str
    language: str
    body: str
    eligible_statuses: frozenset[OrderStatus]

    @property
    def is_configured(self) -> bool:
        return bool(self.template_name)

    def render(self, parameters: list[str]) -> str:
        text = self.body
        for index, value in enumerate(parameters, start=1):
            text = text.replace("{{" + str(index) + "}}", value)
        return text


def format_bdt(amount: Decimal) -> str:
    amount = Decimal(amount)
    if amount == amount.to_integral_value():
        return f"{int(amount):,}"
    return f"{amount:,.2f}"


BODIES = {
    NotificationKind.ORDER_CONFIRMED: (
        "Assalamu Alaikum! Your order #{{1}} has been confirmed. Total: ৳{{2}}. Thank you for shopping with {{3}}."
    ),
    NotificationKind.ORDER_SHIPPED: (
        "Assalamu Alaikum! Your order #{{1}} has been shipped. Amount payable on delivery: ৳{{2}}. "
        "Thank you for shopping with {{3}}."
    ),
    NotificationKind.ORDER_DELIVERED: (
        "Assalamu Alaikum! Your order #{{1}} has been delivered. Thank you for shopping with {{2}}."
    ),
}

ELIGIBLE = {
    NotificationKind.ORDER_CONFIRMED: frozenset({S.CONFIRMED, S.PROCESSING, S.SHIPPED}),
    NotificationKind.ORDER_SHIPPED: frozenset({S.SHIPPED}),
    NotificationKind.ORDER_DELIVERED: frozenset({S.DELIVERED}),
}


def template_registry(settings: Settings) -> dict[NotificationKind, NotificationTemplate]:
    names = {
        NotificationKind.ORDER_CONFIRMED: settings.wa_template_order_confirmed,
        NotificationKind.ORDER_SHIPPED: settings.wa_template_order_shipped,
        NotificationKind.ORDER_DELIVERED: settings.wa_template_order_delivered,
    }
    return {
        kind: NotificationTemplate(kind, names[kind].strip(), settings.wa_template_language, BODIES[kind], ELIGIBLE[kind])
        for kind in BODIES
    }


def order_parameters(kind: NotificationKind, *, order_number: str, total: Decimal, amount_due: Decimal,
                     business_name: str) -> list[str]:
    if kind == NotificationKind.ORDER_CONFIRMED:
        return [order_number, format_bdt(total), business_name]
    if kind == NotificationKind.ORDER_SHIPPED:
        return [order_number, format_bdt(amount_due), business_name]
    if kind == NotificationKind.ORDER_DELIVERED:
        return [order_number, business_name]
    raise ValueError(f"No template parameters for {kind}")
