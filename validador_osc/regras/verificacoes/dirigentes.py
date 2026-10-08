from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date

from validador_osc.dominio.bases import ConsultaLocal
from validador_osc.dominio.pessoa_fisica import calcular_dvs, fragmento_cpf
from validador_osc.dominio.resultado import Achado, Contexto, Estado, RefFonte, ResultadoVerificacao
from validador_osc.dominio.sancoes import RegistroListaTcu, RegistroTcesp, Sancao
from validador_osc.dominio.tipos import Dirigente
from validador_osc.regras.catalogo import DIRIGENTES
from validador_osc.regras.parametros import Limites
from validador_osc.regras.verificacoes.cadastro import data_br

CATEGORIAS_FORA_ART39 = ("demissão", "demissao", "suspensão", "suspensao")
_DIGITOS_INICIO_TCESP = 3


@dataclass(frozen=True, slots=True)
class ConsultaDirigente:
    dirigente: Dirigente
    ceis: ConsultaLocal[Sancao] | None = None
    cnep: ConsultaLocal[Sancao] | None = None
    contas_irregulares: ConsultaLocal[RegistroListaTcu] | None = None
    inabilitados: ConsultaLocal[RegistroListaTcu] | None = None
    tcesp: ConsultaLocal[RegistroTcesp] | None = None


@dataclass(frozen=True, slots=True)
class ObservacoesDirigentes:
    consultas: tuple[ConsultaDirigente, ...] = ()
    sem_fragmento: tuple[Dirigente, ...] = ()


@dataclass(slots=True)
class _Apuracao:
    alertas: list[Achado] = field(default_factory=list)
    historico: list[Achado] = field(default_factory=list)
    fontes: dict[str, RefFonte] = field(default_factory=dict)
    verificadas: set[str] = field(default_factory=set)
    indisponiveis: set[str] = field(default_factory=set)


def _menos_anos(referencia: date, anos: int) -> date:
    try:
        return referencia.replace(year=referencia.year - anos)
    except ValueError:
        return date(referencia.year - anos, 2, 28)


def _valida[T](consulta: ConsultaLocal[T] | None, limites: Limites, contexto: Contexto) -> bool:
    if consulta is None:
        return False
    carga = consulta.carga
    base = carga.data_base or carga.concluida_em.date()
    return contexto.data_referencia - base <= limites.idade_maxima_de(carga.fonte)


def _registrar[T](
    apuracao: _Apuracao, nome_fonte: str, consulta: ConsultaLocal[T] | None, valida: bool
) -> None:
    if not valida or consulta is None:
        apuracao.indisponiveis.add(nome_fonte)
        return
    apuracao.verificadas.add(nome_fonte)
    carga = consulta.carga
    apuracao.fontes[carga.fonte] = RefFonte(
        fonte=carga.fonte,
        obtida_em=carga.concluida_em,
        data_base=carga.data_base,
        carga_id=carga.id,
        sha256=carga.arquivo_sha256,
    )


def _achado(dirigente: Dirigente, fonte: str, hipotese: str, detalhe: str, processo: str | None) -> Achado:
    return Achado(
        "dirigente",
        {
            "nome": dirigente.nome,
            "qualificacao": dirigente.qualificacao,
            "data_entrada": dirigente.data_entrada.isoformat() if dirigente.data_entrada else None,
            "fonte": fonte,
            "hipotese": hipotese,
            "detalhe": detalhe,
            "processo": processo,
        },
    )


def _sancoes(
    apuracao: _Apuracao,
    dirigente: Dirigente,
    nome_fonte: str,
    consulta: ConsultaLocal[Sancao],
    referencia: date,
) -> None:
    for sancao in consulta.registros:
        vigente = sancao.data_fim is None or sancao.data_fim >= referencia
        categoria = sancao.categoria or "sanção"
        fim = data_br(sancao.data_fim) if sancao.data_fim else "sem data final"
        detalhe = f"{categoria} até {fim}, {sancao.orgao or 'órgão não informado'}"
        fora_art39 = categoria.casefold().startswith(CATEGORIAS_FORA_ART39)
        destino = apuracao.alertas if vigente and not fora_art39 else apuracao.historico
        destino.append(_achado(dirigente, nome_fonte, "art. 39, V e VII, c", detalhe, sancao.processo))


def _contas(
    apuracao: _Apuracao,
    dirigente: Dirigente,
    consulta: ConsultaLocal[RegistroListaTcu],
    referencia: date,
    inicio_janela: date,
) -> None:
    for registro in consulta.registros:
        dentro = registro.data_transito is not None and inicio_janela <= registro.data_transito <= referencia
        detalhe = (
            f"contas julgadas irregulares, trânsito em julgado em {data_br(registro.data_transito)}; "
            "a lista não informa se a conta é de parceria, confira o acórdão"
        )
        destino = apuracao.alertas if dentro else apuracao.historico
        destino.append(
            _achado(dirigente, "TCU contas irregulares", "art. 39, VII, a", detalhe, registro.processo)
        )


def _inabilitados(
    apuracao: _Apuracao, dirigente: Dirigente, consulta: ConsultaLocal[RegistroListaTcu], referencia: date
) -> None:
    for registro in consulta.registros:
        vigente = registro.data_final is None or registro.data_final >= referencia
        fim = data_br(registro.data_final) if registro.data_final else "sem data final"
        detalhe = f"inabilitado para cargo em comissão ou função de confiança até {fim}"
        destino = apuracao.alertas if vigente else apuracao.historico
        destino.append(_achado(dirigente, "TCU inabilitados", "art. 39, VII, b", detalhe, registro.processo))


