from collections.abc import Sequence

from validador_osc.dominio.cnpj import formatar
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
    Sancao,
    SituacaoCertidaoTcu,
    TipoCertidaoTcu,
)
from validador_osc.regras.catalogo import CEIS, CEPIM, CNEP
from validador_osc.regras.comum import data_br
from validador_osc.regras.entradas import ObservacoesSancoes
from validador_osc.regras.parametros import (
    AbrangenciaLimitada,
    CepimEsfera,
    CnepMulta,
    Limites,
    Raiz,
    RegrasOrientador,
)
from validador_osc.regras.verificacoes.sancoes_comum import (
    achado_sancao,
    base_valida,
    escopo,
    no_escopo,
    pior_estado,
    ref_local,
    ref_tcu,
    tcu_obtidos,
    vigente,
)


def _deduplicar(registros: Sequence[Sancao]) -> list[Sancao]:
    vistos: set[tuple[object, ...]] = set()
    saida: list[Sancao] = []
    for r in registros:
        chave = (r.documento, r.categoria, r.data_inicio, r.data_fim, r.orgao, r.valor_multa)
        if chave not in vistos:
            vistos.add(chave)
            saida.append(r)
    return saida


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
    if escopo(sancao.documento, obs) == "outro_estabelecimento" and regras.raiz is Raiz.ALERTA:
        estado = Estado.ALERTA
    return estado


def _descrever_sancao(sancao: Sancao, obs: ObservacoesSancoes) -> str:
    periodo = (
        f"{data_br(sancao.data_inicio)} a {data_br(sancao.data_fim) if sancao.data_fim else 'sem data final'}"
    )
    texto = f"{sancao.categoria or 'sanção'} ({periodo}), {sancao.orgao or 'órgão não informado'}"
    if escopo(sancao.documento, obs) != "consultado" and sancao.documento:
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
    local = base_valida(obs.locais.get(cadastro), limites, contexto)
    if local is not None:
        fontes.append(ref_local(local))
        registros = _deduplicar([r for r in local.registros if no_escopo(r.documento, obs, regras.raiz)])

    achados: list[Achado] = []
    vigentes: list[str] = []
    historico: list[str] = []
    pior = Estado.OK
    for sancao in registros:
        if not vigente(sancao.data_fim, referencia):
            historico.append(_descrever_sancao(sancao, obs))
            achados.append(achado_sancao(sancao, obs, None))
            continue
        estado = _estado_sancao(sancao, obs, regras, limites)
        pior = pior_estado(pior, estado)
        vigentes.append(_descrever_sancao(sancao, obs))
        achados.append(achado_sancao(sancao, obs, estado))

    notas: list[str] = []
    documentos_locais = {r.documento for r in registros}
    for cnpj, coleta in tcu_obtidos(obs):
        fontes.append(ref_tcu(coleta))
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
    local = base_valida(obs.locais.get(CadastroSancao.CEPIM), limites, contexto)
    if local is None:
        return ResultadoVerificacao(
            CEPIM, Estado.INDISPONIVEL, "A base do CEPIM não está disponível ou está fora da validade."
        )
    fontes = (ref_local(local),)
    registros = [r for r in local.registros if no_escopo(r.documento, obs, regras.raiz)]
    if not registros:
        return ResultadoVerificacao(CEPIM, Estado.OK, "Nada consta no CEPIM.", fontes=fontes)
    estado = Estado.RESTRICAO
    if regras.cepim is CepimEsfera.SO_UNIAO and contexto.esfera in {Esfera.MUNICIPIO, Esfera.ESTADO}:
        estado = Estado.ALERTA
    if regras.raiz is Raiz.ALERTA and all(
        escopo(r.documento, obs) == "outro_estabelecimento" for r in registros
    ):
        estado = Estado.ALERTA
    itens = [
        f"convênio {r.convenio or 'não informado'} ({r.orgao or 'órgão não informado'}): "
        f"{r.motivo or 'motivo não informado'}"
        + (
            f", estabelecimento {formatar(r.documento)}"
            if r.documento and escopo(r.documento, obs) != "consultado"
            else ""
        )
        for r in registros
    ]
    return ResultadoVerificacao(
        CEPIM,
        estado,
        f"{len(registros)} impedimento(s) no CEPIM (Lei 13.019/2014, art. 39): " + "; ".join(itens) + ".",
        tuple(achado_sancao(r, obs, estado) for r in registros),
        fontes,
    )
