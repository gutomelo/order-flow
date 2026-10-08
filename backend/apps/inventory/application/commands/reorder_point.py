"""Ponto de reposição (configuração, não saldo: não passa pelo ledger, mas é auditado)."""

from uuid import UUID

from django.db import transaction

from apps.inventory.domain.events import ReorderPointChanged
from apps.inventory.models import StockItem
from shared.events.bus import publish


def update_reorder_point(
    organization_id: UUID, actor_id: UUID, stock_item_id: UUID, reorder_point: int
) -> StockItem:
    with transaction.atomic():
        item = (
            StockItem.objects.for_organization(organization_id)
            .select_for_update()
            .get(id=stock_item_id)
        )
        before = item.reorder_point
        if before == reorder_point:  # sem mudança, sem registro
            return item
        item.reorder_point = reorder_point
        item.save(update_fields=["reorder_point", "updated_at"])
        publish(
            ReorderPointChanged(
                organization_id=organization_id,
                stock_item_id=item.id,
                before=before,
                after=reorder_point,
                actor_id=actor_id,
            )
        )
    item.refresh_from_db()  # `available` é calculado pelo banco
    return item
