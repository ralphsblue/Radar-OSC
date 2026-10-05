from dataclasses import replace
from datetime import UTC, date, datetime
from typing import Any

import pytest
from pydantic import SecretStr

from validador_osc.api.privacidade import eh_operador, ocultar_dirigentes
from validador_osc.dominio.bases import CargaAtiva, ConsultaLocal
from validador_osc.dominio.resultado import Contexto, Estado
from validador_osc.dominio.sancoes import (
    CadastroSancao,
    ListaTcu,
    RegistroListaTcu,
    RegistroTcesp,
    Sancao,
    TipoPessoa,
)
from validador_osc.dominio.tipos import Dirigente
from validador_osc.pessoa_fisica import calcular_dvs
from validador_osc.regras.parametros import carregar_limites
from validador_osc.regras.verificacoes.dirigentes import (
    ConsultaDirigente,
    ObservacoesDirigentes,
    verificar_dirigentes,
)

REF = date(2026, 10, 1)
CONTEXTO = Contexto(REF)
LIMITES = carregar_limites()
MEIO = "123456"
PRESIDENTE = Dirigente("MARIA DA SILVA", "Presidente", date(2020, 1, 1), f"***{MEIO}**", True)


def carga(fonte: str, data_base: date = REF) -> CargaAtiva:
    return CargaAtiva(1, fonte, data_base, datetime(2026, 10, 1, tzinfo=UTC), "a" * 64)


def vazias(**alteracoes: Any) -> ConsultaDirigente:
    base = ConsultaDirigente(
        PRESIDENTE,
        ceis=ConsultaLocal(carga("cgu_ceis"), ()),
        cnep=ConsultaLocal(carga("cgu_cnep"), ()),
        contas_irregulares=ConsultaLocal(carga("tcu_contas_irregulares"), ()),
        inabilitados=ConsultaLocal(carga("tcu_inabilitados"), ()),
        tcesp=ConsultaLocal(carga("tcesp_terceiro_setor"), ()),
    )
    return replace(base, **alteracoes)


def sancao(**alteracoes: Any) -> Sancao:
    base = Sancao(
        CadastroSancao.CEIS,
        TipoPessoa.FISICA,
        None,
        None,
        "MARIA DA SILVA",
        "Proibição de contratar com o Poder Público",
        date(2024, 1, 1),
        date(2030, 1, 1),
        "CNJ",
        None,
        None,
        None,
        None,
        "1",
        None,
        None,
        None,
    )
    return replace(base, **alteracoes)


def lista(lista_tcu: ListaTcu, **alteracoes: Any) -> RegistroListaTcu:
    base = RegistroListaTcu(lista_tcu, None, None, "MARIA DA SILVA", "024.778/2024-9", None, None, None, None)
    return replace(base, **alteracoes)


def avaliar(*consultas: ConsultaDirigente) -> tuple[Estado, str]:
    resultado = verificar_dirigentes(ObservacoesDirigentes(consultas), CONTEXTO, LIMITES)
    return resultado.estado, resultado.mensagem


def test_sem_achado_e_ok_com_limites_explicitados() -> None:
    estado, mensagem = avaliar(vazias())
    assert estado is Estado.OK
    assert "costuma listar só o presidente" in mensagem


def test_ceis_vigente_e_alerta_e_nunca_restricao() -> None:
    estado, _ = avaliar(vazias(ceis=ConsultaLocal(carga("cgu_ceis"), (sancao(),))))
    assert estado is Estado.ALERTA


@pytest.mark.parametrize(
    "alteracoes",
    [{"data_fim": date(2020, 1, 1)}, {"categoria": "Demissão"}, {"categoria": "Suspensão"}],
)
def test_ceis_expirado_ou_fora_do_art39_e_historico(alteracoes: dict[str, Any]) -> None:
    estado, mensagem = avaliar(vazias(ceis=ConsultaLocal(carga("cgu_ceis"), (sancao(**alteracoes),))))
    assert estado is Estado.OK
    assert "histórico" in mensagem


@pytest.mark.parametrize(
    ("transito", "estado"), [(date(2019, 1, 1), Estado.ALERTA), (date(2017, 1, 1), Estado.OK)]
)
def test_contas_irregulares_na_janela_de_8_anos(transito: date, estado: Estado) -> None:
    registros = (lista(ListaTcu.CONTAS_IRREGULARES, data_transito=transito),)
    obtido, _ = avaliar(vazias(contas_irregulares=ConsultaLocal(carga("tcu_contas_irregulares"), registros)))
    assert obtido is estado


def test_inabilitado_vigente_e_alerta() -> None:
    registros = (lista(ListaTcu.INABILITADOS, data_final=date(2027, 1, 1)),)
    estado, _ = avaliar(vazias(inabilitados=ConsultaLocal(carga("tcu_inabilitados"), registros)))
    assert estado is Estado.ALERTA


@pytest.mark.parametrize(("dv_confere", "estado"), [(True, Estado.ALERTA), (False, Estado.OK)])
def test_tcesp_exige_dv_com_cpf_complementar(dv_confere: bool, estado: Estado) -> None:
    inicio = "987"
    fim = calcular_dvs(inicio + MEIO)
    if not dv_confere:
        fim = f"{(int(fim) + 1) % 100:02d}"
    registro = RegistroTcesp(
        "MARIA DA SILVA", inicio, fim, "TC-1", "Repasse", "Prefeitura", date(2022, 1, 1), "2020"
    )
    obtido, _ = avaliar(vazias(tcesp=ConsultaLocal(carga("tcesp_terceiro_setor"), (registro,))))
    assert obtido is estado


def test_base_vencida_e_listada_como_nao_verificada() -> None:
    vencida = ConsultaLocal(carga("cgu_ceis", date(2026, 9, 1)), (sancao(),))
    estado, mensagem = avaliar(vazias(ceis=vencida))
    assert estado is Estado.OK
    assert "Não verificado em: CEIS" in mensagem


def test_nenhuma_base_disponivel_e_indisponivel() -> None:
    estado, _ = avaliar(ConsultaDirigente(PRESIDENTE))
    assert estado is Estado.INDISPONIVEL


def test_qsa_sem_pessoa_fisica_e_ok() -> None:
    pj = Dirigente("EMPRESA X", "Sócio", None, "12345678000190", False)
    estado, _ = avaliar(vazias(dirigente=pj))
    assert estado is Estado.OK


def test_publico_nao_ve_nomes_de_dirigentes() -> None:
    documento: dict[str, Any] = {
        "verificacoes": [
            {
                "id": "dirigentes",
                "achados": [{"tipo": "dirigente", "nome": "MARIA", "qualificacao": "Presidente"}],
            }
        ]
    }
    publico = ocultar_dirigentes(documento)
    achado = publico["verificacoes"][0]["achados"][0]
    assert "nome" not in achado
    assert achado["dirigente"] == "Dirigente 1"
    assert documento["verificacoes"][0]["achados"][0]["nome"] == "MARIA"


@pytest.mark.parametrize(
    ("informado", "configurado", "esperado"),
    [
        ("abc", SecretStr("abc"), True),
        ("x", SecretStr("abc"), False),
        (None, SecretStr("abc"), False),
        ("abc", None, False),
    ],
)
def test_token_de_operador(informado: str | None, configurado: SecretStr | None, esperado: bool) -> None:
    assert eh_operador(informado, configurado) is esperado
