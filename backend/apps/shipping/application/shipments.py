"""Remessa do pedido (docs/domain/shipping.md). Chamado por `orders`, que coordena o envio.

request_label     I/O com a transportadora, FORA de transação (S4)
record_shipment   grava a remessa na transação de `orders` (pedido travado)
confirm_delivery  entrega confirmada por uma pessoa (retirada, transportadora própria...)
"""

from datetime import timedelta
from uuid import UUID

import structlog
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.shipping.domain.exceptions import ShippingUnavailable
from apps.shipping.domain.provider import Destination, Label, ProviderUnavailable
from apps.shipping.domain.status import DeliverySource, ShipmentStatus
from apps.shipping.infrastructure.providers import get_shipping_provider
from apps.shipping.models import Shipment

logger = structlog.get_logger(__name__)


def tracking_interval() -> timedelta:
    return timedelta(minutes=settings.SHIPMENT_TRACKING_INTERVAL_MINUTES)


def request_label(*, order_id: UUID, reference: str, destination: Destination) -> Label:
    """Etiqueta na transportadora. A chave é o pedido (S1): repetir devolve a mesma etiqueta."""
    try:
        return get_shipping_provider().create_shipment(
            idempotency_key=order_id, reference=reference, destination=destination
        )
    except ProviderUnavailable as exc:
        logger.warning("shipping.provider.unavailable", order_id=str(order_id), error=str(exc))
        raise ShippingUnavailable() from exc


def record_shipment(
    organization_id: UUID,
    actor_id: UUID,
    *,
    order_id: UUID,
    order_reference: str,
    label: Label,
) -> Shipment:
    now = timezone.now()
    shipment = Shipment.objects.create(
        organization_id=organization_id,
        order_id=order_id,
        order_reference=order_reference,
        carrier=label.carrier,
        tracking_code=label.tracking_code,
        status=ShipmentStatus.IN_TRANSIT,
        shipped_at=now,
        shipped_by_id=actor_id,
        next_check_at=now + tracking_interval(),
    )
    logger.info("shipping.shipment.created", shipment_id=str(shipment.id), order_id=str(order_id))
    return shipment


def confirm_delivery(
    organization_id: UUID, actor_id: UUID, order_id: UUID, *, note: str
) -> Shipment:
    """Confirmação manual. Idempotente: remessa já entregue (pelo rastreio) fica como está."""
    with transaction.atomic():
        shipment = (
            Shipment.objects.for_organization(organization_id)
            .select_for_update()
            .get(order_id=order_id)
        )
        if shipment.status == ShipmentStatus.DELIVERED:
            return shipment
        shipment.status = ShipmentStatus.DELIVERED
        shipment.delivered_at = timezone.now()
        shipment.delivery_source = DeliverySource.MANUAL
        shipment.delivered_by_id = actor_id
        shipment.delivery_note = note
        shipment.next_check_at = None
        shipment.save()
    logger.info("shipping.shipment.delivered", shipment_id=str(shipment.id), source="MANUAL")
    return shipment
