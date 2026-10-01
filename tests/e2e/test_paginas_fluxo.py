import re
import uuid
from html import escape
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.e2e.replay import OpenCnpjReplay
from validador_osc.api.formatacao import rotulo_estado, rotulo_status

pytestmark = pytest.mark.db

PAGINA_CONSULTA = re.compile(r"/consultas/([0-9a-f-]{36})")


def _enviar_formulario(cliente: TestClient, cnpj: str, esfera: str = "") -> str:
    resposta = cliente.post("/consultas", data={"cnpj": cnpj, "esfera": esfera}, follow_redirects=False)
    assert resposta.status_code == 303
    destino = resposta.headers["location"]
    encontrado = PAGINA_CONSULTA.fullmatch(destino)
    assert encontrado is not None
    return encontrado.group(1)


def _documento(cliente: TestClient, consulta_id: str) -> dict[str, Any]:
    resposta = cliente.get(f"/api/v1/consultas/{consulta_id}")
    assert resposta.status_code == 200
    documento: dict[str, Any] = resposta.json()
    return documento


def _pagina(cliente: TestClient, consulta_id: str) -> str:
    resposta = cliente.get(f"/consultas/{consulta_id}")
    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/html")
    return resposta.text


def test_pagina_inicial(cliente: TestClient) -> None:
    resposta = cliente.get("/")

    assert resposta.status_code == 200
    assert '<form class="consulta" method="post" action="/consultas"' in resposta.text
    assert 'name="cnpj"' in resposta.text


def test_formulario_redireciona_para_o_resultado(cliente: TestClient) -> None:
    consulta_id = _enviar_formulario(cliente, "19.131.243/0001-97")

    documento = _documento(cliente, consulta_id)
    pagina = _pagina(cliente, consulta_id)

    assert documento["id"] == consulta_id
    assert escape(rotulo_status(documento["status"])) in pagina
    assert escape(documento["razao_social"]) in pagina
    assert "19.131.243/0001-97" in pagina
    assert f'href="/consultas/{consulta_id}"' in pagina
    for verificacao in documento["verificacoes"]:
        assert f'id="verificacao-{verificacao["id"]}"' in pagina
        assert escape(verificacao["nome"]) in pagina
        assert escape(verificacao["mensagem"]) in pagina
    for estado in {verificacao["estado"] for verificacao in documento["verificacoes"]}:
        assert escape(rotulo_estado(estado)) in pagina


def test_formulario_com_esfera(cliente: TestClient) -> None:
    consulta_id = _enviar_formulario(cliente, "65478551000100", "municipio")

    documento = _documento(cliente, consulta_id)
    pagina = _pagina(cliente, consulta_id)

    assert documento["esfera"] == "municipio"
    assert "<dd>Município</dd>" in pagina


def test_formulario_com_esfera_desconhecida_consulta_sem_esfera(cliente: TestClient) -> None:
    consulta_id = _enviar_formulario(cliente, "65478551000100", "galaxia")

    assert _documento(cliente, consulta_id)["esfera"] is None


def test_cnpj_invalido_volta_ao_formulario_preenchido(cliente: TestClient, replay: OpenCnpjReplay) -> None:
    consulta_id = _enviar_formulario(cliente, "19.131.243/0001-98", "estado")

    pagina = _pagina(cliente, consulta_id)

    assert "Confira o CNPJ digitado" in pagina
    assert '<strong class="destaque-dv">97</strong>' in pagina
    assert "dígito verificador não confere (esperado 97)" in pagina
    assert 'value="19.131.243/0001-98"' in pagina
    assert 'aria-invalid="true"' in pagina
    assert re.search(r'value="estado"\s+checked', pagina) is not None
    assert replay.chamadas == []


def test_pagina_de_consulta_inexistente_e_404(cliente: TestClient) -> None:
    resposta = cliente.get(f"/consultas/{uuid.uuid4()}")

    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith("text/html")
