import uuid
from dataclasses import dataclass
from uuid import UUID

import structlog
from django.db import transaction

from apps.inventory.application.ledger import (
    ensure_stock_items,
    lock_stock_items,
    lock_warehouses_for_movement,
    post_movement,
)
from apps.inventory.domain.exceptions import SameWarehouseTransfer, StockItemNotFound
from apps.inventory.domain.movements import MovementType
from apps.inventory.domain.stock import StockBalance, withdrawal_delta
from apps.inventory.models import StockItem

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class TransferStockCommand:
    organization_id: UUID
    actor_id: UUID
    stock_item_id: UUID
    to_warehouse_id: UUID
    quantity: int
    reason: str = ""


@dataclass(frozen=True)
class TransferResult:
    transfer_id: UUID
    source: StockItem
    destination: StockItem


class TransferStock:
    """Move unidades disponíveis entre depósitos (dois movimentos com o mesmo `reference_id`)."""

    def execute(self, command: TransferStockCommand) -> TransferResult:
        organization_id = command.organization_id
        with transaction.atomic():
            source_ref = (
                StockItem.objects.for_organization(organization_id)
                .filter(id=command.stock_item_id)
                .values("product_id", "warehouse_id")
                .first()
            )
            if source_ref is None:
                raise StockItemNotFound()
            if source_ref["warehouse_id"] == command.to_warehouse_id:
                raise SameWarehouseTransfer(details={"field": "to_warehouse_id"})

            lock_warehouses_for_movement(
                organization_id, [source_ref["warehouse_id"], command.to_warehouse_id]
            )
            ensure_stock_items(
                organization_id, [(source_ref["product_id"], command.to_warehouse_id)]
            )
            # Os dois itens em ordem de id: transferências opostas simultâneas não fazem deadlock.
            items = lock_stock_items(
                organization_id,
                product_id=source_ref["product_id"],
                warehouse_id__in=[source_ref["warehouse_id"], command.to_warehouse_id],
            )
            source = next(i for i in items if i.id == command.stock_item_id)
            destination = next(i for i in items if i.id != command.stock_item_id)

            delta = withdrawal_delta(
                StockBalance(source.on_hand, source.reserved), command.quantity
            )
            transfer_id = uuid.uuid4()
            for item, item_delta in ((source, delta), (destination, -delta)):
                post_movement(
                    item,
                    MovementType.TRANSFER,
                    on_hand_delta=item_delta,
                    actor_id=command.actor_id,
                    reference_type="transfer",
                    reference_id=transfer_id,
                    reason=command.reason.strip(),
                )
        logger.info(
            "inventory.stock.transferred",
            transfer_id=str(transfer_id),
            quantity=command.quantity,
            from_warehouse_id=str(source.warehouse_id),
            to_warehouse_id=str(destination.warehouse_id),
        )
        return TransferResult(transfer_id=transfer_id, source=source, destination=destination)
