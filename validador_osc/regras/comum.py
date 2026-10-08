from dataclasses import dataclass
from datetime import date

from validador_osc.dominio.coleta import Obtido
from validador_osc.dominio.resultado import DefinicaoVerificacao, Estado, RefFonte, ResultadoVerificacao
from validador_osc.dominio.tipos import Cadastro

MENSAGEM_SEM_CADASTRO = "Não verificado: os dados cadastrais do CNPJ não foram obtidos."


@dataclass(frozen=True, slots=True)
class CadastroObtido:
    cadastro: Cadastro
    fonte: RefFonte


def data_br(valor: date | None) -> str:
    return valor.strftime("%d/%m/%Y") if valor else "data não informada"


def referencia_fonte(coleta: Obtido[Cadastro]) -> RefFonte:
    evidencia = coleta.evidencia
    return RefFonte(
        fonte=evidencia.fonte,
        obtida_em=evidencia.recebida_em,
        data_base=coleta.dados.data_base,
        de_cache=evidencia.de_cache,
        evidencia_id=evidencia.id,
        sha256=evidencia.sha256,
    )


def nao_verificada(
    definicao: DefinicaoVerificacao, mensagem: str = MENSAGEM_SEM_CADASTRO
) -> ResultadoVerificacao:
    return ResultadoVerificacao(definicao, Estado.NAO_VERIFICADO, mensagem)