def _tcesp(
    apuracao: _Apuracao,
    dirigente: Dirigente,
    meio: str,
    consulta: ConsultaLocal[RegistroTcesp],
    referencia: date,
    inicio_janela: date,
) -> None:
    for registro in consulta.registros:
        if len(registro.cpf_inicio) != _DIGITOS_INICIO_TCESP or not registro.cpf_inicio.isdecimal():
            continue
        if calcular_dvs(registro.cpf_inicio + meio) != registro.cpf_fim:
            continue
        dentro = registro.data_transito is not None and inicio_janela <= registro.data_transito <= referencia
        detalhe = (
            f"prestação de contas de repasse ao Terceiro Setor julgada irregular pelo TCE-SP, "
            f"trânsito em julgado em {data_br(registro.data_transito)}"
        )
        destino = apuracao.alertas if dentro else apuracao.historico
        destino.append(
            _achado(dirigente, "TCE-SP Terceiro Setor", "art. 39, VII, a", detalhe, registro.processo)
        )


def _apurar(obs: ObservacoesDirigentes, contexto: Contexto, limites: Limites) -> _Apuracao:
    apuracao = _Apuracao()
    referencia = contexto.data_referencia
    inicio_janela = _menos_anos(referencia, limites.janela_contas_irregulares_anos)
    for consulta in obs.consultas:
        dirigente = consulta.dirigente
        fragmento = fragmento_cpf(dirigente.documento_mascarado or "")
        if fragmento is None:
            continue
        for nome_fonte, local in (("CEIS", consulta.ceis), ("CNEP", consulta.cnep)):
            valida = _valida(local, limites, contexto)
            _registrar(apuracao, nome_fonte, local, valida)
            if valida and local is not None:
                _sancoes(apuracao, dirigente, nome_fonte, local, referencia)
        valida = _valida(consulta.contas_irregulares, limites, contexto)
        _registrar(apuracao, "TCU contas irregulares", consulta.contas_irregulares, valida)
        if valida and consulta.contas_irregulares is not None:
            _contas(apuracao, dirigente, consulta.contas_irregulares, referencia, inicio_janela)
        valida = _valida(consulta.inabilitados, limites, contexto)
        _registrar(apuracao, "TCU inabilitados", consulta.inabilitados, valida)
        if valida and consulta.inabilitados is not None:
            _inabilitados(apuracao, dirigente, consulta.inabilitados, referencia)
        valida = _valida(consulta.tcesp, limites, contexto)
        _registrar(apuracao, "TCE-SP Terceiro Setor", consulta.tcesp, valida)
        if valida and consulta.tcesp is not None:
            _tcesp(apuracao, dirigente, fragmento.meio, consulta.tcesp, referencia, inicio_janela)
    apuracao.indisponiveis -= apuracao.verificadas
    return apuracao


def _lista(nomes: Sequence[str]) -> str:
    return ", ".join(sorted(nomes))


AVISO_LIMITES = (
    "A Receita costuma listar só o presidente; outros diretores podem não ter sido verificados. "
    "Não cobre o art. 39, III, outros tribunais de contas nem condenações do CNJ sem proibição de contratar."
)


def verificar_dirigentes(
    obs: ObservacoesDirigentes, contexto: Contexto, limites: Limites
) -> ResultadoVerificacao:
    pessoas = [c for c in obs.consultas if fragmento_cpf(c.dirigente.documento_mascarado or "")]
    if not pessoas:
        return ResultadoVerificacao(
            DIRIGENTES,
            Estado.OK,
            "O quadro de sócios e administradores não traz pessoa física com CPF parcial; nada a casar.",
        )
    apuracao = _apurar(obs, contexto, limites)
    fontes = tuple(apuracao.fontes.values())
    achados = (*apuracao.alertas, *apuracao.historico)
    if not apuracao.verificadas:
        return ResultadoVerificacao(
            DIRIGENTES,
            Estado.INDISPONIVEL,
            "Nenhuma base de pessoas sancionadas está disponível ou dentro da validade.",
        )
    nao_verificadas = (
        f" Não verificado em: {_lista(list(apuracao.indisponiveis))}." if apuracao.indisponiveis else ""
    )
    if apuracao.alertas:
        pessoas_alerta = {str(a.dados["nome"]) for a in apuracao.alertas}
        return ResultadoVerificacao(
            DIRIGENTES,
            Estado.ALERTA,
            f"Possível impedimento (art. 39, VII): {len(pessoas_alerta)} dirigente(s) com correspondência "
            "de nome e CPF parcial em listas de sanção. Confira o CPF no documento oficial."
            + nao_verificadas
            + " "
            + AVISO_LIMITES,
            achados,
            fontes,
        )
    historico = (
        " Há registros antigos ou fora das hipóteses do art. 39 (histórico)." if apuracao.historico else ""
    )
    return ResultadoVerificacao(
        DIRIGENTES,
        Estado.OK,
        f"Nenhum dos {len(pessoas)} dirigente(s) pessoa física encontrado em: "
        f"{_lista(list(apuracao.verificadas))}." + historico + nao_verificadas + " " + AVISO_LIMITES,
        achados,
        fontes,
    )
