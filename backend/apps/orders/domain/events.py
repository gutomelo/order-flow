from dataclasses import dataclass
from uuid import UUID

from shared.events.base import DomainEvent


@dataclass(frozen=True, kw_only=True)
class OrderStatusChanged(DomainEvent):
    """Toda transição do pedido (publicada por `transition`, o único caminho de mudança de status).

    Um evento genérico em vez de um por transição: quem consome decide o que lhe interessa
    (notificações hoje; auditoria na Phase 12). Payload mínimo — detalhes vêm de
    `orders.application.queries` pelo id.
    """

    event_name = "orders.order.status_changed"

    organization_id: UUID
    order_id: UUID
    from_status: str | None
    to_status: str
