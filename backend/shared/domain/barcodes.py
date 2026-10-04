"""GTIN (EAN-8, UPC-A/GTIN-12, EAN-13/GTIN-13, GTIN-14) — padrão GS1."""

_GTIN_LENGTHS = {8, 12, 13, 14}


def is_valid_gtin(value: str) -> bool:
    """Valida tamanho e dígito verificador (pesos 3 e 1 alternados a partir da direita)."""
    if not value.isdigit() or len(value) not in _GTIN_LENGTHS:
        return False
    body, check = value[:-1], int(value[-1])
    total = sum(
        int(digit) * (3 if index % 2 == 0 else 1) for index, digit in enumerate(reversed(body))
    )
    return (10 - total % 10) % 10 == check
