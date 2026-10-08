from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from validador_osc.api.esquemas import Problema
from validador_osc.api.limite import LimitePorCliente
from validador_osc.api.privacidade import eh_operador, ocultar_dirigentes
from validador_osc.composicao import VERSAO_APP, ContextoAplicacao
from validador_osc.servico.consulta import ServicoConsulta

TIPO_PROBLEMA = "application/problem+json"
MENSAGEM_LIMITE = "Muitas consultas seguidas. Aguarde um minuto e tente de novo."
VERSAO = VERSAO_APP


def problema(status: int, titulo: str, detalhe: str | None = None) -> JSONResponse:
    corpo = Problema(title=titulo, status=status, detail=detalhe)
    return JSONResponse(corpo.model_dump(), status_code=status, media_type=TIPO_PROBLEMA)


def obter_contexto(request: Request) -> ContextoAplicacao:
    contexto: ContextoAplicacao = request.app.state.contexto
    return contexto


def obter_servico(request: Request) -> ServicoConsulta:
    return obter_contexto(request).consultas


def obter_templates(request: Request) -> Jinja2Templates:
    templates: Jinja2Templates = request.app.state.templates
    return templates


Contexto = Annotated[ContextoAplicacao, Depends(obter_contexto)]
Servico = Annotated[ServicoConsulta, Depends(obter_servico)]
Templates = Annotated[Jinja2Templates, Depends(obter_templates)]


def excedeu_limite(request: Request) -> bool:
    limite: LimitePorCliente = request.app.state.limite
    cliente = request.client.host if request.client else "desconhecido"
    return not limite.permitir(cliente)


def operador(request: Request, token: str | None) -> bool:
    return eh_operador(token, obter_contexto(request).config.token_operador)


def visivel(request: Request, documento: dict[str, Any], token: str | None) -> dict[str, Any]:
    return documento if operador(request, token) else ocultar_dirigentes(documento)
