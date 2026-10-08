from datetime import date

from validador_osc.dominio.bases import ConsultaLocal
from validador_osc.dominio.coleta import Obtido
from validador_osc.dominio.consulta import Contexto
from validador_osc.dominio.resultado import (
    Achado,
    Estado,
    RefFonte,
)
from validador_osc.dominio.sancoes import (
    ListaTcu,
    RegistroListaTcu,
    RespostaTcu,
    Sancao,
)
from validador_osc.regras.entradas import ObservacoesSancoes
from validador_osc.regras.parametros import (
    Limites,
    Raiz,
    RegrasOrientador,
)

ORDEM_ESTADO = {Estado.OK: 0, Estado.ALERTA: 1, Estado.RESTRICAO: 2}


def pior_estado(a: Estado, b: Estado) -> Estado:
    return a if ORDEM_ESTADO[a] >= ORDEM_ESTADO[b] else b


def vigente(fim: date | None, referencia: date) -> bool:
    return fim is None or fim >= referencia


def escopo(documento: str | None, obs: ObservacoesSancoes) -> str:
    if documento == obs.consultado:
        return "consultado"
    if documento is not None and documento == obs.matriz:
        return "matriz"
    return "outro_estabelecimento"


def base_valida[T](
    consulta: ConsultaLocal[T] | None, limites: Limites, contexto: Contexto
) -> ConsultaLocal[T] | None:
    if consulta is None:
        return None
    carga = consulta.carga
    base = carga.data_base or carga.concluida_em.date()
    if contexto.data_referencia - base > limites.idade_maxima_de(carga.fonte):
        return None
    return consulta


def ref_local[T](consulta: ConsultaLocal[T]) -> RefFonte:
    carga = consulta.carga
    return RefFonte(
        fonte=carga.fonte,
        obtida_em=carga.concluida_em,
        data_base=carga.data_base,
        carga_id=carga.id,
        sha256=carga.arquivo_sha256,
    )


def ref_tcu(coleta: Obtido[RespostaTcu]) -> RefFonte:
    evidencia = coleta.evidencia
    return RefFonte(
        fonte=evidencia.fonte,
        obtida_em=evidencia.recebida_em,
        de_cache=evidencia.de_cache,
        evidencia_id=evidencia.id,
        sha256=evidencia.sha256,
    )


def no_escopo(documento: str | None, obs: ObservacoesSancoes, raiz: Raiz) -> bool:
    return raiz is not Raiz.EXATO or escopo(documento, obs) != "outro_estabelecimento"


def tcu_obtidos(obs: ObservacoesSancoes) -> list[tuple[str, Obtido[RespostaTcu]]]:
    return [(c, coleta) for c in obs.cnpjs if isinstance(coleta := obs.tcu.get(c), Obtido)]


def achado_sancao(sancao: Sancao, obs: ObservacoesSancoes, estado: Estado | None) -> Achado:
    return Achado(
        "sancao",
        {
            "cadastro": sancao.cadastro.value,
            "estabelecimento": sancao.documento,
            "escopo": escopo(sancao.documento, obs),
            "categoria": sancao.categoria,
            "data_inicio": sancao.data_inicio.isoformat() if sancao.data_inicio else None,
            "data_fim": sancao.data_fim.isoformat() if sancao.data_fim else None,
            "orgao": sancao.orgao,
            "abrangencia": sancao.abrangencia,
            "fundamentacao": sancao.fundamentacao,
            "processo": sancao.processo,
            "valor_multa": str(sancao.valor_multa) if sancao.valor_multa is not None else None,
            "motivo": sancao.motivo,
            "convenio": sancao.convenio,
            "vigente": estado is not None,
            "estado": estado.value if estado else None,
        },
    )


def registros_lista(
    lista: ListaTcu, obs: ObservacoesSancoes, regras: RegrasOrientador, limites: Limites, contexto: Contexto
) -> tuple[ConsultaLocal[RegistroListaTcu] | None, list[RegistroListaTcu]]:
    local = base_valida(obs.listas.get(lista), limites, contexto)
    if local is None:
        return None, []
    return local, [r for r in local.registros if no_escopo(r.documento, obs, regras.raiz)]
