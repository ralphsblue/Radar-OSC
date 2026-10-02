from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from validador_osc.persistencia.repositorios import RepositorioSaudeFontes

JANELA = timedelta(hours=24)

DESCRICOES = {
    "opencnpj": "OpenCNPJ (cadastro da Receita, principal)",
    "opencnpj_info": "OpenCNPJ (data da base)",
    "brasilapi": "BrasilAPI (cadastro da Receita, reserva)",
}


class ServicoFontes:
    def __init__(
        self, repositorio: RepositorioSaudeFontes, relogio: Callable[[], datetime] | None = None
    ) -> None:
        self._repositorio = repositorio
        self._relogio = relogio or (lambda: datetime.now(UTC))

    async def estado(self) -> dict[str, Any]:
        agora = self._relogio()
        resumos = await self._repositorio.resumir(agora - JANELA)
        return {
            "gerado_em": agora.isoformat(),
            "janela_horas": int(JANELA.total_seconds() // 3600),
            "online": [
                {
                    "fonte": r.fonte,
                    "descricao": DESCRICOES.get(r.fonte, r.fonte),
                    "ultima_resposta_em": r.ultima_resposta_em.isoformat() if r.ultima_resposta_em else None,
                    "ultimo_resultado": r.ultimo_resultado,
                    "ultima_falha_em": r.ultima_falha_em.isoformat() if r.ultima_falha_em else None,
                    "respostas": r.respostas,
                    "falhas": r.falhas,
                    "latencia_mediana_ms": round(r.latencia_mediana_ms)
                    if r.latencia_mediana_ms is not None
                    else None,
                }
                for r in resumos
            ],
        }
