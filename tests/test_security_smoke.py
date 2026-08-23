import pytest

from payment_routes import _money


def test_money_normalizes_decimal_amounts():
    assert _money("100") == "100.00"
    assert _money("100.5") == "100.50"
    assert _money("0") == "0.00"


def test_money_rejects_invalid_amounts_safely():
    assert _money("not-a-number") == "0.00"
    assert _money(None) == "0.00"
