import hashlib
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from validador_osc.dominio.coleta import RefEvidencia
from validador_osc.dominio.evidencias import RespostaBruta, RespostaGuardada, ResultadoResposta
from validador_osc.persistencia.modelos import Consulta, ConsultaEvidencia, RespostaFonte


def _ref(linha: RespostaFonte, de_cache: bool) -> RefEvidencia:
    return RefEvidencia(linha.id, linha.fonte, linha.sha256, linha.recebida_em, de_cache)


class RepositorioEvidencias:
    def __init__(self, sessoes: async_sessionmaker[AsyncSession]) -> None:
        self._sessoes = sessoes

    async def gravar(self, resposta: RespostaBruta) -> RefEvidencia:
        linha = RespostaFonte(
            fonte=resposta.fonte,
            chave=resposta.chave,
            url=resposta.url,
            resultado=resposta.resultado.value,
            motivo_falha=resposta.motivo_falha.value if resposta.motivo_falha else None,
            http_status=resposta.http_status,
            recebida_em=resposta.recebida_em,
            duracao_ms=resposta.duracao_ms,
            tentativas=resposta.tentativas,
            content_type=resposta.content_type,
            corpo=resposta.corpo,
            sha256=hashlib.sha256(resposta.corpo).hexdigest() if resposta.corpo is not None else None,
        )
        async with self._sessoes() as sessao, sessao.begin():
            sessao.add(linha)
        return _ref(linha, de_cache=False)

    async def buscar_recente(
        self, fonte: str, chave: str, validade: timedelta, agora: datetime
    ) -> RespostaGuardada | None:
        consulta = (
            select(RespostaFonte)
            .where(
                RespostaFonte.fonte == fonte,
                RespostaFonte.chave == chave,
                RespostaFonte.resultado != ResultadoResposta.FALHA.value,
                RespostaFonte.recebida_em >= agora - validade,
            )
            .order_by(RespostaFonte.recebida_em.desc())
            .limit(1)
        )
        async with self._sessoes() as sessao:
            linha = (await sessao.scalars(consulta)).first()
        if linha is None:
            return None
        return RespostaGuardada(ResultadoResposta(linha.resultado), linha.corpo, _ref(linha, de_cache=True))

    async def obter(self, evidencia_id: int) -> RespostaFonte | None:
        async with self._sessoes() as sessao:
            return await sessao.get(RespostaFonte, evidencia_id)


@dataclass(frozen=True, slots=True)
class NovaConsulta:
    id: uuid.UUID
    cnpj_informado: str
    cnpj: str
    cnpj_matriz: str | None
    esfera: str | None
    data_referencia: date
    iniciada_em: datetime
    duracao_ms: int
    status: str
    resultado: dict[str, Any]
    versao_app: str
    versao_regras: str
    forcou_atualizacao: bool
    chave_idempotencia: str | None
    evidencias: tuple[tuple[int, str, bool], ...]


class RepositorioConsultas:
    def __init__(self, sessoes: async_sessionmaker[AsyncSession]) -> None:
        self._sessoes = sessoes

    async def salvar(self, nova: NovaConsulta) -> None:
        async with self._sessoes() as sessao, sessao.begin():
            sessao.add(
                Consulta(
                    id=nova.id,
                    cnpj_informado=nova.cnpj_informado,
                    cnpj=nova.cnpj,
                    cnpj_matriz=nova.cnpj_matriz,
                    esfera=nova.esfera,
                    data_referencia=nova.data_referencia,
                    iniciada_em=nova.iniciada_em,
                    duracao_ms=nova.duracao_ms,
                    status=nova.status,
                    resultado=nova.resultado,
                    versao_app=nova.versao_app,
                    versao_regras=nova.versao_regras,
                    forcou_atualizacao=nova.forcou_atualizacao,
                    chave_idempotencia=nova.chave_idempotencia,
                )
            )
            await sessao.flush()
            sessao.add_all(
                ConsultaEvidencia(
                    consulta_id=nova.id, resposta_fonte_id=evidencia, papel=papel, de_cache=cache
                )
                for evidencia, papel, cache in nova.evidencias
            )

    async def obter_resultado(self, consulta_id: uuid.UUID) -> dict[str, Any] | None:
        async with self._sessoes() as sessao:
            linha = await sessao.get(Consulta, consulta_id)
        return linha.resultado if linha is not None else None

    async def por_chave_idempotencia(self, chave: str) -> dict[str, Any] | None:
        async with self._sessoes() as sessao:
            linha = (
                await sessao.scalars(select(Consulta).where(Consulta.chave_idempotencia == chave))
            ).first()
        return linha.resultado if linha is not None else None

    async def recente_equivalente(
        self, cnpj: str, esfera: str | None, desde: datetime
    ) -> dict[str, Any] | None:
        condicao_esfera = Consulta.esfera.is_(None) if esfera is None else Consulta.esfera == esfera
        consulta = (
            select(Consulta)
            .where(
                Consulta.cnpj == cnpj,
                condicao_esfera,
                Consulta.forcou_atualizacao.is_(False),
                Consulta.iniciada_em >= desde,
            )
            .order_by(Consulta.iniciada_em.desc())
            .limit(1)
        )
        async with self._sessoes() as sessao:
            linha = (await sessao.scalars(consulta)).first()
        return linha.resultado if linha is not None else None


@dataclass(frozen=True, slots=True)
class ResumoFonte:
    fonte: str
    ultima_resposta_em: datetime | None
    ultimo_resultado: str | None
    ultima_falha_em: datetime | None
    respostas: int
    falhas: int
    latencia_mediana_ms: float | None


class RepositorioSaudeFontes:
    def __init__(self, sessoes: async_sessionmaker[AsyncSession]) -> None:
        self._sessoes = sessoes

    async def resumir(self, desde: datetime) -> list[ResumoFonte]:
        falha = RespostaFonte.resultado == ResultadoResposta.FALHA.value
        agregado = (
            select(
                RespostaFonte.fonte,
                func.count().label("respostas"),
                func.count().filter(falha).label("falhas"),
                func.percentile_cont(0.5).within_group(RespostaFonte.duracao_ms).label("mediana"),
                func.max(RespostaFonte.recebida_em).filter(falha).label("ultima_falha"),
            )
            .where(RespostaFonte.recebida_em >= desde)
            .group_by(RespostaFonte.fonte)
            .subquery()
        )
        ultima = (
            select(RespostaFonte.fonte, RespostaFonte.recebida_em, RespostaFonte.resultado)
            .ext(distinct_on(RespostaFonte.fonte))
            .order_by(RespostaFonte.fonte, RespostaFonte.recebida_em.desc())
            .subquery()
        )
        consulta = (
            select(
                ultima.c.fonte,
                ultima.c.recebida_em,
                ultima.c.resultado,
                agregado.c.ultima_falha,
                func.coalesce(agregado.c.respostas, 0),
                func.coalesce(agregado.c.falhas, 0),
                agregado.c.mediana,
            )
            .outerjoin(agregado, agregado.c.fonte == ultima.c.fonte)
            .order_by(ultima.c.fonte)
        )
        async with self._sessoes() as sessao:
            linhas = (await sessao.execute(consulta)).all()
        return [
            ResumoFonte(
                fonte=fonte,
                ultima_resposta_em=recebida_em,
                ultimo_resultado=resultado,
                ultima_falha_em=ultima_falha,
                respostas=int(respostas),
                falhas=int(falhas),
                latencia_mediana_ms=float(mediana) if mediana is not None else None,
            )
            for fonte, recebida_em, resultado, ultima_falha, respostas, falhas, mediana in linhas
        ]
