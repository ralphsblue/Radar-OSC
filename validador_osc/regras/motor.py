from dataclasses import dataclass

from validador_osc.cnpj import eh_alfanumerico, validar
from validador_osc.dominio.resultado import (
    Avaliacao,
    Contexto,
    DefinicaoVerificacao,
    Estado,
    ResultadoVerificacao,
)
from validador_osc.regras.agregacao import agregar
from validador_osc.regras.catalogo import CATALOGO, DV
from validador_osc.regras.verificacoes.dv import verificar_dv

MENSAGEM_ALFANUMERICO = (
    "CNPJ alfanumérico ainda não é consultado nas fontes nesta versão; "
    "nenhuma verificação cadastral foi feita."
)
MENSAGEM_SEM_FONTE = "Verificação ainda não disponível nesta versão."


@dataclass(frozen=True, slots=True)
class DadosConsulta:
    cnpj_informado: str


def _nao_verificada(definicao: DefinicaoVerificacao, mensagem: str) -> ResultadoVerificacao:
    return ResultadoVerificacao(definicao, Estado.NAO_VERIFICADO, mensagem)


def avaliar(dados: DadosConsulta, contexto: Contexto) -> Avaliacao:
    del contexto
    resultado_dv = validar(dados.cnpj_informado)
    dv = verificar_dv(resultado_dv)
    if dv.estado is Estado.RESTRICAO:
        return agregar([dv])

    mensagem = MENSAGEM_ALFANUMERICO if eh_alfanumerico(resultado_dv.cnpj) else MENSAGEM_SEM_FONTE
    demais = [_nao_verificada(d, mensagem) for d in CATALOGO if d != DV]
    return agregar([dv, *demais])
