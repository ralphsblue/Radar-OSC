import json
import uuid
from collections.abc import Iterator
from datetime import date, timedelta
from typing import Any

import pytest
from _pytest.mark import ParameterSet
from fastapi.testclient import TestClient

from tests.conftest import RAIZ
from tests.e2e.replay import (
    HOST_BRASILAPI,
    HOST_OPENCNPJ,
    OPCOES_CLIENTE,
    PREFIXO_BRASILAPI,
    FontesReplay,
    RelogioFixo,
    instante_referencia,
)
from validador_osc.api.app import criar_app
from validador_osc.cnpj import cnpj_da_matriz, eh_alfanumerico, validar
from validador_osc.config import Configuracao
from validador_osc.regras.parametros import carregar_limites

pytestmark = pytest.mark.db

ROTA = "/api/v1/consultas"
TIPO_PROBLEMA = "application/problem+json"
CADASTRAIS = ("dv", "situacao", "estabelecimento", "natureza", "cnae", "religiosa", "tempo")
OKBR = "19131243000197"
INEXISTENTE = "94580730000152"
URL_BANCO_FORA = "postgresql+psycopg://validador:validador@127.0.0.1:1/validador"
CASOS: list[dict[str, Any]] = json.loads(
    (RAIZ / "fase0" / "casos_referencia.json").read_text(encoding="utf-8")
)["casos"]


def _precisa_de_rede(cnpj: str) -> bool:
    return validar(cnpj).valido and not eh_alfanumerico(cnpj)


def _tem_fixtures(replay: FontesReplay, cnpj: str) -> bool:
    if not _precisa_de_rede(cnpj):
        return True
    return replay.tem_fixture(cnpj) and replay.tem_fixture(cnpj_da_matriz(cnpj))


def _cenarios() -> Iterator[ParameterSet]:
    replay = FontesReplay()
    for caso in CASOS:
        if not _tem_fixtures(replay, caso["cnpj"]):
            continue
        variantes = [caso, *caso["variantes"]]
        for indice, variante in enumerate(variantes):
            sufixo = f"-v{indice}" if indice else ""
            yield pytest.param(caso, variante, id=f"{caso['id']}{sufixo}")


def _consultar(cliente: TestClient, cnpj: str, **campos: Any) -> dict[str, Any]:
    resposta = cliente.post(ROTA, json={"cnpj": cnpj, **campos})
    assert resposta.status_code == 201, resposta.text
    documento: dict[str, Any] = resposta.json()
    assert resposta.headers["location"] == f"{ROTA}/{documento['id']}"
    return documento


def _verificacao(documento: dict[str, Any], id_: str) -> dict[str, Any]:
    encontrada: dict[str, Any] = next(v for v in documento["verificacoes"] if v["id"] == id_)
    return encontrada


DATA_ESPELHO_REPLAY = date(2026, 9, 14)


def _fontes(documento: dict[str, Any]) -> list[dict[str, Any]]:
    return [fonte for v in documento["verificacoes"] for fonte in v["fontes"]]


def _assert_problema(resposta: Any, status: int) -> None:
    assert resposta.status_code == status
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["status"] == status


@pytest.mark.parametrize(("caso", "variante"), list(_cenarios()))
def test_caso_de_referencia(
    cliente: TestClient,
    relogio: RelogioFixo,
    replay: FontesReplay,
    caso: dict[str, Any],
    variante: dict[str, Any],
) -> None:
    parametros = variante["parametros"]
    relogio.instante = instante_referencia(date.fromisoformat(parametros["data_referencia"]))

    documento = _consultar(cliente, caso["cnpj"], esfera=parametros["esfera"])

    assert documento["data_referencia"] == parametros["data_referencia"]
    assert documento["esfera"] == parametros["esfera"]
    obtidos = {v["id"]: v["estado"] for v in documento["verificacoes"]}
    esperados = {v["id"]: v["estado"] for v in variante["verificacoes"] if v["id"] in CADASTRAIS}
    data_referencia = date.fromisoformat(parametros["data_referencia"])
    if (
        esperados.get("situacao") == "OK"
        and data_referencia - DATA_ESPELHO_REPLAY > carregar_limites().idade_maxima_espelho
    ):
        esperados["situacao"] = "ALERTA"
    if variante["status_final"] == "CNPJ_INVALIDO":
        assert documento["status"] == "CNPJ_INVALIDO"
        assert obtidos == {"dv": esperados["dv"]}
    else:
        assert {id_: obtidos.get(id_) for id_ in esperados} == esperados
    contexto = caso.get("contexto", {})
    if "razao_social" in contexto:
        assert documento["razao_social"] == contexto["razao_social"]
        assert documento["estabelecimento"] == ("FILIAL" if contexto["filial"] else "MATRIZ")
        assert documento["cnpj_avaliado"] == (contexto["matriz"] or caso["cnpj"])
    if not _precisa_de_rede(caso["cnpj"]):
        assert replay.chamadas == []


