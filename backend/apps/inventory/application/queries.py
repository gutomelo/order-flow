"""Leituras públicas de estoque para outros módulos (ex.: orders)."""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from apps.inventory.models import StockItem, Warehouse


def get_active_warehouse(organization_id: UUID, warehouse_id: UUID) -> Warehouse | None:
    return (
        Warehouse.objects.for_organization(organization_id)
        .filter(id=warehouse_id, is_active=True)
        .first()
    )


@dataclass(frozen=True)
class StockLevel:
    on_hand: int
    reserved: int
    available: int


def stock_levels(
    organization_id: UUID, warehouse_id: UUID, product_ids: Sequence[UUID]
) -> dict[UUID, StockLevel]:
    """Saldo atual por produto no depósito (produto sem item = zero). Leitura sem lock:
    serve para informar a tela; quem decide é a reserva (com lock)."""
    rows = (
        StockItem.objects.for_organization(organization_id)
        .filter(warehouse_id=warehouse_id, product_id__in=product_ids)
        .values_list("product_id", "on_hand", "reserved", "available")
    )
    levels = {
        pid: StockLevel(on_hand, reserved, available) for pid, on_hand, reserved, available in rows
    }
    return {pid: levels.get(pid, StockLevel(0, 0, 0)) for pid in product_ids}
