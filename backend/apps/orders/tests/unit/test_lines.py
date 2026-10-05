from decimal import Decimal
from uuid import uuid4

import pytest

from apps.orders.domain.exceptions import (
    DuplicateOrderLine,
    EmptyOrder,
    InvalidQuantity,
    PricesChanged,
)
from apps.orders.domain.lines import (
    LineRequest,
    PricedLine,
    compute_totals,
    ensure_expected_total,
    validate_line_requests,
)
from shared.domain.money import Money

pytestmark = pytest.mark.unit


def _line(quantity: int, price: str, discount: str = "0") -> PricedLine:
    return PricedLine(
        product_id=uuid4(),
        sku="SKU",
        product_name="Produto",
        quantity=quantity,
        unit_price=Money(Decimal(price)),
        price_source="DEFAULT",
        discount=Money(Decimal(discount)),
    )


def test_totals_follow_o4_and_o5() -> None:
    totals = compute_totals(
        [_line(3, "0.10"), _line(2, "19.99", discount="1.00")],
        shipping_total=Money(Decimal("15")),
    )

    assert totals.subtotal == Money(Decimal("39.28"))  # 0.30 + (39.98 - 1.00)
    assert totals.total == Money(Decimal("54.28"))


def test_discount_cannot_exceed_the_line() -> None:
    with pytest.raises(ValueError, match="Desconto maior"):
        _line(1, "5.00", discount="5.01")


def test_empty_order_is_rejected_only_when_lines_are_required() -> None:
    validate_line_requests([], require_lines=False)
    with pytest.raises(EmptyOrder):
        validate_line_requests([], require_lines=True)


def test_reports_which_lines_are_invalid() -> None:
    bad, good = uuid4(), uuid4()

    with pytest.raises(InvalidQuantity) as invalid:
        validate_line_requests([LineRequest(bad, 0), LineRequest(good, 1)], require_lines=True)
    with pytest.raises(DuplicateOrderLine) as duplicated:
        validate_line_requests([LineRequest(good, 1), LineRequest(good, 2)], require_lines=True)

    assert invalid.value.details == {"product_ids": [str(bad)]}
    assert duplicated.value.details == {"product_ids": [str(good)]}


def test_expected_total_must_match_the_recalculated_total() -> None:
    ensure_expected_total(None, Money(Decimal("10")))
    ensure_expected_total(Decimal("10.00"), Money(Decimal("10")))

    with pytest.raises(PricesChanged) as exc:
        ensure_expected_total(Decimal("9.90"), Money(Decimal("10")))
    assert exc.value.details == {"expected": "9.90", "actual": "10.00"}
