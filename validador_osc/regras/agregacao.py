from collections.abc import Sequence

from validador_osc.dominio.resultado import (
    Avaliacao,
    Estado,
    ResultadoVerificacao,
    StatusFinal,
    TipoVerificacao,
)
from validador_osc.regras.catalogo import DV

_SEM_RESPOSTA = frozenset({Estado.INDISPONIVEL, Estado.NAO_VERIFICADO})


def _ids(verificacoes: Sequence[ResultadoVerificacao]) -> tuple[str, ...]:
    return tuple(v.id for v in verificacoes)


def agregar(verificacoes: Sequence[ResultadoVerificacao]) -> Avaliacao:
    resultados = tuple(verificacoes)
    eliminatorias = [v for v in resultados if v.tipo is TipoVerificacao.ELIMINATORIA]
    avisos = _ids(
        [v for v in resultados if v.tipo is not TipoVerificacao.ELIMINATORIA and v.estado in _SEM_RESPOSTA]
    )

    dv = next((v for v in resultados if v.definicao == DV), None)
    if dv is not None and dv.estado is Estado.RESTRICAO:
        return Avaliacao(StatusFinal.CNPJ_INVALIDO, (dv.id,), (), resultados)

    restricoes = [v for v in eliminatorias if v.estado is Estado.RESTRICAO]
    if restricoes:
        return Avaliacao(StatusFinal.INAPTA, _ids(restricoes), avisos, resultados)

    sem_resposta = [v for v in eliminatorias if v.estado in _SEM_RESPOSTA]
    if sem_resposta:
        return Avaliacao(StatusFinal.INCONCLUSIVA, _ids(sem_resposta), avisos, resultados)

    alertas = [v for v in resultados if v.estado is Estado.ALERTA]
    if alertas:
        return Avaliacao(StatusFinal.APTA_COM_RESSALVAS, _ids(alertas), avisos, resultados)

    return Avaliacao(StatusFinal.APTA, (), avisos, resultados)
