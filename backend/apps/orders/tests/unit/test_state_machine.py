import pytest

from apps.orders.domain.exceptions import InvalidOrderTransition
from apps.orders.domain.state_machine import TRANSITIONS, assert_transition, can_transition
from apps.orders.domain.status import OrderStatus as S

pytestmark = pytest.mark.unit

# Tabela de docs/domain/orders.md#transições-permitidas, escrita de novo aqui de propósito:
# mudar a máquina sem mudar o documento (ou o contrário) quebra este teste.
DOCUMENTED = {
    (None, S.DRAFT), (None, S.PENDING),
    (S.DRAFT, S.PENDING), (S.DRAFT, S.CANCELLED),
    (S.PENDING, S.AWAITING_PAYMENT), (S.PENDING, S.CANCELLED),
    (S.AWAITING_PAYMENT, S.PAID), (S.AWAITING_PAYMENT, S.PENDING),
    (S.AWAITING_PAYMENT, S.CANCELLED),
    (S.PAID, S.PROCESSING), (S.PAID, S.CANCELLED),
    (S.PROCESSING, S.READY_TO_SHIP), (S.PROCESSING, S.CANCELLED),
    (S.READY_TO_SHIP, S.SHIPPED), (S.READY_TO_SHIP, S.CANCELLED),
    (S.SHIPPED, S.DELIVERED),
    (S.DELIVERED, S.REFUNDED),
    (S.CANCELLED, S.REFUNDED),
}  # fmt: skip


def test_machine_matches_the_documented_table() -> None:
    actual = {(src, dst) for src, targets in TRANSITIONS.items() for dst in targets}

    assert actual == DOCUMENTED


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (S.DELIVERED, S.PENDING),
        (S.SHIPPED, S.CANCELLED),  # após o envio, só devolução
        (S.CANCELLED, S.PAID),
        (S.REFUNDED, S.PENDING),
        (S.DRAFT, S.PAID),
        (S.PENDING, S.DRAFT),
    ],
)
def test_forbidden_transitions_raise(source: S, target: S) -> None:
    assert not can_transition(source, target)
    with pytest.raises(InvalidOrderTransition) as exc:
        assert_transition(source, target)
    assert exc.value.details == {"from": source.value, "to": target.value}


def test_refunded_is_terminal() -> None:
    assert TRANSITIONS[S.REFUNDED] == frozenset()
