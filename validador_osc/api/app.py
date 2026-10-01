from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version
from importlib.resources import files
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from validador_osc.api.formatacao import registrar_filtros
from validador_osc.config import Configuracao, obter_configuracao
from validador_osc.logs import configurar_logs
from validador_osc.servico.contexto import ContextoAplicacao, abrir_contexto
from validador_osc.servico.saude import verificar_prontidao

_RECURSOS = files("validador_osc.api")
VERSAO = version("validador-osc")


def criar_app(config: Configuracao | None = None) -> FastAPI:
    configuracao = config or obter_configuracao()
    configurar_logs(configuracao)

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
        async with abrir_contexto(configuracao) as contexto:
            app.state.contexto = contexto
            yield

    app = FastAPI(title="Validador de OSC", version=VERSAO, lifespan=ciclo_de_vida)
    app.mount("/static", StaticFiles(directory=str(_RECURSOS / "static")), name="static")
    templates = Jinja2Templates(directory=str(_RECURSOS / "templates"))
    registrar_filtros(templates.env, configuracao.zona)

    def obter_contexto(request: Request) -> ContextoAplicacao:
        contexto: ContextoAplicacao = request.app.state.contexto
        return contexto

    Contexto = Annotated[ContextoAplicacao, Depends(obter_contexto)]

    @app.get("/health", include_in_schema=False)
    async def saude() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", include_in_schema=False)
    async def prontidao(contexto: Contexto) -> JSONResponse:
        pronto = await verificar_prontidao(contexto.engine)
        return JSONResponse(
            {"status": "ok" if pronto else "indisponivel"}, status_code=200 if pronto else 503
        )

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def inicio(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "inicio.html", {"versao": VERSAO})

    return app
