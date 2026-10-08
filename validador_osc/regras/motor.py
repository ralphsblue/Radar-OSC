from dataclasses import dataclass, replace

from validador_osc.dominio.cnpj import eh_alfanumerico, validar
from validador_osc.dominio.coleta import Coleta, Obtido
from validador_osc.dominio.consulta import Contexto
from validador_osc.dominio.resultado import Avaliacao, Estado, ResultadoVerificacao
from validador_osc.dominio.tipos import Cadastro, PerfilMapa
from validador_osc.regras.agregacao import agregar
from validador_osc.regras.catalogo import (
    CATALOGO,
    CEIS,
    CEPIM,
    CNAE,
    CNEP,
    CNJ_CNIA,
    DIRIGENTES,
    DV,
    ESTABELECIMENTO,
    MAPA_OSC,
    NATUREZA,
    RELIGIOSA,
    SITUACAO,
    TCU_CONTAS_IRREGULARES,
    TCU_INIDONEOS,
    TEMPO,
)
from validador_osc.regras.entidade import Entidade, resolver_entidade
from validador_osc.regras.parametros import ContasIrregulares
from validador_osc.regras.tabelas import AvaliacaoCnae, Tabelas, avaliar_cnaes, resolver_natureza
from validador_osc.regras.verificacoes.cadastro import (
    nao_verificada,
    verificar_natureza,
    verificar_situacao,
    verificar_tempo,
)
from validador_osc.regras.verificacoes.cnae import verificar_cnae, verificar_religiosa
from validador_osc.regras.verificacoes.dirigentes import ObservacoesDirigentes, verificar_dirigentes
from validador_osc.regras.verificacoes.dv import verificar_dv
from validador_osc.regras.verificacoes.estabelecimento import (
    verificar_estabelecimento,
    verificar_situacao_entidade,
)
from validador_osc.regras.verificacoes.mapa import verificar_mapa_osc
from validador_osc.regras.verificacoes.sancoes import (
    ObservacoesSancoes,
    verificar_ceis,
    verificar_cepim,
    verificar_cnep,
    verificar_cnj_cnia,
    verificar_tcu_contas_irregulares,
    verificar_tcu_inidoneos,
)

MENSAGEM_ALFANUMERICO = (
    "CNPJ alfanumérico ainda não é consultado nas fontes nesta versão; "
    "nenhuma verificação cadastral foi feita."
)
MENSAGEM_SEM_FONTE = "Verificação ainda não disponível nesta versão."

CADASTRAIS = frozenset({SITUACAO, ESTABELECIMENTO, NATUREZA, CNAE, RELIGIOSA, TEMPO})
SANCOES = frozenset({CEPIM, CEIS, CNEP, TCU_INIDONEOS, CNJ_CNIA, TCU_CONTAS_IRREGULARES})


@dataclass(frozen=True, slots=True)
class DadosConsulta:
    cnpj_informado: str
    cadastro: Coleta[Cadastro] | None = None
    matriz: Coleta[Cadastro] | None = None
    sancoes: ObservacoesSancoes | None = None
    mapa: Coleta[PerfilMapa] | None = None
    dirigentes: ObservacoesDirigentes | None = None


def _avaliacao_cnae(entidade: Entidade, tabelas: Tabelas) -> AvaliacaoCnae | None:
    cadastro = entidade.avaliado.cadastro
    principal, secundarios = entidade.cnaes
    if principal is None:
        return None
    natureza = resolver_natureza(tabelas.natureza, cadastro.natureza_codigo, cadastro.natureza_descricao)
    return avaliar_cnaes(
        tabelas.cnae,
        natureza.codigo if natureza else cadastro.natureza_codigo,
        principal,
        secundarios,
    )


def _cadastrais(entidade: Entidade, contexto: Contexto, tabelas: Tabelas) -> list[ResultadoVerificacao]:
    avaliado = entidade.avaliado
    avaliacao = _avaliacao_cnae(entidade, tabelas)
    return [
        verificar_situacao_entidade(entidade, contexto),
        verificar_estabelecimento(entidade),
        verificar_natureza(avaliado, tabelas.natureza),
        replace(verificar_cnae(avaliado, tabelas.cnae, avaliacao), fontes=entidade.fontes),
        replace(verificar_religiosa(avaliado, avaliacao), fontes=entidade.fontes),
        verificar_tempo(avaliado, contexto),
    ]


def _ordenar(resultados: list[ResultadoVerificacao]) -> list[ResultadoVerificacao]:
    por_id = {r.definicao: r for r in resultados}
    return [por_id[d] for d in CATALOGO if d in por_id]


def avaliar(dados: DadosConsulta, contexto: Contexto, tabelas: Tabelas) -> Avaliacao:
    resultado_dv = validar(dados.cnpj_informado)
    dv = verificar_dv(resultado_dv)
    if dv.estado is Estado.RESTRICAO:
        return agregar([dv])

    if eh_alfanumerico(resultado_dv.cnpj) or dados.cadastro is None:
        mensagem = MENSAGEM_ALFANUMERICO if eh_alfanumerico(resultado_dv.cnpj) else MENSAGEM_SEM_FONTE
        return agregar([dv, *(nao_verificada(d, mensagem) for d in CATALOGO if d != DV)])

    resultados: list[ResultadoVerificacao] = [dv]
    if isinstance(dados.cadastro, Obtido):
        resultados.extend(_cadastrais(resolver_entidade(dados.cadastro, dados.matriz), contexto, tabelas))
    else:
        resultados.append(verificar_situacao(dados.cadastro, contexto))
        resultados.extend(nao_verificada(d) for d in CADASTRAIS if d != SITUACAO)

    if dados.sancoes is not None:
        resultados.extend(_sancoes(dados.sancoes, contexto, tabelas))
    else:
        resultados.extend(nao_verificada(d, MENSAGEM_SEM_FONTE) for d in SANCOES)

    if dados.mapa is not None:
        resultados.append(verificar_mapa_osc(dados.mapa))
    else:
        resultados.append(nao_verificada(MAPA_OSC, MENSAGEM_SEM_FONTE))

    if dados.dirigentes is not None:
        resultados.append(verificar_dirigentes(dados.dirigentes, contexto, tabelas.limites))
    else:
        resultados.append(nao_verificada(DIRIGENTES, MENSAGEM_SEM_FONTE))

    tratadas = CADASTRAIS | SANCOES | {DV, MAPA_OSC, DIRIGENTES}
    resultados.extend(nao_verificada(d, MENSAGEM_SEM_FONTE) for d in CATALOGO if d not in tratadas)
    return agregar(_ordenar(_ativas(resultados, tabelas)))


def _sancoes(obs: ObservacoesSancoes, contexto: Contexto, tabelas: Tabelas) -> list[ResultadoVerificacao]:
    regras, limites = tabelas.orientador, tabelas.limites
    return [
        verificar_cepim(obs, contexto, regras, limites),
        verificar_ceis(obs, contexto, regras, limites),
        verificar_cnep(obs, contexto, regras, limites),
        verificar_tcu_inidoneos(obs, contexto, regras, limites),
        verificar_cnj_cnia(obs, contexto, regras),
        verificar_tcu_contas_irregulares(obs, contexto, regras, limites),
    ]


def _ativas(resultados: list[ResultadoVerificacao], tabelas: Tabelas) -> list[ResultadoVerificacao]:
    if tabelas.orientador.contas_irregulares is ContasIrregulares.NAO_USAR:
        return [r for r in resultados if r.definicao != TCU_CONTAS_IRREGULARES]
    return resultados
