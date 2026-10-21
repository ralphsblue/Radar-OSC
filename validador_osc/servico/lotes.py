import uuid
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from validador_osc.dominio.resultado import StatusFinal
from validador_osc.persistencia.repositorios import (
    ItemComLoteRegistro,
    ItemLoteRegistro,
    LoteRegistro,
    NovoLote,
    RepositorioConsultas,
    RepositorioLotes,
)

ESTADOS_TERMINAIS_ITEM = ("CONCLUIDO", "ERRO")

CNPJS_MAXIMO_POR_LOTE = 20


def _agora() -> datetime:
    return datetime.now(UTC)


def dividir_cnpjs(texto: str) -> tuple[str, ...]:
    return tuple(parte.strip() for parte in texto.split(";") if parte.strip())


@dataclass(frozen=True, slots=True)
class PedidoLote:
    usuario_id: uuid.UUID
    esfera: str | None
    cnpjs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ItemLote:
    posicao: int
    cnpj_informado: str
    status: str
    consulta_id: uuid.UUID | None
    erro: str | None


@dataclass(frozen=True, slots=True)
class LoteDetalhe:
    id: uuid.UUID
    esfera: str | None
    status: str
    total_itens: int
    criado_em: datetime
    concluido_em: datetime | None
    itens: tuple[ItemLote, ...]


@dataclass(frozen=True, slots=True)
class ItemComLote:
    id: int
    lote_id: uuid.UUID
    cnpj_informado: str
    esfera: str | None


@dataclass(frozen=True, slots=True)
class LoteResumo:
    id: uuid.UUID
    esfera: str | None
    status: str
    total_itens: int
    criado_em: datetime
    concluido_em: datetime | None


@dataclass(frozen=True, slots=True)
class LinhaExportacaoLote:
    cnpj_informado: str
    razao_social: str | None
    status_item: str
    status_consulta: str | None
    impedimento_principal: str | None
    consultado_em: datetime | None


@dataclass(frozen=True, slots=True)
class MetricasUsuario:
    total_lotes: int
    total_cnpjs_avaliados: int
    distribuicao_status: dict[str, int]
    impedimentos_por_tipo: dict[str, int]


class LimiteLoteExcedido(Exception):
    pass


def _item_lote(registro: ItemLoteRegistro) -> ItemLote:
    return ItemLote(
        posicao=registro.posicao,
        cnpj_informado=registro.cnpj_informado,
        status=registro.status,
        consulta_id=registro.consulta_id,
        erro=registro.erro,
    )


def _lote_detalhe(registro: LoteRegistro) -> LoteDetalhe:
    return LoteDetalhe(
        id=registro.id,
        esfera=registro.esfera,
        status=registro.status,
        total_itens=registro.total_itens,
        criado_em=registro.criado_em,
        concluido_em=registro.concluido_em,
        itens=tuple(_item_lote(item) for item in registro.itens),
    )


def _item_com_lote(registro: ItemComLoteRegistro) -> ItemComLote:
    return ItemComLote(
        id=registro.id,
        lote_id=registro.lote_id,
        cnpj_informado=registro.cnpj_informado,
        esfera=registro.esfera,
    )


def _lote_resumo(registro: LoteRegistro) -> LoteResumo:
    return LoteResumo(
        id=registro.id,
        esfera=registro.esfera,
        status=registro.status,
        total_itens=registro.total_itens,
        criado_em=registro.criado_em,
        concluido_em=registro.concluido_em,
    )


def _linha_exportacao(item: ItemLoteRegistro, documento: dict[str, Any] | None) -> LinhaExportacaoLote:
    if documento is None:
        return LinhaExportacaoLote(
            cnpj_informado=item.cnpj_informado,
            razao_social=None,
            status_item=item.status,
            status_consulta=None,
            impedimento_principal=None,
            consultado_em=None,
        )
    motivos = documento.get("motivos") or []
    verificacoes = documento.get("verificacoes") or []
    nomes_motivos = [v["nome"] for v in verificacoes if v.get("id") in motivos]
    consultado_em_texto = documento.get("consultado_em")
    return LinhaExportacaoLote(
        cnpj_informado=item.cnpj_informado,
        razao_social=documento.get("razao_social"),
        status_item=item.status,
        status_consulta=documento.get("status"),
        impedimento_principal="; ".join(nomes_motivos) if nomes_motivos else None,
        consultado_em=datetime.fromisoformat(consultado_em_texto) if consultado_em_texto else None,
    )


