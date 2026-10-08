"""Cotação de preços — interface pública para `orders` (docs/domain/pricing.md)."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from apps.pricing.exceptions import PriceNotFound
from apps.pricing.models import PriceListItem
from shared.domain.money import Money


class PriceSource(StrEnum):
    SEGMENT = "SEGMENT"
    DEFAULT = "DEFAULT"


@dataclass(frozen=True)
class PriceQuote:
    product_id: UUID
    unit_price: Money
    source: PriceSource


def quote_prices(
    organization_id: UUID, segment_id: UUID | None, product_ids: Sequence[UUID]
) -> dict[UUID, PriceQuote]:
    """Preço de cada produto para um cliente do segmento `segment_id` (ou sem segmento).

    Ordem: tabela do segmento → tabela padrão. Produto sem preço em nenhuma → `PriceNotFound`
    com `details.product_ids` (o pedido marca as linhas afetadas).
    """
    wanted = set(product_ids)
    items = (
        PriceListItem.objects.for_organization(organization_id)
        .filter(product_id__in=wanted)
        .filter(price_list__segment_id__isnull=True)
        .values_list("product_id", "unit_price")
    )
    quotes = {pid: PriceQuote(pid, Money(price), PriceSource.DEFAULT) for pid, price in items}
    if segment_id is not None:
        segment_items = (
            PriceListItem.objects.for_organization(organization_id)
            .filter(product_id__in=wanted, price_list__segment_id=segment_id)
            .values_list("product_id", "unit_price")
        )
        for pid, price in segment_items:
            quotes[pid] = PriceQuote(pid, Money(price), PriceSource.SEGMENT)
    missing = sorted(str(pid) for pid in wanted - quotes.keys())
    if missing:
        raise PriceNotFound(details={"product_ids": missing})
    return quotes
