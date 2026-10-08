from uuid import UUID

from apps.orders.domain.events import OrderStatusChanged
from apps.orders.domain.state_machine import assert_transition
from apps.orders.domain.status import OrderStatus
from apps.orders.models import Order, OrderStatusHistory
from shared.events.bus import publish


def lock_order(organization_id: UUID, order_id: UUID) -> Order:
    """Toda transição acontece com o pedido bloqueado (docs/domain/orders.md)."""
    return (
        Order.objects.for_organization(organization_id)
        .select_for_update(of=("self",))
        .get(id=order_id)
    )


def transition(
    order: Order, target: OrderStatus, *, actor_id: UUID | None, reason: str = ""
) -> None:
    """Único caminho para mudar `status` (O10), sempre com histórico (O9) e evento (outbox) na
    mesma transação: rollback desfaz os três."""
    source = None if order._state.adding else OrderStatus(order.status)
    assert_transition(source, target)
    order.status = target
    order.save()
    OrderStatusHistory.objects.create(
        organization_id=order.organization_id,
        order=order,
        from_status=source.value if source else None,
        to_status=target.value,
        changed_by_id=actor_id,
        reason=reason,
    )
    publish(
        OrderStatusChanged(
            organization_id=order.organization_id,
            order_id=order.id,
            from_status=source.value if source else None,
            to_status=target.value,
            actor_id=actor_id,
            reason=reason,
        )
    )
