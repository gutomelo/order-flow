"""Prévia de preços e totais pelo mesmo código do pedido: a tela não faz contas de dinheiro."""

from dataclasses import dataclass
from uuid import UUID

from apps.orders.application import resolution
from apps.orders.domain.lines import (
    LineRequest,
    OrderTotals,
    PricedLine,
    compute_totals,
    validate_line_requests,
)


@dataclass(frozen=True)
class Quote:
    lines: list[PricedLine]
    totals: OrderTotals


def quote_order(organization_id: UUID, customer_id: UUID, lines: tuple[LineRequest, ...]) -> Quote:
    validate_line_requests(lines, require_lines=False)
    customer = resolution.active_customer(organization_id, customer_id)
    priced = resolution.price_lines(organization_id, customer, lines)
    return Quote(priced, compute_totals(priced))
