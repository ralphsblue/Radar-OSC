from datetime import datetime, timedelta

from validador_osc.dominio.evidencias import (
    Evidencias,
    RespostaBruta,
    RespostaGuardada,
    ResultadoResposta,
)
from validador_osc.fontes.http import FalhaHttp, RespostaHttp


async def buscar_em_cache(
    evidencias: Evidencias,
    fonte: str,
    chave: str,
    agora: datetime,
    *,
    validade: timedelta,
    validade_nao_encontrado: timedelta,
) -> RespostaGuardada | None:
    guardada = await evidencias.buscar_recente(fonte, chave, validade, agora)
    if guardada is None:
        return None
    if (
        guardada.resultado is ResultadoResposta.NAO_ENCONTRADO
        and agora - guardada.evidencia.recebida_em > validade_nao_encontrado
    ):
        return None
    return guardada


def resposta_ok(
    fonte: str, chave: str, resposta: RespostaHttp, resultado: ResultadoResposta
) -> RespostaBruta:
    return RespostaBruta(
        fonte=fonte,
        chave=chave,
        url=resposta.url,
        resultado=resultado,
        recebida_em=resposta.recebida_em,
        duracao_ms=resposta.duracao_ms,
        tentativas=resposta.tentativas,
        http_status=resposta.status,
        content_type=resposta.content_type,
        corpo=resposta.corpo,
    )


def resposta_falha(fonte: str, chave: str, falha: FalhaHttp) -> RespostaBruta:
    return RespostaBruta(
        fonte=fonte,
        chave=chave,
        url=falha.url,
        resultado=ResultadoResposta.FALHA,
        recebida_em=falha.recebida_em,
        duracao_ms=falha.duracao_ms,
        tentativas=falha.tentativas,
        http_status=falha.status,
        motivo_falha=falha.motivo,
    )
