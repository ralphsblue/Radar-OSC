import re

from validador_osc.dominio.cnpj import formatar
from validador_osc.dominio.coleta import Obtido
from validador_osc.dominio.consulta import Contexto
from validador_osc.dominio.resultado import (
    Achado,
    Estado,
    RefFonte,
    ResultadoVerificacao,
)
from validador_osc.dominio.sancoes import (
    CadastroSancao,
    ListaTcu,
    RegistroListaTcu,
    Sancao,
    SituacaoCertidaoTcu,
    TipoCertidaoTcu,
)
from validador_osc.regras.catalogo import CNJ_CNIA, TCU_CONTAS_IRREGULARES, TCU_INIDONEOS
from validador_osc.regras.comum import data_br, menos_anos
from validador_osc.regras.entradas import ObservacoesSancoes
from validador_osc.regras.parametros import (
    Cnia,
    ContasIrregulares,
    Limites,
    Raiz,
    RegrasOrientador,
)
from validador_osc.regras.verificacoes.sancoes_comum import (
    escopo,
    pior_estado,
    ref_local,
    ref_tcu,
    registros_lista,
    tcu_obtidos,
    vigente,
)

_DIGITOS = re.compile(r"\D")
_PROCESSO_MINIMO = 10


def verificar_tcu_inidoneos(
    obs: ObservacoesSancoes, contexto: Contexto, regras: RegrasOrientador, limites: Limites
) -> ResultadoVerificacao:
    referencia = contexto.data_referencia
    fontes: list[RefFonte] = []
    ocorrencias: list[str] = []
    achados: list[Achado] = []
    notas: list[str] = []
    tcu_completo = all(isinstance(obs.tcu.get(c), Obtido) for c in obs.cnpjs)
    for cnpj, coleta in tcu_obtidos(obs):
        certidao = coleta.dados.certidao(TipoCertidaoTcu.INIDONEOS)
        if certidao is None or certidao.situacao in {
            SituacaoCertidaoTcu.INDISPONIVEL,
            SituacaoCertidaoTcu.NAO_SUPORTADO,
        }:
            tcu_completo = False
            continue
        fontes.append(ref_tcu(coleta))
        if not coleta.dados.cnpj_encontrado:
            notas.append(f"O CNPJ {formatar(cnpj)} não consta na base do TCU (informativo).")
        if certidao.situacao is SituacaoCertidaoTcu.CONSTAM_REGISTROS:
            ocorrencias.append(f"TCU ({formatar(cnpj)}): {certidao.observacao or 'registro sem detalhe'}")
            achados.append(
                Achado("certidao_tcu", {"cnpj": cnpj, "tipo": "INIDONEOS", "observacao": certidao.observacao})
            )
    if not tcu_completo:
        fontes.clear()

    local, registros = registros_lista(ListaTcu.INIDONEOS, obs, regras, limites, contexto)
    pior = Estado.RESTRICAO if ocorrencias else Estado.OK
    if local is not None:
        fontes.append(ref_local(local))
        for r in registros:
            if not vigente(r.data_final, referencia):
                notas.append(
                    f"Inidoneidade de {formatar(r.documento or '')} encerrada em "
                    f"{data_br(r.data_final)} (histórico)."
                )
                continue
            estado = (
                Estado.ALERTA
                if regras.raiz is Raiz.ALERTA and escopo(r.documento, obs) == "outro_estabelecimento"
                else Estado.RESTRICAO
            )
            pior = pior_estado(pior, estado)
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
        fontes.append(ref_tcu(coleta))
        if certidao.situacao is not SituacaoCertidaoTcu.CONSTAM_REGISTROS:
            continue
        processos = certidao.processos or ("",)
        for processo in processos:
            if regras.cnia is Cnia.QUALQUER_REGISTRO:
                estado, texto = Estado.RESTRICAO, "condenação registrada no CNIA"
            else:
                ligados = _processos_ceis(obs, processo) if processo else []
                vigentes = [r for r in ligados if vigente(r.data_fim, referencia)]
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
            pior = pior_estado(pior, estado)
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


def verificar_tcu_contas_irregulares(
    obs: ObservacoesSancoes, contexto: Contexto, regras: RegrasOrientador, limites: Limites
) -> ResultadoVerificacao:
    local, registros = registros_lista(ListaTcu.CONTAS_IRREGULARES, obs, regras, limites, contexto)
    if local is None:
        return ResultadoVerificacao(
            TCU_CONTAS_IRREGULARES,
            Estado.INDISPONIVEL,
            "A lista de contas julgadas irregulares do TCU não está disponível ou está fora da validade.",
        )
    referencia = contexto.data_referencia
    anos = limites.janela_contas_irregulares_anos
    inicio = menos_anos(referencia, anos)
    dentro = [r for r in registros if r.data_transito and inicio <= r.data_transito <= referencia]
    fora = [r for r in registros if r not in dentro]
    fontes = (ref_local(local),)

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