def test_cnpj_invalido_e_resultado_de_negocio_sem_rede(cliente: TestClient, replay: FontesReplay) -> None:
    documento = _consultar(cliente, "19.131.243/0001-98")

    assert documento["status"] == "CNPJ_INVALIDO"
    assert documento["motivos"] == ["dv"]
    assert documento["razao_social"] is None
    [dv] = documento["verificacoes"]
    assert dv["estado"] == "RESTRICAO"
    assert "esperado 97" in dv["mensagem"]
    assert dv["achados"] == [{"tipo": "cnpj_invalido", "motivo": "dv", "dv_esperado": "97"}]
    assert replay.chamadas == []


def test_alfanumerico_fica_inconclusivo_sem_rede(cliente: TestClient, replay: FontesReplay) -> None:
    documento = _consultar(cliente, "12.ABC.345/01DE-35")

    assert documento["cnpj"] == "12ABC34501DE35"
    assert documento["status"] == "INCONCLUSIVA"
    assert "situacao" in documento["motivos"]
    assert _verificacao(documento, "dv")["estado"] == "OK"
    assert {v["estado"] for v in documento["verificacoes"] if v["id"] != "dv"} == {"NAO_VERIFICADO"}
    assert "alfanumérico" in _verificacao(documento, "situacao")["mensagem"]
    assert replay.chamadas == []


def test_cnpj_inexistente_deixa_situacao_indisponivel(cliente: TestClient, replay: FontesReplay) -> None:
    documento = _consultar(cliente, INEXISTENTE)

    situacao = _verificacao(documento, "situacao")
    assert situacao["estado"] == "INDISPONIVEL"
    assert situacao["situacao"] == "NAO_ENCONTRADO"
    assert documento["status"] == "INCONCLUSIVA"
    assert documento["razao_social"] is None
    assert f"/{INEXISTENTE}" in replay.caminhos()


def test_consulta_okbr_traz_cadastro_e_evidencia(cliente: TestClient, replay: FontesReplay) -> None:
    documento = _consultar(cliente, "19.131.243/0001-97")

    assert documento["cnpj"] == OKBR
    assert documento["razao_social"] == "OPEN KNOWLEDGE BRASIL"
    assert documento["estabelecimento"] == "MATRIZ"
    assert documento["consultado_em"] == instante_referencia().isoformat()
    [fonte, *_] = _verificacao(documento, "situacao")["fontes"]
    assert fonte["fonte"] == "opencnpj"
    assert fonte["data_base"] == "2026-09-14"
    assert fonte["de_cache"] is False
    assert isinstance(fonte["evidencia"], int)
    assert len(fonte["sha256"]) == 64
    assert sorted(replay.caminhos()) == sorted(["/info", f"/{OKBR}"])


def test_get_devolve_o_mesmo_documento(cliente: TestClient) -> None:
    documento = _consultar(cliente, OKBR)

    resposta = cliente.get(f"{ROTA}/{documento['id']}")

    assert resposta.status_code == 200
    assert resposta.json() == documento


def test_get_inexistente_e_404_problem_json(cliente: TestClient) -> None:
    _assert_problema(cliente.get(f"{ROTA}/{uuid.uuid4()}"), 404)


def test_get_com_id_que_nao_e_uuid_e_422(cliente: TestClient) -> None:
    _assert_problema(cliente.get(f"{ROTA}/nao-e-uuid"), 422)


@pytest.mark.parametrize(
    "corpo",
    [
        pytest.param({}, id="sem-cnpj"),
        pytest.param({"cnpj": ""}, id="cnpj-vazio"),
        pytest.param({"cnpj": "1" * 33}, id="cnpj-longo"),
        pytest.param({"cnpj": 19131243000197}, id="cnpj-numero"),
        pytest.param({"cnpj": OKBR, "esfera": "distrito"}, id="esfera-desconhecida"),
        pytest.param({"cnpj": OKBR, "atualizar": "talvez"}, id="atualizar-invalido"),
        pytest.param({"cnpj": OKBR, "extra": 1}, id="campo-extra"),
    ],
)
def test_corpo_invalido_e_422(cliente: TestClient, replay: FontesReplay, corpo: dict[str, Any]) -> None:
    _assert_problema(cliente.post(ROTA, json=corpo), 422)
    assert replay.chamadas == []


