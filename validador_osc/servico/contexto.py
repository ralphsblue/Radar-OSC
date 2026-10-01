from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from validador_osc.config import Configuracao
from validador_osc.persistencia.banco import criar_engine_async, criar_fabrica_sessoes


@dataclass(frozen=True, slots=True)
class ContextoAplicacao:
    config: Configuracao
    engine: AsyncEngine
    sessoes: async_sessionmaker[AsyncSession]


@asynccontextmanager
async def abrir_contexto(config: Configuracao) -> AsyncIterator[ContextoAplicacao]:
    engine = criar_engine_async(config.url_banco)
    try:
        yield ContextoAplicacao(config, engine, criar_fabrica_sessoes(engine))
    finally:
        await engine.dispose()
