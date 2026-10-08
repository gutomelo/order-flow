"""Quais mudanças de pedido viram e-mail ao cliente (docs/domain/notifications.md)."""

from apps.notifications.domain.kinds import NotificationKind

PAID_STATUSES = frozenset({"PAID", "PROCESSING", "READY_TO_SHIP"})


def order_notification_kind(from_status: str | None, to_status: str) -> NotificationKind | None:
    """`None` = transição interna, sem aviso ao cliente.

    - Confirmado = estoque reservado e pagamento liberado (`→ AWAITING_PAYMENT`). Pedido parado em
      `PENDING` por falta de estoque não avisa até reservar.
    - Rascunho descartado nunca chegou ao cliente: cancelar a partir de `DRAFT` não avisa.
    - Separação (`PROCESSING`, `READY_TO_SHIP`) é operação interna.
    """
    if to_status == "AWAITING_PAYMENT":
        return NotificationKind.ORDER_CONFIRMED
    if to_status == "CANCELLED":
        return None if from_status == "DRAFT" else NotificationKind.ORDER_CANCELLED
    return {
        "PAID": NotificationKind.ORDER_PAID,
        "SHIPPED": NotificationKind.ORDER_SHIPPED,
        "DELIVERED": NotificationKind.ORDER_DELIVERED,
        "REFUNDED": NotificationKind.ORDER_REFUNDED,
    }.get(to_status)


def mask_email(email: str) -> str:
    """Para telas e histórico: `ma***@empresa.com` (minimização, LGPD)."""
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    return f"{local[:2]}***@{domain}"