def test_corpo_que_nao_e_json_e_422(cliente: TestClient) -> None:
    resposta = cliente.post(ROTA, content=b"cnpj=1", headers={"content-type": "application/json"})

    _assert_problema(resposta, 422)


def test_idempotency_key_devolve_a_mesma_consulta(
    cliente: TestClient, relogio: RelogioFixo, replay: FontesReplay
) -> None:
    cabecalho = {"Idempotency-Key": "pedido-1"}
    primeira = cliente.post(ROTA, json={"cnpj": OKBR}, headers=cabecalho)
    chamadas = len(replay.chamadas)
    relogio.avancar(timedelta(minutes=5))

    segunda = cliente.post(ROTA, json={"cnpj": OKBR, "atualizar": True}, headers=cabecalho)

    assert primeira.status_code == 201
    assert segunda.status_code == 200
    assert segunda.json() == primeira.json()
    assert segunda.headers["location"] == primeira.headers["location"]
    assert len(replay.chamadas) == chamadas


def test_repeticao_em_menos_de_10s_devolve_a_consulta_feita(
    cliente: TestClient, relogio: RelogioFixo, replay: FontesReplay
) -> None:
    primeira = _consultar(cliente, OKBR)
    chamadas = len(replay.chamadas)
    relogio.avancar(timedelta(seconds=9))

    segunda = cliente.post(ROTA, json={"cnpj": "19.131.243/0001-97"})

    assert segunda.status_code == 200
    assert segunda.json() == primeira
    assert len(replay.chamadas) == chamadas


def test_outra_esfera_nao_e_repeticao(cliente: TestClient) -> None:
    primeira = _consultar(cliente, OKBR)

    segunda = _consultar(cliente, OKBR, esfera="municipio")

    assert segunda["id"] != primeira["id"]
    assert segunda["esfera"] == "municipio"


def test_atualizar_ignora_janela_e_cache(cliente: TestClient, replay: FontesReplay) -> None:
    primeira = _consultar(cliente, OKBR)
    replay.chamadas.clear()

    segunda = _consultar(cliente, OKBR, atualizar=True)

    assert segunda["id"] != primeira["id"]
    assert replay.caminhos() == [f"/{OKBR}"]
    assert {fonte["de_cache"] for fonte in _fontes(segunda)} == {False}
    assert _fontes(segunda)[0]["evidencia"] != _fontes(primeira)[0]["evidencia"]


def test_segunda_consulta_depois_de_10s_usa_cache(
    cliente: TestClient, relogio: RelogioFixo, replay: FontesReplay
) -> None:
    primeira = _consultar(cliente, OKBR)
    replay.chamadas.clear()
    relogio.avancar(timedelta(seconds=11))

    segunda = _consultar(cliente, OKBR)

    assert segunda["id"] != primeira["id"]
    assert replay.chamadas == []
    assert {fonte["de_cache"] for fonte in _fontes(segunda)} == {True}
    assert {fonte["evidencia"] for fonte in _fontes(segunda)} == {_fontes(primeira)[0]["evidencia"]}
    assert [v["estado"] for v in segunda["verificacoes"]] == [v["estado"] for v in primeira["verificacoes"]]


def test_as_duas_fontes_fora_do_ar_ficam_inconclusivas_sem_5xx(
    cliente: TestClient, relogio: RelogioFixo, replay: FontesReplay
) -> None:
    replay.derrubar(HOST_OPENCNPJ, HOST_BRASILAPI)

    documento = _consultar(cliente, OKBR)

    situacao = _verificacao(documento, "situacao")
    assert situacao["estado"] == "INDISPONIVEL"
    assert situacao["situacao"] == "FONTE_INDISPONIVEL"
    assert "HTTP_5XX" in situacao["mensagem"]
    assert documento["status"] == "INCONCLUSIVA"
    assert "situacao" in documento["motivos"]
    assert replay.caminhos().count(f"/{OKBR}") == 3
    assert replay.caminhos(HOST_BRASILAPI) == [f"{PREFIXO_BRASILAPI}{OKBR}"]

    replay.religar()
    replay.chamadas.clear()
    relogio.avancar(timedelta(seconds=11))
    recuperada = _consultar(cliente, OKBR)

    assert _verificacao(recuperada, "situacao")["estado"] == "OK"
    assert f"/{OKBR}" in replay.caminhos()
    assert replay.caminhos(HOST_BRASILAPI) == []
    assert {fonte["fonte"] for fonte in _fontes(recuperada)} == {"opencnpj"}


