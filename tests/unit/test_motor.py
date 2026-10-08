from datetime import date

import pytest

from tests.unit.fabricas import EVIDENCIA, RECEBIDA_EM, cadastro, coleta_obtida, fonte_esperada
from validador_osc.dominio.coleta import Coleta, Falha, MotivoFalha, NaoEncontrado, Obtido, RefEvidencia
from validador_osc.dominio.consulta import Contexto, Esfera
from validador_osc.dominio.resultado import (
    Avaliacao,
    Estado,
    ResultadoVerificacao,
    StatusFinal,
    TipoVerificacao,
)
from validador_osc.dominio.tipos import Cadastro, SituacaoCadastral
from validador_osc.regras.catalogo import CATALOGO
from validador_osc.regras.comum import MENSAGEM_SEM_CADASTRO
from validador_osc.regras.motor import (
    CADASTRAIS,
    MENSAGEM_ALFANUMERICO,
    MENSAGEM_SEM_FONTE,
    DadosConsulta,
    avaliar,
)
from validador_osc.regras.tabelas import carregar_tabelas, formatar_cnae

CONTEXTO = Contexto(data_referencia=date(2026, 10, 1))
TABELAS = carregar_tabelas()


@pytest.mark.parametrize(
    ("cnpj", "mensagem"),
    [
        ("19.131.243/0001-98", "esperado 97"),
        ("11111111111180", "repetidos"),
        ("12ABC34501DE3", "14 caracteres"),
    ],
)
def test_cnpj_invalido_nao_avalia_mais_nada(cnpj: str, mensagem: str) -> None:
    avaliacao = avaliar(DadosConsulta(cnpj), CONTEXTO, TABELAS)
    assert avaliacao.status is StatusFinal.CNPJ_INVALIDO
    assert [v.id for v in avaliacao.verificacoes] == ["dv"]
    assert mensagem in avaliacao.verificacoes[0].mensagem


def test_alfanumerico_valido_e_inconclusivo() -> None:
    avaliacao = avaliar(DadosConsulta("12.ABC.345/01DE-35"), CONTEXTO, TABELAS)
    assert avaliacao.status is StatusFinal.INCONCLUSIVA
    assert "alfanumérico" in avaliacao.verificacoes[1].mensagem


def test_cnpj_valido_cobre_todo_o_catalogo() -> None:
    avaliacao = avaliar(DadosConsulta("19131243000197"), CONTEXTO, TABELAS)
    assert [v.id for v in avaliacao.verificacoes] == [d.id for d in CATALOGO]
    assert avaliacao.verificacoes[0].estado is Estado.OK


IDS_CATALOGO = [d.id for d in CATALOGO]
CADASTRAIS_SEM_SITUACAO = {d.id for d in CADASTRAIS} - {"situacao"}
PENDENTES = {d.id for d in CATALOGO} - {d.id for d in CADASTRAIS} - {"dv"}
CNPJ_OKBR = "19.131.243/0001-97"


def por_id(avaliacao: Avaliacao) -> dict[str, ResultadoVerificacao]:
    return {v.id: v for v in avaliacao.verificacoes}


def test_cadastro_obtido_avalia_todas_as_cadastrais() -> None:
    avaliacao = avaliar(DadosConsulta(CNPJ_OKBR, coleta_obtida()), CONTEXTO, TABELAS)
    resultados = por_id(avaliacao)
    assert [v.id for v in avaliacao.verificacoes] == IDS_CATALOGO
    assert {i: resultados[i].estado for i in ("dv", *sorted(CADASTRAIS_SEM_SITUACAO), "situacao")} == {
        "dv": Estado.OK,
        "situacao": Estado.OK,
        "estabelecimento": Estado.OK,
        "natureza": Estado.OK,
        "cnae": Estado.OK,
        "religiosa": Estado.OK,
        "tempo": Estado.OK,
    }
    for ident in CADASTRAIS_SEM_SITUACAO | {"situacao"}:
        assert resultados[ident].fontes == (fonte_esperada(),)
    for ident in PENDENTES:
        assert resultados[ident].estado is Estado.NAO_VERIFICADO
        assert resultados[ident].mensagem == MENSAGEM_SEM_FONTE
    assert avaliacao.status is StatusFinal.INCONCLUSIVA


def test_cadastro_obtido_inativo_e_inapto() -> None:
    coleta = coleta_obtida(situacao=SituacaoCadastral.BAIXADA)
    avaliacao = avaliar(DadosConsulta(CNPJ_OKBR, coleta), CONTEXTO, TABELAS)
    assert avaliacao.status is StatusFinal.INAPTA
    assert avaliacao.motivos == ("situacao",)
    assert [v.id for v in avaliacao.verificacoes] == IDS_CATALOGO


