"""Grava o registro de auditoria a partir de um evento do outbox (ADR-011).

Roda na transação da entrega do evento: `ProcessedEvent` + o UNIQUE de `source_event_id`
garantem um registro por evento, mesmo com reentrega.
"""

from uuid import UUID

import structlog

from apps.audit.domain.entries import AuditEntry, EntityType
from apps.audit.models import AuditLog
from apps.inventory.application.queries import get_stock_item_view
from apps.orders.application.queries import get_order_view
from shared.events.base import EventEnvelope

logger = structlog.get_logger(__name__)


def _label(organization_id: UUID, entry: AuditEntry, order_reference: str) -> str:
    """Nome legível na hora do registro (o histórico não muda se o produto for renomeado)."""
    if entry.entity_type == EntityType.STOCK_ITEM:
        item = get_stock_item_view(organization_id, entry.entity_id)
        return f"{item.sku} · {item.warehouse_code}" if item else str(entry.entity_id)
    if order_reference:
        return order_reference
    order = get_order_view(organization_id, entry.order_id) if entry.order_id else None
    return order.reference if order else str(entry.entity_id)


def record(event: EventEnvelope, entry: AuditEntry) -> AuditLog:
    organization_id = UUID(event.payload["organization_id"])
    log = AuditLog.objects.create(
        organization_id=organization_id,
        action=entry.action,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        entity_label=_label(organization_id, entry, event.payload.get("order_reference", "")),
        order_id=entry.order_id,
        actor_id=entry.actor_id,
        reason=entry.reason[:500],
        changes=entry.changes,
        occurred_at=event.occurred_at,
        request_id=event.payload.get("request_id", "")[:64],
        source_event_id=event.event_id,
    )
    logger.info("audit.log.recorded", audit_id=str(log.id), action=entry.action.value)
    return log
