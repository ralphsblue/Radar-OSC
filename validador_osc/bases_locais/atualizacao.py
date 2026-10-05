import time
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
from sqlalchemy import Engine

from validador_osc.bases_locais import listas_tcu, sancoes_cgu, tcesp
from validador_osc.bases_locais.carga import CicloCarga, DefinicaoBase, Obtencao, ResultadoCarga, Sanidade
from validador_osc.config import Configuracao

FONTES_IMPLEMENTADAS: tuple[str, ...] = (
    *sancoes_cgu.FONTES_CGU,
    *listas_tcu.FONTES_TCU,
    *tcesp.FONTES_TCESP,
)
PAUSA_ENTRE_FONTES_S = 1.5


class FonteDesconhecida(ValueError):
    pass


def criar_cliente(config: Configuracao) -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": config.user_agent},
        follow_redirects=True,
        timeout=httpx.Timeout(config.timeout_download_s, connect=config.timeout_fonte_s),
    )


class Atualizador:
    def __init__(
        self,
        engine: Engine,
        config: Configuracao,
        cliente: httpx.Client,
        relogio: Callable[[], datetime] = lambda: datetime.now(UTC),
        sanidade: dict[str, Sanidade] | None = None,
    ) -> None:
        self._ciclo = CicloCarga(engine, config.dir_arquivos, relogio)
        self._cliente = cliente
        self._relogio = relogio
        self._zona = config.zona
        self._sanidade = sanidade or {}

    def ingerir(self, fonte: str, arquivo: Path | None = None) -> ResultadoCarga:
        definicao, obtencao = self._preparar(fonte, arquivo)
        return self._ciclo.executar(definicao, obtencao)

    def atualizar(self, diretorio: Path | None = None) -> list[ResultadoCarga]:
        resultados: list[ResultadoCarga] = []
        for indice, fonte in enumerate(FONTES_IMPLEMENTADAS):
            if indice and diretorio is None:
                time.sleep(PAUSA_ENTRE_FONTES_S)
            arquivo = _arquivo_mais_recente(diretorio, fonte) if diretorio is not None else None
            resultados.append(self.ingerir(fonte, arquivo))
        return resultados

    def _hoje(self) -> date:
        return self._relogio().astimezone(self._zona).date()

    def _preparar(self, fonte: str, arquivo: Path | None) -> tuple[DefinicaoBase, Obtencao]:
        sanidade = self._sanidade.get(fonte)
        if (cgu := sancoes_cgu.FONTES_CGU.get(fonte)) is not None:
            obtencao = (
                sancoes_cgu.obtencao_local(arquivo)
                if arquivo is not None
                else sancoes_cgu.obtencao_remota(self._cliente, cgu)
            )
            return sancoes_cgu.definicao(cgu, sanidade), obtencao
        if (tcu := listas_tcu.FONTES_TCU.get(fonte)) is not None:
            obtencao = (
                listas_tcu.obtencao_local(arquivo)
                if arquivo is not None
                else listas_tcu.obtencao_remota(self._cliente, tcu, self._hoje)
            )
            return listas_tcu.definicao(tcu, sanidade), obtencao
        if (terceiro_setor := tcesp.FONTES_TCESP.get(fonte)) is not None:
            obtencao = (
                tcesp.obtencao_local(arquivo) if arquivo is not None else tcesp.obtencao_remota(self._cliente)
            )
            return tcesp.definicao(terceiro_setor, sanidade), obtencao
        raise FonteDesconhecida(
            f"fonte desconhecida: {fonte} (conhecidas: {', '.join(FONTES_IMPLEMENTADAS)})"
        )


def _arquivo_mais_recente(diretorio: Path, fonte: str) -> Path:
    if fonte in listas_tcu.FONTES_TCU:
        padroes = [f"*_{fonte}.{listas_tcu.EXTENSAO}"]
    elif fonte in tcesp.FONTES_TCESP:
        padroes = [f"*_{fonte}.{tcesp.EXTENSAO}"]
    else:
        cadastro = sancoes_cgu.FONTES_CGU[fonte].cadastro.value
        padroes = [f"*_{cadastro}.zip", f"*_{cadastro}.csv"]
    for padrao in padroes:
        candidatos = sorted(diretorio.glob(padrao))
        if candidatos:
            return candidatos[-1]
    return diretorio / padroes[0]
