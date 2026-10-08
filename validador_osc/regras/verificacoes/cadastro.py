from calendar import isleap
from datetime import date

from validador_osc.dominio.coleta import Coleta, Falha, NaoEncontrado, Obtido
from validador_osc.dominio.consulta import Contexto, Esfera
from validador_osc.dominio.resultado import (
    Achado,
    Estado,
    ResultadoVerificacao,
)
from validador_osc.dominio.tipos import Cadastro, SituacaoCadastral
from validador_osc.regras.catalogo import NATUREZA, SITUACAO, TEMPO
from validador_osc.regras.comum import CadastroObtido, data_br, referencia_fonte
from validador_osc.regras.parametros import carregar_limites
from validador_osc.regras.tabelas.natureza import RegraNatureza, TabelaNatureza, resolver_natureza

IDADE_MAXIMA_ESPELHO = carregar_limites().idade_maxima_espelho
PRAZO_ANOS: dict[Esfera, int] = {Esfera.MUNICIPIO: 1, Esfera.ESTADO: 2, Esfera.UNIAO: 3}
NOME_ESFERA: dict[Esfera, str] = {
    Esfera.MUNICIPIO: "municípios",
    Esfera.ESTADO: "estados e Distrito Federal",
    Esfera.UNIAO: "a União",
}
_FEVEREIRO = 2
_DIA_BISSEXTO = 29


def _desde(valor: date | None) -> str:
    return f" desde {data_br(valor)}" if valor else ""


def verificar_situacao(coleta: Coleta[Cadastro], contexto: Contexto) -> ResultadoVerificacao:
    match coleta:
        case NaoEncontrado(data_base=data_base):
            sufixo = f" de {data_br(data_base)}" if data_base else ""
            return ResultadoVerificacao(
                SITUACAO,
                Estado.INDISPONIVEL,
                f"CNPJ não encontrado na base cadastral{sufixo}. Pode ser um CNPJ inexistente ou aberto "
                "depois da última atualização da base.",
                situacao="NAO_ENCONTRADO",
            )
        case Falha(motivo=motivo):
            return ResultadoVerificacao(
                SITUACAO,
                Estado.INDISPONIVEL,
                f"A fonte cadastral não respondeu ({motivo}). Tente de novo em alguns minutos.",
                situacao="FONTE_INDISPONIVEL",
            )
        case Obtido(dados=cadastro):
            return avaliar_situacao(CadastroObtido(cadastro, referencia_fonte(coleta)), contexto)


def avaliar_situacao(obtido: CadastroObtido, contexto: Contexto, sujeito: str = "") -> ResultadoVerificacao:
    cadastro = obtido.cadastro
    fontes = (obtido.fonte,)
    if cadastro.situacao is not SituacaoCadastral.ATIVA:
        explicacao = f" Motivo: {cadastro.motivo_descricao}." if cadastro.motivo_descricao else ""
        return ResultadoVerificacao(
            SITUACAO,
            Estado.RESTRICAO,
            f"{sujeito}Situação {cadastro.situacao.name}{_desde(cadastro.situacao_data)}."
            f"{explicacao} A Lei 13.019/2014 exige cadastro ativo.",
            fontes=fontes,
        )
    base = cadastro.data_base
    if base is not None and contexto.data_referencia - base > IDADE_MAXIMA_ESPELHO:
        return ResultadoVerificacao(
            SITUACAO,
            Estado.ALERTA,
            f"{sujeito}Situação ATIVA, mas a base cadastral é de {data_br(base)}. "
            "Confirme no site da Receita.",
            fontes=fontes,
        )
    return ResultadoVerificacao(
        SITUACAO,
        Estado.OK,
        f"{sujeito}Situação ATIVA{_desde(cadastro.situacao_data)}.",
        fontes=fontes,
    )


