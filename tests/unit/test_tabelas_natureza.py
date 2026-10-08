import copy
import json
from importlib.resources import files
from pathlib import Path

import pytest

from validador_osc.regras.tabelas import carregar_tabelas
from validador_osc.regras.tabelas.leitura import ErroTabela
from validador_osc.regras.tabelas.natureza import (
    RegraNatureza,
    TabelaNatureza,
    carregar_tabela_natureza,
    digito_natureza,
    formatar_natureza,
    montar_tabela_natureza,
    normalizar_descricao_natureza,
    resolver_natureza,
)

NATUREZAS_VISTAS = Path(__file__).resolve().parents[1] / "fixtures" / "naturezas_vistas_fase0.json"


def _bruto() -> dict[str, object]:
    texto = files("validador_osc").joinpath("dados", "natureza_juridica.json").read_text(encoding="utf-8")
    resultado: dict[str, object] = json.loads(texto)
    return resultado


def _itens(bruto: dict[str, object]) -> list[dict[str, object]]:
    itens = bruto["naturezas"]
    assert isinstance(itens, list)
    return itens


def _descricoes_da_fase0() -> set[str]:
    vistas: list[str] = json.loads(NATUREZAS_VISTAS.read_text(encoding="utf-8"))
    return set(vistas)


@pytest.fixture(scope="module")
def tabela() -> TabelaNatureza:
    return carregar_tabela_natureza()


def test_tabela_inteira_valida(tabela: TabelaNatureza) -> None:
    assert len(tabela.naturezas) == 89
    for codigo, natureza in tabela.naturezas.items():
        assert codigo == natureza.codigo
        assert 1000 <= codigo <= 9999
        assert natureza.codigo_formatado == formatar_natureza(codigo)
        assert digito_natureza(codigo // 10) == codigo % 10
        assert natureza.justificativa.strip()
        assert tabela.por_descricao[normalizar_descricao_natureza(natureza.descricao)] is natureza
    assert carregar_tabelas().natureza is tabela


def test_contagem_por_regra(tabela: TabelaNatureza) -> None:
    contagem = {regra: 0 for regra in RegraNatureza}
    for natureza in tabela.naturezas.values():
        contagem[natureza.regra] += 1
    assert contagem == {
        RegraNatureza.ELEGIVEL: 2,
        RegraNatureza.ELEGIVEL_COM_ALERTA_RELIGIOSO: 1,
        RegraNatureza.REVISAO_MANUAL: 4,
        RegraNatureza.NAO_ELEGIVEL: 82,
    }


@pytest.mark.parametrize(
    ("codigo", "formatado", "regra"),
    [
        (3999, "399-9", RegraNatureza.ELEGIVEL),
        (3069, "306-9", RegraNatureza.ELEGIVEL),
        (3220, "322-0", RegraNatureza.ELEGIVEL_COM_ALERTA_RELIGIOSO),
        (2143, "214-3", RegraNatureza.REVISAO_MANUAL),
        (3301, "330-1", RegraNatureza.REVISAO_MANUAL),
        (3204, "320-4", RegraNatureza.REVISAO_MANUAL),
        (2330, "233-0", RegraNatureza.REVISAO_MANUAL),
        (3077, "307-7", RegraNatureza.NAO_ELEGIVEL),
        (2062, "206-2", RegraNatureza.NAO_ELEGIVEL),
        (2038, "203-8", RegraNatureza.NAO_ELEGIVEL),
        (1015, "101-5", RegraNatureza.NAO_ELEGIVEL),
        (4090, "409-0", RegraNatureza.NAO_ELEGIVEL),
    ],
)
def test_regras_esperadas(tabela: TabelaNatureza, codigo: int, formatado: str, regra: RegraNatureza) -> None:
    natureza = resolver_natureza(tabela, codigo, None)
    assert natureza is not None
    assert (natureza.codigo_formatado, natureza.regra) == (formatado, regra)


@pytest.mark.parametrize(
    ("descricao", "codigo"),
    [
        ("Associação Privada", 3999),
        ("Fundação Privada", 3069),
        ("Organização Religiosa", 3220),
        ("Sociedade de Economia Mista", 2038),
        ("Cooperativa", 2143),
        ("Organização Social (OS)", 3301),
        ("Organização Social", 3301),
        ("Sociedade Empresária Limitada", 2062),
        ("Candidato a Cargo Político Eletivo", 4090),
        ("Empresário (Individual)", 2135),
        ("ASSOCIACAO PRIVADA", 3999),
        ("  associação   privada ", 3999),
        ("Estabelecimento no Brasil de Fundação ou Associação Estrangeiras", 3204),
        ("Entidade Pública sob Regime Especial", 1350),
    ],
)
def test_resolve_por_texto(tabela: TabelaNatureza, descricao: str, codigo: int) -> None:
    natureza = resolver_natureza(tabela, None, descricao)
    assert natureza is not None
    assert natureza.codigo == codigo


@pytest.mark.parametrize(
    "descricao", ["Associação Pública Privada", "Natureza Jurídica não informada", "", "   ", "OSC"]
)
def test_texto_desconhecido_nao_resolve(tabela: TabelaNatureza, descricao: str) -> None:
    assert resolver_natureza(tabela, None, descricao) is None


def test_sem_codigo_nem_texto_nao_resolve(tabela: TabelaNatureza) -> None:
    assert resolver_natureza(tabela, None, None) is None


def test_codigo_tem_precedencia_sobre_texto(tabela: TabelaNatureza) -> None:
    natureza = resolver_natureza(tabela, 2038, "Associação Privada")
    assert natureza is not None
    assert natureza.codigo == 2038


@pytest.mark.parametrize("codigo", [0, 8885, 1234])
def test_codigo_desconhecido_cai_para_texto(tabela: TabelaNatureza, codigo: int) -> None:
    assert resolver_natureza(tabela, codigo, None) is None
    natureza = resolver_natureza(tabela, codigo, "Associação Privada")
    assert natureza is not None
    assert natureza.codigo == 3999


def test_toda_descricao_vista_na_fase0_e_resolvida(tabela: TabelaNatureza) -> None:
    vistas = _descricoes_da_fase0()
    assert {"Associação Privada", "Organização Religiosa", "Cooperativa", "Organização Social"} <= vistas
    assert {d for d in vistas if resolver_natureza(tabela, None, d) is None} == set()


def test_normalizacao() -> None:
    assert normalizar_descricao_natureza("  Organização   Social (OS) ") == "organizacao social os"
    assert normalizar_descricao_natureza("Grupo, no Brasil, de X") == "grupo no brasil de x"


def _alterar(campo: str, valor: object, indice: int = 0) -> dict[str, object]:
    bruto = copy.deepcopy(_bruto())
    _itens(bruto)[indice][campo] = valor
    return bruto


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("codigo", 399),
        ("codigo", "1015"),
        ("codigo", True),
        ("codigo_formatado", "1015"),
        ("codigo_formatado", "101-6"),
        ("regra", "ELEGIVEL_TALVEZ"),
        ("justificativa", "  "),
        ("descricao", ""),
        ("sinonimos", "Órgão"),
        ("sinonimos", [""]),
        ("sinonimos", ["Associação Privada"]),
        ("sinonimos", ["(...)"]),
    ],
)
def test_carga_rejeita_item_invalido(campo: str, valor: object) -> None:
    with pytest.raises(ErroTabela):
        montar_tabela_natureza(_alterar(campo, valor))


