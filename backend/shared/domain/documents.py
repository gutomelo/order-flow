"""CNPJ numérico e alfanumérico (IN RFB nº 2.229/2024, emitido a partir de julho de 2026).

As 12 primeiras posições aceitam letras maiúsculas e dígitos; os 2 dígitos verificadores são
numéricos. O módulo 11 usa o valor `ASCII - 48` de cada caractere, o que mantém os CNPJs
numéricos válidos sem regra especial.
"""

import re

_CNPJ_FORMAT = re.compile(r"[0-9A-Z]{12}[0-9]{2}")
_FIRST_WEIGHTS = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_SECOND_WEIGHTS = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


def normalize_cnpj(value: str) -> str:
    """Remove máscara (`.`, `/`, `-`, espaços) e converte para maiúsculas."""
    return re.sub(r"[.\-/\s]", "", value).upper()


def _check_digit(base: str, weights: tuple[int, ...]) -> int:
    total = sum((ord(char) - 48) * weight for char, weight in zip(base, weights, strict=True))
    remainder = total % 11
    return 0 if remainder < 2 else 11 - remainder


def is_valid_cnpj(value: str) -> bool:
    cnpj = normalize_cnpj(value)
    if not _CNPJ_FORMAT.fullmatch(cnpj) or len(set(cnpj)) == 1:
        return False
    first = _check_digit(cnpj[:12], _FIRST_WEIGHTS)
    second = _check_digit(cnpj[:12] + str(first), _SECOND_WEIGHTS)
    return cnpj[12:] == f"{first}{second}"


def format_cnpj(value: str) -> str:
    """`12ABC34501DE35` → `12.ABC.345/01DE-35`."""
    cnpj = normalize_cnpj(value)
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
