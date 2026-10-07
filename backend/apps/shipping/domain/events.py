from dataclasses import dataclass
from uuid import UUID

from shared.events.base import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ShipmentDelivered(DomainEvent):
    """A transportadora informou a entrega (rastreio). A confirmação manual não publica: quem
    confirma é `orders`, que já muda o pedido na mesma transação."""

    event_name = "shipping.shipment.delivered"

    organization_id: UUID
    shipment_id: UUID
    order_id: UUID
