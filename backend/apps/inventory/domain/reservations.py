"""Regras de reserva — puras, sem ORM (docs/domain/inventory.md#reservas-stockreservation)."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from apps.inventory.domain.exceptions import InsufficientStock, ReservationNotActive


class ReservationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CONFIRMED = "CONFIRMED"
    CONSUMED = "CONSUMED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


S = ReservationStatus

# Estados que ainda seguram unidades em `reserved` (I6).
HOLDING = frozenset({S.ACTIVE, S.CONFIRMED})

_TRANSITIONS: dict[ReservationStatus, frozenset[ReservationStatus]] = {
    S.ACTIVE: frozenset({S.CONFIRMED, S.RELEASED, S.EXPIRED}),
    S.CONFIRMED: frozenset({S.CONSUMED, S.RELEASED}),
    S.CONSUMED: frozenset(),
    S.RELEASED: frozenset(),
    S.EXPIRED: frozenset(),
}


def assert_reservation_transition(source: ReservationStatus, target: ReservationStatus) -> None:
    if target not in _TRANSITIONS[source]:
        raise ReservationNotActive(details={"from": source.value, "to": target.value})


@dataclass(frozen=True)
class ReservationRequest:
    product_id: UUID
    quantity: int
    available: int


def ensure_all_available(requests: Sequence[ReservationRequest]) -> None:
    """Tudo-ou-nada: se qualquer linha não cabe no disponível, nenhuma é reservada.

    O erro lista **todas** as faltas, para a tela marcar cada item de uma vez.
    """
    shortages = [
        {
            "product_id": str(r.product_id),
            "requested": r.quantity,
            "available": max(r.available, 0),
        }
        for r in requests
        if r.quantity > r.available
    ]
    if shortages:
        raise InsufficientStock(details={"lines": shortages})