def verificar_natureza(obtido: CadastroObtido, tabela: TabelaNatureza) -> ResultadoVerificacao:
    cadastro = obtido.cadastro
    natureza = resolver_natureza(tabela, cadastro.natureza_codigo, cadastro.natureza_descricao)
    fontes = (obtido.fonte,)
    if natureza is None:
        return ResultadoVerificacao(
            NATUREZA,
            Estado.ALERTA,
            f"Natureza jurídica não reconhecida ({cadastro.natureza_descricao or 'não informada'}). "
            "Confira manualmente se é compatível com OSC.",
            fontes=fontes,
        )
    rotulo = f"{natureza.codigo_formatado} ({natureza.descricao})"
    achado = (Achado("natureza", {"codigo": natureza.codigo, "regra": natureza.regra.value}),)
    match natureza.regra:
        case RegraNatureza.ELEGIVEL | RegraNatureza.ELEGIVEL_COM_ALERTA_RELIGIOSO:
            return ResultadoVerificacao(
                NATUREZA, Estado.OK, f"Natureza jurídica {rotulo} é compatível com OSC.", achado, fontes
            )
        case RegraNatureza.REVISAO_MANUAL:
            return ResultadoVerificacao(
                NATUREZA,
                Estado.ALERTA,
                f"Natureza jurídica {rotulo} exige revisão manual: só alguns casos são OSC "
                f"(Lei 13.019/2014, art. 2º, I). {natureza.justificativa}",
                achado,
                fontes,
            )
        case RegraNatureza.NAO_ELEGIVEL:
            return ResultadoVerificacao(
                NATUREZA,
                Estado.RESTRICAO,
                f"Natureza jurídica {rotulo} não é compatível com OSC (Lei 13.019/2014, art. 2º, I).",
                achado,
                fontes,
            )


def _anos(quantidade: int) -> str:
    return f"{quantidade} ano{'s' if quantidade != 1 else ''}"


def anos_completos(inicio: date, referencia: date) -> int:
    aniversario = (inicio.month, inicio.day)
    if aniversario == (_FEVEREIRO, _DIA_BISSEXTO) and not isleap(referencia.year):
        aniversario = (_FEVEREIRO, _DIA_BISSEXTO - 1)
    anos = referencia.year - inicio.year
    return anos - 1 if (referencia.month, referencia.day) < aniversario else anos


def verificar_tempo(obtido: CadastroObtido, contexto: Contexto) -> ResultadoVerificacao:
    inicio = obtido.cadastro.data_inicio
    fontes = (obtido.fonte,)
    if inicio is None:
        return ResultadoVerificacao(
            TEMPO, Estado.INDISPONIVEL, "Data de início de atividade não informada na base.", fontes=fontes
        )
    anos = anos_completos(inicio, contexto.data_referencia)
    atendidas = [e for e, prazo in PRAZO_ANOS.items() if anos >= prazo]
    cenarios = tuple(
        Achado("cenario_esfera", {"esfera": e.value, "prazo_anos": prazo, "atende": anos >= prazo})
        for e, prazo in PRAZO_ANOS.items()
    )
    tempo = f"{_anos(anos)} completo{'s' if anos != 1 else ''} desde {data_br(inicio)}"
    esfera = contexto.esfera
    if esfera is not None:
        prazo = PRAZO_ANOS[esfera]
        if anos >= prazo:
            mensagem = f"{tempo}: atende o prazo de {_anos(prazo)} exigido para {NOME_ESFERA[esfera]}."
            return ResultadoVerificacao(TEMPO, Estado.OK, mensagem, cenarios, fontes)
        mensagem = (
            f"{tempo}: não atende o prazo de {_anos(prazo)} exigido para {NOME_ESFERA[esfera]} "
            "(art. 33, V, a). O gestor pode reduzir o prazo quando nenhuma organização o atingir."
        )
        return ResultadoVerificacao(TEMPO, Estado.ALERTA, mensagem, cenarios, fontes)
    if len(atendidas) == len(PRAZO_ANOS):
        return ResultadoVerificacao(
            TEMPO, Estado.OK, f"{tempo}: atende o prazo para municípios, estados e a União.", cenarios, fontes
        )
    if not atendidas:
        mensagem = f"{tempo}: ainda não atinge o prazo mínimo de 1 ano para nenhuma esfera (art. 33, V, a)."
    else:
        nomes = ", ".join(NOME_ESFERA[e] for e in atendidas)
        faltam = " e ".join(
            f"de {_anos(p)} para {NOME_ESFERA[e]}" for e, p in PRAZO_ANOS.items() if e not in atendidas
        )
        mensagem = f"{tempo}: atende o prazo para {nomes}; o prazo é {faltam} (art. 33, V, a)."
    return ResultadoVerificacao(TEMPO, Estado.ALERTA, mensagem, cenarios, fontes)
