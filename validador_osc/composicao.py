import hashlib
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from importlib.metadata import version
from importlib.resources import files

import httpx
import redis
import rq
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from validador_osc.config import Configuracao
from validador_osc.fontes.brasilapi import POLITICA_RETRY as RETRY_BRASILAPI
from validador_osc.fontes.brasilapi import FonteBrasilApi
from validador_osc.fontes.http import ClienteHttp
from validador_osc.fontes.mapa_osc import FonteMapaOsc
from validador_osc.fontes.opencnpj import FonteOpenCnpj
from validador_osc.fontes.tcu import POLITICA_RETRY as RETRY_TCU
from validador_osc.fontes.tcu import TIMEOUT as TIMEOUT_TCU
from validador_osc.fontes.tcu import FonteTcu
from validador_osc.persistencia.banco import criar_engine_async, criar_fabrica_sessoes
from validador_osc.persistencia.bases import RepositorioBasesLocais
from validador_osc.persistencia.repositorios import (
    RepositorioConsultas,
    RepositorioEvidencias,
    RepositorioLotes,
    RepositorioSaudeFontes,
    RepositorioUsuarios,
)
from validador_osc.regras import carregar_limites, carregar_tabelas
from validador_osc.servico.auth import ServicoAuth
from validador_osc.servico.cadastral import CadastralComReserva
from validador_osc.servico.consulta import Coletores, ServicoConsulta
from validador_osc.servico.dirigentes import ColetorDirigentes
from validador_osc.servico.evidencias import ServicoEvidencias
from validador_osc.servico.fontes import ServicoFontes
from validador_osc.servico.lotes import ServicoLotes
from validador_osc.servico.sancoes import ColetorSancoes

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
    fontes: ServicoFontes
    evidencias: ServicoEvidencias
    auth: ServicoAuth
    lotes: ServicoLotes


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
        http = ClienteHttp(cliente)
        servico = ServicoConsulta(
            coletores=Coletores(
                cadastral=CadastralComReserva(
                    FonteOpenCnpj(http, evidencias, relogio=relogio),
                    FonteBrasilApi(ClienteHttp(cliente, RETRY_BRASILAPI), evidencias, relogio=relogio),
                ),
                sancoes=ColetorSancoes(
                    FonteTcu(
                        ClienteHttp(cliente, RETRY_TCU, timeout=TIMEOUT_TCU), evidencias, relogio=relogio
                    ),
                    RepositorioBasesLocais(sessoes),
                ),
                mapa=FonteMapaOsc(ClienteHttp(cliente), evidencias, relogio=relogio),
                dirigentes=ColetorDirigentes(RepositorioBasesLocais(sessoes)),
            ),
            consultas=RepositorioConsultas(sessoes),
            tabelas=carregar_tabelas(),
            zona=config.zona,
            versao_app=VERSAO_APP,
            versao_regras=calcular_versao_regras(),
            relogio=relogio,
            prazo=timedelta(seconds=config.prazo_consulta_s),
        )
        try:
            fontes = ServicoFontes(
                RepositorioSaudeFontes(sessoes),
                RepositorioBasesLocais(sessoes),
                carregar_limites(),
                config.zona,
                relogio,
            )
            auth = ServicoAuth(RepositorioUsuarios(sessoes), config.jwt_segredo, config.jwt_expiracao_min)
            conexao_redis = redis.Redis.from_url(config.redis_url)
            fila = rq.Queue(config.fila_nome, connection=conexao_redis)

            def enfileirar(lote_id: uuid.UUID, item_id: int) -> None:
                # Passa o nome da função (string) em vez de importar `processar_item_lote`
                # direto: o módulo `validador_osc.trabalhador` só existe a partir da Fase 4
                # e importá-lo aqui criaria uma dependência de um módulo ainda inexistente.
                fila.enqueue("validador_osc.trabalhador.processar_item_lote", str(lote_id), item_id)

            lotes = ServicoLotes(
                RepositorioLotes(sessoes), enfileirar, relogio, RepositorioConsultas(sessoes)
            )
            yield ContextoAplicacao(
                config, engine, sessoes, servico, fontes, ServicoEvidencias(evidencias), auth, lotes
            )
        finally:
            await engine.dispose()
