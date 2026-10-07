"""Reserva e liberação de estoque para pedidos (ADR-008, docs/domain/inventory.md).

Chamados por `orders` dentro da transação dele. Ordem global de locks:
pedido (orders) → depósito (FOR SHARE) → itens de estoque (por id) → reservas.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

import structlog
from django.conf import settings
from django.db import OperationalError, transaction
from django.utils import timezone

from apps.inventory.application.ledger import (
    lock_stock_items,
    lock_warehouses_for_movement,
    post_movement,
)
from apps.inventory.domain.exceptions import ReservationNotConfirmed, StockBusy
from apps.inventory.domain.movements import MovementType
from apps.inventory.domain.reservations import (
    HOLDING,
    ReservationRequest,
    ReservationStatus,
    assert_reservation_transition,
    ensure_all_available,
)
from apps.inventory.domain.stock import ensure_positive_quantity
from apps.inventory.models import StockReservation
from shared.infrastructure.db import is_lock_timeout, set_local_lock_timeout

logger = structlog.get_logger(__name__)

REFERENCE_TYPE = "ORDER"


@dataclass(frozen=True)
class ReservationLine:
    order_line_id: UUID
    product_id: UUID
    quantity: int


@dataclass(frozen=True)
class ReserveStockCommand:
    organization_id: UUID
    actor_id: UUID | None
    warehouse_id: UUID
    order_id: UUID
    lines: tuple[ReservationLine, ...]
    expires_at: datetime


def reserve_stock(command: ReserveStockCommand) -> list[StockReservation]:
    """Reserva **todas** as linhas ou nenhuma (`INSUFFICIENT_STOCK` lista cada falta)."""
    for line in command.lines:
        ensure_positive_quantity(line.quantity)
    try:
        with transaction.atomic():
            set_local_lock_timeout(settings.STOCK_LOCK_TIMEOUT_MS)
            return _reserve(command)
    except OperationalError as exc:
        if is_lock_timeout(exc):  # disputa longa por um item: falha rápida e re-tentável
            raise StockBusy() from exc
        raise


def _reserve(command: ReserveStockCommand) -> list[StockReservation]:
    organization_id = command.organization_id
    lock_warehouses_for_movement(organization_id, [command.warehouse_id])  # W2
    items = {
        item.product_id: item
        for item in lock_stock_items(
            organization_id,
            warehouse_id=command.warehouse_id,
            product_id__in=[line.product_id for line in command.lines],
        )
    }
    # Disponibilidade verificada DEPOIS do lock (ADR-008, regra 4). Sem item = nada em estoque.
    ensure_all_available(
        [
            ReservationRequest(
                line.product_id,
                line.quantity,
                items[line.product_id].available if line.product_id in items else 0,
            )
            for line in command.lines
        ]
    )
    reservations = []
    for line in command.lines:
        item = items[line.product_id]
        post_movement(
            item,
            MovementType.RESERVATION,
            on_hand_delta=0,
            reserved_delta=line.quantity,
            actor_id=command.actor_id,
            reference_type=REFERENCE_TYPE,
            reference_id=command.order_id,
        )
        reservations.append(
            StockReservation.objects.create(
                organization_id=organization_id,
                stock_item=item,
                order_id=command.order_id,
                order_line_id=line.order_line_id,
                quantity=line.quantity,
                status=ReservationStatus.ACTIVE,
                expires_at=command.expires_at,
            )
        )
    logger.info("inventory.stock.reserved", order_id=str(command.order_id), lines=len(reservations))
    return reservations


ReleaseReason = Literal[ReservationStatus.RELEASED, ReservationStatus.EXPIRED]


def release_reservations(
    organization_id: UUID, actor_id: UUID | None, order_id: UUID, *, reason: ReleaseReason
) -> int:
    """Devolve ao disponível tudo o que o pedido segura. Sem reservas ativas: nada a fazer."""
    with transaction.atomic():
        holding = StockReservation.objects.for_organization(organization_id).filter(
            order_id=order_id, status__in=HOLDING
        )
        item_ids = set(holding.values_list("stock_item_id", flat=True))
        if not item_ids:
            return 0
        items = {item.id: item for item in lock_stock_items(organization_id, id__in=item_ids)}
        # Relê com lock: outra transação pode ter encerrado alguma reserva nesse meio-tempo.
        reservations = list(holding.select_for_update().order_by("id"))
        now = timezone.now()
        for reservation in reservations:
            assert_reservation_transition(ReservationStatus(reservation.status), reason)
            post_movement(
                items[reservation.stock_item_id],
                MovementType.RELEASE,
                on_hand_delta=0,
                reserved_delta=-reservation.quantity,
                actor_id=actor_id,
                reference_type=REFERENCE_TYPE,
                reference_id=order_id,
                reason="Reserva expirada" if reason == ReservationStatus.EXPIRED else "",
            )
            reservation.status = reason
            reservation.closed_at = now
            reservation.save(update_fields=["status", "closed_at", "updated_at"])
    logger.info(
        "inventory.stock.released",
        order_id=str(order_id),
        reason=reason.value,
        lines=len(reservations),
    )
    return len(reservations)


def confirm_reservations(organization_id: UUID, order_id: UUID) -> int:
    """Pagamento aprovado: ACTIVE → CONFIRMED (não expira mais). Saldo não muda — a unidade
    continua reservada até o envio (`consume_reservations`)."""
    with transaction.atomic():
        reservations = list(
            StockReservation.objects.for_organization(organization_id)
            .select_for_update()
            .filter(order_id=order_id, status=ReservationStatus.ACTIVE)
            .order_by("id")
        )
        for reservation in reservations:
            assert_reservation_transition(ReservationStatus.ACTIVE, ReservationStatus.CONFIRMED)
            reservation.status = ReservationStatus.CONFIRMED
            reservation.save(update_fields=["status", "updated_at"])
    logger.info("inventory.stock.confirmed", order_id=str(order_id), lines=len(reservations))
    return len(reservations)


def consume_reservations(organization_id: UUID, actor_id: UUID | None, order_id: UUID) -> int:
    """Envio do pedido: CONFIRMED → CONSUMED com movimento `SALE` (`on_hand` e `reserved` menos q).

    A unidade sai do depósito e deixa de estar reservada no mesmo movimento: `available` não muda
    (já não estava disponível desde a reserva). Ordem de locks: itens (por id) → reservas.
    """
    with transaction.atomic():
        confirmed = StockReservation.objects.for_organization(organization_id).filter(
            order_id=order_id, status=ReservationStatus.CONFIRMED
        )
        item_ids = set(confirmed.values_list("stock_item_id", flat=True))
        if not item_ids:
            raise ReservationNotConfirmed(details={"order_id": str(order_id)})
        items = {item.id: item for item in lock_stock_items(organization_id, id__in=item_ids)}
        reservations = list(confirmed.select_for_update().order_by("id"))
        now = timezone.now()
        for reservation in reservations:
            assert_reservation_transition(ReservationStatus.CONFIRMED, ReservationStatus.CONSUMED)
            post_movement(
                items[reservation.stock_item_id],
                MovementType.SALE,
                on_hand_delta=-reservation.quantity,
                reserved_delta=-reservation.quantity,
                actor_id=actor_id,
                reference_type=REFERENCE_TYPE,
                reference_id=order_id,
            )
            reservation.status = ReservationStatus.CONSUMED
            reservation.closed_at = now
            reservation.save(update_fields=["status", "closed_at", "updated_at"])
    logger.info("inventory.stock.consumed", order_id=str(order_id), lines=len(reservations))
    return len(reservations)
