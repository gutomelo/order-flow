"""Máquina de estados do pedido como **tabela** (pattern State na forma mais simples).

O comportamento que varia por estado é só "para onde posso ir"; classes por estado não se pagariam
(docs/domain/orders.md#implementação-da-máquina-de-estados). A tabela é a fonte única: use cases
pedem a transição aqui e nunca escrevem `status` diretamente (O10).
"""

from apps.orders.domain.exceptions import InvalidOrderTransition
from apps.orders.domain.status import OrderStatus

S = OrderStatus

# `None` = pedido ainda não existe.
TRANSITIONS: dict[OrderStatus | None, frozenset[OrderStatus]] = {
    None: frozenset({S.DRAFT, S.PENDING}),
    S.DRAFT: frozenset({S.PENDING, S.CANCELLED}),
    S.PENDING: frozenset({S.AWAITING_PAYMENT, S.CANCELLED}),
    S.AWAITING_PAYMENT: frozenset({S.PAID, S.PENDING, S.CANCELLED}),
    S.PAID: frozenset({S.PROCESSING, S.CANCELLED}),
    S.PROCESSING: frozenset({S.READY_TO_SHIP, S.CANCELLED}),
    S.READY_TO_SHIP: frozenset({S.SHIPPED, S.CANCELLED}),
    S.SHIPPED: frozenset({S.DELIVERED}),
    S.DELIVERED: frozenset({S.REFUNDED}),
    S.CANCELLED: frozenset({S.REFUNDED}),
    S.REFUNDED: frozenset(),
}

# Cancelar a partir destes estados exige refund (Phase 8) e `orders:cancel_paid`.
CANCEL_REQUIRES_REFUND = frozenset({S.PAID, S.PROCESSING, S.READY_TO_SHIP})


def can_transition(source: OrderStatus | None, target: OrderStatus) -> bool:
    return target in TRANSITIONS[source]


def assert_transition(source: OrderStatus | None, target: OrderStatus) -> None:
    if not can_transition(source, target):
        raise InvalidOrderTransition(
            details={"from": source.value if source else None, "to": target.value}
        )
