import uuid
from collections import Counter
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from validador_osc.api.dependencias import (
    COOKIE_TOKEN,
    MENSAGEM_LIMITE,
    VERSAO,
    Contexto,
    Servico,
    Templates,
    UsuarioOpcional,
    excedeu_limite,
)
from validador_osc.api.privacidade import ocultar_dirigentes
from validador_osc.dominio.consulta import Esfera
from validador_osc.servico.auth import Credenciais, CredenciaisInvalidas, EmailJaCadastrado
from validador_osc.servico.consulta import PedidoConsulta
from validador_osc.servico.lotes import LimiteLoteExcedido, PedidoLote, dividir_cnpjs

rotas = APIRouter(include_in_schema=False)


@rotas.get("/favicon.ico")
async def favicon() -> RedirectResponse:
    return RedirectResponse(f"/static/favicon.svg?v={VERSAO}", status_code=301)


@rotas.get("/", response_class=HTMLResponse)
async def inicio(request: Request, templates: Templates, usuario: UsuarioOpcional) -> HTMLResponse:
    return templates.TemplateResponse(request, "inicio.html", {"versao": VERSAO, "usuario": usuario})


@rotas.get("/fontes", response_class=HTMLResponse)
async def pagina_fontes(
    request: Request, contexto: Contexto, templates: Templates, usuario: UsuarioOpcional
) -> HTMLResponse:
    estado = await contexto.fontes.estado()
    contexto_pagina = {"versao": VERSAO, "estado": estado, "usuario": usuario}
    return templates.TemplateResponse(request, "fontes.html", contexto_pagina)


@rotas.post("/consultas")
async def consultar_pela_pagina(
    request: Request,
    servico: Servico,
    templates: Templates,
    usuario: UsuarioOpcional,
    cnpj: Annotated[str, Form(max_length=32)],
    esfera: Annotated[str, Form()] = "",
) -> Response:
    if excedeu_limite(request):
        contexto = {"versao": VERSAO, "usuario": usuario, "erro_geral": MENSAGEM_LIMITE}
        return templates.TemplateResponse(request, "inicio.html", contexto, status_code=429)
    esfera_escolhida = Esfera(esfera) if esfera in {e.value for e in Esfera} else None
    feita = await servico.executar(PedidoConsulta(cnpj, esfera_escolhida))
    return RedirectResponse(f"/consultas/{feita.documento['id']}", status_code=303)


@rotas.get("/consultas/{consulta_id}", response_class=HTMLResponse)
async def pagina_consulta(
    request: Request, consulta_id: uuid.UUID, servico: Servico, templates: Templates, usuario: UsuarioOpcional
) -> HTMLResponse:
    documento = await servico.obter(consulta_id)
    if documento is None:
        contexto_ausente = {"versao": VERSAO, "usuario": usuario}
        return templates.TemplateResponse(request, "inicio.html", contexto_ausente, status_code=404)
    contexto = {
        "versao": VERSAO,
        "usuario": usuario,
        "consulta": ocultar_dirigentes(documento),
        "link_permanente": str(request.url),
    }
    return templates.TemplateResponse(request, "resultado.html", contexto)


def _definir_cookie_sessao(resposta: Response, token: str, expiracao_min: int) -> None:
    resposta.set_cookie(
        COOKIE_TOKEN,
        token,
        max_age=expiracao_min * 60,
        httponly=True,
        samesite="lax",
        path="/",
    )


@rotas.get("/entrar", response_class=HTMLResponse)
async def pagina_entrar(request: Request, templates: Templates, usuario: UsuarioOpcional) -> Response:
    if usuario is not None:
        return RedirectResponse("/painel", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"versao": VERSAO, "usuario": None})


@rotas.post("/entrar")
async def entrar(
    request: Request,
    contexto: Contexto,
    templates: Templates,
    email: Annotated[str, Form(max_length=255)],
    senha: Annotated[str, Form(max_length=128)],
) -> Response:
    try:
        emitido = await contexto.auth.autenticar(Credenciais(email, senha))
    except CredenciaisInvalidas:
        contexto_pagina = {
            "versao": VERSAO,
            "usuario": None,
            "erro_geral": "E-mail ou senha incorretos.",
            "email_digitado": email,
        }
        return templates.TemplateResponse(request, "login.html", contexto_pagina, status_code=401)
    resposta = RedirectResponse("/painel", status_code=303)
    _definir_cookie_sessao(resposta, emitido.token, contexto.config.jwt_expiracao_min)
    return resposta


@rotas.get("/registrar", response_class=HTMLResponse)
async def pagina_registrar(request: Request, templates: Templates, usuario: UsuarioOpcional) -> Response:
    if usuario is not None:
        return RedirectResponse("/painel", status_code=303)
    return templates.TemplateResponse(request, "registrar.html", {"versao": VERSAO, "usuario": None})


