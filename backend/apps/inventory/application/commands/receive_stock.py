from dataclasses import dataclass
from uuid import UUID

import structlog
from django.db import IntegrityError, transaction

from apps.catalog.selectors import get_sellable_products
from apps.inventory.application.ledger import (
    ensure_stock_items,
    lock_stock_items,
    lock_warehouses_for_movement,
    post_movement,
)
from apps.inventory.domain.exceptions import (
    ProductNotAvailable,
    ReceiptAlreadyRegistered,
    SupplierNotAvailable,
)
from apps.inventory.domain.movements import MovementType
from apps.inventory.domain.stock import ensure_positive_quantity
from apps.inventory.models import StockMovement, StockReceipt
from apps.suppliers.selectors import get_active_supplier
from shared.infrastructure.db import violated_constraint

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ReceiptLine:
    product_id: UUID
    quantity: int


@dataclass(frozen=True)
class ReceiveStockCommand:
    organization_id: UUID
    actor_id: UUID
    warehouse_id: UUID
    lines: tuple[ReceiptLine, ...]
    supplier_id: UUID | None = None
    document_number: str = ""
    notes: str = ""


@dataclass(frozen=True)
class ReceiptResult:
    receipt: StockReceipt
    movements: list[StockMovement]


class ReceiveStock:
    """Entrada de mercadoria: tudo-ou-nada (R4); cada linha vira um movimento PURCHASE."""

    def execute(self, command: ReceiveStockCommand) -> ReceiptResult:
        product_ids = [line.product_id for line in command.lines]
        for line in command.lines:
            ensure_positive_quantity(line.quantity)

        try:
            with transaction.atomic():
                return self._receive(command, product_ids)
        except IntegrityError as exc:
            if violated_constraint(exc) == "inventory_receipt_org_supplier_document_uniq":
                raise ReceiptAlreadyRegistered(details={"field": "document_number"}) from exc
            raise

    def _receive(self, command: ReceiveStockCommand, product_ids: list[UUID]) -> ReceiptResult:
        organization_id = command.organization_id
        lock_warehouses_for_movement(organization_id, [command.warehouse_id])

        sellable = {p.id for p in get_sellable_products(organization_id, product_ids)}
        missing = [str(pid) for pid in product_ids if pid not in sellable]
        if missing:  # R2
            raise ProductNotAvailable(details={"product_ids": missing})
        if command.supplier_id and not get_active_supplier(organization_id, command.supplier_id):
            raise SupplierNotAvailable(details={"field": "supplier_id"})

        receipt = StockReceipt.objects.create(
            organization_id=organization_id,
            warehouse_id=command.warehouse_id,
            supplier_id=command.supplier_id,
            document_number=command.document_number.strip(),
            notes=command.notes.strip(),
            received_by_id=command.actor_id,
        )

        ensure_stock_items(organization_id, [(pid, command.warehouse_id) for pid in product_ids])
        items = {
            item.product_id: item
            for item in lock_stock_items(
                organization_id, warehouse_id=command.warehouse_id, product_id__in=product_ids
            )
        }
        movements = [
            post_movement(
                items[line.product_id],
                MovementType.PURCHASE,
                on_hand_delta=line.quantity,
                actor_id=command.actor_id,
                reference_type="receipt",
                reference_id=receipt.id,
            )
            for line in command.lines
        ]
        logger.info(
            "inventory.receipt.registered",
            receipt_id=str(receipt.id),
            warehouse_id=str(command.warehouse_id),
            lines=len(movements),
        )
        return ReceiptResult(receipt=receipt, movements=movements)
