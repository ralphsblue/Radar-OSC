from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def criar_engine_async(url: str) -> AsyncEngine:
    return create_async_engine(url, pool_pre_ping=True)


def criar_engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True)


def criar_fabrica_sessoes(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def transacao(fabrica: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with fabrica() as sessao, sessao.begin():
        yield sessao


async def banco_pronto(engine: AsyncEngine) -> bool:
    async with engine.connect() as conexao:
        versao = await conexao.scalar(text("SELECT version_num FROM alembic_version"))
    return versao is not None
