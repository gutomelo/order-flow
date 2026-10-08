"""Regras de saldo de estoque — puras, sem ORM (docs/domain/inventory.md).

on_hand    unidades fisicamente no depósito
reserved   unidades comprometidas com pedidos ainda não enviados
available  on_hand - reserved
"""

from dataclasses import dataclass

from apps.inventory.domain.exceptions import (
    InsufficientStock,
    InvalidAdjustment,
    InvalidStockBalance,
    StockChangedSinceCount,
)


@dataclass(frozen=True)
class StockBalance:
    on_hand: int
    reserved: int

    @property
    def available(self) -> int:
        return self.on_hand - self.reserved

    def apply(self, *, on_hand_delta: int, reserved_delta: int) -> "StockBalance":
        """Novo saldo após um movimento; garante I1-I3.

        I1: on_hand >= 0; I2: reserved >= 0; I3: reserved <= on_hand.
        """
        result = StockBalance(self.on_hand + on_hand_delta, self.reserved + reserved_delta)
        if result.on_hand < 0 or result.reserved < 0 or result.reserved > result.on_hand:
            raise InvalidStockBalance(
                details={"on_hand": result.on_hand, "reserved": result.reserved}
            )
        return result


def ensure_positive_quantity(quantity: int) -> None:
    if quantity <= 0:  # I5
        raise ValueError("quantity must be positive")


def withdrawal_delta(balance: StockBalance, quantity: int) -> int:
    """Delta de `on_hand` para retirar `quantity` sem tocar no que está reservado."""
    ensure_positive_quantity(quantity)
    if balance.available < quantity:
        raise InsufficientStock(details={"requested": quantity, "available": balance.available})
    return -quantity


def adjustment_delta(balance: StockBalance, *, counted: int, expected_on_hand: int) -> int:
    """Delta de `on_hand` para um ajuste por contagem física (regras A2-A4).

    `expected_on_hand` é o saldo que a pessoa via ao contar: se mudou, alguém movimentou o item
    durante a contagem e o ajuste sobrescreveria esse movimento (controle otimista).
    """
    if expected_on_hand != balance.on_hand:
        raise StockChangedSinceCount(
            details={"expected_on_hand": expected_on_hand, "current_on_hand": balance.on_hand}
        )
    if counted < balance.reserved:
        raise InvalidAdjustment(details={"counted": counted, "reserved": balance.reserved})
    return counted - balance.on_hand


def crossed_reorder_point(available_before: int, available_after: int, reorder_point: int) -> bool:
    """Estoque baixo só no momento em que o disponível **cruza** o ponto de reposição para baixo:
    um aviso por queda, não um a cada movimento enquanto continua baixo. `reorder_point = 0`
    desliga o alerta."""
    return reorder_point > 0 and available_before > reorder_point >= available_after