def test_opencnpj_fora_do_ar_usa_a_brasilapi(cliente: TestClient, replay: FontesReplay) -> None:
    replay.derrubar(HOST_OPENCNPJ)

    documento = _consultar(cliente, OKBR)

    assert documento["razao_social"] == "OPEN KNOWLEDGE BRASIL"
    assert {_verificacao(documento, id_)["estado"] for id_ in CADASTRAIS} == {"OK"}
    assert {fonte["fonte"] for fonte in _fontes(documento)} == {"brasilapi"}
    [fonte, *_] = _verificacao(documento, "situacao")["fontes"]
    assert fonte["data_base"] is None
    assert fonte["de_cache"] is False
    assert len(fonte["sha256"]) == 64
    assert replay.caminhos().count(f"/{OKBR}") == 3
    assert replay.caminhos(HOST_BRASILAPI) == [f"{PREFIXO_BRASILAPI}{OKBR}"]


def test_brasilapi_fora_do_ar_nao_afeta_quando_o_opencnpj_responde(
    cliente: TestClient, replay: FontesReplay
) -> None:
    replay.derrubar(HOST_BRASILAPI)

    documento = _consultar(cliente, OKBR)

    assert _verificacao(documento, "situacao")["estado"] == "OK"
    assert replay.caminhos(HOST_BRASILAPI) == []


def test_cnpj_inexistente_nas_duas_fontes(cliente: TestClient, replay: FontesReplay) -> None:
    documento = _consultar(cliente, INEXISTENTE)

    assert _verificacao(documento, "situacao")["situacao"] == "NAO_ENCONTRADO"
    assert replay.caminhos(HOST_BRASILAPI) == [f"{PREFIXO_BRASILAPI}{INEXISTENTE}"]


def test_estado_das_fontes_depois_de_consultas(
    cliente: TestClient, relogio: RelogioFixo, replay: FontesReplay
) -> None:
    _consultar(cliente, OKBR)
    replay.derrubar(HOST_OPENCNPJ)
    _consultar(cliente, "65478551000100")
    replay.religar()
    relogio.avancar(timedelta(minutes=1))

    resposta = cliente.get("/api/v1/fontes")

    assert resposta.status_code == 200
    estado = resposta.json()
    assert estado["gerado_em"] == relogio.instante.isoformat()
    assert estado["janela_horas"] == 24
    por_fonte = {f["fonte"]: f for f in estado["online"]}
    assert [f["fonte"] for f in estado["online"]] == sorted(por_fonte)
    assert {"opencnpj", "opencnpj_info", "brasilapi"} == set(por_fonte)
    opencnpj = por_fonte["opencnpj"]
    assert (opencnpj["respostas"], opencnpj["falhas"]) == (2, 1)
    assert opencnpj["ultimo_resultado"] == "FALHA"
    assert opencnpj["ultima_falha_em"] == opencnpj["ultima_resposta_em"]
    assert opencnpj["descricao"].startswith("OpenCNPJ")
    brasilapi = por_fonte["brasilapi"]
    assert (brasilapi["respostas"], brasilapi["falhas"]) == (1, 0)
    assert brasilapi["ultimo_resultado"] == "OBTIDO"
    assert brasilapi["ultima_falha_em"] is None
    assert brasilapi["descricao"].startswith("BrasilAPI")
    for fonte in estado["online"]:
        assert fonte["ultima_resposta_em"] is not None
        assert isinstance(fonte["latencia_mediana_ms"], int)
        assert fonte["latencia_mediana_ms"] >= 0


def test_estado_das_fontes_sem_consultas(cliente: TestClient) -> None:
    resposta = cliente.get("/api/v1/fontes")

    assert resposta.status_code == 200
    assert resposta.json()["online"] == []


def test_banco_fora_do_ar_e_503_problem_json(replay: FontesReplay, relogio: RelogioFixo) -> None:
    configuracao = Configuracao(database_url=URL_BANCO_FORA, timeout_banco_s=2)
    app = criar_app(configuracao, replay.transporte, relogio)
    with TestClient(app, backend_options=OPCOES_CLIENTE) as cliente:
        _assert_problema(cliente.post(ROTA, json={"cnpj": OKBR}), 503)
        _assert_problema(cliente.get(f"{ROTA}/{uuid.uuid4()}"), 503)
        pronto = cliente.get("/health/ready")

    assert pronto.status_code == 503
    assert replay.chamadas == []
