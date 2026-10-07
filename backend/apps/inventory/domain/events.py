from dataclasses import dataclass
from uuid import UUID

from shared.events.base import DomainEvent


@dataclass(frozen=True, kw_only=True)
class StockLevelLow(DomainEvent):
    """O disponível do item cruzou o ponto de reposição para baixo (`crossed_reorder_point`)."""

    event_name = "inventory.stock.low"

    organization_id: UUID
    stock_item_id: UUID
    available: int
    reorder_point: int