def test_carga_rejeita_dv_incoerente() -> None:
    bruto = _alterar("codigo", 1016)
    _itens(bruto)[0]["codigo_formatado"] = "101-6"
    with pytest.raises(ErroTabela, match="dígito verificador"):
        montar_tabela_natureza(bruto)


def test_carga_rejeita_codigo_duplicado() -> None:
    bruto = copy.deepcopy(_bruto())
    itens = _itens(bruto)
    itens.append({**itens[0], "descricao": "Outra descrição"})
    with pytest.raises(ErroTabela, match="duplicado"):
        montar_tabela_natureza(bruto)


def test_carga_rejeita_campo_extra_ou_ausente() -> None:
    bruto = _alterar("extra", 1)
    with pytest.raises(ErroTabela, match="campos esperados"):
        montar_tabela_natureza(bruto)
    bruto = copy.deepcopy(_bruto())
    del _itens(bruto)[0]["sinonimos"]
    with pytest.raises(ErroTabela, match="campos esperados"):
        montar_tabela_natureza(bruto)


def test_carga_rejeita_lista_vazia() -> None:
    with pytest.raises(ErroTabela):
        montar_tabela_natureza({**_bruto(), "naturezas": []})


@pytest.mark.parametrize(("radical", "digito"), [(399, 9), (306, 9), (322, 0), (214, 3), (135, 0), (206, 2)])
def test_digito_natureza(radical: int, digito: int) -> None:
    assert digito_natureza(radical) == digito
