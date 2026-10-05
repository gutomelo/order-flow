"""Leituras públicas de estoque para outros módulos (ex.: orders)."""

from uuid import UUID

from apps.inventory.models import Warehouse


def get_active_warehouse(organization_id: UUID, warehouse_id: UUID) -> Warehouse | None:
    return (
        Warehouse.objects.for_organization(organization_id)
        .filter(id=warehouse_id, is_active=True)
        .first()
    )
