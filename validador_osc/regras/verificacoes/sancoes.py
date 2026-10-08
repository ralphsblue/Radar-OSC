import re
from collections.abc import Sequence
from datetime import date

from validador_osc.dominio.bases import ConsultaLocal
from validador_osc.dominio.cnpj import formatar
from validador_osc.dominio.coleta import Obtido
from validador_osc.dominio.consulta import Contexto, Esfera
from validador_osc.dominio.resultado import (
    Achado,
    DefinicaoVerificacao,
    Estado,
    RefFonte,
    ResultadoVerificacao,
)
from validador_osc.dominio.sancoes import (
    CadastroSancao,
    ListaTcu,
    RegistroListaTcu,
    RespostaTcu,
    Sancao,
    SituacaoCertidaoTcu,
    TipoCertidaoTcu,
)
from validador_osc.regras.catalogo import CEIS, CEPIM, CNEP, CNJ_CNIA, TCU_CONTAS_IRREGULARES, TCU_INIDONEOS
from validador_osc.regras.comum import data_br
from validador_osc.regras.entradas import ObservacoesSancoes
from validador_osc.regras.parametros import (
    AbrangenciaLimitada,
    CepimEsfera,
    CnepMulta,
    Cnia,
    ContasIrregulares,
    Limites,
    Raiz,
    RegrasOrientador,
)

_DIGITOS = re.compile(r"\D")
_PROCESSO_MINIMO = 10
_ORDEM_ESTADO = {Estado.OK: 0, Estado.ALERTA: 1, Estado.RESTRICAO: 2}


def _pior(a: Estado, b: Estado) -> Estado:
    return a if _ORDEM_ESTADO[a] >= _ORDEM_ESTADO[b] else b


def _vigente(fim: date | None, referencia: date) -> bool:
    return fim is None or fim >= referencia


def _escopo(documento: str | None, obs: ObservacoesSancoes) -> str:
    if documento == obs.consultado:
        return "consultado"
    if documento is not None and documento == obs.matriz:
        return "matriz"
    return "outro_estabelecimento"


def _base_valida[T](
    consulta: ConsultaLocal[T] | None, limites: Limites, contexto: Contexto
) -> ConsultaLocal[T] | None:
    if consulta is None:
        return None
    carga = consulta.carga
    base = carga.data_base or carga.concluida_em.date()
    if contexto.data_referencia - base > limites.idade_maxima_de(carga.fonte):
        return None
    return consulta


def _ref_local[T](consulta: ConsultaLocal[T]) -> RefFonte:
    carga = consulta.carga
    return RefFonte(
        fonte=carga.fonte,
        obtida_em=carga.concluida_em,
        data_base=carga.data_base,
        carga_id=carga.id,
        sha256=carga.arquivo_sha256,
    )


def _ref_tcu(coleta: Obtido[RespostaTcu]) -> RefFonte:
    evidencia = coleta.evidencia
    return RefFonte(
        fonte=evidencia.fonte,
        obtida_em=evidencia.recebida_em,
        de_cache=evidencia.de_cache,
        evidencia_id=evidencia.id,
        sha256=evidencia.sha256,
    )


def _no_escopo(documento: str | None, obs: ObservacoesSancoes, raiz: Raiz) -> bool:
    return raiz is not Raiz.EXATO or _escopo(documento, obs) != "outro_estabelecimento"


def _tcu_obtidos(obs: ObservacoesSancoes) -> list[tuple[str, Obtido[RespostaTcu]]]:
    return [(c, coleta) for c in obs.cnpjs if isinstance(coleta := obs.tcu.get(c), Obtido)]


def _deduplicar(registros: Sequence[Sancao]) -> list[Sancao]:
    vistos: set[tuple[object, ...]] = set()
    saida: list[Sancao] = []
    for r in registros:
        chave = (r.documento, r.categoria, r.data_inicio, r.data_fim, r.orgao, r.valor_multa)
        if chave not in vistos:
            vistos.add(chave)
            saida.append(r)
    return saida


