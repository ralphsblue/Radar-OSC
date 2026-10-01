import hashlib
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from importlib.metadata import version
from importlib.resources import files

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from validador_osc.config import Configuracao
from validador_osc.fontes.http import ClienteHttp
from validador_osc.fontes.opencnpj import FonteOpenCnpj
from validador_osc.persistencia.banco import criar_engine_async, criar_fabrica_sessoes
from validador_osc.persistencia.repositorios import RepositorioConsultas, RepositorioEvidencias
from validador_osc.regras.tabelas import carregar_tabelas
from validador_osc.servico.consulta import ServicoConsulta

VERSAO_APP = version("validador-osc")


def calcular_versao_regras() -> str:
    resumo = hashlib.sha256()
    dados = files("validador_osc").joinpath("dados")
    for arquivo in sorted(dados.iterdir(), key=lambda a: a.name):
        if arquivo.name.endswith(".json"):
            resumo.update(arquivo.name.encode())
            resumo.update(arquivo.read_bytes())
    return f"sha256:{resumo.hexdigest()}"


@dataclass(frozen=True, slots=True)
class ContextoAplicacao:
    config: Configuracao
    engine: AsyncEngine
    sessoes: async_sessionmaker[AsyncSession]
    consultas: ServicoConsulta


@asynccontextmanager
async def abrir_contexto(
    config: Configuracao,
    transporte: httpx.AsyncBaseTransport | None = None,
    relogio: Callable[[], datetime] | None = None,
) -> AsyncIterator[ContextoAplicacao]:
    engine = criar_engine_async(config.url_banco, config.timeout_banco_s)
    sessoes = criar_fabrica_sessoes(engine)
    timeout = httpx.Timeout(config.timeout_fonte_s, connect=5.0)
    async with httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": config.user_agent},
        follow_redirects=True,
        transport=transporte,
    ) as cliente:
        evidencias = RepositorioEvidencias(sessoes)
        servico = ServicoConsulta(
            cadastral=FonteOpenCnpj(ClienteHttp(cliente), evidencias, relogio=relogio),
            consultas=RepositorioConsultas(sessoes),
            tabelas=carregar_tabelas(),
            zona=config.zona,
            versao_app=VERSAO_APP,
            versao_regras=calcular_versao_regras(),
            relogio=relogio,
        )
        try:
            yield ContextoAplicacao(config, engine, sessoes, servico)
        finally:
            await engine.dispose()
