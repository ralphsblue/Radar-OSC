from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from tests.e2e.replay import OPCOES_CLIENTE, FontesReplay, RelogioFixo
from validador_osc.api.app import criar_app
from validador_osc.config import Configuracao

pytestmark = pytest.mark.db

TOKEN = "segredo-de-teste"
OKBR = "19131243000197"


@pytest.fixture
def cliente_operador(banco_limpo: str, replay: FontesReplay, relogio: RelogioFixo) -> Iterator[TestClient]:
    configuracao = Configuracao(
        database_url=banco_limpo, token_operador=SecretStr(TOKEN), limite_consultas_por_minuto=2
    )
    with TestClient(
        criar_app(configuracao, replay.transporte, relogio), backend_options=OPCOES_CLIENTE
    ) as cliente:
        yield cliente


def _primeira_evidencia(documento: dict[str, Any]) -> int:
    for verificacao in documento["verificacoes"]:
        for fonte in verificacao["fontes"]:
            if fonte["evidencia"]:
                return int(fonte["evidencia"])
    raise AssertionError("consulta sem evidência")


def test_evidencia_bruta_so_para_operador(cliente_operador: TestClient) -> None:
    documento = cliente_operador.post("/api/v1/consultas", json={"cnpj": OKBR}).json()
    evidencia = _primeira_evidencia(documento)

    publica = cliente_operador.get(f"/api/v1/evidencias/{evidencia}")
    errada = cliente_operador.get(f"/api/v1/evidencias/{evidencia}", headers={"X-Token-Operador": "x"})
    operador = cliente_operador.get(f"/api/v1/evidencias/{evidencia}", headers={"X-Token-Operador": TOKEN})

    assert publica.status_code == 403
    assert errada.status_code == 403
    assert operador.status_code == 200
    assert len(operador.headers["x-sha256"]) == 64
    assert operador.content


def test_limite_de_consultas_por_minuto(cliente_operador: TestClient) -> None:
    for _ in range(2):
        cliente_operador.post("/api/v1/consultas", json={"cnpj": OKBR, "atualizar": True})
    resposta = cliente_operador.post("/api/v1/consultas", json={"cnpj": OKBR, "atualizar": True})
    assert resposta.status_code == 429
    assert resposta.headers["content-type"].startswith("application/problem+json")


def test_pagina_de_fontes_lista_bases_e_fontes_online(cliente_operador: TestClient) -> None:
    cliente_operador.post("/api/v1/consultas", json={"cnpj": OKBR})
    resposta = cliente_operador.get("/fontes")
    assert resposta.status_code == 200
    assert "CGU, CEIS" in resposta.text
    assert "TCE-SP, repasses ao Terceiro Setor" in resposta.text
    assert "Mapa das OSCs (Ipea), busca por CNPJ" in resposta.text
    assert "Sem carga" in resposta.text
    assert "OpenCNPJ" in resposta.text
