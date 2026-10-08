from collections.abc import Sequence
from uuid import UUID

from apps.orders.domain.lines import PricedLine, compute_totals
from apps.orders.models import Order, OrderLine, OrderNumberSequence


def apply_lines(order: Order, lines: Sequence[PricedLine]) -> None:
    """Substitui as linhas e recalcula os totais (o chamador salva o pedido antes)."""
    OrderLine.objects.filter(order=order).delete()
    OrderLine.objects.bulk_create(
        OrderLine(
            organization_id=order.organization_id,
            order=order,
            position=position,
            product_id=line.product_id,
            sku=line.sku,
            product_name=line.product_name,
            quantity=line.quantity,
            unit_price=line.unit_price.amount,
            discount_amount=line.discount.amount,
            line_total=line.line_total.amount,
            price_source=line.price_source,
        )
        for position, line in enumerate(lines, start=1)
    )
    totals = compute_totals(lines)
    order.subtotal = totals.subtotal.amount
    order.discount_total = totals.discount_total.amount
    order.shipping_total = totals.shipping_total.amount
    order.total = totals.total.amount


def next_order_number(organization_id: UUID) -> int:
    """O7: número sequencial por organização, sem lacunas (ver Order Meta e orders.md)."""
    OrderNumberSequence.objects.get_or_create(organization_id=organization_id)
    sequence = OrderNumberSequence.objects.select_for_update().get(organization_id=organization_id)
    sequence.last_value += 1
    sequence.save(update_fields=["last_value"])
    return sequence.last_value
