from importlib.resources import files
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from validador_osc.api.app import criar_app
from validador_osc.api.formatacao import formatar_cnpj, formatar_data, registrar_filtros, rotulo_status
from validador_osc.config import Configuracao
from validador_osc.dominio.resultado import StatusFinal

_TEMPLATES = str(files("validador_osc.api") / "templates")


@pytest.fixture(scope="module")
def ambiente() -> Environment:
    env = Environment(
        loader=FileSystemLoader(_TEMPLATES),
        autoescape=select_autoescape(),
        undefined=StrictUndefined,
    )
    registrar_filtros(env, ZoneInfo("America/Sao_Paulo"))
    return env


def _fonte() -> dict[str, Any]:
    return {
        "fonte": "opencnpj",
        "data_base": "2026-09-15",
        "obtida_em": "2026-10-05T17:32:09+00:00",
        "de_cache": False,
        "evidencia": 1832,
        "sha256": "a" * 64,
    }


def _verificacao(id_: str, nome: str, tipo: str, estado: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": id_,
        "spec": 2,
        "nome": nome,
        "tipo": tipo,
        "estado": estado,
        "mensagem": f"Mensagem de {nome}.",
        "achados": [],
        "fontes": [_fonte()],
        **extra,
    }


def _consulta(status: StatusFinal) -> dict[str, Any]:
    estados = {
        StatusFinal.APTA: ("OK", "OK", "OK"),
        StatusFinal.APTA_COM_RESSALVAS: ("OK", "ALERTA", "OK"),
        StatusFinal.INAPTA: ("RESTRICAO", "OK", "OK"),
        StatusFinal.INCONCLUSIVA: ("INDISPONIVEL", "OK", "INDISPONIVEL"),
    }[status]
    verificacoes = [
        _verificacao("situacao", "Situação cadastral", "ELIMINATORIA", estados[0]),
        _verificacao("tempo", "Tempo de existência", "ALERTA", estados[1]),
        _verificacao("mapa_osc", "Mapa das OSCs", "INFORMATIVA", estados[2], situacao="PREENCHIDO"),
    ]
    motivos = [v["id"] for v in verificacoes if v["estado"] in {"RESTRICAO", "ALERTA"}][:1]
    if status is StatusFinal.INCONCLUSIVA:
        motivos = ["situacao"]
    return {
        "id": "6f1c2a7e-0000-4000-8000-000000000001",
        "cnpj": "62779145000270",
        "cnpj_avaliado": "62779145000190",
        "estabelecimento": "FILIAL",
        "razao_social": "IRMANDADE DA SANTA CASA DE MISERICORDIA DE SAO PAULO",
        "esfera": "municipio",
        "data_referencia": "2026-10-05",
        "consultado_em": "2026-10-05T14:32:10-03:00",
        "status": status,
        "motivos": motivos,
        "avisos": ["mapa_osc"] if status is StatusFinal.INCONCLUSIVA else [],
        "resumo": {"ok": 2, "alerta": 1, "restricao": 0, "indisponivel": 0, "nao_verificado": 0},
        "verificacoes": verificacoes,
        "versao": {"app": "0.1.0", "regras": "sha256:abc"},
        "aviso": "Triagem automatizada de cadastros públicos. Não substitui certidões oficiais.",
    }


def _consulta_invalida() -> dict[str, Any]:
    dv = {
        "id": "dv",
        "spec": 1,
        "nome": "Dígito verificador",
        "tipo": "ELIMINATORIA",
        "estado": "RESTRICAO",
        "mensagem": "CNPJ inválido: dígito verificador não confere (esperado 97).",
        "achados": [{"tipo": "cnpj_invalido", "motivo": "dv", "dv_esperado": "97"}],
        "fontes": [],
    }
    return {
        "id": "6f1c2a7e-0000-4000-8000-000000000002",
        "cnpj": "19131243000198",
        "cnpj_avaliado": None,
        "estabelecimento": None,
        "razao_social": None,
        "esfera": None,
        "data_referencia": "2026-10-05",
        "consultado_em": "2026-10-05T14:32:10-03:00",
        "status": StatusFinal.CNPJ_INVALIDO,
        "motivos": ["dv"],
        "avisos": [],
        "resumo": None,
        "verificacoes": [dv],
        "versao": {"app": "0.1.0", "regras": "sha256:abc"},
        "aviso": "Triagem automatizada de cadastros públicos. Não substitui certidões oficiais.",
    }


def test_inicio_mostra_formulario() -> None:
    with TestClient(criar_app(Configuracao())) as cliente:
        resposta = cliente.get("/")
    assert resposta.status_code == 200
    html = resposta.text
    assert '<html lang="pt-BR">' in html
    assert 'action="/consultas"' in html
    assert 'name="cnpj"' in html
    assert html.count('name="esfera"') == 4
    assert "Não substitui certidões oficiais." in html
    assert "—" not in html


@pytest.mark.parametrize("arquivo", ["estilo.css", "app.js", "favicon.svg"])
def test_arquivos_estaticos(arquivo: str) -> None:
    with TestClient(criar_app(Configuracao())) as cliente:
        resposta = cliente.get(f"/static/{arquivo}")
    assert resposta.status_code == 200


@pytest.mark.parametrize(
    "status",
    [StatusFinal.APTA, StatusFinal.APTA_COM_RESSALVAS, StatusFinal.INAPTA, StatusFinal.INCONCLUSIVA],
)
def test_resultado_renderiza_cada_status(ambiente: Environment, status: StatusFinal) -> None:
    consulta = _consulta(status)
    html = ambiente.get_template("resultado.html").render(consulta=consulta, versao="0.1.0")
    assert f'class="status status--{status.lower().replace("_", "-")}"' in html
    assert f">{rotulo_status(status)}</h2>" in html
    assert "62.779.145/0001-90" in html
    assert "62.779.145/0002-70" in html
    assert f'href="/consultas/{consulta["id"]}"' in html
    assert "05/10/2026 às 14:32" in html
    assert 'action="/consultas"' not in html
    assert ("Não foi possível verificar: Mapa das OSCs" in html) is (status is StatusFinal.INCONCLUSIVA)
    assert "—" not in html


def test_resultado_cnpj_invalido_volta_ao_formulario(ambiente: Environment) -> None:
    html = ambiente.get_template("resultado.html").render(consulta=_consulta_invalida(), versao="0.1.0")
    assert "Confira o CNPJ digitado" in html
    assert 'action="/consultas"' in html
    assert 'value="19.131.243/0001-98"' in html
    assert 'aria-invalid="true"' in html
    assert "esperado 97" in html
    assert "/consultas/6f1c" not in html


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("62779145000190", "62.779.145/0001-90"),
        ("12ABC34501DE35", "12.ABC.345/01DE-35"),
        ("123", "123"),
    ],
)
def test_formatar_cnpj(entrada: str, esperado: str) -> None:
    assert formatar_cnpj(entrada) == esperado


def test_formatar_data() -> None:
    assert formatar_data("2026-10-05") == "05/10/2026"
    assert formatar_data(None) == ""


def test_favicon_ico_redireciona_para_o_svg() -> None:
    with TestClient(criar_app(Configuracao())) as cliente:
        resposta = cliente.get("/favicon.ico", follow_redirects=False)
    assert resposta.status_code == 301
    assert resposta.headers["location"].startswith("/static/favicon.svg")
