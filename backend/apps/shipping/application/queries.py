"""Leituras públicas de remessas para `orders` (sem expor models)."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from apps.shipping.models import Shipment


@dataclass(frozen=True)
class ShipmentSummary:
    id: UUID
    carrier: str
    tracking_code: str
    status: str
    shipped_at: datetime
    delivered_at: datetime | None
    delivery_source: str
    delivery_note: str


def shipment_for_order(organization_id: UUID, order_id: UUID) -> ShipmentSummary | None:
    shipment = Shipment.objects.for_organization(organization_id).filter(order_id=order_id).first()
    if shipment is None:
        return None
    return ShipmentSummary(
        id=shipment.id,
        carrier=shipment.carrier,
        tracking_code=shipment.tracking_code,
        status=shipment.status,
        shipped_at=shipment.shipped_at,
        delivered_at=shipment.delivered_at,
        delivery_source=shipment.delivery_source,
        delivery_note=shipment.delivery_note,
    )
