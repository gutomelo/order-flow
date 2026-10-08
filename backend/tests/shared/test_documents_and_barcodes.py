import pytest

from shared.domain.barcodes import is_valid_gtin
from shared.domain.documents import format_cnpj, is_valid_cnpj, normalize_cnpj

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "cnpj",
    [
        "11.222.333/0001-81",  # numérico com máscara
        "11222333000181",  # numérico sem máscara
        "12.ABC.345/01DE-35",  # alfanumérico: exemplo oficial da Receita Federal
        "12abc34501de35",  # letras minúsculas são normalizadas
    ],
)
def test_accepts_valid_numeric_and_alphanumeric_cnpj(cnpj: str) -> None:
    assert is_valid_cnpj(cnpj)


@pytest.mark.parametrize(
    "cnpj",
    [
        "11.222.333/0001-82",  # dígito verificador errado
        "12.ABC.345/01DE-36",
        "11111111111111",  # todos iguais
        "1122233300018",  # 13 caracteres
        "12ABC34501DEAB",  # verificadores não numéricos
        "12ABC34501D@35",
        "",
    ],
)
def test_rejects_invalid_cnpj(cnpj: str) -> None:
    assert not is_valid_cnpj(cnpj)


def test_normalizes_and_formats_cnpj() -> None:
    assert normalize_cnpj(" 12.abc.345/01de-35 ") == "12ABC34501DE35"
    assert format_cnpj("12ABC34501DE35") == "12.ABC.345/01DE-35"


@pytest.mark.parametrize(
    "code", ["4006381333931", "73513537", "036000291452", "10012345678902", "7891000315507"]
)
def test_accepts_valid_gtin(code: str) -> None:
    assert is_valid_gtin(code)


@pytest.mark.parametrize("code", ["4006381333932", "123", "400638133393A", "123456789012345"])
def test_rejects_invalid_gtin(code: str) -> None:
    assert not is_valid_gtin(code)
