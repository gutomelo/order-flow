from decimal import Decimal

import pytest

from shared.domain.money import Money, quantize

pytestmark = pytest.mark.unit


def test_rounds_half_up_to_cents() -> None:
    assert quantize(Decimal("2.675")) == Decimal("2.68")
    assert quantize(Decimal("2.665")) == Decimal("2.67")
    assert Money(Decimal("10")).amount == Decimal("10.00")


def test_rejects_float() -> None:
    with pytest.raises(TypeError):
        Money(0.1)  # type: ignore[arg-type]


def test_arithmetic_keeps_cents_exact() -> None:
    price = Money(Decimal("0.10"))

    assert price.times(3) == Money(Decimal("0.30"))
    assert price + Money(Decimal("0.20")) == Money(Decimal("0.30"))


def test_refuses_mixing_currencies() -> None:
    with pytest.raises(ValueError, match="Moedas diferentes"):
        Money(Decimal(1)) + Money(Decimal(1), "USD")
