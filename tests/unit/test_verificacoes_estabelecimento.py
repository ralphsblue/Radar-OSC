from datetime import date, timedelta

import pytest

from tests.unit.fabricas import DATA_REFERENCIA, RECEBIDA_EM, SHA256, cadastro, coleta_obtida
from validador_osc.dominio.coleta import Coleta, Falha, MotivoFalha, NaoEncontrado, Obtido, RefEvidencia
from validador_osc.dominio.resultado import Achado, Contexto, Estado
from validador_osc.dominio.tipos import Cadastro, SituacaoCadastral
from validador_osc.regras.catalogo import ESTABELECIMENTO, SITUACAO
from validador_osc.regras.entidade import Entidade, resolver_entidade
from validador_osc.regras.verificacoes.estabelecimento import (
    verificar_estabelecimento,
    verificar_situacao_entidade,
)

CONTEXTO = Contexto(data_referencia=DATA_REFERENCIA)
FILIAL = "04955882000523"
MATRIZ = "04955882000108"
FILIAL_0001 = "24006302000135"
EVIDENCIA_MATRIZ = RefEvidencia(id=8, fonte="opencnpj", sha256=SHA256, recebida_em=RECEBIDA_EM)
NAO_ATIVAS = [SituacaoCadastral.BAIXADA, SituacaoCadastral.INAPTA, SituacaoCadastral.SUSPENSA]


def filial(**alteracoes: object) -> Obtido[Cadastro]:
    return coleta_obtida(**{"cnpj": FILIAL, "matriz": False, **alteracoes})


def matriz(**alteracoes: object) -> Obtido[Cadastro]:
    return Obtido(cadastro(**{"cnpj": MATRIZ, "matriz": True, **alteracoes}), EVIDENCIA_MATRIZ)


def entidade_de(consultado: Obtido[Cadastro], coleta_matriz: Coleta[Cadastro] | None) -> Entidade:
    return resolver_entidade(consultado, coleta_matriz)


def test_situacao_da_matriz_consultada() -> None:
    resultado = verificar_situacao_entidade(entidade_de(coleta_obtida(), None), CONTEXTO)

    assert resultado.definicao == SITUACAO
    assert resultado.estado is Estado.OK
    assert resultado.mensagem.startswith("Situação ATIVA desde 03/10/2013")
    assert [f.evidencia_id for f in resultado.fontes] == [7]


def test_situacao_de_filial_usa_a_matriz_e_cita_as_duas_fontes() -> None:
    entidade = entidade_de(filial(situacao=SituacaoCadastral.BAIXADA), matriz())

    resultado = verificar_situacao_entidade(entidade, CONTEXTO)

    assert resultado.estado is Estado.OK
    assert resultado.mensagem.startswith("Matriz: Situação ATIVA")
    assert [f.evidencia_id for f in resultado.fontes] == [7, 8]
    assert resultado.situacao is None


def test_situacao_de_filial_com_matriz_baixada_e_restricao() -> None:
    entidade = entidade_de(
        filial(),
        matriz(situacao=SituacaoCadastral.BAIXADA, situacao_data=date(2020, 5, 4), motivo_descricao="X"),
    )

    resultado = verificar_situacao_entidade(entidade, CONTEXTO)

    assert resultado.estado is Estado.RESTRICAO
    assert resultado.mensagem.startswith("Matriz: Situação BAIXADA desde 04/05/2020. Motivo: X.")
    assert [f.evidencia_id for f in resultado.fontes] == [7, 8]


def test_situacao_de_filial_com_matriz_em_base_antiga_e_alerta() -> None:
    antiga = DATA_REFERENCIA - timedelta(days=61)

    resultado = verificar_situacao_entidade(entidade_de(filial(), matriz(data_base=antiga)), CONTEXTO)

    assert resultado.estado is Estado.ALERTA
    assert resultado.mensagem.startswith("Matriz: Situação ATIVA, mas a base cadastral")


@pytest.mark.parametrize(
    "coleta",
    [Falha(MotivoFalha.HTTP_5XX, "fora"), Falha(MotivoFalha.PRAZO_ESGOTADO, "prazo")],
    ids=["fonte-fora", "prazo"],
)
def test_situacao_com_matriz_indisponivel_e_indisponivel(coleta: Falha) -> None:
    resultado = verificar_situacao_entidade(entidade_de(filial(), coleta), CONTEXTO)

    assert resultado.estado is Estado.INDISPONIVEL
    assert resultado.situacao == "MATRIZ_INDISPONIVEL"
    assert "matriz não puderam ser obtidos" in resultado.mensagem
    assert [f.evidencia_id for f in resultado.fontes] == [7]


@pytest.mark.parametrize("situacao", [SituacaoCadastral.ATIVA, SituacaoCadastral.BAIXADA])
def test_situacao_com_matriz_nao_identificada_usa_a_filial(situacao: SituacaoCadastral) -> None:
    entidade = entidade_de(filial(situacao=situacao), NaoEncontrado(None))

    resultado = verificar_situacao_entidade(entidade, CONTEXTO)

    esperado = Estado.OK if situacao is SituacaoCadastral.ATIVA else Estado.RESTRICAO
    assert resultado.estado is esperado
    assert not resultado.mensagem.startswith("Matriz:")


def test_estabelecimento_da_matriz_e_ok() -> None:
    resultado = verificar_estabelecimento(entidade_de(coleta_obtida(), None))

    assert resultado.definicao == ESTABELECIMENTO
    assert resultado.estado is Estado.OK
    assert resultado.mensagem == "Consulta feita pelo CNPJ da matriz."
    assert resultado.situacao is None
    assert resultado.achados == ()


