from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog

from validador_osc.dominio.coleta import Coleta, Falha, MotivoFalha, NaoEncontrado, Obtido
from validador_osc.dominio.evidencias import Evidencias, RespostaGuardada, ResultadoResposta
from validador_osc.dominio.tipos import Cadastro
from validador_osc.fontes.http import ClienteHttp, FalhaHttp, PoliticaRetry
from validador_osc.fontes.normalizacao.brasilapi import ErroFormato, normalizar_cadastro
from validador_osc.fontes.registro import buscar_em_cache, resposta_falha, resposta_ok

FONTE = "brasilapi"
URL_BASE = "https://brasilapi.com.br/api/cnpj/v1"
POLITICA_RETRY = PoliticaRetry(tentativas=1)
_NAO_ENCONTRADO = 404

log = structlog.get_logger()


def _agora() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class ValidadeBrasilApi:
    cadastro: timedelta = timedelta(days=7)
    nao_encontrado: timedelta = timedelta(hours=6)


class FonteBrasilApi:
    nome = FONTE
    aceita_alfanumerico = True

    def __init__(
        self,
        http: ClienteHttp,
        evidencias: Evidencias,
        validade: ValidadeBrasilApi | None = None,
        url_base: str = URL_BASE,
        relogio: Callable[[], datetime] | None = None,
    ) -> None:
        self._http = http
        self._evidencias = evidencias
        self._validade = validade or ValidadeBrasilApi()
        self._url_base = url_base.rstrip("/")
        self._relogio = relogio or _agora

    async def consultar(self, cnpj: str, *, ignorar_cache: bool = False) -> Coleta[Cadastro]:
        if not ignorar_cache:
            guardada = await buscar_em_cache(
                self._evidencias,
                FONTE,
                cnpj,
                self._relogio(),
                validade=self._validade.cadastro,
                validade_nao_encontrado=self._validade.nao_encontrado,
            )
            if guardada is not None:
                return _interpretar(guardada)
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
        return _interpretar(RespostaGuardada(resultado, resposta.corpo, evidencia))


def _interpretar(guardada: RespostaGuardada) -> Coleta[Cadastro]:
    if guardada.resultado is ResultadoResposta.NAO_ENCONTRADO:
        return NaoEncontrado(guardada.evidencia)
    try:
        cadastro = normalizar_cadastro(guardada.corpo or b"")
    except ErroFormato as erro:
        log.error("fonte_formato_inesperado", fonte=FONTE, evidencia=guardada.evidencia.id, erro=str(erro))
        return Falha(MotivoFalha.FORMATO_INESPERADO, str(erro), guardada.evidencia)
    return Obtido(cadastro, guardada.evidencia)