def test_natureza_pela_descricao_dispara_alerta_religioso() -> None:
    coleta = coleta_obtida(natureza_descricao="Organização Religiosa", cnae_principal="9491000")
    resultados = por_id(avaliar(DadosConsulta(CNPJ_OKBR, coleta), CONTEXTO, TABELAS))
    assert resultados["natureza"].estado is Estado.OK
    assert resultados["religiosa"].estado is Estado.ALERTA


def test_sem_cnae_principal_deixa_cnae_indisponivel_e_religiosa_ok() -> None:
    coleta = coleta_obtida(cnae_principal=None)
    resultados = por_id(avaliar(DadosConsulta(CNPJ_OKBR, coleta), CONTEXTO, TABELAS))
    assert resultados["cnae"].estado is Estado.INDISPONIVEL
    assert resultados["religiosa"].estado is Estado.OK


def test_esfera_do_contexto_chega_ao_tempo() -> None:
    coleta = coleta_obtida(data_inicio=date(2024, 10, 2))
    contexto = Contexto(data_referencia=date(2026, 10, 1), esfera=Esfera.ESTADO)
    resultados = por_id(avaliar(DadosConsulta(CNPJ_OKBR, coleta), contexto, TABELAS))
    assert resultados["tempo"].estado is Estado.ALERTA
    assert "estados e Distrito Federal" in resultados["tempo"].mensagem


@pytest.mark.parametrize(
    ("coleta", "situacao"),
    [
        (NaoEncontrado(EVIDENCIA), "NAO_ENCONTRADO"),
        (Falha(MotivoFalha.TIMEOUT, "ReadTimeout"), "FONTE_INDISPONIVEL"),
        (Falha(MotivoFalha.HTTP_5XX, "HTTP 503", EVIDENCIA), "FONTE_INDISPONIVEL"),
    ],
)
def test_cadastro_ausente_deixa_cadastrais_nao_verificadas(
    coleta: NaoEncontrado | Falha, situacao: str
) -> None:
    avaliacao = avaliar(DadosConsulta(CNPJ_OKBR, coleta), CONTEXTO, TABELAS)
    resultados = por_id(avaliacao)
    assert [v.id for v in avaliacao.verificacoes] == IDS_CATALOGO
    assert avaliacao.status is StatusFinal.INCONCLUSIVA
    assert resultados["situacao"].estado is Estado.INDISPONIVEL
    assert resultados["situacao"].situacao == situacao
    for ident in CADASTRAIS_SEM_SITUACAO:
        assert resultados[ident].estado is Estado.NAO_VERIFICADO
        assert resultados[ident].mensagem == MENSAGEM_SEM_CADASTRO
    for ident in PENDENTES:
        assert resultados[ident].mensagem == MENSAGEM_SEM_FONTE
    assert "situacao" in avaliacao.motivos


@pytest.mark.parametrize("coleta", [None, coleta_obtida(), NaoEncontrado(None)])
def test_alfanumerico_ignora_o_cadastro(coleta: Coleta[Cadastro] | None) -> None:
    avaliacao = avaliar(DadosConsulta("12ABC34501DE35", coleta), CONTEXTO, TABELAS)
    assert avaliacao.status is StatusFinal.INCONCLUSIVA
    assert [v.id for v in avaliacao.verificacoes] == IDS_CATALOGO
    assert avaliacao.verificacoes[0].estado is Estado.OK
    for resultado in avaliacao.verificacoes[1:]:
        assert resultado.estado is Estado.NAO_VERIFICADO
        assert resultado.mensagem == MENSAGEM_ALFANUMERICO


def test_sem_coleta_cadastral_tudo_fica_sem_fonte() -> None:
    avaliacao = avaliar(DadosConsulta(CNPJ_OKBR), CONTEXTO, TABELAS)
    assert {v.mensagem for v in avaliacao.verificacoes[1:]} == {MENSAGEM_SEM_FONTE}


@pytest.mark.parametrize(
    "alteracoes",
    [
        {},
        {"cnae_principal": "4711302"},
        {"natureza_descricao": "Organização Religiosa", "cnae_principal": "9491000"},
        {"natureza_descricao": "Sociedade Empresária Limitada"},
        {"natureza_descricao": "Desconhecida"},
        {"data_inicio": date(2026, 9, 1), "matriz": False},
        {"data_inicio": None, "cnae_principal": None},
        {"situacao": SituacaoCadastral.SUSPENSA, "data_base": date(2020, 1, 1)},
    ],
)
@pytest.mark.parametrize("esfera", [None, *Esfera])
def test_nao_eliminatoria_nunca_devolve_restricao(
    alteracoes: dict[str, object], esfera: Esfera | None
) -> None:
    contexto = Contexto(data_referencia=date(2026, 10, 1), esfera=esfera)
    avaliacao = avaliar(DadosConsulta(CNPJ_OKBR, coleta_obtida(**alteracoes)), contexto, TABELAS)
    for resultado in avaliacao.verificacoes:
        if resultado.tipo is not TipoVerificacao.ELIMINATORIA:
            assert resultado.estado is not Estado.RESTRICAO, resultado.id