def _achado_sancao(sancao: Sancao, obs: ObservacoesSancoes, estado: Estado | None) -> Achado:
    return Achado(
        "sancao",
        {
            "cadastro": sancao.cadastro.value,
            "estabelecimento": sancao.documento,
            "escopo": _escopo(sancao.documento, obs),
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


def _estado_sancao(
    sancao: Sancao, obs: ObservacoesSancoes, regras: RegrasOrientador, limites: Limites
) -> Estado:
    estado = Estado.RESTRICAO
    categoria = (sancao.categoria or "").casefold()
    if (
        sancao.cadastro is CadastroSancao.CNEP
        and categoria.startswith(limites.categorias_cnep_fora_art39)
        and regras.cnep_multa is CnepMulta.ALERTA
    ):
        estado = Estado.ALERTA
    abrangencia = (sancao.abrangencia or "").strip().casefold()
    if (
        abrangencia not in limites.abrangencia_total
        and regras.abrangencia_limitada is AbrangenciaLimitada.ALERTA
    ):
        estado = Estado.ALERTA
    if _escopo(sancao.documento, obs) == "outro_estabelecimento" and regras.raiz is Raiz.ALERTA:
        estado = Estado.ALERTA
    return estado


def _descrever_sancao(sancao: Sancao, obs: ObservacoesSancoes) -> str:
    periodo = (
        f"{data_br(sancao.data_inicio)} a {data_br(sancao.data_fim) if sancao.data_fim else 'sem data final'}"
    )
    texto = f"{sancao.categoria or 'sanção'} ({periodo}), {sancao.orgao or 'órgão não informado'}"
    if _escopo(sancao.documento, obs) != "consultado" and sancao.documento:
        texto += f", registrada no estabelecimento {formatar(sancao.documento)}"
    return texto


def verificar_sancao_datada(
    definicao: DefinicaoVerificacao,
    cadastro: CadastroSancao,
    tipo_tcu: TipoCertidaoTcu,
    obs: ObservacoesSancoes,
    contexto: Contexto,
    regras: RegrasOrientador,
    limites: Limites,
) -> ResultadoVerificacao:
    referencia = contexto.data_referencia
    fontes: list[RefFonte] = []
    registros: list[Sancao] = []
    local = _base_valida(obs.locais.get(cadastro), limites, contexto)
    if local is not None:
        fontes.append(_ref_local(local))
        registros = _deduplicar([r for r in local.registros if _no_escopo(r.documento, obs, regras.raiz)])

    achados: list[Achado] = []
    vigentes: list[str] = []
    historico: list[str] = []
    pior = Estado.OK
    for sancao in registros:
        if not _vigente(sancao.data_fim, referencia):
            historico.append(_descrever_sancao(sancao, obs))
            achados.append(_achado_sancao(sancao, obs, None))
            continue
        estado = _estado_sancao(sancao, obs, regras, limites)
        pior = _pior(pior, estado)
        vigentes.append(_descrever_sancao(sancao, obs))
        achados.append(_achado_sancao(sancao, obs, estado))

    notas: list[str] = []
    documentos_locais = {r.documento for r in registros}
    for cnpj, coleta in _tcu_obtidos(obs):
        fontes.append(_ref_tcu(coleta))
        certidao = coleta.dados.certidao(tipo_tcu)
        if certidao is None or certidao.situacao is not SituacaoCertidaoTcu.CONSTAM_REGISTROS:
            continue
        if local is not None and cnpj in documentos_locais:
            continue
        datas = certidao.datas_observacao
        legivel = bool(datas) and len(datas) == (certidao.observacao or "").count("(")
        if legivel and all(d < referencia for d in datas):
            notas.append(
                f"O TCU lista registro para {formatar(cnpj)} com todas as datas já passadas "
                f"({', '.join(data_br(d) for d in datas)}): histórico."
            )
            continue
        pior = Estado.RESTRICAO
        vigentes.append(
            f"registro informado pelo TCU para {formatar(cnpj)}: {certidao.observacao or 'sem detalhe'}"
        )
        achados.append(
            Achado("certidao_tcu", {"cnpj": cnpj, "tipo": tipo_tcu.value, "observacao": certidao.observacao})
        )

    if not fontes:
        return ResultadoVerificacao(
            definicao,
            Estado.INDISPONIVEL,
            f"Nenhuma fonte do {cadastro.value} respondeu ou está dentro da validade.",
        )
    sufixo = (" " + " ".join(notas)) if notas else ""
    if vigentes:
        mensagem = f"{len(vigentes)} registro(s) vigente(s) no {cadastro.value}: " + "; ".join(vigentes) + "."
        return ResultadoVerificacao(definicao, pior, mensagem + sufixo, tuple(achados), tuple(fontes))
    if historico:
        mensagem = (
            f"Nenhuma sanção vigente no {cadastro.value}. Histórico (já encerradas): "
            + "; ".join(historico)
            + "."
        )
    else:
        mensagem = f"Nada consta no {cadastro.value}."
    return ResultadoVerificacao(definicao, Estado.OK, mensagem + sufixo, tuple(achados), tuple(fontes))


def verificar_ceis(
    obs: ObservacoesSancoes, contexto: Contexto, regras: RegrasOrientador, limites: Limites
) -> ResultadoVerificacao:
    return verificar_sancao_datada(
        CEIS, CadastroSancao.CEIS, TipoCertidaoTcu.CEIS, obs, contexto, regras, limites
    )


def verificar_cnep(
    obs: ObservacoesSancoes, contexto: Contexto, regras: RegrasOrientador, limites: Limites
) -> ResultadoVerificacao:
    return verificar_sancao_datada(
        CNEP, CadastroSancao.CNEP, TipoCertidaoTcu.CNEP, obs, contexto, regras, limites
    )


def verificar_cepim(
    obs: ObservacoesSancoes, contexto: Contexto, regras: RegrasOrientador, limites: Limites
) -> ResultadoVerificacao:
    local = _base_valida(obs.locais.get(CadastroSancao.CEPIM), limites, contexto)
    if local is None:
        return ResultadoVerificacao(
            CEPIM, Estado.INDISPONIVEL, "A base do CEPIM não está disponível ou está fora da validade."
        )
    fontes = (_ref_local(local),)
    registros = [r for r in local.registros if _no_escopo(r.documento, obs, regras.raiz)]
    if not registros:
        return ResultadoVerificacao(CEPIM, Estado.OK, "Nada consta no CEPIM.", fontes=fontes)
    estado = Estado.RESTRICAO
    if regras.cepim is CepimEsfera.SO_UNIAO and contexto.esfera in {Esfera.MUNICIPIO, Esfera.ESTADO}:
        estado = Estado.ALERTA
    if regras.raiz is Raiz.ALERTA and all(
        _escopo(r.documento, obs) == "outro_estabelecimento" for r in registros
    ):
        estado = Estado.ALERTA
    itens = [
        f"convênio {r.convenio or 'não informado'} ({r.orgao or 'órgão não informado'}): "
        f"{r.motivo or 'motivo não informado'}"
        + (
            f", estabelecimento {formatar(r.documento)}"
            if r.documento and _escopo(r.documento, obs) != "consultado"
            else ""
        )
        for r in registros
    ]
    return ResultadoVerificacao(
        CEPIM,
        estado,
        f"{len(registros)} impedimento(s) no CEPIM (Lei 13.019/2014, art. 39): " + "; ".join(itens) + ".",
        tuple(_achado_sancao(r, obs, estado) for r in registros),
        fontes,
    )


def _registros_lista(
    lista: ListaTcu, obs: ObservacoesSancoes, regras: RegrasOrientador, limites: Limites, contexto: Contexto
) -> tuple[ConsultaLocal[RegistroListaTcu] | None, list[RegistroListaTcu]]:
    local = _base_valida(obs.listas.get(lista), limites, contexto)
    if local is None:
        return None, []
    return local, [r for r in local.registros if _no_escopo(r.documento, obs, regras.raiz)]


def verificar_tcu_inidoneos(
    obs: ObservacoesSancoes, contexto: Contexto, regras: RegrasOrientador, limites: Limites
) -> ResultadoVerificacao:
    referencia = contexto.data_referencia
    fontes: list[RefFonte] = []
    ocorrencias: list[str] = []
    achados: list[Achado] = []
    notas: list[str] = []
    tcu_completo = all(isinstance(obs.tcu.get(c), Obtido) for c in obs.cnpjs)
    for cnpj, coleta in _tcu_obtidos(obs):
        certidao = coleta.dados.certidao(TipoCertidaoTcu.INIDONEOS)
        if certidao is None or certidao.situacao in {
            SituacaoCertidaoTcu.INDISPONIVEL,
            SituacaoCertidaoTcu.NAO_SUPORTADO,
        }:
            tcu_completo = False
            continue
        fontes.append(_ref_tcu(coleta))
        if not coleta.dados.cnpj_encontrado:
            notas.append(f"O CNPJ {formatar(cnpj)} não consta na base do TCU (informativo).")
        if certidao.situacao is SituacaoCertidaoTcu.CONSTAM_REGISTROS:
            ocorrencias.append(f"TCU ({formatar(cnpj)}): {certidao.observacao or 'registro sem detalhe'}")
            achados.append(
                Achado("certidao_tcu", {"cnpj": cnpj, "tipo": "INIDONEOS", "observacao": certidao.observacao})
            )
    if not tcu_completo:
        fontes.clear()

    local, registros = _registros_lista(ListaTcu.INIDONEOS, obs, regras, limites, contexto)
    pior = Estado.RESTRICAO if ocorrencias else Estado.OK
    if local is not None:
        fontes.append(_ref_local(local))
        for r in registros:
            if not _vigente(r.data_final, referencia):
                notas.append(
                    f"Inidoneidade de {formatar(r.documento or '')} encerrada em "
                    f"{data_br(r.data_final)} (histórico)."
                )
                continue
            estado = (
                Estado.ALERTA
                if regras.raiz is Raiz.ALERTA and _escopo(r.documento, obs) == "outro_estabelecimento"
                else Estado.RESTRICAO
            )
            pior = _pior(pior, estado)
            ocorrencias.append(
                f"lista de inidôneos ({formatar(r.documento or '')}): processo {r.processo or '?'}, "
                f"acórdão {r.acordao or '?'}, "
                f"até {data_br(r.data_final) if r.data_final else 'sem data final'}"
            )
            achados.append(
                Achado("lista_tcu", {"lista": "INIDONEOS", "documento": r.documento, "processo": r.processo})
            )
    if not fontes:
        return ResultadoVerificacao(
            TCU_INIDONEOS,
            Estado.INDISPONIVEL,
            "A Consulta Consolidada do TCU e a lista de inidôneos não responderam.",
        )
    sufixo = (" " + " ".join(notas)) if notas else ""
    if ocorrencias:
        return ResultadoVerificacao(
            TCU_INIDONEOS,
            pior,
            "Declarada inidônea pelo TCU: " + "; ".join(ocorrencias) + "." + sufixo,
            tuple(achados),
            tuple(fontes),
        )
    return ResultadoVerificacao(
        TCU_INIDONEOS,
        Estado.OK,
        "Nada consta na relação de inidôneos do TCU." + sufixo,
        tuple(achados),
        tuple(fontes),
    )


def _processos_ceis(obs: ObservacoesSancoes, processo: str) -> list[Sancao]:
    alvo = _DIGITOS.sub("", processo)
    if len(alvo) < _PROCESSO_MINIMO:
        return []
    local = obs.locais.get(CadastroSancao.CEIS)
    if local is None:
        return []
    return [r for r in local.registros if alvo in _DIGITOS.sub("", r.processo or "")]


def verificar_cnj_cnia(
    obs: ObservacoesSancoes, contexto: Contexto, regras: RegrasOrientador
) -> ResultadoVerificacao:
    referencia = contexto.data_referencia
    fontes: list[RefFonte] = []
    achados: list[Achado] = []
    textos: list[str] = []
    pior = Estado.OK
    indisponivel = False
    for cnpj in obs.cnpjs:
        coleta = obs.tcu.get(cnpj)
        if not isinstance(coleta, Obtido):
            indisponivel = True
            continue
        certidao = coleta.dados.certidao(TipoCertidaoTcu.CNIA)
        if certidao is None or certidao.situacao in {
            SituacaoCertidaoTcu.INDISPONIVEL,
            SituacaoCertidaoTcu.NAO_SUPORTADO,
        }:
            indisponivel = True
            continue
        fontes.append(_ref_tcu(coleta))
        if certidao.situacao is not SituacaoCertidaoTcu.CONSTAM_REGISTROS:
            continue
        processos = certidao.processos or ("",)
        for processo in processos:
            if regras.cnia is Cnia.QUALQUER_REGISTRO:
                estado, texto = Estado.RESTRICAO, "condenação registrada no CNIA"
            else:
                ligados = _processos_ceis(obs, processo) if processo else []
                vigentes = [r for r in ligados if _vigente(r.data_fim, referencia)]
                if vigentes:
                    fim = vigentes[0].data_fim
                    estado = Estado.RESTRICAO
                    texto = f"proibição de contratar vigente até {data_br(fim) if fim else 'sem data final'}"
                elif ligados:
                    estado = Estado.ALERTA
                    texto = f"proibição de contratar encerrada em {data_br(ligados[0].data_fim)} (histórico)"
                else:
                    estado = Estado.ALERTA
                    texto = "sem data das penas nas bases; confira o detalhe no CNIA"
            pior = _pior(pior, estado)
            rotulo = f"processo {processo}" if processo else "registro"
            textos.append(f"{rotulo} ({formatar(cnpj)}): {texto}")
            achados.append(
                Achado("cnia", {"cnpj": cnpj, "processo": processo or None, "estado": estado.value})
            )
    if indisponivel and not textos:
        return ResultadoVerificacao(
            CNJ_CNIA,
            Estado.INDISPONIVEL,
            "O CNIA (via Consulta Consolidada do TCU) não respondeu.",
            fontes=tuple(fontes),
        )
    if textos:
        return ResultadoVerificacao(
            CNJ_CNIA,
            pior,
            "Condenação por improbidade administrativa no CNIA: " + "; ".join(textos) + ".",
            tuple(achados),
            tuple(fontes),
        )
    return ResultadoVerificacao(CNJ_CNIA, Estado.OK, "Nada consta no CNIA.", fontes=tuple(fontes))


def _menos_anos(referencia: date, anos: int) -> date:
    try:
        return referencia.replace(year=referencia.year - anos)
    except ValueError:
        return date(referencia.year - anos, 2, 28)


def verificar_tcu_contas_irregulares(
    obs: ObservacoesSancoes, contexto: Contexto, regras: RegrasOrientador, limites: Limites
) -> ResultadoVerificacao:
    local, registros = _registros_lista(ListaTcu.CONTAS_IRREGULARES, obs, regras, limites, contexto)
    if local is None:
        return ResultadoVerificacao(
            TCU_CONTAS_IRREGULARES,
            Estado.INDISPONIVEL,
            "A lista de contas julgadas irregulares do TCU não está disponível ou está fora da validade.",
        )
    referencia = contexto.data_referencia
    anos = limites.janela_contas_irregulares_anos
    inicio = _menos_anos(referencia, anos)
    dentro = [r for r in registros if r.data_transito and inicio <= r.data_transito <= referencia]
    fora = [r for r in registros if r not in dentro]
    fontes = (_ref_local(local),)

    def texto(r: RegistroListaTcu) -> str:
        return f"processo {r.processo or '?'}, trânsito em julgado em {data_br(r.data_transito)}"

    achados = tuple(
        Achado(
            "lista_tcu",
            {
                "lista": "CONTAS_IRREGULARES",
                "documento": r.documento,
                "processo": r.processo,
                "na_janela": r in dentro,
            },
        )
        for r in registros
    )
    if dentro:
        estado = (
            Estado.RESTRICAO if regras.contas_irregulares is ContasIrregulares.RESTRICAO else Estado.ALERTA
        )
        return ResultadoVerificacao(
            TCU_CONTAS_IRREGULARES,
            estado,
            f"Contas julgadas irregulares pelo TCU nos últimos {anos} anos: "
            + "; ".join(texto(r) for r in dentro)
            + ". A lista não informa se a conta é de parceria (art. 39, VI); confira o acórdão.",
            achados,
            fontes,
        )
    historico = f" Histórico fora da janela: {'; '.join(texto(r) for r in fora)}." if fora else ""
    return ResultadoVerificacao(
        TCU_CONTAS_IRREGULARES,
        Estado.OK,
        f"Nada consta nos últimos {anos} anos na lista de contas irregulares do TCU.{historico}",
        achados,
        fontes,
    )
