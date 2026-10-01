from dataclasses import dataclass

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
from validador_osc.regras.tabelas import AvaliacaoCnae, Tabelas, avaliar_cnaes, resolver_natureza
from validador_osc.regras.verificacoes.cadastro import (
    CadastroObtido,
    nao_verificada,
    referencia_fonte,
    verificar_estabelecimento,
    verificar_natureza,
    verificar_situacao,
    verificar_tempo,
)
from validador_osc.regras.verificacoes.cnae import verificar_cnae, verificar_religiosa
from validador_osc.regras.verificacoes.dv import verificar_dv

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


def _avaliacao_cnae(cadastro: Cadastro, tabelas: Tabelas) -> AvaliacaoCnae | None:
    if cadastro.cnae_principal is None:
        return None
    natureza = resolver_natureza(tabelas.natureza, cadastro.natureza_codigo, cadastro.natureza_descricao)
    return avaliar_cnaes(
        tabelas.cnae,
        natureza.codigo if natureza else cadastro.natureza_codigo,
        cadastro.cnae_principal,
        cadastro.cnaes_secundarios,
    )


def _cadastrais(obtido: CadastroObtido, contexto: Contexto, tabelas: Tabelas) -> list[ResultadoVerificacao]:
    avaliacao = _avaliacao_cnae(obtido.cadastro, tabelas)
    return [
        verificar_estabelecimento(obtido),
        verificar_natureza(obtido, tabelas.natureza),
        verificar_cnae(obtido, tabelas.cnae, avaliacao),
        verificar_religiosa(obtido, avaliacao),
        verificar_tempo(obtido, contexto),
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

    resultados: list[ResultadoVerificacao] = [dv, verificar_situacao(dados.cadastro, contexto)]
    if isinstance(dados.cadastro, Obtido):
        obtido = CadastroObtido(dados.cadastro.dados, referencia_fonte(dados.cadastro))
        resultados.extend(_cadastrais(obtido, contexto, tabelas))
    else:
        resultados.extend(nao_verificada(d) for d in CADASTRAIS if d != SITUACAO)

    pendentes: list[DefinicaoVerificacao] = [d for d in CATALOGO if d != DV and d not in CADASTRAIS]
    resultados.extend(nao_verificada(d, MENSAGEM_SEM_FONTE) for d in pendentes)
    return agregar(_ordenar(resultados))
