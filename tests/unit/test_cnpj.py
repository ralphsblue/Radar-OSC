import pytest

from validador_osc.cnpj import (
    Motivo,
    ResultadoDV,
    calcular_dvs,
    cnpj_da_matriz,
    normalizar,
    validar,
)


@pytest.mark.parametrize(
    ("entrada", "normalizado"),
    [
        ("19.131.243/0001-97", "19131243000197"),
        ("00.000.000/0001-91", "00000000000191"),
        ("12.ABC.345/01DE-35", "12ABC34501DE35"),
    ],
)
def test_cnpjs_validos_da_especificacao(entrada: str, normalizado: str) -> None:
    assert validar(entrada) == ResultadoDV(normalizado, True)


def test_dv_divergente_informa_dv_esperado() -> None:
    assert validar("19.131.243/0001-98") == ResultadoDV("19131243000198", False, Motivo.DV, "97")


def test_dv_divergente_alfanumerico() -> None:
    resultado = validar("12.ABC.345/01DE-36")
    assert (resultado.motivo, resultado.dv_esperado) == (Motivo.DV, "35")


@pytest.mark.parametrize(
    "entrada",
    [
        "11111111111111",
        "00000000000000",
        "11111111111180",
        "AAAAAAAAAAAA00",
    ],
)
def test_sequencia_repetida(entrada: str) -> None:
    assert validar(entrada) == ResultadoDV(entrada, False, Motivo.REPETIDO)


@pytest.mark.parametrize(
    "entrada",
    [
        "12ABC34501DE3",
        "",
        "191312430001970",
        "12ABC34501DEA5",
        "19131243#000197",
        "12\u0131BC34501DE35",
        "12ABC34501DE\u0663\u0665",
    ],
)
def test_formato_invalido(entrada: str) -> None:
    resultado = validar(entrada)
    assert (resultado.valido, resultado.motivo, resultado.dv_esperado) == (False, Motivo.FORMATO, None)


@pytest.mark.parametrize("entrada", ["12.abc.345/01de-35", "12abc34501de35", "12.aBc.345/01dE-35"])
def test_minusculas_aceitas(entrada: str) -> None:
    assert validar(entrada) == ResultadoDV("12ABC34501DE35", True)


@pytest.mark.parametrize(
    "entrada",
    [
        "19131243000197",
        "19.131.243.0001-97",
        "19 131 243 0001 97",
        "  19.131.243/0001-97\n",
        "19-131-243/0001/97",
        "19.131.243/0001\u201397",
    ],
)
def test_pontuacao_variada(entrada: str) -> None:
    assert validar(entrada) == ResultadoDV("19131243000197", True)


def test_normalizar() -> None:
    assert normalizar(" 12.abc.345/01de-35 ") == "12ABC34501DE35"


@pytest.mark.parametrize(
    ("base", "dvs"),
    [
        ("191312430001", "97"),
        ("000000000001", "91"),
        ("12ABC34501DE", "35"),
        ("12.abc.345/01de", "35"),
    ],
)
def test_calcular_dvs(base: str, dvs: str) -> None:
    assert calcular_dvs(base) == dvs


@pytest.mark.parametrize("base", ["19131243000", "1913124300011", "12ABC34501D!"])
def test_calcular_dvs_rejeita_base_invalida(base: str) -> None:
    with pytest.raises(ValueError, match="12 caracteres"):
        calcular_dvs(base)


def test_montar_matriz_a_partir_da_raiz() -> None:
    base = "19131243" + "0001"
    assert base + calcular_dvs(base) == "19131243000197"


def test_cnpj_da_matriz_a_partir_de_filial() -> None:
    filial = "19131243" + "0002"
    filial += calcular_dvs(filial)
    assert validar(filial).valido
    assert cnpj_da_matriz(filial) == "19131243000197"
    assert validar(cnpj_da_matriz(filial)).valido


def test_cnpj_da_matriz_alfanumerico() -> None:
    matriz = cnpj_da_matriz("12.ABC.345/01DE-35")
    assert matriz.startswith("12ABC3450001")
    assert validar(matriz).valido
