"""Separação, envio e entrega (docs/domain/orders.md#implementação-phase-9).

    PAID → PROCESSING → READY_TO_SHIP      start_picking / complete_picking (depósito)
    READY_TO_SHIP → SHIPPED                ship_order: etiqueta FORA de transação, depois
                                           baixa do estoque (SALE) + remessa + transição juntas
    SHIPPED → DELIVERED                    confirm_delivery (pessoa) ou mark_order_delivered
                                           (evento do rastreio, outbox)

Todas idempotentes por estado: repetir a ação no estado de destino devolve o pedido sem efeito.
"""

from uuid import UUID

import structlog
from django.db import transaction

from apps.inventory.application.commands.reservations import consume_reservations
from apps.orders.application.transitions import lock_order, transition
from apps.orders.domain.state_machine import assert_transition
from apps.orders.domain.status import OrderStatus
from apps.orders.format import order_reference
from apps.orders.models import Order
from apps.shipping.application import shipments
from apps.shipping.domain.provider import Destination

logger = structlog.get_logger(__name__)

PROVIDER_DELIVERY_REASON = "Entrega confirmada pela transportadora"
MANUAL_DELIVERY_REASON = "Entrega confirmada manualmente"


def _advance(organization_id: UUID, actor_id: UUID, order_id: UUID, target: OrderStatus) -> Order:
    with transaction.atomic():
        order = lock_order(organization_id, order_id)
        if order.status != target:
            transition(order, target, actor_id=actor_id)
    return order


def start_picking(organization_id: UUID, actor_id: UUID, order_id: UUID) -> Order:
    return _advance(organization_id, actor_id, order_id, OrderStatus.PROCESSING)


def complete_picking(organization_id: UUID, actor_id: UUID, order_id: UUID) -> Order:
    return _advance(organization_id, actor_id, order_id, OrderStatus.READY_TO_SHIP)


def ship_order(organization_id: UUID, actor_id: UUID, order_id: UUID) -> Order:
    order = Order.objects.for_organization(organization_id).get(id=order_id)
    if order.status == OrderStatus.SHIPPED:
        return order
    assert_transition(OrderStatus(order.status), OrderStatus.SHIPPED)  # falha cedo, sem I/O
    snapshot = order.shipping_snapshot or {}
    # Sem lock e sem transação: a transportadora pode demorar (S4). A etiqueta é idempotente
    # pelo pedido, então repetir após erro devolve a mesma.
    label = shipments.request_label(
        order_id=order.id,
        reference=order_reference(order),
        destination=Destination(
            postal_code=snapshot.get("postal_code", ""),
            city=snapshot.get("city", ""),
            state=snapshot.get("state", ""),
        ),
    )
    with transaction.atomic():
        order = lock_order(organization_id, order_id)
        if order.status == OrderStatus.SHIPPED:  # outro despacho chegou antes
            return order
        if order.status != OrderStatus.READY_TO_SHIP:
            # Cancelado enquanto a etiqueta era gerada: nada sai do estoque. A etiqueta fica sem
            # uso na transportadora (sem custo na simulada; ver shipping.md, questões em aberto).
            logger.warning("orders.shipping.label_unused", order_id=str(order.id))
        # Ordem de locks: pedido → itens de estoque → reservas → remessa.
        assert_transition(OrderStatus(order.status), OrderStatus.SHIPPED)
        consume_reservations(organization_id, actor_id, order.id)
        shipments.record_shipment(
            organization_id,
            actor_id,
            order_id=order.id,
            order_reference=order_reference(order),
            label=label,
        )
        transition(order, OrderStatus.SHIPPED, actor_id=actor_id)
    logger.info("orders.order.shipped", order_id=str(order.id))
    return order


def confirm_delivery(organization_id: UUID, actor_id: UUID, order_id: UUID, *, note: str) -> Order:
    note = note.strip()
    with transaction.atomic():
        order = lock_order(organization_id, order_id)
        if order.status == OrderStatus.DELIVERED:
            return order
        assert_transition(OrderStatus(order.status), OrderStatus.DELIVERED)
        shipments.confirm_delivery(organization_id, actor_id, order.id, note=note)
        transition(
            order,
            OrderStatus.DELIVERED,
            actor_id=actor_id,
            reason=note or MANUAL_DELIVERY_REASON,
        )
    return order


def mark_order_delivered(organization_id: UUID, order_id: UUID) -> Order:
    """`shipping.shipment.delivered`: SHIPPED → DELIVERED. Já entregue à mão: nada a fazer."""
    with transaction.atomic():
        order = lock_order(organization_id, order_id)
        if order.status == OrderStatus.SHIPPED:
            transition(order, OrderStatus.DELIVERED, actor_id=None, reason=PROVIDER_DELIVERY_REASON)
    return order
