import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx
import structlog

from validador_osc.dominio.coleta import MotivoFalha

_STATUS_RETENTAVEIS = frozenset({429, 500, 502, 503, 504})
_ESPERA_MAXIMA_RETRY_AFTER_S = 5.0

log = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class PoliticaRetry:
    tentativas: int = 3
    espera_inicial_s: float = 0.5
    fator: float = 2.0


@dataclass(frozen=True, slots=True)
class RespostaHttp:
    url: str
    status: int
    content_type: str | None
    corpo: bytes
    recebida_em: datetime
    duracao_ms: int
    tentativas: int


@dataclass(frozen=True, slots=True)
class FalhaHttp(Exception):
    url: str
    motivo: MotivoFalha
    detalhe: str
    recebida_em: datetime
    duracao_ms: int
    tentativas: int
    status: int | None = None


def _motivo_status(status: int) -> MotivoFalha:
    if status == httpx.codes.TOO_MANY_REQUESTS:
        return MotivoFalha.HTTP_429
    if status >= httpx.codes.INTERNAL_SERVER_ERROR:
        return MotivoFalha.HTTP_5XX
    return MotivoFalha.HTTP_4XX


def _espera_retry_after(resposta: httpx.Response) -> float | None:
    valor = resposta.headers.get("retry-after")
    if valor is None:
        return None
    try:
        segundos = float(valor)
    except ValueError:
        try:
            segundos = (parsedate_to_datetime(valor) - datetime.now(UTC)).total_seconds()
        except TypeError, ValueError:
            return None
    return max(0.0, segundos)


class ClienteHttp:
    def __init__(
        self,
        cliente: httpx.AsyncClient,
        politica: PoliticaRetry | None = None,
        dormir: Callable[[float], Awaitable[object]] | None = None,
    ) -> None:
        self._cliente = cliente
        self._politica = politica or PoliticaRetry()
        self._dormir = dormir or asyncio.sleep

    async def obter(self, url: str, *, status_aceitos: frozenset[int] = frozenset({200})) -> RespostaHttp:
        inicio = time.perf_counter()
        espera = self._politica.espera_inicial_s
        ultima: FalhaHttp | None = None
        for tentativa in range(1, self._politica.tentativas + 1):
            try:
                resposta = await self._cliente.get(url)
            except httpx.TimeoutException as erro:
                ultima = self._falha(
                    url, MotivoFalha.TIMEOUT, detalhe=repr(erro), inicio=inicio, tentativas=tentativa
                )
            except httpx.TransportError as erro:
                ultima = self._falha(
                    url, MotivoFalha.CONEXAO, detalhe=repr(erro), inicio=inicio, tentativas=tentativa
                )
            else:
                if resposta.status_code in status_aceitos:
                    return RespostaHttp(
                        url=url,
                        status=resposta.status_code,
                        content_type=resposta.headers.get("content-type"),
                        corpo=resposta.content,
                        recebida_em=datetime.now(UTC),
                        duracao_ms=_ms(inicio),
                        tentativas=tentativa,
                    )
                ultima = self._falha(
                    url,
                    _motivo_status(resposta.status_code),
                    detalhe=f"HTTP {resposta.status_code}",
                    inicio=inicio,
                    tentativas=tentativa,
                    status=resposta.status_code,
                )
                if resposta.status_code not in _STATUS_RETENTAVEIS:
                    raise ultima
                retry_after = _espera_retry_after(resposta)
                if retry_after is not None:
                    if retry_after > _ESPERA_MAXIMA_RETRY_AFTER_S:
                        raise ultima
                    espera = retry_after
            log.warning("fonte_tentativa_falhou", url=url, tentativa=tentativa, motivo=ultima.motivo)
            if tentativa < self._politica.tentativas:
                await self._dormir(espera)
                espera *= self._politica.fator
        if ultima is None:
            raise RuntimeError("política de retry sem tentativas")
        raise ultima

    @staticmethod
    def _falha(
        url: str,
        motivo: MotivoFalha,
        *,
        detalhe: str,
        inicio: float,
        tentativas: int,
        status: int | None = None,
    ) -> FalhaHttp:
        return FalhaHttp(url, motivo, detalhe, datetime.now(UTC), _ms(inicio), tentativas, status)


def _ms(inicio: float) -> int:
    return int((time.perf_counter() - inicio) * 1000)
