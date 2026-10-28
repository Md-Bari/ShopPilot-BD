from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.domain.enums import ConsentStatus, MessageStatus, OrderStatus, PaymentStatus, WhatsAppMode
from app.domain.errors import ValidationError
from app.domain.messaging_policy import (
    MessagingContext,
    free_form_blockers,
    is_service_window_open,
    should_apply_status,
    template_blockers,
)
from app.domain.order_rules import assert_transition
from app.domain.phone import normalize_phone, normalize_wa_id, to_wa_id
from app.domain.pricing import LineInput, calculate_totals, estimated_profit, payment_status_for

D = Decimal
NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


class TestPricing:
    def test_totals(self):
        totals = calculate_totals(
            [LineInput(D("650"), 2, D("400")), LineInput(D("99.995"), 1, D("50"))], D("60"), D("100"))
        assert totals.subtotal == D("1400.00")  # 1300 + 100.00 (rounded line)
        assert totals.total == D("1360.00")
        assert totals.cost_total == D("850.00")

    def test_discount_cannot_exceed_subtotal(self):
        with pytest.raises(ValidationError):
            calculate_totals([LineInput(D("100"), 1)], D("0"), D("101"))

    def test_requires_items_and_positive_quantity(self):
        with pytest.raises(ValidationError):
            calculate_totals([], D("0"), D("0"))
        with pytest.raises(ValidationError):
            calculate_totals([LineInput(D("100"), 0)], D("0"), D("0"))

    def test_payment_status(self):
        assert payment_status_for(D("100"), D("0")) == PaymentStatus.UNPAID
        assert payment_status_for(D("100"), D("40")) == PaymentStatus.PARTIAL
        assert payment_status_for(D("100"), D("100")) == PaymentStatus.PAID

    def test_profit_excludes_delivery(self):
        assert estimated_profit(D("1000"), D("100"), D("600")) == D("300.00")


class TestOrderRules:
    def test_valid_transitions(self):
        assert_transition(OrderStatus.PENDING, OrderStatus.CONFIRMED)
        assert_transition(OrderStatus.SHIPPED, OrderStatus.RETURNED)

    @pytest.mark.parametrize("current,target", [
        (OrderStatus.PENDING, OrderStatus.DELIVERED),
        (OrderStatus.CANCELLED, OrderStatus.CONFIRMED),
        (OrderStatus.DELIVERED, OrderStatus.SHIPPED),
    ])
    def test_invalid_transitions(self, current, target):
        with pytest.raises(ValidationError):
            assert_transition(current, target)


class TestPhone:
    @pytest.mark.parametrize("raw", ["01712345678", "+8801712345678", "8801712345678", "01712-345678",
                                     "+880 1712 345678", "008801712345678"])
    def test_normalizes_bd_formats(self, raw):
        assert normalize_phone(raw) == "+8801712345678"

    @pytest.mark.parametrize("raw", ["", "123", "abc", "0171234"])
    def test_rejects_invalid(self, raw):
        with pytest.raises(ValidationError):
            normalize_phone(raw)

    def test_wa_id_roundtrip(self):
        assert normalize_wa_id("8801712345678") == "+8801712345678"
        assert to_wa_id("+8801712345678") == "8801712345678"


class TestMessagingPolicy:
    def ctx(self, **kw):
        base = dict(mode=WhatsAppMode.PRODUCTION, recipient="+8801712345678")
        base.update(kw)
        return MessagingContext(**base)

    def test_service_window(self):
        assert is_service_window_open(NOW - timedelta(hours=23), NOW)
        assert not is_service_window_open(NOW - timedelta(hours=25), NOW)
        assert not is_service_window_open(None, NOW)

    def test_free_form_requires_open_window(self):
        assert free_form_blockers(self.ctx(last_inbound_at=NOW - timedelta(hours=1)), NOW) == []
        assert free_form_blockers(self.ctx(last_inbound_at=NOW - timedelta(days=2)), NOW)

    def test_template_requires_consent(self):
        assert template_blockers(self.ctx())
        assert template_blockers(self.ctx(transactional_consent=ConsentStatus.GRANTED)) == []
        assert template_blockers(self.ctx(transactional_consent=ConsentStatus.REVOKED))

    def test_opt_out_blocks_free_form_too(self):
        reasons = free_form_blockers(self.ctx(last_inbound_at=NOW, transactional_consent=ConsentStatus.REVOKED), NOW)
        assert any("opted out" in r for r in reasons)

    def test_test_mode_requires_authorized_recipient(self):
        ctx = self.ctx(mode=WhatsAppMode.TEST, transactional_consent=ConsentStatus.GRANTED)
        assert template_blockers(ctx)
        ctx = self.ctx(mode=WhatsAppMode.TEST, transactional_consent=ConsentStatus.GRANTED,
                       test_recipients=frozenset({"+8801712345678"}))
        assert template_blockers(ctx) == []

    @pytest.mark.parametrize("current,new,expected", [
        (MessageStatus.ACCEPTED, MessageStatus.SENT, True),
        (MessageStatus.SENT, MessageStatus.DELIVERED, True),
        (MessageStatus.DELIVERED, MessageStatus.SENT, False),  # out-of-order webhook
        (MessageStatus.READ, MessageStatus.DELIVERED, False),
        (MessageStatus.SENT, MessageStatus.FAILED, True),
        (MessageStatus.READ, MessageStatus.FAILED, False),
        (MessageStatus.FAILED, MessageStatus.DELIVERED, False),
        (MessageStatus.UNKNOWN, MessageStatus.DELIVERED, True),
        (MessageStatus.SENT, MessageStatus.SENT, False),
    ])
    def test_status_progression(self, current, new, expected):
        assert should_apply_status(current, new) is expected
