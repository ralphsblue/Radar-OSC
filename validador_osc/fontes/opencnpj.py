from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import structlog

from validador_osc.dominio.coleta import Coleta, Falha, MotivoFalha, NaoEncontrado, Obtido
from validador_osc.dominio.evidencias import Evidencias, RespostaGuardada, ResultadoResposta
from validador_osc.dominio.tipos import Cadastro
from validador_osc.fontes.http import ClienteHttp, FalhaHttp
from validador_osc.fontes.normalizacao.opencnpj import ErroFormato, extrair_data_base, normalizar_cadastro
from validador_osc.fontes.registro import buscar_em_cache, resposta_falha, resposta_ok

FONTE = "opencnpj"
FONTE_INFO = "opencnpj_info"
URL_BASE = "https://api.opencnpj.org"
_NAO_ENCONTRADO = 404

log = structlog.get_logger()


def _agora() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class ValidadeOpenCnpj:
    cadastro: timedelta = timedelta(hours=24)
    nao_encontrado: timedelta = timedelta(hours=6)
    info: timedelta = timedelta(hours=24)
    info_reserva: timedelta = timedelta(days=45)
    espera_apos_falha_info: timedelta = timedelta(minutes=5)


class FonteOpenCnpj:
    nome = FONTE
    aceita_alfanumerico = True

    def __init__(
        self,
        http: ClienteHttp,
        evidencias: Evidencias,
        validade: ValidadeOpenCnpj | None = None,
        url_base: str = URL_BASE,
        relogio: Callable[[], datetime] | None = None,
    ) -> None:
        self._http = http
        self._evidencias = evidencias
        self._validade = validade or ValidadeOpenCnpj()
        self._url_base = url_base.rstrip("/")
        self._info_falhou_em: datetime | None = None
        self._relogio = relogio or _agora

    async def consultar(self, cnpj: str, *, ignorar_cache: bool = False) -> Coleta[Cadastro]:
        data_base = await self._data_base()
        agora = self._relogio()
        if not ignorar_cache:
            guardada = await buscar_em_cache(
                self._evidencias,
                FONTE,
                cnpj,
                agora,
                validade=self._validade.cadastro,
                validade_nao_encontrado=self._validade.nao_encontrado,
            )
            if guardada is not None:
                return self._interpretar(guardada, data_base)
        try:
            resposta = await self._http.obter(
                f"{self._url_base}/{cnpj}", status_aceitos=frozenset({200, _NAO_ENCONTRADO})
            )
        except FalhaHttp as falha:
            evidencia = await self._evidencias.gravar(resposta_falha(FONTE, cnpj, falha))
            log.warning("fonte_falhou", fonte=FONTE, cnpj=cnpj, motivo=falha.motivo, detalhe=falha.detalhe)
            return Falha(falha.motivo, falha.detalhe, evidencia)
        resultado = (
            ResultadoResposta.NAO_ENCONTRADO
            if resposta.status == _NAO_ENCONTRADO
            else ResultadoResposta.OBTIDO
        )
        evidencia = await self._evidencias.gravar(resposta_ok(FONTE, cnpj, resposta, resultado))
        return self._interpretar(RespostaGuardada(resultado, resposta.corpo, evidencia), data_base)

    def _interpretar(self, guardada: RespostaGuardada, data_base: date | None) -> Coleta[Cadastro]:
        if guardada.resultado is ResultadoResposta.NAO_ENCONTRADO:
            return NaoEncontrado(guardada.evidencia, data_base)
        try:
            cadastro = normalizar_cadastro(guardada.corpo or b"", data_base)
        except ErroFormato as erro:
            log.error(
                "fonte_formato_inesperado", fonte=FONTE, evidencia=guardada.evidencia.id, erro=str(erro)
            )
            return Falha(MotivoFalha.FORMATO_INESPERADO, str(erro), guardada.evidencia)
        return Obtido(cadastro, guardada.evidencia)

    async def _data_base(self) -> date | None:
        agora = self._relogio()
        guardada = await self._evidencias.buscar_recente(FONTE_INFO, "info", self._validade.info, agora)
        corpo = guardada.corpo if guardada is not None else None
        if corpo is None and not self._info_em_espera(agora):
            corpo = await self._baixar_info()
        if corpo is None:
            reserva = await self._evidencias.buscar_recente(
                FONTE_INFO, "info", self._validade.info_reserva, agora
            )
            corpo = reserva.corpo if reserva is not None else None
        if corpo is None:
            return None
        try:
            return extrair_data_base(corpo)
        except ErroFormato:
            return None

    def _info_em_espera(self, agora: datetime) -> bool:
        falhou = self._info_falhou_em
        return falhou is not None and agora - falhou < self._validade.espera_apos_falha_info

    async def _baixar_info(self) -> bytes | None:
        try:
            resposta = await self._http.obter(f"{self._url_base}/info")
        except FalhaHttp as falha:
            self._info_falhou_em = falha.recebida_em
            await self._evidencias.gravar(resposta_falha(FONTE_INFO, "info", falha))
            log.warning("fonte_falhou", fonte=FONTE_INFO, motivo=falha.motivo)
            return None
        self._info_falhou_em = None
        await self._evidencias.gravar(resposta_ok(FONTE_INFO, "info", resposta, ResultadoResposta.OBTIDO))
        return resposta.corpo
