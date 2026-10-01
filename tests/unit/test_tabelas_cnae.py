import copy
import json
from importlib.resources import files
from types import MappingProxyType

import pytest

from validador_osc.regras.tabelas import (
    ErroTabela,
    Faixa,
    TabelaCnae,
    avaliar_cnaes,
    carregar_tabela_cnae,
    carregar_tabelas,
    classificar_subclasse,
    descrever_subclasse,
    formatar_cnae,
    melhor_faixa,
    montar_estrutura_cnae,
    montar_tabela_cnae,
    normalizar_cnae,
)

ASSOCIACAO = 3999
RELIGIOSA = 3220


def _bruto(nome: str) -> dict[str, object]:
    texto = files("validador_osc").joinpath("dados", nome).read_text(encoding="utf-8")
    resultado: dict[str, object] = json.loads(texto)
    return resultado


@pytest.fixture(scope="module")
def tabela() -> TabelaCnae:
    return carregar_tabela_cnae()


@pytest.mark.parametrize(
    ("cnae", "faixa", "regra"),
    [
        ("9430800", Faixa.ALTA, "94.30-8 (classe)"),
        ("8800600", Faixa.ALTA, "88 (divisao)"),
        ("9499500", Faixa.MEDIA, "94.99-5 (classe)"),
        ("9491000", Faixa.MEDIA, "94.91-0 (classe)"),
        ("4711302", Faixa.BAIXA, "padrao"),
        ("9411100", Faixa.BAIXA, "94.1 (grupo)"),
        ("8711505", Faixa.MEDIA, "8711-5/05 (subclasse)"),
        ("8513900", Faixa.ALTA, "85 (divisao)"),
        ("9001901", Faixa.ALTA, "90 (divisao)"),
    ],
)
def test_cnaes_de_referencia(tabela: TabelaCnae, cnae: str, faixa: Faixa, regra: str) -> None:
    c = classificar_subclasse(tabela, cnae)
    assert (c.faixa, c.regra_aplicada) == (faixa, regra)


def test_todas_as_subclasses_recebem_faixa(tabela: TabelaCnae) -> None:
    subclasses = tabela.estrutura.subclasses
    assert len(subclasses) == 1332
    contagem = {f: 0 for f in Faixa}
    for codigo in subclasses:
        contagem[classificar_subclasse(tabela, codigo).faixa] += 1
    assert contagem == {Faixa.ALTA: 86, Faixa.MEDIA: 25, Faixa.BAIXA: 1221}


@pytest.mark.parametrize("entrada", [9430800, "94.30-8-00", "9430-8/00", "9430800"])
def test_normalizacao(entrada: str | int) -> None:
    assert normalizar_cnae(entrada) == "9430800"


def test_inteiro_brasilapi_sem_zero_a_esquerda() -> None:
    assert normalizar_cnae(111301) == "0111301"


def test_religiosa_so_culto_gera_alerta_religioso_mas_nao_alerta_cnae(tabela: TabelaCnae) -> None:
    r = avaliar_cnaes(tabela, RELIGIOSA, "9491000", [])
    assert r.melhor_faixa is Faixa.MEDIA
    assert not r.alerta_cnae
    assert r.alerta_religiosa


def test_religiosa_com_assistencia_social_nao_gera_alerta(tabela: TabelaCnae) -> None:
    r = avaliar_cnaes(tabela, RELIGIOSA, "9491000", ["8800600"])
    assert not r.alerta_religiosa
    assert not r.alerta_cnae


def test_religiosa_com_secundario_generico_mantem_alerta(tabela: TabelaCnae) -> None:
    assert avaliar_cnaes(tabela, RELIGIOSA, "9491000", ["9499500"]).alerta_religiosa


def test_associacao_com_cnae_principal_religioso_gera_alerta(tabela: TabelaCnae) -> None:
    assert avaliar_cnaes(tabela, ASSOCIACAO, "9491000", ["9499500"]).alerta_religiosa


