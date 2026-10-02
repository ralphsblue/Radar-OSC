from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import httpx
import structlog

from validador_osc.dominio.coleta import Coleta, Falha, MotivoFalha, Obtido
from validador_osc.dominio.evidencias import Evidencias, RespostaGuardada, ResultadoResposta
from validador_osc.dominio.sancoes import RespostaTcu
from validador_osc.fontes.http import ClienteHttp, FalhaHttp, PoliticaRetry
from validador_osc.fontes.normalizacao.tcu import ErroFormato, normalizar_certidoes
from validador_osc.fontes.registro import resposta_falha, resposta_ok

FONTE = "tcu_consolidada"
URL_BASE = "https://certidoes-apf.apps.tcu.gov.br/api/rest/publico/certidoes"
POLITICA_RETRY = PoliticaRetry(tentativas=2)
TIMEOUT = httpx.Timeout(15.0, connect=5.0)
VALIDADE = timedelta(hours=24)

log = structlog.get_logger()


def _agora() -> datetime:
    return datetime.now(UTC)


class FonteTcu:
    nome = FONTE
    aceita_alfanumerico = True

    def __init__(
        self,
        http: ClienteHttp,
        evidencias: Evidencias,
        validade: timedelta = VALIDADE,
        url_base: str = URL_BASE,
        relogio: Callable[[], datetime] | None = None,
    ) -> None:
        self._http = http
        self._evidencias = evidencias
        self._validade = validade
        self._url_base = url_base.rstrip("/")
        self._relogio = relogio or _agora

    async def consultar(self, cnpj: str, *, ignorar_cache: bool = False) -> Coleta[RespostaTcu]:
        if not ignorar_cache:
            guardada = await self._evidencias.buscar_recente(FONTE, cnpj, self._validade, self._relogio())
            if guardada is not None:
                return _interpretar(cnpj, guardada)
        try:
            resposta = await self._http.obter(f"{self._url_base}/{cnpj}?seEmitirPDF=false")
        except FalhaHttp as falha:
            evidencia = await self._evidencias.gravar(resposta_falha(FONTE, cnpj, falha))
            log.warning("fonte_falhou", fonte=FONTE, cnpj=cnpj, motivo=falha.motivo, detalhe=falha.detalhe)
            return Falha(falha.motivo, falha.detalhe, evidencia)
        evidencia = await self._evidencias.gravar(
            resposta_ok(FONTE, cnpj, resposta, ResultadoResposta.OBTIDO)
        )
        return _interpretar(cnpj, RespostaGuardada(ResultadoResposta.OBTIDO, resposta.corpo, evidencia))


def _interpretar(cnpj: str, guardada: RespostaGuardada) -> Coleta[RespostaTcu]:
    try:
        certidoes = normalizar_certidoes(guardada.corpo or b"")
        if certidoes.cnpj != cnpj:
            raise ErroFormato(f"TCU: resposta de outro CNPJ {certidoes.cnpj!r}")
    except ErroFormato as erro:
        log.error("fonte_formato_inesperado", fonte=FONTE, evidencia=guardada.evidencia.id, erro=str(erro))
        return Falha(MotivoFalha.FORMATO_INESPERADO, str(erro), guardada.evidencia)
    return Obtido(certidoes, guardada.evidencia)