class ServicoLotes:
    def __init__(
        self,
        lotes: RepositorioLotes,
        enfileirar: Callable[[uuid.UUID, int], None],
        relogio: Callable[[], datetime] | None = None,
        consultas: RepositorioConsultas | None = None,
    ) -> None:
        self._lotes = lotes
        self._enfileirar = enfileirar
        self._relogio = relogio or _agora
        self._consultas = consultas

    async def criar(self, pedido: PedidoLote) -> uuid.UUID:
        if len(pedido.cnpjs) > CNPJS_MAXIMO_POR_LOTE:
            raise LimiteLoteExcedido(len(pedido.cnpjs))
        lote_id = uuid.uuid4()
        item_ids = await self._lotes.criar(
            NovoLote(
                id=lote_id,
                usuario_id=pedido.usuario_id,
                esfera=pedido.esfera,
                criado_em=self._relogio(),
                cnpjs=pedido.cnpjs,
            )
        )
        for item_id in item_ids:
            self._enfileirar(lote_id, item_id)
        return lote_id

    async def obter(self, lote_id: uuid.UUID, usuario_id: uuid.UUID) -> LoteDetalhe | None:
        registro = await self._lotes.obter(lote_id)
        if registro is None or registro.usuario_id != usuario_id:
            return None
        return _lote_detalhe(registro)

    async def listar(self, usuario_id: uuid.UUID) -> list[LoteResumo]:
        registros = await self._lotes.listar_por_usuario(usuario_id)
        return [_lote_resumo(registro) for registro in registros]

    async def obter_item(self, item_id: int) -> ItemComLote | None:
        registro = await self._lotes.obter_item_com_lote(item_id)
        return _item_com_lote(registro) if registro is not None else None

    async def marcar_item(
        self, item_id: int, *, status: str, consulta_id: uuid.UUID | None = None, erro: str | None = None
    ) -> None:
        await self._lotes.marcar_item(
            item_id, status=status, consulta_id=consulta_id, erro=erro, atualizado_em=self._relogio()
        )

    async def exportar_linhas(
        self, lote_id: uuid.UUID, usuario_id: uuid.UUID
    ) -> list[LinhaExportacaoLote] | None:
        registro = await self._lotes.obter(lote_id)
        if registro is None or registro.usuario_id != usuario_id:
            return None
        linhas = []
        for item in registro.itens:
            documento = None
            if item.consulta_id is not None and self._consultas is not None:
                documento = await self._consultas.obter_resultado(item.consulta_id)
            linhas.append(_linha_exportacao(item, documento))
        return linhas

    async def metricas(self, usuario_id: uuid.UUID) -> MetricasUsuario:
        registros = await self._lotes.listar_por_usuario(usuario_id)
        cnpjs_vistos: set[str] = set()
        contagem_status: Counter[str] = Counter()
        contagem_impedimentos: Counter[str] = Counter()
        for registro in registros:
            for item in registro.itens:
                if item.consulta_id is None or self._consultas is None:
                    continue
                documento = await self._consultas.obter_resultado(item.consulta_id)
                if documento is None:
                    continue
                cnpjs_vistos.add(documento.get("cnpj") or item.cnpj_informado)
                status = documento.get("status")
                if status:
                    contagem_status[status] += 1
                motivos = documento.get("motivos") or []
                for verificacao in documento.get("verificacoes") or []:
                    if verificacao.get("id") in motivos:
                        contagem_impedimentos[verificacao["nome"]] += 1
        distribuicao_status = {status.value: contagem_status.get(status.value, 0) for status in StatusFinal}
        impedimentos_por_tipo = dict(
            sorted(contagem_impedimentos.items(), key=lambda item: (-item[1], item[0]))
        )
        return MetricasUsuario(
            total_lotes=len(registros),
            total_cnpjs_avaliados=len(cnpjs_vistos),
            distribuicao_status=distribuicao_status,
            impedimentos_por_tipo=impedimentos_por_tipo,
        )

    async def recalcular_status_lote(self, lote_id: uuid.UUID) -> None:
        lote = await self._lotes.obter(lote_id)
        if lote is None:
            return
        if all(item.status in ESTADOS_TERMINAIS_ITEM for item in lote.itens):
            status = "CONCLUIDO"
            concluido_em = lote.concluido_em or self._relogio()
        elif any(item.status != "PENDENTE" for item in lote.itens):
            status = "PROCESSANDO"
            concluido_em = None
        else:
            status = "PENDENTE"
            concluido_em = None
        await self._lotes.atualizar_status_lote(lote_id, status=status, concluido_em=concluido_em)
