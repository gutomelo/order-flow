"""Leituras públicas de estoque para outros módulos (ex.: orders)."""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from django.db.models import F

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


@dataclass(frozen=True)
class StockItemView:
    id: UUID
    sku: str
    product_name: str
    warehouse_code: str
    warehouse_name: str
    available: int
    reorder_point: int


def get_stock_item_view(organization_id: UUID, stock_item_id: UUID) -> StockItemView | None:
    item = (
        StockItem.objects.for_organization(organization_id)
        .select_related("product", "warehouse")
        .filter(id=stock_item_id)
        .first()
    )
    if item is None:
        return None
    return StockItemView(
        id=item.id,
        sku=item.product.sku,
        product_name=item.product.name,
        warehouse_code=item.warehouse.code,
        warehouse_name=item.warehouse.name,
        available=item.available,
        reorder_point=item.reorder_point,
    )


def low_stock_count(organization_id: UUID) -> int:
    """Itens no ponto de reposição ou abaixo (mesma regra do filtro "estoque baixo" da tela)."""
    return (
        StockItem.objects.for_organization(organization_id)
        .filter(reorder_point__gt=0, available__lte=F("reorder_point"))
        .count()
    )
