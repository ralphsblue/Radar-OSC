import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from importlib.resources import files
from typing import Annotated, Any

import httpx
import structlog
from fastapi import Depends, FastAPI, Form, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import DBAPIError

from validador_osc.api.esquemas import PedidoConsultaApi, Problema
from validador_osc.api.formatacao import registrar_filtros
from validador_osc.config import Configuracao, obter_configuracao
from validador_osc.dominio.resultado import Esfera
from validador_osc.logs import configurar_logs
from validador_osc.servico.consulta import PedidoConsulta, ServicoConsulta
from validador_osc.servico.contexto import VERSAO_APP, ContextoAplicacao, abrir_contexto
from validador_osc.servico.saude import verificar_prontidao

_RECURSOS = files("validador_osc.api")
_TIPO_PROBLEMA = "application/problem+json"
VERSAO = VERSAO_APP

log = structlog.get_logger()


def _problema(status: int, titulo: str, detalhe: str | None = None) -> JSONResponse:
    corpo = Problema(title=titulo, status=status, detail=detalhe)
    return JSONResponse(corpo.model_dump(), status_code=status, media_type=_TIPO_PROBLEMA)


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

    def obter_contexto(request: Request) -> ContextoAplicacao:
        contexto: ContextoAplicacao = request.app.state.contexto
        return contexto

    def obter_servico(request: Request) -> ServicoConsulta:
        return obter_contexto(request).consultas

    Contexto = Annotated[ContextoAplicacao, Depends(obter_contexto)]
    Servico = Annotated[ServicoConsulta, Depends(obter_servico)]

    @app.exception_handler(DBAPIError)
    async def banco_indisponivel(request: Request, erro: DBAPIError) -> JSONResponse:
        log.error("banco_indisponivel", rota=request.url.path, erro=type(erro.orig).__name__)
        return _problema(503, "Serviço indisponível", "O banco de dados não está acessível.")

    @app.exception_handler(RequestValidationError)
    async def corpo_invalido(request: Request, erro: RequestValidationError) -> JSONResponse:
        del request
        return _problema(422, "Requisição inválida", str(erro.errors()))

    @app.get("/health", include_in_schema=False)
    async def saude() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", include_in_schema=False)
    async def prontidao(contexto: Contexto) -> JSONResponse:
        pronto = await verificar_prontidao(contexto.engine)
        return JSONResponse(
            {"status": "ok" if pronto else "indisponivel"}, status_code=200 if pronto else 503
        )

    @app.post("/api/v1/consultas", status_code=201, tags=["consultas"])
    async def criar_consulta(
        pedido: PedidoConsultaApi,
        servico: Servico,
        response: Response,
        idempotency_key: Annotated[str | None, Header(max_length=128)] = None,
    ) -> dict[str, Any]:
        feita = await servico.executar(
            PedidoConsulta(pedido.cnpj, pedido.esfera, pedido.atualizar, idempotency_key)
        )
        response.headers["Location"] = f"/api/v1/consultas/{feita.documento['id']}"
        if not feita.nova:
            response.status_code = 200
        return feita.documento

    @app.get("/api/v1/consultas/{consulta_id}", tags=["consultas"], response_model=None)
    async def ler_consulta(consulta_id: uuid.UUID, servico: Servico) -> dict[str, Any] | JSONResponse:
        documento = await servico.obter(consulta_id)
        if documento is None:
            return _problema(404, "Consulta não encontrada")
        return documento

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def inicio(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "inicio.html", {"versao": VERSAO})

    @app.post("/consultas", include_in_schema=False)
    async def consultar_pela_pagina(
        servico: Servico,
        cnpj: Annotated[str, Form(max_length=32)],
        esfera: Annotated[str, Form()] = "",
    ) -> RedirectResponse:
        esfera_escolhida = Esfera(esfera) if esfera in {e.value for e in Esfera} else None
        feita = await servico.executar(PedidoConsulta(cnpj, esfera_escolhida))
        return RedirectResponse(f"/consultas/{feita.documento['id']}", status_code=303)

    @app.get("/consultas/{consulta_id}", response_class=HTMLResponse, include_in_schema=False)
    async def pagina_consulta(request: Request, consulta_id: uuid.UUID, servico: Servico) -> HTMLResponse:
        documento = await servico.obter(consulta_id)
        if documento is None:
            return templates.TemplateResponse(request, "inicio.html", {"versao": VERSAO}, status_code=404)
        return templates.TemplateResponse(
            request,
            "resultado.html",
            {"versao": VERSAO, "consulta": documento, "link_permanente": str(request.url)},
        )

    return app
