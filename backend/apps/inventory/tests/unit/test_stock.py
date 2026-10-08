import pytest

from apps.inventory.domain.exceptions import (
    InsufficientStock,
    InvalidAdjustment,
    InvalidStockBalance,
    StockChangedSinceCount,
)
from apps.inventory.domain.stock import StockBalance, adjustment_delta, withdrawal_delta

pytestmark = pytest.mark.unit


def test_available_is_on_hand_minus_reserved() -> None:
    assert StockBalance(on_hand=10, reserved=3).available == 7


@pytest.mark.parametrize(
    ("on_hand_delta", "reserved_delta"),
    [(-11, 0), (0, -4), (0, 8), (-8, 0)],  # on_hand<0, reserved<0, reserved>on_hand (2 formas)
)
def test_apply_rejects_balances_that_break_invariants(
    on_hand_delta: int, reserved_delta: int
) -> None:
    with pytest.raises(InvalidStockBalance):
        StockBalance(10, 3).apply(on_hand_delta=on_hand_delta, reserved_delta=reserved_delta)


def test_apply_returns_the_new_balance() -> None:
    assert StockBalance(10, 3).apply(on_hand_delta=-2, reserved_delta=-2) == StockBalance(8, 1)


def test_withdrawal_cannot_take_reserved_units() -> None:
    balance = StockBalance(on_hand=5, reserved=4)

    assert withdrawal_delta(balance, 1) == -1
    with pytest.raises(InsufficientStock) as error:
        withdrawal_delta(balance, 2)
    assert error.value.details == {"requested": 2, "available": 1}


def test_withdrawal_requires_positive_quantity() -> None:
    with pytest.raises(ValueError):
        withdrawal_delta(StockBalance(5, 0), 0)


def test_adjustment_delta_is_counted_minus_current() -> None:
    assert adjustment_delta(StockBalance(10, 2), counted=7, expected_on_hand=10) == -3
    assert adjustment_delta(StockBalance(10, 2), counted=12, expected_on_hand=10) == 2
    assert adjustment_delta(StockBalance(10, 2), counted=10, expected_on_hand=10) == 0


def test_adjustment_rejects_stale_count() -> None:
    with pytest.raises(StockChangedSinceCount):
        adjustment_delta(StockBalance(9, 0), counted=5, expected_on_hand=10)


def test_adjustment_cannot_go_below_reserved() -> None:
    with pytest.raises(InvalidAdjustment):
        adjustment_delta(StockBalance(10, 4), counted=3, expected_on_hand=10)
