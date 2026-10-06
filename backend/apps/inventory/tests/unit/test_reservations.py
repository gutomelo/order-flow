from uuid import uuid4

import pytest

from apps.inventory.domain.exceptions import InsufficientStock, ReservationNotActive
from apps.inventory.domain.reservations import (
    ReservationRequest,
    ReservationStatus,
    assert_reservation_transition,
    ensure_all_available,
)

pytestmark = pytest.mark.unit
S = ReservationStatus


def test_all_lines_fit_or_every_shortage_is_reported() -> None:
    ok, short_a, short_b = uuid4(), uuid4(), uuid4()

    ensure_all_available([ReservationRequest(ok, 5, 5)])
    with pytest.raises(InsufficientStock) as exc:
        ensure_all_available(
            [
                ReservationRequest(ok, 1, 10),
                ReservationRequest(short_a, 3, 2),
                ReservationRequest(short_b, 1, -1),  # nunca expõe disponível negativo
            ]
        )

    assert exc.value.details == {
        "lines": [
            {"product_id": str(short_a), "requested": 3, "available": 2},
            {"product_id": str(short_b), "requested": 1, "available": 0},
        ]
    }


@pytest.mark.parametrize(
    ("source", "target"),
    [(S.ACTIVE, S.CONFIRMED), (S.ACTIVE, S.RELEASED), (S.ACTIVE, S.EXPIRED),
     (S.CONFIRMED, S.CONSUMED), (S.CONFIRMED, S.RELEASED)],
)  # fmt: skip
def test_allowed_transitions(source: S, target: S) -> None:
    assert_reservation_transition(source, target)


@pytest.mark.parametrize(
    ("source", "target"),
    [(S.CONFIRMED, S.EXPIRED), (S.RELEASED, S.ACTIVE), (S.EXPIRED, S.RELEASED),
     (S.CONSUMED, S.RELEASED)],
)  # fmt: skip
def test_terminal_and_confirmed_reservations_cannot_expire_or_reopen(source: S, target: S) -> None:
    with pytest.raises(ReservationNotActive):
        assert_reservation_transition(source, target)
