"""Dinheiro: `Decimal` com 2 casas e `ROUND_HALF_UP`, quantizado em um único lugar.

`float` é recusado na construção — um `0.1 + 0.2` não pode virar preço (CLAUDE.md, regra 4).
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
DEFAULT_CURRENCY = "BRL"


def quantize(value: Decimal | int | str) -> Decimal:
    if isinstance(value, float):
        raise TypeError("Use Decimal (ou str) para valores monetários, nunca float.")
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = DEFAULT_CURRENCY

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", quantize(self.amount))

    @classmethod
    def zero(cls, currency: str = DEFAULT_CURRENCY) -> "Money":
        return cls(Decimal(0), currency)

    def _check(self, other: "Money") -> None:
        if other.currency != self.currency:
            raise ValueError(f"Moedas diferentes: {self.currency} e {other.currency}.")

    def __add__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.amount - other.amount, self.currency)

    def times(self, quantity: int) -> "Money":
        return Money(self.amount * quantity, self.currency)

    def __lt__(self, other: "Money") -> bool:
        self._check(other)
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        self._check(other)
        return self.amount <= other.amount

    def __str__(self) -> str:
        return str(self.amount)