CNPJ_FILIAL = "62779145000270"
CNPJ_MATRIZ = "62779145000190"
EVIDENCIA_MATRIZ = RefEvidencia(id=8, fonte="opencnpj", sha256="cd" * 32, recebida_em=RECEBIDA_EM)


def _filial(**alteracoes: object) -> Obtido[Cadastro]:
    return coleta_obtida(**{"cnpj": CNPJ_FILIAL, "matriz": False, **alteracoes})


def _matriz(**alteracoes: object) -> Obtido[Cadastro]:
    return Obtido(cadastro(**{"cnpj": CNPJ_MATRIZ, "matriz": True, **alteracoes}), EVIDENCIA_MATRIZ)


def test_filial_usa_natureza_e_tempo_da_matriz() -> None:
    consultado = _filial(natureza_descricao="Sociedade Empresária Limitada", data_inicio=date(2026, 9, 1))
    matriz = _matriz(natureza_descricao="Associação Privada", data_inicio=date(1970, 4, 27))

    resultados = por_id(avaliar(DadosConsulta(CNPJ_FILIAL, consultado, matriz), CONTEXTO, TABELAS))

    assert resultados["natureza"].estado is Estado.OK
    assert [f.evidencia_id for f in resultados["natureza"].fontes] == [8]
    assert resultados["tempo"].estado is Estado.OK
    assert "27/04/1970" in resultados["tempo"].mensagem
    assert [f.evidencia_id for f in resultados["tempo"].fontes] == [8]
    assert resultados["situacao"].mensagem.startswith("Matriz: ")
    assert resultados["estabelecimento"].situacao == "FILIAL"


def test_filial_sem_matriz_identificada_usa_os_proprios_dados() -> None:
    consultado = _filial(natureza_descricao="Sociedade Empresária Limitada")

    avaliacao = avaliar(DadosConsulta(CNPJ_FILIAL, consultado, NaoEncontrado(None)), CONTEXTO, TABELAS)
    resultados = por_id(avaliacao)

    assert resultados["natureza"].estado is Estado.RESTRICAO
    assert resultados["estabelecimento"].estado is Estado.ALERTA
    assert avaliacao.status is StatusFinal.INAPTA


def test_filial_une_os_cnaes_da_matriz_e_da_filial() -> None:
    consultado = _filial(cnae_principal="8610101", cnaes_secundarios=("4711302",))
    matriz = _matriz(cnae_principal="4711302", cnaes_secundarios=())

    resultados = por_id(avaliar(DadosConsulta(CNPJ_FILIAL, consultado, matriz), CONTEXTO, TABELAS))

    cnae = resultados["cnae"]
    assert cnae.estado is Estado.OK
    assert f"principal {formatar_cnae('4711302')}" in cnae.mensagem
    assert [(a.dados["papel"], a.dados["codigo"]) for a in cnae.achados] == [
        ("principal", formatar_cnae("4711302")),
        ("secundario", formatar_cnae("8610101")),
    ]
    assert [f.evidencia_id for f in cnae.fontes] == [7, 8]
    assert [f.evidencia_id for f in resultados["religiosa"].fontes] == [7, 8]


def test_so_a_matriz_com_cnae_baixo_e_alerta() -> None:
    matriz = _matriz(cnae_principal="4711302", cnaes_secundarios=())

    avaliacao = avaliar(DadosConsulta(CNPJ_MATRIZ, matriz), CONTEXTO, TABELAS)

    assert por_id(avaliacao)["cnae"].estado is Estado.ALERTA
    assert [f.evidencia_id for f in por_id(avaliacao)["cnae"].fontes] == [8]


def test_filial_com_matriz_indisponivel_e_inconclusiva() -> None:
    falha = Falha(MotivoFalha.PRAZO_ESGOTADO, "prazo")

    avaliacao = avaliar(DadosConsulta(CNPJ_FILIAL, _filial(), falha), CONTEXTO, TABELAS)
    resultados = por_id(avaliacao)

    assert resultados["situacao"].estado is Estado.INDISPONIVEL
    assert resultados["situacao"].situacao == "MATRIZ_INDISPONIVEL"
    assert avaliacao.status is StatusFinal.INCONCLUSIVA
    assert "situacao" in avaliacao.motivos
