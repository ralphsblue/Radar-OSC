import csv
import io
import uuid
from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse

from validador_osc.api.dependencias import Contexto, UsuarioLogado, problema
from validador_osc.api.esquemas import PedidoLoteApi
from validador_osc.api.formatacao import criar_formatar_instante, rotulo_status
from validador_osc.servico.lotes import (
    LimiteLoteExcedido,
    LinhaExportacaoLote,
    LoteDetalhe,
    LoteResumo,
    MetricasUsuario,
    PedidoLote,
    dividir_cnpjs,
)

rotas = APIRouter()

_ROTULOS_STATUS_ITEM = {
    "PENDENTE": "Pendente",
    "PROCESSANDO": "Processando",
    "CONCLUIDO": "Concluído",
    "ERRO": "Erro",
}


def _item_json(item: Any) -> dict[str, Any]:
    return {
        "posicao": item.posicao,
        "cnpj_informado": item.cnpj_informado,
        "status": item.status,
        "consulta_id": str(item.consulta_id) if item.consulta_id else None,
        "erro": item.erro,
    }


def _lote_json(lote: LoteDetalhe | LoteResumo) -> dict[str, Any]:
    documento: dict[str, Any] = {
        "id": str(lote.id),
        "esfera": lote.esfera,
        "status": lote.status,
        "total_itens": lote.total_itens,
        "criado_em": lote.criado_em.isoformat(),
        "concluido_em": lote.concluido_em.isoformat() if lote.concluido_em else None,
    }
    if isinstance(lote, LoteDetalhe):
        documento["itens"] = [_item_json(item) for item in lote.itens]
    return documento


@rotas.post("/api/v1/lotes", status_code=201, tags=["lotes"], response_model=None)
async def criar_lote(
    pedido: PedidoLoteApi, contexto: Contexto, usuario: UsuarioLogado, response: Response
) -> dict[str, Any] | Response:
    cnpjs = dividir_cnpjs(pedido.cnpjs)
    try:
        lote_id = await contexto.lotes.criar(
            PedidoLote(
                usuario_id=usuario.id,
                esfera=pedido.esfera.value if pedido.esfera else None,
                cnpjs=cnpjs,
            )
        )
    except LimiteLoteExcedido:
        return problema(400, "Lote excede o limite", "No máximo 20 CNPJs por lote.")
    response.headers["Location"] = f"/api/v1/lotes/{lote_id}"
    return {"id": str(lote_id)}


@rotas.get("/api/v1/lotes/{lote_id}", tags=["lotes"], response_model=None)
async def ler_lote(
    lote_id: uuid.UUID, contexto: Contexto, usuario: UsuarioLogado
) -> dict[str, Any] | Response:
    detalhe = await contexto.lotes.obter(lote_id, usuario.id)
    if detalhe is None:
        return problema(404, "Lote não encontrado")
    return _lote_json(detalhe)


@rotas.get("/api/v1/lotes", tags=["lotes"], response_model=None)
async def listar_lotes(contexto: Contexto, usuario: UsuarioLogado) -> list[dict[str, Any]]:
    resumos = await contexto.lotes.listar(usuario.id)
    return [_lote_json(resumo) for resumo in resumos]


def _linhas_csv(
    linhas: list[LinhaExportacaoLote], formatar_instante: Callable[[datetime | None], str]
) -> Iterator[str]:
    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(["CNPJ", "Razão social", "Status", "Impedimento principal", "Data"])
    yield buffer.getvalue()
    for linha in linhas:
        buffer.seek(0)
        buffer.truncate(0)
        status = (
            rotulo_status(linha.status_consulta)
            if linha.status_consulta
            else _ROTULOS_STATUS_ITEM.get(linha.status_item, linha.status_item)
        )
        escritor.writerow(
            [
                linha.cnpj_informado,
                linha.razao_social or "",
                status,
                linha.impedimento_principal or "",
                formatar_instante(linha.consultado_em),
            ]
        )
        yield buffer.getvalue()


def _metricas_json(metricas: MetricasUsuario) -> dict[str, Any]:
    return {
        "total_lotes": metricas.total_lotes,
        "total_cnpjs_avaliados": metricas.total_cnpjs_avaliados,
        "distribuicao_status": metricas.distribuicao_status,
        "impedimentos_por_tipo": metricas.impedimentos_por_tipo,
    }


@rotas.get("/api/v1/usuarios/me/metricas", tags=["usuarios"], response_model=None)
async def ler_metricas_usuario(contexto: Contexto, usuario: UsuarioLogado) -> dict[str, Any]:
    metricas = await contexto.lotes.metricas(usuario.id)
    return _metricas_json(metricas)


@rotas.get("/api/v1/lotes/{lote_id}/export.csv", tags=["lotes"], response_model=None)
async def exportar_lote_csv(lote_id: uuid.UUID, contexto: Contexto, usuario: UsuarioLogado) -> Response:
    linhas = await contexto.lotes.exportar_linhas(lote_id, usuario.id)
    if linhas is None:
        return problema(404, "Lote não encontrado")
    formatar_instante = criar_formatar_instante(contexto.config.zona)
    cabecalhos = {"Content-Disposition": f'attachment; filename="lote-{lote_id}.csv"'}
    conteudo = _linhas_csv(linhas, formatar_instante)
    return StreamingResponse(conteudo, media_type="text/csv", headers=cabecalhos)
