from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import structlog

from validador_osc.dominio.coleta import Coleta, Falha, MotivoFalha, NaoEncontrado, Obtido, RefEvidencia
from validador_osc.dominio.evidencias import Evidencias, ResultadoResposta
from validador_osc.dominio.tipos import PerfilMapa
from validador_osc.fontes.http import ClienteHttp, FalhaHttp
from validador_osc.fontes.normalizacao.comum import ErroFormato
from validador_osc.fontes.normalizacao.mapa_osc import localizar_osc, normalizar_perfil
from validador_osc.fontes.registro import resposta_falha, resposta_ok

FONTE_BUSCA = "mapa_osc_busca"
FONTE_PERFIL = "mapa_osc_perfil"
URL_BASE = "https://mapaosc.ipea.gov.br/api/api"
VALIDADE = timedelta(days=30)
SECOES = ("dados_gerais", "descricao", "areas_atuacao_rep", "indice_preenchimento")

log = structlog.get_logger()


def _agora() -> datetime:
    return datetime.now(UTC)


class _FalhaColeta(Exception):
    def __init__(self, falha: Falha) -> None:
        super().__init__(falha.detalhe)
        self.falha = falha


class FonteMapaOsc:
    nome = FONTE_BUSCA
    aceita_alfanumerico = False

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

    async def consultar(self, cnpj: str, *, ignorar_cache: bool = False) -> Coleta[PerfilMapa]:
        try:
            busca, evidencia = await self._obter(FONTE_BUSCA, cnpj, f"busca/cnpj/{int(cnpj)}", ignorar_cache)
            localizado = localizar_osc(busca, cnpj)
            if localizado is None:
                return NaoEncontrado(evidencia)
            id_osc, situacao = localizado
            secoes = [
                (
                    await self._obter(
                        FONTE_PERFIL, f"{secao}/{id_osc}", f"osc/{secao}/{id_osc}", ignorar_cache
                    )
                )[0]
                for secao in SECOES
            ]
            perfil = normalizar_perfil(id_osc, cnpj, situacao, *secoes)
        except _FalhaColeta as erro:
            return erro.falha
        except ErroFormato as erro:
            log.error("fonte_formato_inesperado", fonte=FONTE_BUSCA, cnpj=cnpj, erro=str(erro))
            return Falha(MotivoFalha.FORMATO_INESPERADO, str(erro))
        return Obtido(perfil, evidencia)

    async def _obter(
        self, fonte: str, chave: str, caminho: str, ignorar_cache: bool
    ) -> tuple[bytes, RefEvidencia]:
        if not ignorar_cache:
            guardada = await self._evidencias.buscar_recente(fonte, chave, self._validade, self._relogio())
            if guardada is not None and guardada.corpo is not None:
                return guardada.corpo, guardada.evidencia
        try:
            resposta = await self._http.obter(f"{self._url_base}/{caminho}")
        except FalhaHttp as falha:
            evidencia = await self._evidencias.gravar(resposta_falha(fonte, chave, falha))
            log.warning("fonte_falhou", fonte=fonte, chave=chave, motivo=falha.motivo)
            raise _FalhaColeta(Falha(falha.motivo, falha.detalhe, evidencia)) from falha
        evidencia = await self._evidencias.gravar(
            resposta_ok(fonte, chave, resposta, ResultadoResposta.OBTIDO)
        )
        return resposta.corpo, evidencia
