from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from importlib.resources import files

import httpx
import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError

from validador_osc.api import rotas_json, rotas_paginas
from validador_osc.api.dependencias import VERSAO, problema
from validador_osc.api.formatacao import registrar_filtros
from validador_osc.api.limite import LimitePorCliente
from validador_osc.config import Configuracao, obter_configuracao
from validador_osc.logs import configurar_logs
from validador_osc.servico.contexto import abrir_contexto

_RECURSOS = files("validador_osc.api")

log = structlog.get_logger()


async def _erro_banco(request: Request, erro: Exception) -> JSONResponse:
    origem = type(getattr(erro, "orig", erro)).__name__
    if isinstance(erro, OperationalError | InterfaceError):
        log.error("banco_indisponivel", rota=request.url.path, erro=origem)
        return problema(503, "Serviço indisponível", "O banco de dados não está acessível.")
    log.exception("erro_banco", rota=request.url.path, erro=origem)
    return problema(500, "Erro interno", "Falha inesperada ao gravar ou ler dados.")


async def _corpo_invalido(request: Request, erro: Exception) -> JSONResponse:
    del request
    detalhe = str(erro.errors()) if isinstance(erro, RequestValidationError) else str(erro)
    return problema(422, "Requisição inválida", detalhe)


def criar_app(
    config: Configuracao | None = None,
    transporte: httpx.AsyncBaseTransport | None = None,
    relogio: Callable[[], datetime] | None = None,
) -> FastAPI:
    configuracao = config or obter_configuracao()
    configurar_logs(configuracao)

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
        async with abrir_contexto(configuracao, transporte, relogio) as contexto:
            app.state.contexto = contexto
            yield

    app = FastAPI(title="Validador de OSC", version=VERSAO, lifespan=ciclo_de_vida)
    app.mount("/static", StaticFiles(directory=str(_RECURSOS / "static")), name="static")
    templates = Jinja2Templates(directory=str(_RECURSOS / "templates"))
    registrar_filtros(templates.env, configuracao.zona)
    app.state.templates = templates
    app.state.limite = LimitePorCliente(configuracao.limite_consultas_por_minuto)
    app.add_exception_handler(DBAPIError, _erro_banco)
    app.add_exception_handler(RequestValidationError, _corpo_invalido)
    app.include_router(rotas_json.rotas)
    app.include_router(rotas_paginas.rotas)
    return app
