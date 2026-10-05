import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse, Response

from validador_osc.api.dependencias import (
    MENSAGEM_LIMITE,
    Contexto,
    Servico,
    excedeu_limite,
    operador,
    problema,
    visivel,
)
from validador_osc.api.esquemas import PedidoConsultaApi
from validador_osc.servico.consulta import PedidoConsulta
from validador_osc.servico.saude import verificar_prontidao

rotas = APIRouter()
TokenOperador = Annotated[str | None, Header()]


@rotas.get("/health", include_in_schema=False)
async def saude() -> dict[str, str]:
    return {"status": "ok"}


@rotas.get("/health/ready", include_in_schema=False)
async def prontidao(contexto: Contexto) -> JSONResponse:
    pronto = await verificar_prontidao(contexto.engine)
    return JSONResponse({"status": "ok" if pronto else "indisponivel"}, status_code=200 if pronto else 503)


@rotas.post("/api/v1/consultas", status_code=201, tags=["consultas"], response_model=None)
async def criar_consulta(
    pedido: PedidoConsultaApi,
    servico: Servico,
    response: Response,
    request: Request,
    idempotency_key: Annotated[str | None, Header(max_length=128)] = None,
    x_token_operador: TokenOperador = None,
) -> dict[str, Any] | JSONResponse:
    if excedeu_limite(request):
        return problema(429, "Muitas consultas", MENSAGEM_LIMITE)
    feita = await servico.executar(
        PedidoConsulta(pedido.cnpj, pedido.esfera, pedido.atualizar, idempotency_key)
    )
    response.headers["Location"] = f"/api/v1/consultas/{feita.documento['id']}"
    if not feita.nova:
        response.status_code = 200
    return visivel(request, feita.documento, x_token_operador)


@rotas.get("/api/v1/consultas/{consulta_id}", tags=["consultas"], response_model=None)
async def ler_consulta(
    consulta_id: uuid.UUID, servico: Servico, request: Request, x_token_operador: TokenOperador = None
) -> dict[str, Any] | JSONResponse:
    documento = await servico.obter(consulta_id)
    if documento is None:
        return problema(404, "Consulta não encontrada")
    return visivel(request, documento, x_token_operador)


@rotas.get("/api/v1/evidencias/{evidencia_id}", tags=["evidencias"], response_model=None)
async def evidencia(
    evidencia_id: int, contexto: Contexto, request: Request, x_token_operador: TokenOperador = None
) -> Response:
    if not operador(request, x_token_operador):
        return problema(403, "Acesso restrito", "Evidências brutas só com token de operador.")
    bruta = await contexto.evidencias.obter(evidencia_id)
    if bruta is None:
        return problema(404, "Evidência não encontrada")
    return Response(
        content=bruta.corpo,
        media_type=bruta.content_type or "application/octet-stream",
        headers={"X-Sha256": bruta.sha256 or "", "X-Fonte": bruta.fonte},
    )


@rotas.get("/api/v1/fontes", tags=["fontes"])
async def estado_fontes(contexto: Contexto) -> dict[str, Any]:
    return await contexto.fontes.estado()
