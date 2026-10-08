import pytest

from tests.apoio.fabricas import EVIDENCIA, RECEBIDA_EM, SHA256, cadastro, coleta_obtida
from validador_osc.dominio.coleta import Coleta, Falha, MotivoFalha, NaoEncontrado, Obtido, RefEvidencia
from validador_osc.dominio.tipos import Cadastro
from validador_osc.regras.entidade import SituacaoMatriz, resolver_entidade

FILIAL = "62779145000270"
MATRIZ = "62779145000190"
FILIAL_0001 = "24006302000135"
EVIDENCIA_MATRIZ = RefEvidencia(id=8, fonte="brasilapi", sha256=SHA256, recebida_em=RECEBIDA_EM)


def filial(**alteracoes: object) -> Obtido[Cadastro]:
    return coleta_obtida(**{"cnpj": FILIAL, "matriz": False, **alteracoes})


def matriz(**alteracoes: object) -> Obtido[Cadastro]:
    return Obtido(cadastro(**{"cnpj": MATRIZ, "matriz": True, **alteracoes}), EVIDENCIA_MATRIZ)


def test_matriz_consultada_e_a_propria_entidade() -> None:
    consultado = coleta_obtida()

    entidade = resolver_entidade(consultado, None)

    assert entidade.situacao_matriz is SituacaoMatriz.CONSULTADA_E_MATRIZ
    assert entidade.matriz is entidade.consultado
    assert entidade.avaliado is entidade.consultado
    assert entidade.coleta_matriz is None
    assert not entidade.eh_filial
    assert [f.evidencia_id for f in entidade.fontes] == [EVIDENCIA.id]


def test_matriz_consultada_ignora_coleta_de_matriz_recebida() -> None:
    entidade = resolver_entidade(coleta_obtida(), matriz())

    assert entidade.situacao_matriz is SituacaoMatriz.CONSULTADA_E_MATRIZ
    assert entidade.coleta_matriz is None


def test_filial_com_matriz_obtida_avalia_a_matriz() -> None:
    coleta_matriz = matriz()

    entidade = resolver_entidade(filial(), coleta_matriz)

    assert entidade.situacao_matriz is SituacaoMatriz.OBTIDA
    assert entidade.eh_filial
    assert entidade.matriz is not None
    assert entidade.avaliado is entidade.matriz
    assert entidade.avaliado.cadastro.cnpj == MATRIZ
    assert entidade.consultado.cadastro.cnpj == FILIAL
    assert entidade.coleta_matriz is coleta_matriz
    assert [(f.fonte, f.evidencia_id) for f in entidade.fontes] == [("opencnpj", 7), ("brasilapi", 8)]


@pytest.mark.parametrize(
    "coleta",
    [
        pytest.param(matriz(cnpj=MATRIZ, matriz=False), id="matriz-volta-como-filial"),
        pytest.param(NaoEncontrado(None), id="0001-nao-encontrada"),
        pytest.param(None, id="sem-coleta"),
    ],
)
def test_matriz_nao_identificada(coleta: Coleta[Cadastro] | None) -> None:
    entidade = resolver_entidade(filial(), coleta)

    assert entidade.situacao_matriz is SituacaoMatriz.NAO_IDENTIFICADA
    assert entidade.matriz is None
    assert entidade.avaliado is entidade.consultado
    assert entidade.coleta_matriz is coleta
    assert [f.evidencia_id for f in entidade.fontes] == [EVIDENCIA.id]


def test_cnpj_da_matriz_igual_ao_consultado_nao_identifica_matriz() -> None:
    consultado = coleta_obtida(cnpj=FILIAL_0001, matriz=False)
    mesma = Obtido(cadastro(cnpj=FILIAL_0001, matriz=True), EVIDENCIA_MATRIZ)

    entidade = resolver_entidade(consultado, mesma)

    assert entidade.situacao_matriz is SituacaoMatriz.NAO_IDENTIFICADA
    assert entidade.matriz is None


@pytest.mark.parametrize("motivo", [MotivoFalha.HTTP_5XX, MotivoFalha.PRAZO_ESGOTADO])
def test_falha_na_matriz_deixa_indisponivel(motivo: MotivoFalha) -> None:
    falha = Falha(motivo, "fora")

    entidade = resolver_entidade(filial(), falha)

    assert entidade.situacao_matriz is SituacaoMatriz.INDISPONIVEL
    assert entidade.matriz is None
    assert entidade.avaliado is entidade.consultado
    assert entidade.coleta_matriz is falha


def test_cnaes_da_matriz_consultada_vem_como_estao() -> None:
    entidade = resolver_entidade(coleta_obtida(cnaes_secundarios=("9493600", "9499500")), None)

    assert entidade.cnaes == ("9430800", ("9493600", "9499500"))


def test_cnaes_sem_matriz_identificada_sao_os_da_filial() -> None:
    entidade = resolver_entidade(filial(cnae_principal="8610101", cnaes_secundarios=("8630501",)), None)

    assert entidade.cnaes == ("8610101", ("8630501",))


def test_cnaes_unem_matriz_e_filial_sem_duplicata_com_principal_da_matriz() -> None:
    consultado = filial(cnae_principal="8610101", cnaes_secundarios=("9493600", "9430800", "8630501"))
    coleta_matriz = matriz(cnae_principal="9430800", cnaes_secundarios=("9493600", "9499500"))

    entidade = resolver_entidade(consultado, coleta_matriz)

    assert entidade.cnaes == ("9430800", ("9493600", "9499500", "8610101", "8630501"))


def test_cnaes_da_filial_entram_mesmo_sem_principal_na_matriz() -> None:
    consultado = filial(cnae_principal="8610101", cnaes_secundarios=())
    coleta_matriz = matriz(cnae_principal=None, cnaes_secundarios=("9499500",))

    entidade = resolver_entidade(consultado, coleta_matriz)

    assert entidade.cnaes == (None, ("9499500", "8610101"))


def test_cnaes_ignoram_principal_vazio_da_filial() -> None:
    consultado = filial(cnae_principal=None, cnaes_secundarios=("8630501",))

    entidade = resolver_entidade(consultado, matriz(cnaes_secundarios=()))

    assert entidade.cnaes == ("9430800", ("8630501",))
