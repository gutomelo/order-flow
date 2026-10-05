"""Linhas e totais do pedido: invariantes O1 a O5 e O8 (docs/domain/orders.md#invariantes)."""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from apps.orders.domain.exceptions import (
    DuplicateOrderLine,
    EmptyOrder,
    InvalidQuantity,
    PricesChanged,
)
from shared.domain.money import Money, quantize

ZERO = Money.zero()


@dataclass(frozen=True)
class LineRequest:
    product_id: UUID
    quantity: int


def validate_line_requests(lines: Sequence[LineRequest], *, require_lines: bool) -> None:
    if require_lines and not lines:  # O1
        raise EmptyOrder()
    invalid = [str(line.product_id) for line in lines if line.quantity < 1]
    if invalid:  # O2
        raise InvalidQuantity(details={"product_ids": invalid})
    counts = Counter(line.product_id for line in lines)
    duplicated = sorted(str(pid) for pid, count in counts.items() if count > 1)
    if duplicated:  # O8
        raise DuplicateOrderLine(details={"product_ids": duplicated})


@dataclass(frozen=True)
class PricedLine:
    product_id: UUID
    sku: str
    product_name: str
    quantity: int
    unit_price: Money
    price_source: str
    discount: Money = ZERO

    def __post_init__(self) -> None:
        # O3: desconto entre zero e o bruto da linha.
        if self.unit_price.amount < 0 or self.discount.amount < 0:
            raise ValueError("Preço e desconto não podem ser negativos.")
        if self.gross < self.discount:
            raise ValueError("Desconto maior que o valor da linha.")

    @property
    def gross(self) -> Money:
        return self.unit_price.times(self.quantity)

    @property
    def line_total(self) -> Money:  # O4: calculado, nunca aceito do cliente
        return self.gross - self.discount


@dataclass(frozen=True)
class OrderTotals:
    subtotal: Money
    discount_total: Money
    shipping_total: Money
    total: Money


def compute_totals(
    lines: Sequence[PricedLine],
    *,
    discount_total: Money = ZERO,
    shipping_total: Money = ZERO,
) -> OrderTotals:
    """O5: `subtotal = Σ line_total`; `total = subtotal - discount_total + shipping_total`."""
    subtotal = Money.zero()
    for line in lines:
        subtotal = subtotal + line.line_total
    total = subtotal - discount_total + shipping_total
    if total.amount < 0:
        raise ValueError("O total do pedido não pode ser negativo.")
    return OrderTotals(subtotal, discount_total, shipping_total, total)


def ensure_expected_total(expected: Decimal | None, actual: Money) -> None:
    """A pessoa confirma o total que viu; se a recotação mudou, ninguém confirma às cegas."""
    if expected is not None and quantize(expected) != actual.amount:
        raise PricesChanged(details={"expected": str(quantize(expected)), "actual": str(actual)})
