"""Rastreio das remessas em trânsito (Beat). Entregue ⇒ evento para `orders` (outbox)."""

from datetime import datetime
from uuid import UUID

import structlog
from django.db import transaction
from django.utils import timezone

from apps.shipping.application.shipments import tracking_interval
from apps.shipping.domain.events import ShipmentDelivered
from apps.shipping.domain.provider import ProviderUnavailable
from apps.shipping.domain.status import DeliverySource, ShipmentStatus
from apps.shipping.infrastructure.providers import get_shipping_provider
from apps.shipping.models import Shipment
from shared.events.bus import publish

logger = structlog.get_logger(__name__)

BATCH_SIZE = 100


def track_shipment(shipment_id: UUID, *, now: datetime) -> bool:
    """Consulta uma remessa. Devolve `True` se ela foi dada como entregue agora."""
    shipment = Shipment.objects.get(id=shipment_id)
    if shipment.status != ShipmentStatus.IN_TRANSIT:
        return False
    try:  # consulta fora de transação (I/O externo)
        delivered_at = (
            get_shipping_provider().track(tracking_code=shipment.tracking_code).delivered_at
        )
    except ProviderUnavailable:
        delivered_at = None  # sem resposta: tenta no próximo intervalo
    with transaction.atomic():
        locked = (
            Shipment.objects.select_for_update(skip_locked=True)
            .filter(id=shipment_id, status=ShipmentStatus.IN_TRANSIT)
            .first()
        )
        if locked is None:  # confirmada à mão nesse meio-tempo, ou outro rastreio em curso
            return False
        locked.last_checked_at = now
        if delivered_at is None:
            locked.next_check_at = now + tracking_interval()
            locked.save()
            return False
        locked.status = ShipmentStatus.DELIVERED
        locked.delivered_at = delivered_at
        locked.delivery_source = DeliverySource.PROVIDER
        locked.next_check_at = None
        locked.save()
        publish(
            ShipmentDelivered(
                organization_id=locked.organization_id,
                shipment_id=locked.id,
                order_id=locked.order_id,
            )
        )
    logger.info("shipping.shipment.delivered", shipment_id=str(shipment_id), source="PROVIDER")
    return True


def track_due_shipments(now: datetime | None = None) -> int:
    now = now or timezone.now()
    due = list(
        Shipment.objects.filter(
            status=ShipmentStatus.IN_TRANSIT, next_check_at__lte=now
        ).values_list("id", flat=True)[:BATCH_SIZE]
    )
    delivered = sum(track_shipment(shipment_id, now=now) for shipment_id in due)
    if due:
        logger.info("shipping.tracking.run", checked=len(due), delivered=delivered)
    return delivered
