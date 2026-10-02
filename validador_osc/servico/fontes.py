from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from validador_osc.persistencia.bases import FONTES_LISTA_TCU, FONTES_SANCAO, RepositorioBasesLocais
from validador_osc.persistencia.repositorios import RepositorioSaudeFontes
from validador_osc.regras.parametros import Limites

JANELA = timedelta(hours=24)

DESCRICOES = {
    "opencnpj": "OpenCNPJ (cadastro da Receita, principal)",
    "opencnpj_info": "OpenCNPJ (data da base)",
    "brasilapi": "BrasilAPI (cadastro da Receita, reserva)",
    "tcu_consolidada": "TCU, Consulta Consolidada de Pessoa Jurídica (inidôneos, CNIA, CEIS, CNEP)",
    "cgu_cepim": "CGU, CEPIM (arquivo diário oficial)",
    "cgu_ceis": "CGU, CEIS (arquivo diário oficial)",
    "cgu_cnep": "CGU, CNEP (arquivo diário oficial)",
    "tcu_inidoneos": "TCU, relação de licitantes inidôneos",
    "tcu_contas_irregulares": "TCU, responsáveis com contas julgadas irregulares",
    "tcu_inabilitados": "TCU, inabilitados para função pública",
}

FONTES_LOCAIS = (*FONTES_SANCAO.values(), *FONTES_LISTA_TCU.values())


class ServicoFontes:
    def __init__(
        self,
        repositorio: RepositorioSaudeFontes,
        bases: RepositorioBasesLocais,
        limites: Limites,
        zona: ZoneInfo,
        relogio: Callable[[], datetime] | None = None,
    ) -> None:
        self._repositorio = repositorio
        self._bases = bases
        self._limites = limites
        self._zona = zona
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
            "locais": await self._locais(agora),
        }

    async def _locais(self, agora: datetime) -> list[dict[str, Any]]:
        hoje = agora.astimezone(self._zona).date()
        saida: list[dict[str, Any]] = []
        for fonte in FONTES_LOCAIS:
            carga = await self._bases.carga_ativa(fonte)
            idade_maxima = self._limites.idade_maxima_de(fonte)
            if carga is None:
                saida.append(
                    {"fonte": fonte, "descricao": DESCRICOES.get(fonte, fonte), "estado": "SEM_CARGA"}
                )
                continue
            base = carga.data_base or carga.concluida_em.astimezone(self._zona).date()
            idade = hoje - base
            saida.append(
                {
                    "fonte": fonte,
                    "descricao": DESCRICOES.get(fonte, fonte),
                    "estado": "VALIDA" if idade <= idade_maxima else "VENCIDA",
                    "data_base": base.isoformat(),
                    "carregada_em": carga.concluida_em.isoformat(),
                    "idade_dias": idade.days,
                    "idade_maxima_dias": idade_maxima.days,
                    "carga": carga.id,
                    "sha256": carga.arquivo_sha256,
                }
            )
        return saida
