"""Eventos que viram e-mail (outbox, ADR-011). Cada handler só cria registros; o envio é uma task
separada, depois do commit — e-mail nunca sai de dentro de uma transação que pode desfazer."""

from uuid import UUID

from apps.customers.selectors import get_notification_recipient
from apps.identity.application.queries import active_users_with_permission, get_user_contact
from apps.identity.domain.permissions import Permission
from apps.notifications.application.queueing import queue_notification
from apps.notifications.domain.kinds import NotificationKind
from apps.notifications.domain.policies import PAID_STATUSES, order_notification_kind
from apps.orders.application.queries import get_order_view
from shared.events.base import EventEnvelope
from shared.events.bus import subscribe


@subscribe("orders.order.status_changed")
def on_order_status_changed(event: EventEnvelope) -> None:
    payload = event.payload
    kind = order_notification_kind(payload["from_status"], payload["to_status"])
    if kind is None:
        return
    organization_id = UUID(payload["organization_id"])
    order = get_order_view(organization_id, UUID(payload["order_id"]))
    if order is None:
        return
    recipient = get_notification_recipient(organization_id, order.customer_id)
    queue_notification(
        organization_id=organization_id,
        kind=kind,
        source_event_id=event.event_id,
        reference_id=order.id,
        recipient_email=recipient.email if recipient else "",
        recipient_name=recipient.name if recipient else order.customer_name,
        # Cancelar pedido pago estorna: o texto avisa. Vem do evento (o pedido já mudou).
        context={"refund": payload["from_status"] in PAID_STATUSES},
    )


@subscribe("inventory.stock.low")
def on_stock_low(event: EventEnvelope) -> None:
    organization_id = UUID(event.payload["organization_id"])
    # Quem cuida do estoque = quem pode movimentá-lo (RBAC), não um papel fixo.
    for user in active_users_with_permission(organization_id, Permission.INVENTORY_UPDATE):
        queue_notification(
            organization_id=organization_id,
            kind=NotificationKind.STOCK_LOW,
            source_event_id=event.event_id,
            reference_id=UUID(event.payload["stock_item_id"]),
            recipient_email=user.email,
            recipient_name=user.first_name,
        )


def _queue_for_user(event: EventEnvelope, kind: NotificationKind) -> None:
    user = get_user_contact(UUID(event.payload["user_id"]))
    if user is None:
        return
    queue_notification(
        organization_id=UUID(event.payload["organization_id"]),
        kind=kind,
        source_event_id=event.event_id,
        reference_id=user.id,
        recipient_email=user.email,
        recipient_name=user.first_name,
    )


@subscribe("identity.user.invited")
def on_user_invited(event: EventEnvelope) -> None:
    _queue_for_user(event, NotificationKind.USER_INVITATION)


@subscribe("identity.password_reset.requested")
def on_password_reset_requested(event: EventEnvelope) -> None:
    _queue_for_user(event, NotificationKind.PASSWORD_RESET)
