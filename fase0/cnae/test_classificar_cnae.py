"""Testes da classificação CNAE e da regra de alerta religiosa.

    .venv/Scripts/python -m pytest fase0/cnae -q
"""

import pytest
from classificar_cnae import (
    avaliar_entidade,
    carregar_ibge,
    classificar,
    normalizar_cnae,
)

ASSOCIACAO = 3999
RELIGIOSA = 3220


@pytest.mark.parametrize(
    ("cnae", "faixa", "regra"),
    [
        ("9430800", "ALTA", "94.30-8 (classe)"),
        ("8800600", "ALTA", "88 (divisao)"),
        ("9499500", "MEDIA", "94.99-5 (classe)"),
        ("9491000", "MEDIA", "94.91-0 (classe)"),
        ("4711302", "BAIXA", "padrao"),
        ("9411100", "BAIXA", "94.1 (grupo)"),
        ("8711505", "MEDIA", "8711-5/05 (subclasse)"),
        ("8513900", "ALTA", "85 (divisao)"),
        ("9001901", "ALTA", "90 (divisao)"),
    ],
)
def test_cnaes_de_referencia(cnae, faixa, regra):
    c = classificar(cnae)
    assert (c.faixa, c.regra_aplicada) == (faixa, regra)


def test_todas_as_subclasses_recebem_faixa():
    subclasses = carregar_ibge()["subclasses"]
    assert len(subclasses) == 1332
    assert all(classificar(s["id"]).faixa in {"ALTA", "MEDIA", "BAIXA"} for s in subclasses)


@pytest.mark.parametrize("entrada", [9430800, "94.30-8-00", "9430-8/00", "9430800"])
def test_normalizacao(entrada):
    assert normalizar_cnae(entrada) == "9430800"


def test_inteiro_brasilapi_sem_zero_a_esquerda():
    assert normalizar_cnae(111301) == "0111301"


def test_religiosa_so_culto_gera_alerta_religioso_mas_nao_alerta_cnae():
    r = avaliar_entidade(RELIGIOSA, "9491000", [])
    assert r.melhor_faixa == "MEDIA"
    assert r.alerta_cnae is None
    assert r.alerta_religiosa is not None


def test_religiosa_com_assistencia_social_nao_gera_alerta():
    r = avaliar_entidade(RELIGIOSA, "9491000", ["8800600"])
    assert r.alerta_religiosa is None and r.alerta_cnae is None


def test_religiosa_com_secundario_generico_mantem_alerta():
    assert avaliar_entidade(RELIGIOSA, "9491000", ["9499500"]).alerta_religiosa is not None


def test_associacao_com_cnae_principal_religioso_gera_alerta():
    assert avaliar_entidade(ASSOCIACAO, "9491000", ["9499500"]).alerta_religiosa is not None


def test_associacao_com_religioso_so_secundario_nao_gera_alerta():
    assert avaliar_entidade(ASSOCIACAO, "9499500", ["9491000"]).alerta_religiosa is None


def test_natureza_religiosa_com_principal_social():
    assert avaliar_entidade(RELIGIOSA, "8513900", ["9491000"]).alerta_religiosa is None


def test_so_baixa_gera_alerta_cnae():
    r = avaliar_entidade(ASSOCIACAO, "4711302", ["9411100"])
    assert r.melhor_faixa == "BAIXA" and r.alerta_cnae is not None and r.alerta_religiosa is None
