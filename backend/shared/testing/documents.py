import random
import string

# Pesos do módulo 11 do CNPJ (mesmo cálculo de shared/domain/documents.py).
_FIRST = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_SECOND = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


def _digit(base: str, weights: tuple[int, ...]) -> str:
    remainder = sum((ord(c) - 48) * w for c, w in zip(base, weights, strict=True)) % 11
    return "0" if remainder < 2 else str(11 - remainder)


def generate_cnpj(alphanumeric: bool = False) -> str:
    """CNPJ válido aleatório (numérico ou alfanumérico) para testes."""
    alphabet = string.digits + (string.ascii_uppercase if alphanumeric else "")
    base = "".join(random.choices(alphabet, k=12))  # noqa: S311 (dado de teste)
    first = _digit(base, _FIRST)
    return base + first + _digit(base + first, _SECOND)
