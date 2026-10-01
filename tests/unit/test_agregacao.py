import pytest

from validador_osc.dominio.resultado import (
    DefinicaoVerificacao,
    Estado,
    ResultadoVerificacao,
    StatusFinal,
    TipoVerificacao,
)
from validador_osc.regras.agregacao import agregar
from validador_osc.regras.catalogo import CEBAS, CEIS, CNAE, DV, MAPA_OSC, SITUACAO


def _r(definicao: DefinicaoVerificacao, estado: Estado) -> ResultadoVerificacao:
    return ResultadoVerificacao(definicao, estado, "")


def test_dv_com_restricao_gera_cnpj_invalido() -> None:
    avaliacao = agregar([_r(DV, Estado.RESTRICAO)])
    assert avaliacao.status is StatusFinal.CNPJ_INVALIDO
    assert avaliacao.motivos == ("dv",)


def test_restricao_eliminatoria_vence_indisponivel_e_alerta() -> None:
    avaliacao = agregar(
        [
            _r(DV, Estado.OK),
            _r(SITUACAO, Estado.INDISPONIVEL),
            _r(CEIS, Estado.RESTRICAO),
            _r(CNAE, Estado.ALERTA),
        ]
    )
    assert avaliacao.status is StatusFinal.INAPTA
    assert avaliacao.motivos == ("ceis",)


@pytest.mark.parametrize("estado", [Estado.INDISPONIVEL, Estado.NAO_VERIFICADO])
def test_eliminatoria_sem_resposta_gera_inconclusiva(estado: Estado) -> None:
    avaliacao = agregar([_r(DV, Estado.OK), _r(SITUACAO, estado), _r(CNAE, Estado.ALERTA)])
    assert avaliacao.status is StatusFinal.INCONCLUSIVA
    assert avaliacao.motivos == ("situacao",)


def test_alerta_gera_apta_com_ressalvas() -> None:
    avaliacao = agregar([_r(DV, Estado.OK), _r(SITUACAO, Estado.OK), _r(MAPA_OSC, Estado.ALERTA)])
    assert avaliacao.status is StatusFinal.APTA_COM_RESSALVAS
    assert avaliacao.motivos == ("mapa_osc",)


def test_tudo_ok_gera_apta() -> None:
    avaliacao = agregar([_r(DV, Estado.OK), _r(SITUACAO, Estado.OK), _r(CEBAS, Estado.OK)])
    assert avaliacao.status is StatusFinal.APTA
    assert avaliacao.motivos == ()


def test_nao_eliminatoria_indisponivel_nao_muda_status_mas_gera_aviso() -> None:
    avaliacao = agregar(
        [_r(DV, Estado.OK), _r(SITUACAO, Estado.OK), _r(MAPA_OSC, Estado.INDISPONIVEL), _r(CEBAS, Estado.OK)]
    )
    assert avaliacao.status is StatusFinal.APTA
    assert avaliacao.avisos == ("mapa_osc",)


def test_nao_eliminatoria_nunca_vira_motivo_de_inapta() -> None:
    alerta = DefinicaoVerificacao("x", 0, "x", TipoVerificacao.ALERTA)
    avaliacao = agregar([_r(DV, Estado.OK), _r(alerta, Estado.RESTRICAO)])
    assert avaliacao.status is StatusFinal.APTA
