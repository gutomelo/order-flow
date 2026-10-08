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


@dataclass(frozen=True, kw_only=True)
class StockChanged(DomainEvent):
    """Movimento **manual** de saldo (recebimento, ajuste, transferência), para a auditoria. Os
    movimentos do ciclo do pedido (reserva, liberação, venda) são auditados pelo pedido."""

    event_name = "inventory.stock.changed"

    organization_id: UUID
    stock_item_id: UUID
    movement_id: UUID
    movement_type: str
    on_hand_before: int
    on_hand_after: int
    reserved_before: int
    reserved_after: int
    actor_id: UUID | None
    reason: str


@dataclass(frozen=True, kw_only=True)
class ReorderPointChanged(DomainEvent):
    event_name = "inventory.reorder_point.changed"

    organization_id: UUID
    stock_item_id: UUID
    before: int
    after: int
    actor_id: UUID
