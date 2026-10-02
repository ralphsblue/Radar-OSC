from dataclasses import dataclass, replace

from validador_osc.cnpj import eh_alfanumerico, validar
from validador_osc.dominio.coleta import Coleta, Obtido
from validador_osc.dominio.resultado import (
    Avaliacao,
    Contexto,
    DefinicaoVerificacao,
    Estado,
    ResultadoVerificacao,
)
from validador_osc.dominio.tipos import Cadastro
from validador_osc.regras.agregacao import agregar
from validador_osc.regras.catalogo import (
    CATALOGO,
    CNAE,
    DV,
    ESTABELECIMENTO,
    NATUREZA,
    RELIGIOSA,
    SITUACAO,
    TEMPO,
)
from validador_osc.regras.entidade import Entidade, resolver_entidade
from validador_osc.regras.tabelas import AvaliacaoCnae, Tabelas, avaliar_cnaes, resolver_natureza
from validador_osc.regras.verificacoes.cadastro import (
    nao_verificada,
    verificar_natureza,
    verificar_situacao,
    verificar_tempo,
)
from validador_osc.regras.verificacoes.cnae import verificar_cnae, verificar_religiosa
from validador_osc.regras.verificacoes.dv import verificar_dv
from validador_osc.regras.verificacoes.estabelecimento import (
    verificar_estabelecimento,
    verificar_situacao_entidade,
)

MENSAGEM_ALFANUMERICO = (
    "CNPJ alfanumérico ainda não é consultado nas fontes nesta versão; "
    "nenhuma verificação cadastral foi feita."
)
MENSAGEM_SEM_FONTE = "Verificação ainda não disponível nesta versão."

CADASTRAIS = frozenset({SITUACAO, ESTABELECIMENTO, NATUREZA, CNAE, RELIGIOSA, TEMPO})


@dataclass(frozen=True, slots=True)
class DadosConsulta:
    cnpj_informado: str
    cadastro: Coleta[Cadastro] | None = None
    matriz: Coleta[Cadastro] | None = None


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

    pendentes: list[DefinicaoVerificacao] = [d for d in CATALOGO if d != DV and d not in CADASTRAIS]
    resultados.extend(nao_verificada(d, MENSAGEM_SEM_FONTE) for d in pendentes)
    return agregar(_ordenar(resultados))
