import uuid
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from validador_osc.api.dependencias import (
    MENSAGEM_LIMITE,
    VERSAO,
    Contexto,
    Servico,
    Templates,
    excedeu_limite,
)
from validador_osc.api.privacidade import ocultar_dirigentes
from validador_osc.dominio.consulta import Esfera
from validador_osc.servico.consulta import PedidoConsulta

rotas = APIRouter(include_in_schema=False)


@rotas.get("/favicon.ico")
async def favicon() -> RedirectResponse:
    return RedirectResponse(f"/static/favicon.svg?v={VERSAO}", status_code=301)


@rotas.get("/", response_class=HTMLResponse)
async def inicio(request: Request, templates: Templates) -> HTMLResponse:
    return templates.TemplateResponse(request, "inicio.html", {"versao": VERSAO})


@rotas.get("/fontes", response_class=HTMLResponse)
async def pagina_fontes(request: Request, contexto: Contexto, templates: Templates) -> HTMLResponse:
    estado = await contexto.fontes.estado()
    return templates.TemplateResponse(request, "fontes.html", {"versao": VERSAO, "estado": estado})


@rotas.post("/consultas")
async def consultar_pela_pagina(
    request: Request,
    servico: Servico,
    templates: Templates,
    cnpj: Annotated[str, Form(max_length=32)],
    esfera: Annotated[str, Form()] = "",
) -> Response:
    if excedeu_limite(request):
        contexto = {"versao": VERSAO, "erro_geral": MENSAGEM_LIMITE}
        return templates.TemplateResponse(request, "inicio.html", contexto, status_code=429)
    esfera_escolhida = Esfera(esfera) if esfera in {e.value for e in Esfera} else None
    feita = await servico.executar(PedidoConsulta(cnpj, esfera_escolhida))
    return RedirectResponse(f"/consultas/{feita.documento['id']}", status_code=303)


@rotas.get("/consultas/{consulta_id}", response_class=HTMLResponse)
async def pagina_consulta(
    request: Request, consulta_id: uuid.UUID, servico: Servico, templates: Templates
) -> HTMLResponse:
    documento = await servico.obter(consulta_id)
    if documento is None:
        return templates.TemplateResponse(request, "inicio.html", {"versao": VERSAO}, status_code=404)
    contexto = {
        "versao": VERSAO,
        "consulta": ocultar_dirigentes(documento),
        "link_permanente": str(request.url),
    }
    return templates.TemplateResponse(request, "resultado.html", contexto)
