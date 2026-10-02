import asyncio
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import structlog

from validador_osc.cnpj import cnpj_da_matriz, eh_alfanumerico, normalizar, validar
from validador_osc.dominio.coleta import Coleta, Falha, MotivoFalha, Obtido
from validador_osc.dominio.resultado import Contexto, Esfera
from validador_osc.dominio.tipos import Cadastro
from validador_osc.persistencia.repositorios import NovaConsulta, RepositorioConsultas
from validador_osc.regras.motor import DadosConsulta, avaliar
from validador_osc.regras.tabelas import Tabelas
from validador_osc.servico.apresentacao import montar_documento
from validador_osc.servico.cadastral import FonteCadastral

JANELA_REPETICAO = timedelta(seconds=10)
PRAZO_PADRAO = timedelta(seconds=20)
CNPJ_INFORMADO_MAXIMO = 32

log = structlog.get_logger()


def _agora() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class PedidoConsulta:
    cnpj: str
    esfera: Esfera | None = None
    atualizar: bool = False
    chave_idempotencia: str | None = None


@dataclass(frozen=True, slots=True)
class ConsultaFeita:
    documento: dict[str, Any]
    nova: bool


class ServicoConsulta:
    def __init__(
        self,
        cadastral: FonteCadastral,
        consultas: RepositorioConsultas,
        tabelas: Tabelas,
        zona: ZoneInfo,
        versao_app: str,
        versao_regras: str,
        relogio: Callable[[], datetime] | None = None,
        prazo: timedelta = PRAZO_PADRAO,
    ) -> None:
        self._cadastral = cadastral
        self._consultas = consultas
        self._tabelas = tabelas
        self._zona = zona
        self._versao_app = versao_app
        self._versao_regras = versao_regras
        self._relogio = relogio or _agora
        self._prazo = prazo

    async def _coletar_cadastro(
        self, cnpj: str, atualizar: bool
    ) -> tuple[Coleta[Cadastro], Coleta[Cadastro] | None]:
        limite = asyncio.get_running_loop().time() + self._prazo.total_seconds()
        try:
            async with asyncio.timeout_at(limite):
                cadastro = await self._cadastral.consultar(cnpj, ignorar_cache=atualizar)
        except TimeoutError:
            return self._prazo_esgotado(), None
        if not isinstance(cadastro, Obtido) or cadastro.dados.matriz:
            return cadastro, None
        cnpj_matriz = cnpj_da_matriz(cnpj)
        if cnpj_matriz == cnpj:
            return cadastro, None
        try:
            async with asyncio.timeout_at(limite):
                matriz = await self._cadastral.consultar(cnpj_matriz, ignorar_cache=atualizar)
        except TimeoutError:
            return cadastro, self._prazo_esgotado()
        return cadastro, matriz

    def _prazo_esgotado(self) -> Falha:
        log.warning("prazo_consulta_esgotado", prazo_s=self._prazo.total_seconds())
        return Falha(MotivoFalha.PRAZO_ESGOTADO, "prazo global da consulta esgotado")

    async def obter(self, consulta_id: uuid.UUID) -> dict[str, Any] | None:
        return await self._consultas.obter_resultado(consulta_id)

    async def executar(self, pedido: PedidoConsulta) -> ConsultaFeita:
        inicio = time.perf_counter()
        iniciada_em = self._relogio()
        cnpj = normalizar(pedido.cnpj)
        esfera_texto = pedido.esfera.value if pedido.esfera else None

        if pedido.chave_idempotencia:
            existente = await self._consultas.por_chave_idempotencia(pedido.chave_idempotencia)
            if existente is not None:
                return ConsultaFeita(existente, nova=False)
        if not pedido.atualizar:
            recente = await self._consultas.recente_equivalente(
                cnpj, esfera_texto, iniciada_em - JANELA_REPETICAO
            )
            if recente is not None:
                return ConsultaFeita(recente, nova=False)

        structlog.contextvars.bind_contextvars(cnpj=cnpj)
        cadastro: Coleta[Cadastro] | None = None
        matriz: Coleta[Cadastro] | None = None
        if validar(cnpj).valido and not eh_alfanumerico(cnpj):
            cadastro, matriz = await self._coletar_cadastro(cnpj, pedido.atualizar)

        contexto = Contexto(data_referencia=iniciada_em.astimezone(self._zona).date(), esfera=pedido.esfera)
        avaliacao = avaliar(DadosConsulta(cnpj, cadastro, matriz), contexto, self._tabelas)
        consulta_id = uuid.uuid4()
        dados_cadastro = cadastro.dados if isinstance(cadastro, Obtido) else None
        dados_matriz = matriz.dados if isinstance(matriz, Obtido) and matriz.dados.matriz else None
        documento = montar_documento(
            consulta_id=str(consulta_id),
            cnpj=cnpj,
            cadastro=dados_cadastro,
            matriz=dados_matriz,
            esfera=pedido.esfera,
            data_referencia=contexto.data_referencia,
            consultado_em=iniciada_em.astimezone(self._zona),
            avaliacao=avaliacao,
            versao_app=self._versao_app,
            versao_regras=self._versao_regras,
        )
        evidencias = tuple(
            {
                (f.evidencia_id, f.fonte, f.de_cache)
                for v in avaliacao.verificacoes
                for f in v.fontes
                if f.evidencia_id is not None
            }
        )
        duracao_ms = int((time.perf_counter() - inicio) * 1000)
        await self._consultas.salvar(
            NovaConsulta(
                id=consulta_id,
                cnpj_informado=pedido.cnpj[:CNPJ_INFORMADO_MAXIMO],
                cnpj=cnpj[:14],
                cnpj_matriz=dados_matriz.cnpj if dados_matriz else None,
                esfera=esfera_texto,
                data_referencia=contexto.data_referencia,
                iniciada_em=iniciada_em,
                duracao_ms=duracao_ms,
                status=avaliacao.status.value,
                resultado=documento,
                versao_app=self._versao_app,
                versao_regras=self._versao_regras,
                forcou_atualizacao=pedido.atualizar,
                chave_idempotencia=pedido.chave_idempotencia,
                evidencias=evidencias,
            )
        )
        log.info(
            "consulta_concluida", status=avaliacao.status.value, motivos=avaliacao.motivos, ms=duracao_ms
        )
        structlog.contextvars.unbind_contextvars("cnpj")
        return ConsultaFeita(documento, nova=True)
