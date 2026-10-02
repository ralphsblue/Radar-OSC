import asyncio
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from typing import Any

import httpx
import pytest

from validador_osc.dominio.coleta import MotivoFalha
from validador_osc.fontes.http import ClienteHttp, FalhaHttp, PoliticaRetry, RespostaHttp

URL = "https://api.exemplo.org/recurso"

type Passo = httpx.Response | Exception


class Servidor:
    def __init__(self, passos: Sequence[Passo]) -> None:
        self._passos = list(passos)
        self.chamadas: list[httpx.Request] = []
        self.esperas: list[float] = []

    def responder(self, request: httpx.Request) -> httpx.Response:
        self.chamadas.append(request)
        passo = self._passos[min(len(self.chamadas), len(self._passos)) - 1]
        if isinstance(passo, Exception):
            raise passo
        return passo

    async def dormir(self, segundos: float) -> None:
        self.esperas.append(segundos)

    def obter(
        self,
        *,
        status_aceitos: frozenset[int] = frozenset({200}),
        politica: PoliticaRetry | None = None,
    ) -> RespostaHttp:
        async def rodar() -> RespostaHttp:
            async with httpx.AsyncClient(transport=httpx.MockTransport(self.responder)) as cliente:
                http = ClienteHttp(cliente, politica, dormir=self.dormir)
                return await http.obter(URL, status_aceitos=status_aceitos)

        return asyncio.run(rodar())

    def falhar(self, **opcoes: Any) -> FalhaHttp:
        with pytest.raises(FalhaHttp) as erro:
            self.obter(**opcoes)
        return erro.value


def resposta(
    status: int, corpo: bytes = b"", *, retry_after: str | None = None, content_type: str | None = None
) -> httpx.Response:
    cabecalhos = {
        nome: valor
        for nome, valor in (("retry-after", retry_after), ("content-type", content_type))
        if valor is not None
    }
    return httpx.Response(status, content=corpo, headers=cabecalhos)


def erro_de(fabrica: Callable[..., Exception]) -> Exception:
    return fabrica("falhou", request=httpx.Request("GET", URL))


def test_sucesso_na_primeira() -> None:
    servidor = Servidor([resposta(200, b'{"ok":true}', content_type="application/json")])
    obtida = servidor.obter()
    assert obtida.status == 200
    assert obtida.corpo == b'{"ok":true}'
    assert obtida.content_type == "application/json"
    assert obtida.url == URL
    assert obtida.tentativas == 1
    assert obtida.duracao_ms >= 0
    assert obtida.recebida_em.tzinfo is UTC
    assert len(servidor.chamadas) == 1
    assert servidor.esperas == []


def test_404_aceito_volta_como_resposta() -> None:
    servidor = Servidor([resposta(404, b'{"error":"not found"}')])
    obtida = servidor.obter(status_aceitos=frozenset({200, 404}))
    assert obtida.status == 404
    assert obtida.corpo == b'{"error":"not found"}'
    assert len(servidor.chamadas) == 1


def test_500_retenta_e_obtem_na_segunda() -> None:
    servidor = Servidor([resposta(500), resposta(200, b"ok")])
    obtida = servidor.obter()
    assert obtida.corpo == b"ok"
    assert obtida.tentativas == 2
    assert servidor.esperas == [0.5]


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_tres_falhas_5xx_desistem(status: int) -> None:
    servidor = Servidor([resposta(status)])
    falha = servidor.falhar()
    assert falha.motivo is MotivoFalha.HTTP_5XX
    assert falha.status == status
    assert falha.tentativas == 3
    assert falha.detalhe == f"HTTP {status}"
    assert falha.url == URL
    assert len(servidor.chamadas) == 3
    assert servidor.esperas == [0.5, 1.0]


def test_politica_personalizada() -> None:
    servidor = Servidor([resposta(503)])
    falha = servidor.falhar(politica=PoliticaRetry(tentativas=4, espera_inicial_s=1.0, fator=3.0))
    assert falha.tentativas == 4
    assert servidor.esperas == [1.0, 3.0, 9.0]


def test_uma_tentativa_nao_dorme() -> None:
    servidor = Servidor([resposta(500)])
    falha = servidor.falhar(politica=PoliticaRetry(tentativas=1))
    assert falha.tentativas == 1
    assert servidor.esperas == []


def test_politica_sem_tentativas_e_erro_de_programacao() -> None:
    servidor = Servidor([resposta(200)])
    with pytest.raises(RuntimeError):
        servidor.obter(politica=PoliticaRetry(tentativas=0))
    assert servidor.chamadas == []


@pytest.mark.parametrize("fabrica", [httpx.ReadTimeout, httpx.ConnectTimeout, httpx.PoolTimeout])
def test_timeout(fabrica: Callable[..., Exception]) -> None:
    servidor = Servidor([erro_de(fabrica)])
    falha = servidor.falhar()
    assert falha.motivo is MotivoFalha.TIMEOUT
    assert falha.status is None
    assert falha.tentativas == 3
    assert "falhou" in falha.detalhe


@pytest.mark.parametrize("fabrica", [httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadError])
def test_erro_de_conexao(fabrica: Callable[..., Exception]) -> None:
    servidor = Servidor([erro_de(fabrica)])
    falha = servidor.falhar()
    assert falha.motivo is MotivoFalha.CONEXAO
    assert falha.tentativas == 3
    assert len(servidor.chamadas) == 3