def test_associacao_com_religioso_so_secundario_nao_gera_alerta(tabela: TabelaCnae) -> None:
    r = avaliar_cnaes(tabela, ASSOCIACAO, "9499500", ["9491000"])
    assert not r.gatilho_religioso
    assert not r.alerta_religiosa


def test_natureza_religiosa_com_principal_social(tabela: TabelaCnae) -> None:
    r = avaliar_cnaes(tabela, RELIGIOSA, "8513900", ["9491000"])
    assert r.gatilho_religioso
    assert not r.alerta_religiosa


def test_so_baixa_gera_alerta_cnae(tabela: TabelaCnae) -> None:
    r = avaliar_cnaes(tabela, ASSOCIACAO, "4711302", ["9411100"])
    assert r.melhor_faixa is Faixa.BAIXA
    assert r.alerta_cnae
    assert not r.alerta_religiosa


def test_natureza_desconhecida_usa_so_o_cnae_principal(tabela: TabelaCnae) -> None:
    assert avaliar_cnaes(tabela, None, "9491000", []).alerta_religiosa
    assert not avaliar_cnaes(tabela, None, "9499500", []).gatilho_religioso


@pytest.mark.parametrize("entrada", ["94308", "94.30-8-000", "", True, 12345])
def test_normalizacao_rejeita_codigo_invalido(entrada: str | int) -> None:
    with pytest.raises(ValueError, match="CNAE inválido"):
        normalizar_cnae(entrada)


@pytest.mark.parametrize(
    ("codigo", "formatado"),
    [("94", "94"), ("941", "94.1"), ("94308", "94.30-8"), ("9430800", "9430-8/00")],
)
def test_formatacao(codigo: str, formatado: str) -> None:
    assert formatar_cnae(codigo) == formatado


def test_descricao_da_subclasse(tabela: TabelaCnae) -> None:
    assert descrever_subclasse(tabela, 220906) == "CONSERVAÇÃO DE FLORESTAS NATIVAS"
    assert descrever_subclasse(tabela, "9999999") is None


def testmelhor_faixa_exige_ao_menos_uma_classificacao() -> None:
    with pytest.raises(ValueError, match="Nenhuma"):
        melhor_faixa([])


def test_carga_e_unica_e_imutavel() -> None:
    tabelas = carregar_tabelas()
    assert tabelas.cnae is carregar_tabela_cnae()
    assert isinstance(tabelas.cnae.regras, MappingProxyType)
    assert isinstance(tabelas.cnae.estrutura.subclasses, MappingProxyType)


@pytest.mark.parametrize(
    ("alteracao", "mensagem"),
    [
        ({"prefixo": "9999"}, "não confere"),
        ({"prefixo": "0000000"}, "não existe"),
        ({"faixa": "ALTISSIMA"}, "valor inválido"),
        ({"nivel": "secao"}, "valor inválido"),
        ({"justificativa": "  "}, "texto não vazio"),
    ],
)
def test_regra_mal_formada_falha_na_carga(alteracao: dict[str, str], mensagem: str) -> None:
    bruto = copy.deepcopy(_bruto("regras_cnae.json"))
    regras = bruto["regras"]
    assert isinstance(regras, list)
    regras[0].update(alteracao)
    with pytest.raises(ErroTabela, match=mensagem):
        montar_tabela_cnae(bruto, carregar_tabela_cnae().estrutura)


def test_prefixo_duplicado_falha_na_carga() -> None:
    bruto = copy.deepcopy(_bruto("regras_cnae.json"))
    regras = bruto["regras"]
    assert isinstance(regras, list)
    regras.append(dict(regras[0]))
    with pytest.raises(ErroTabela, match="duplicado"):
        montar_tabela_cnae(bruto, carregar_tabela_cnae().estrutura)


def test_estrutura_com_subclasse_orfa_falha_na_carga() -> None:
    bruto = copy.deepcopy(_bruto("cnae_subclasses.json"))
    subclasses = bruto["subclasses"]
    assert isinstance(subclasses, dict)
    subclasses["0000000"] = "INEXISTENTE"
    with pytest.raises(ErroTabela, match="sem classe"):
        montar_estrutura_cnae(bruto)
