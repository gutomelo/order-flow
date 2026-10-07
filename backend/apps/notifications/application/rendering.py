"""Assunto e corpo de cada tipo de aviso, montados **na hora do envio** a partir dos dados atuais
(o corpo não é guardado — ver o model). Textos em pt-BR nos templates `notifications/email/`."""

from dataclasses import dataclass
from typing import Any

from django.template.loader import render_to_string

from apps.identity.application.passwords import password_setup_link
from apps.inventory.application.queries import get_stock_item_view
from apps.notifications.application.formatting import local_datetime, money
from apps.notifications.domain.kinds import NotificationKind
from apps.notifications.models import Notification
from apps.orders.application.queries import get_order_view

K = NotificationKind

ORDER_SUBJECTS = {
    K.ORDER_CONFIRMED: "Pedido {reference} confirmado — aguardando pagamento",
    K.ORDER_PAID: "Pagamento do pedido {reference} aprovado",
    K.ORDER_SHIPPED: "Pedido {reference} despachado",
    K.ORDER_DELIVERED: "Pedido {reference} entregue",
    K.ORDER_CANCELLED: "Pedido {reference} cancelado",
    K.ORDER_REFUNDED: "Estorno do pedido {reference} concluído",
}


@dataclass(frozen=True)
class EmailContent:
    subject: str
    body: str


def _render(kind: NotificationKind, context: dict[str, Any]) -> str:
    return render_to_string(f"notifications/email/{kind.value.lower()}.txt", context)


def _order_email(notification: Notification, kind: NotificationKind) -> EmailContent | None:
    order = get_order_view(notification.organization_id, notification.reference_id)
    if order is None:
        return None
    context = {
        "name": notification.recipient_name,
        "order": order,
        "total": money(order.total, order.currency),
        "payment_due": local_datetime(order.payment_due_at) if order.payment_due_at else "",
        **notification.context,
    }
    return EmailContent(
        ORDER_SUBJECTS[kind].format(reference=order.reference), _render(kind, context)
    )


def _stock_email(notification: Notification) -> EmailContent | None:
    item = get_stock_item_view(notification.organization_id, notification.reference_id)
    if item is None:
        return None
    subject = f"Estoque baixo: {item.sku} em {item.warehouse_code}"
    context = {"name": notification.recipient_name, "item": item}
    return EmailContent(subject, _render(NotificationKind.STOCK_LOW, context))


def _security_email(notification: Notification, kind: NotificationKind) -> EmailContent | None:
    link = password_setup_link(notification.reference_id)
    if link is None:  # conta desativada (ou removida) antes do envio
        return None
    subject = (
        f"Convite para o OrderFlow — {link.organization_name}"
        if kind == NotificationKind.USER_INVITATION
        else "Redefinição de senha do OrderFlow"
    )
    return EmailContent(subject, _render(kind, {"link": link}))


def build_email(notification: Notification) -> EmailContent | None:
    """`None` = não há mais o que enviar (referência sumiu ou conta desativada)."""
    kind = NotificationKind(notification.kind)
    if kind in ORDER_SUBJECTS:
        return _order_email(notification, kind)
    if kind == NotificationKind.STOCK_LOW:
        return _stock_email(notification)
    return _security_email(notification, kind)
