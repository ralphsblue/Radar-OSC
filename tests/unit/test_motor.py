from datetime import date

import pytest

from validador_osc.dominio.resultado import Contexto, Estado, StatusFinal
from validador_osc.regras.catalogo import CATALOGO
from validador_osc.regras.motor import DadosConsulta, avaliar

CONTEXTO = Contexto(data_referencia=date(2026, 10, 1))


@pytest.mark.parametrize(
    ("cnpj", "mensagem"),
    [
        ("19.131.243/0001-98", "esperado 97"),
        ("11111111111180", "repetidos"),
        ("12ABC34501DE3", "14 caracteres"),
    ],
)
def test_cnpj_invalido_nao_avalia_mais_nada(cnpj: str, mensagem: str) -> None:
    avaliacao = avaliar(DadosConsulta(cnpj), CONTEXTO)
    assert avaliacao.status is StatusFinal.CNPJ_INVALIDO
    assert [v.id for v in avaliacao.verificacoes] == ["dv"]
    assert mensagem in avaliacao.verificacoes[0].mensagem


def test_alfanumerico_valido_e_inconclusivo() -> None:
    avaliacao = avaliar(DadosConsulta("12.ABC.345/01DE-35"), CONTEXTO)
    assert avaliacao.status is StatusFinal.INCONCLUSIVA
    assert "alfanumérico" in avaliacao.verificacoes[1].mensagem


def test_cnpj_valido_cobre_todo_o_catalogo() -> None:
    avaliacao = avaliar(DadosConsulta("19131243000197"), CONTEXTO)
    assert [v.id for v in avaliacao.verificacoes] == [d.id for d in CATALOGO]
    assert avaliacao.verificacoes[0].estado is Estado.OK
