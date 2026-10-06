"""Políticas de autorização que dependem do estado do pedido (security.md: autorização central).

A view não decide "quem pode" com `if` de papel: pergunta aqui qual permissão o estado exige.
"""

from apps.orders.domain.state_machine import CANCEL_REQUIRES_REFUND
from apps.orders.domain.status import OrderStatus


def permission_to_cancel(status: OrderStatus) -> str:
    """Cancelar pedido pago devolve dinheiro: exige `orders:cancel_paid` (matriz RBAC)."""
    return "orders:cancel_paid" if status in CANCEL_REQUIRES_REFUND else "orders:cancel"
