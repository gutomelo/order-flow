from dataclasses import dataclass
from uuid import UUID

import structlog
from django.db import transaction

from apps.inventory.application.ledger import (
    lock_stock_items,
    lock_warehouses_for_movement,
    post_movement,
)
from apps.inventory.domain.exceptions import StockItemNotFound
from apps.inventory.domain.movements import MovementType
from apps.inventory.domain.stock import StockBalance, adjustment_delta
from apps.inventory.models import StockItem, StockMovement

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class AdjustStockCommand:
    organization_id: UUID
    actor_id: UUID
    stock_item_id: UUID
    counted_quantity: int
    expected_on_hand: int
    reason: str


@dataclass(frozen=True)
class AdjustmentResult:
    stock_item: StockItem
    movement: StockMovement | None  # None quando a contagem confere com o saldo (A4)


class AdjustStock:
    """Ajuste por contagem física com controle otimista (A2) e lock pessimista curto (ADR-008)."""

    def execute(self, command: AdjustStockCommand) -> AdjustmentResult:
        organization_id = command.organization_id
        with transaction.atomic():
            warehouse_id = (
                StockItem.objects.for_organization(organization_id)
                .filter(id=command.stock_item_id)
                .values_list("warehouse_id", flat=True)
                .first()
            )
            if warehouse_id is None:
                raise StockItemNotFound()
            lock_warehouses_for_movement(organization_id, [warehouse_id])
            [item] = lock_stock_items(organization_id, id=command.stock_item_id)

            delta = adjustment_delta(
                StockBalance(item.on_hand, item.reserved),
                counted=command.counted_quantity,
                expected_on_hand=command.expected_on_hand,
            )
            if delta == 0:
                return AdjustmentResult(stock_item=item, movement=None)

            movement = post_movement(
                item,
                MovementType.ADJUSTMENT,
                on_hand_delta=delta,
                actor_id=command.actor_id,
                reference_type="adjustment",
                reason=command.reason.strip(),
            )
        logger.info(
            "inventory.stock.adjusted",
            stock_item_id=str(item.id),
            delta=delta,
            actor_id=str(command.actor_id),
        )
        return AdjustmentResult(stock_item=item, movement=movement)