def test_timeout_seguido_de_sucesso() -> None:
    servidor = Servidor([erro_de(httpx.ReadTimeout), resposta(200, b"ok")])
    assert servidor.obter().tentativas == 2


@pytest.mark.parametrize("status", [400, 401, 403, 404, 410, 422])
def test_4xx_nao_retenta(status: int) -> None:
    servidor = Servidor([resposta(status)])
    falha = servidor.falhar()
    assert falha.motivo is MotivoFalha.HTTP_4XX
    assert falha.status == status
    assert falha.tentativas == 1
    assert len(servidor.chamadas) == 1
    assert servidor.esperas == []


def test_429_com_retry_after_curto_espera_o_pedido() -> None:
    servidor = Servidor([resposta(429, retry_after="2"), resposta(200, b"ok")])
    obtida = servidor.obter()
    assert obtida.tentativas == 2
    assert servidor.esperas == [2.0]


def test_429_com_retry_after_no_limite_ainda_espera() -> None:
    servidor = Servidor([resposta(429, retry_after="5"), resposta(200)])
    servidor.obter()
    assert servidor.esperas == [5.0]


def test_429_sem_retry_after_usa_backoff_e_desiste() -> None:
    servidor = Servidor([resposta(429)])
    falha = servidor.falhar()
    assert falha.motivo is MotivoFalha.HTTP_429
    assert falha.tentativas == 3
    assert servidor.esperas == [0.5, 1.0]


@pytest.mark.parametrize("status", [429, 503])
def test_retry_after_longo_desiste_na_hora(status: int) -> None:
    servidor = Servidor([resposta(status, retry_after="5.5"), resposta(200)])
    falha = servidor.falhar()
    assert falha.status == status
    assert falha.tentativas == 1
    assert len(servidor.chamadas) == 1
    assert servidor.esperas == []


def test_retry_after_negativo_vira_zero() -> None:
    servidor = Servidor([resposta(429, retry_after="-3"), resposta(200)])
    servidor.obter()
    assert servidor.esperas == [0.0]


def test_retry_after_invalido_usa_backoff() -> None:
    servidor = Servidor([resposta(503, retry_after="logo mais"), resposta(200)])
    servidor.obter()
    assert servidor.esperas == [0.5]


def test_retry_after_em_data_http_curta() -> None:
    quando = format_datetime(datetime.now(UTC) + timedelta(seconds=4), usegmt=True)
    servidor = Servidor([resposta(429, retry_after=quando), resposta(200)])
    servidor.obter()
    assert len(servidor.esperas) == 1
    assert 2.0 < servidor.esperas[0] <= 4.0


def test_retry_after_em_data_http_passada_vira_zero() -> None:
    quando = format_datetime(datetime.now(UTC) - timedelta(minutes=1), usegmt=True)
    servidor = Servidor([resposta(503, retry_after=quando), resposta(200)])
    servidor.obter()
    assert servidor.esperas == [0.0]


def test_retry_after_em_data_http_longa_desiste() -> None:
    quando = format_datetime(datetime.now(UTC) + timedelta(minutes=2), usegmt=True)
    servidor = Servidor([resposta(429, retry_after=quando), resposta(200)])
    falha = servidor.falhar()
    assert falha.motivo is MotivoFalha.HTTP_429
    assert len(servidor.chamadas) == 1


def test_backoff_continua_depois_do_retry_after() -> None:
    servidor = Servidor([resposta(429, retry_after="1"), resposta(500), resposta(200)])
    servidor.obter()
    assert servidor.esperas == [1.0, 2.0]


def test_dormir_padrao_e_asyncio_sleep() -> None:
    async def rodar() -> RespostaHttp:
        servidor = Servidor([resposta(500), resposta(200)])
        politica = PoliticaRetry(espera_inicial_s=0.0)
        async with httpx.AsyncClient(transport=httpx.MockTransport(servidor.responder)) as cliente:
            return await ClienteHttp(cliente, politica).obter(URL)

    assert asyncio.run(rodar()).tentativas == 2


def _timeout_enviado(cliente_timeout: httpx.Timeout, timeout: httpx.Timeout | None) -> dict[str, float]:
    enviados: list[dict[str, float]] = []

    def responder(request: httpx.Request) -> httpx.Response:
        enviados.append(request.extensions["timeout"])
        return httpx.Response(200)

    async def rodar() -> None:
        transporte = httpx.MockTransport(responder)
        async with httpx.AsyncClient(transport=transporte, timeout=cliente_timeout) as cliente:
            await ClienteHttp(cliente, timeout=timeout).obter(URL)

    asyncio.run(rodar())
    [enviado] = enviados
    return enviado


def test_sem_timeout_proprio_usa_o_do_cliente() -> None:
    enviado = _timeout_enviado(httpx.Timeout(12.0, connect=5.0), None)
    assert enviado == {"connect": 5.0, "read": 12.0, "write": 12.0, "pool": 12.0}


def test_timeout_proprio_substitui_o_do_cliente() -> None:
    enviado = _timeout_enviado(httpx.Timeout(12.0, connect=5.0), httpx.Timeout(15.0, connect=4.0))
    assert enviado == {"connect": 4.0, "read": 15.0, "write": 15.0, "pool": 15.0}