@rotas.post("/registrar")
async def registrar(
    request: Request,
    contexto: Contexto,
    templates: Templates,
    email: Annotated[str, Form(max_length=255)],
    senha: Annotated[str, Form(min_length=8, max_length=128)],
) -> Response:
    try:
        emitido = await contexto.auth.registrar(Credenciais(email, senha))
    except EmailJaCadastrado:
        contexto_pagina = {
            "versao": VERSAO,
            "usuario": None,
            "erro_geral": "Já existe uma conta com esse e-mail.",
            "email_digitado": email,
        }
        return templates.TemplateResponse(request, "registrar.html", contexto_pagina, status_code=409)
    resposta = RedirectResponse("/painel", status_code=303)
    _definir_cookie_sessao(resposta, emitido.token, contexto.config.jwt_expiracao_min)
    return resposta


@rotas.post("/sair")
async def sair() -> Response:
    resposta = RedirectResponse("/", status_code=303)
    resposta.delete_cookie(COOKIE_TOKEN, path="/")
    return resposta


@rotas.get("/painel", response_class=HTMLResponse)
async def pagina_painel(
    request: Request, contexto: Contexto, templates: Templates, usuario: UsuarioOpcional
) -> Response:
    if usuario is None:
        return RedirectResponse("/entrar", status_code=303)
    metricas = await contexto.lotes.metricas(usuario.id)
    lotes = await contexto.lotes.listar(usuario.id)
    total_impedimentos = sum(metricas.impedimentos_por_tipo.values())
    maior_impedimento = max(metricas.impedimentos_por_tipo.values(), default=0)
    contexto_pagina = {
        "versao": VERSAO,
        "usuario": usuario,
        "metricas": metricas,
        "lotes": lotes,
        "total_impedimentos": total_impedimentos,
        "maior_impedimento": maior_impedimento,
    }
    return templates.TemplateResponse(request, "painel.html", contexto_pagina)


@rotas.get("/lotes/novo", response_class=HTMLResponse)
async def pagina_lote_novo(request: Request, templates: Templates, usuario: UsuarioOpcional) -> Response:
    if usuario is None:
        return RedirectResponse("/entrar", status_code=303)
    return templates.TemplateResponse(request, "lotes_novo.html", {"versao": VERSAO, "usuario": usuario})


@rotas.post("/lotes")
async def criar_lote_pela_pagina(
    request: Request,
    contexto: Contexto,
    templates: Templates,
    usuario: UsuarioOpcional,
    cnpjs: Annotated[str, Form()],
    esfera: Annotated[str, Form()] = "",
) -> Response:
    if usuario is None:
        return RedirectResponse("/entrar", status_code=303)
    esfera_escolhida = Esfera(esfera) if esfera in {e.value for e in Esfera} else None
    pedido = PedidoLote(
        usuario_id=usuario.id,
        esfera=esfera_escolhida.value if esfera_escolhida else None,
        cnpjs=dividir_cnpjs(cnpjs),
    )
    try:
        lote_id = await contexto.lotes.criar(pedido)
    except LimiteLoteExcedido:
        contexto_pagina = {
            "versao": VERSAO,
            "usuario": usuario,
            "erro_geral": "O lote excede o limite de 20 CNPJs.",
            "cnpjs_digitado": cnpjs,
            "esfera_escolhida": esfera,
        }
        return templates.TemplateResponse(request, "lotes_novo.html", contexto_pagina, status_code=400)
    return RedirectResponse(f"/lotes/{lote_id}", status_code=303)


@rotas.get("/lotes/{lote_id}", response_class=HTMLResponse)
async def pagina_lote(
    request: Request, lote_id: uuid.UUID, contexto: Contexto, templates: Templates, usuario: UsuarioOpcional
) -> Response:
    if usuario is None:
        return RedirectResponse("/entrar", status_code=303)
    detalhe = await contexto.lotes.obter(lote_id, usuario.id)
    if detalhe is None:
        contexto_ausente = {"versao": VERSAO, "usuario": usuario}
        return templates.TemplateResponse(request, "inicio.html", contexto_ausente, status_code=404)
    linhas = await contexto.lotes.exportar_linhas(lote_id, usuario.id) or []
    linhas_itens = list(zip(detalhe.itens, linhas, strict=True))
    contagens_item = Counter(item.status for item in detalhe.itens)
    contagens_final = Counter(
        linha.status_consulta
        for item, linha in linhas_itens
        if item.status == "CONCLUIDO" and linha.status_consulta
    )
    contexto_pagina = {
        "versao": VERSAO,
        "usuario": usuario,
        "lote": detalhe,
        "linhas_itens": linhas_itens,
        "contagens_item": contagens_item,
        "contagens_final": contagens_final,
    }
    return templates.TemplateResponse(request, "lotes_detalhe.html", contexto_pagina)
