from apps.orders.models import Order


def order_reference(order: Order) -> str:
    """Número legível do pedido para outros módulos (ex.: pagamentos): `#000003`."""
    return f"#{order.number:06d}" if order.number else str(order.id)