def test_estabelecimento_de_filial_ativa_com_matriz_ativa_e_ok() -> None:
    resultado = verificar_estabelecimento(entidade_de(filial(), matriz()))

    assert resultado.estado is Estado.OK
    assert resultado.situacao == "FILIAL"
    assert resultado.mensagem == (
        "A consulta partiu da filial 04.955.882/0005-23 (ATIVA); a entidade foi avaliada pela matriz "
        "04.955.882/0001-08."
    )
    assert resultado.achados == (Achado("filial", {"cnpj_filial": FILIAL, "cnpj_matriz": MATRIZ}),)
    assert [f.evidencia_id for f in resultado.fontes] == [7, 8]


@pytest.mark.parametrize("situacao", NAO_ATIVAS, ids=lambda s: s.name)
def test_filial_nao_ativa_com_matriz_ativa_e_alerta(situacao: SituacaoCadastral) -> None:
    consultado = filial(
        situacao=situacao,
        situacao_data=date(2017, 1, 5),
        motivo_codigo=1,
        motivo_descricao="EXTINCAO POR ENCERRAMENTO LIQUIDACAO VOLUNTARIA",
    )
    entidade = entidade_de(consultado, matriz())

    resultado = verificar_estabelecimento(entidade)
    situacao_entidade = verificar_situacao_entidade(entidade, CONTEXTO)

    assert resultado.estado is Estado.ALERTA
    assert resultado.situacao == "FILIAL_NAO_ATIVA"
    assert resultado.mensagem == (
        f"O estabelecimento informado (04.955.882/0005-23, filial) está {situacao.name} desde 05/01/2017 "
        "(motivo: EXTINCAO POR ENCERRAMENTO LIQUIDACAO VOLUNTARIA); a entidade (matriz 04.955.882/0001-08) "
        "está ATIVA. Confira se o CNPJ do edital ou do contrato está correto."
    )
    assert resultado.achados == (Achado("filial", {"cnpj_filial": FILIAL, "cnpj_matriz": MATRIZ}),)
    assert situacao_entidade.estado is Estado.OK


def test_filial_nao_ativa_sem_data_nem_motivo_omite_os_dois() -> None:
    consultado = filial(
        situacao=SituacaoCadastral.INAPTA, situacao_data=None, motivo_codigo=0, motivo_descricao="SEM MOTIVO"
    )

    resultado = verificar_estabelecimento(entidade_de(consultado, matriz()))

    assert resultado.mensagem.startswith(
        "O estabelecimento informado (04.955.882/0005-23, filial) está INAPTA; a entidade"
    )


def test_filial_e_matriz_baixadas_restringem_pela_situacao_e_nao_pelo_estabelecimento() -> None:
    entidade = entidade_de(
        filial(situacao=SituacaoCadastral.BAIXADA), matriz(situacao=SituacaoCadastral.BAIXADA)
    )

    estabelecimento = verificar_estabelecimento(entidade)
    situacao = verificar_situacao_entidade(entidade, CONTEXTO)

    assert estabelecimento.estado is Estado.OK
    assert estabelecimento.situacao == "FILIAL"
    assert "(BAIXADA)" in estabelecimento.mensagem
    assert situacao.estado is Estado.RESTRICAO


def test_filial_ativa_com_matriz_baixada_nao_alerta_no_estabelecimento() -> None:
    entidade = entidade_de(filial(), matriz(situacao=SituacaoCadastral.BAIXADA))

    assert verificar_estabelecimento(entidade).estado is Estado.OK
    assert verificar_situacao_entidade(entidade, CONTEXTO).estado is Estado.RESTRICAO


def test_matriz_nao_identificada_e_alerta_com_o_cnpj_tentado() -> None:
    resultado = verificar_estabelecimento(entidade_de(filial(), NaoEncontrado(None)))

    assert resultado.estado is Estado.ALERTA
    assert resultado.situacao == "MATRIZ_NAO_IDENTIFICADA"
    assert resultado.mensagem == (
        "O CNPJ 04.955.882/0005-23 é de uma filial e a matriz não foi identificada pelo CNPJ "
        "04.955.882/0001-08. Informe o CNPJ da matriz para avaliar a entidade; nesta consulta a avaliação "
        "usa os dados da filial."
    )
    assert resultado.achados == (Achado("matriz_nao_identificada", {"cnpj_tentado": MATRIZ}),)
    assert [f.evidencia_id for f in resultado.fontes] == [7]


def test_filial_com_ordem_0001_explica_que_nao_e_a_matriz() -> None:
    consultado = coleta_obtida(cnpj=FILIAL_0001, matriz=False)

    resultado = verificar_estabelecimento(entidade_de(consultado, None))

    assert resultado.estado is Estado.ALERTA
    assert resultado.situacao == "MATRIZ_NAO_IDENTIFICADA"
    assert resultado.mensagem.startswith(
        "O CNPJ 24.006.302/0001-35 é de uma filial e tem a ordem 0001, mas não é a matriz. "
    )
    assert resultado.achados == (Achado("matriz_nao_identificada", {"cnpj_tentado": FILIAL_0001}),)


def test_matriz_indisponivel_nao_alerta_no_estabelecimento() -> None:
    resultado = verificar_estabelecimento(entidade_de(filial(), Falha(MotivoFalha.TIMEOUT, "lenta")))

    assert resultado.estado is Estado.OK
    assert resultado.situacao == "FILIAL"
    assert resultado.mensagem == (
        "A consulta partiu da filial 04.955.882/0005-23; os dados da matriz não puderam ser obtidos."
    )
