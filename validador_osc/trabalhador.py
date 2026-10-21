import asyncio
import selectors
import sys
import uuid
from collections.abc import Callable
from typing import Protocol

import structlog

from validador_osc.composicao import abrir_contexto
from validador_osc.config import obter_configuracao
from validador_osc.dominio.consulta import Esfera
from validador_osc.servico.consulta import ConsultaFeita, PedidoConsulta
from validador_osc.servico.lotes import ServicoLotes

log = structlog.get_logger()


class FonteConsulta(Protocol):
    async def executar(self, pedido: PedidoConsulta) -> ConsultaFeita: ...


class ContextoTrabalhador(Protocol):
    @property
    def consultas(self) -> FonteConsulta: ...

    @property
    def lotes(self) -> ServicoLotes: ...


async def _processar_item_async(contexto: ContextoTrabalhador, lote_id: uuid.UUID, item_id: int) -> None:
    item = await contexto.lotes.obter_item(item_id)
    if item is None:
        return
    await contexto.lotes.marcar_item(item_id, status="PROCESSANDO")
    try:
        esfera = Esfera(item.esfera) if item.esfera else None
        feita = await contexto.consultas.executar(PedidoConsulta(cnpj=item.cnpj_informado, esfera=esfera))
        await contexto.lotes.marcar_item(
            item_id, status="CONCLUIDO", consulta_id=uuid.UUID(feita.documento["id"])
        )
    except Exception as erro:
        log.exception("item_lote_falhou", lote_id=str(lote_id), item_id=item_id, erro=repr(erro))
        await contexto.lotes.marcar_item(item_id, status="ERRO", erro=str(erro))
    finally:
        await contexto.lotes.recalcular_status_lote(lote_id)


async def _processar_item_lote_async(lote_id: str, item_id: int) -> None:
    config = obter_configuracao()
    async with abrir_contexto(config) as contexto:
        await _processar_item_async(contexto, uuid.UUID(lote_id), item_id)


def _fabrica_loop_selector() -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop(selectors.SelectSelector())


def processar_item_lote(lote_id: str, item_id: int) -> None:
    # Se o processo do worker morrer no meio (crash, não exceção Python), o item
    # fica PROCESSANDO pra sempre - gap conhecido, aceito nesta fase.
    # No Windows, o driver async do psycopg não roda sobre o ProactorEventLoop
    # (padrão do asyncio), então precisamos forçar um SelectorEventLoop - mesmo
    # motivo pelo qual `cli.py:_servir` passa esse loop pro uvicorn.
    fabrica_loop: Callable[[], asyncio.AbstractEventLoop] | None = (
        _fabrica_loop_selector if sys.platform == "win32" else None
    )
    asyncio.run(_processar_item_lote_async(lote_id, item_id), loop_factory=fabrica_loop)
