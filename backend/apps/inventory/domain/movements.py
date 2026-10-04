from enum import StrEnum


class MovementType(StrEnum):
    """Tipos de movimentação (docs/domain/inventory.md, tabela de movimentações)."""

    PURCHASE = "PURCHASE"
    RESERVATION = "RESERVATION"
    RELEASE = "RELEASE"
    SALE = "SALE"
    ADJUSTMENT = "ADJUSTMENT"
    RETURN = "RETURN"
    TRANSFER = "TRANSFER"
