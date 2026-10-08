from dataclasses import dataclass
from enum import StrEnum

from validador_osc.dominio.coleta import Coleta, NaoEncontrado, Obtido
from validador_osc.dominio.resultado import RefFonte
from validador_osc.dominio.tipos import Cadastro
from validador_osc.regras.comum import CadastroObtido, referencia_fonte


class SituacaoMatriz(StrEnum):
    CONSULTADA_E_MATRIZ = "CONSULTADA_E_MATRIZ"
    OBTIDA = "OBTIDA"
    INDISPONIVEL = "INDISPONIVEL"
    NAO_IDENTIFICADA = "NAO_IDENTIFICADA"


@dataclass(frozen=True, slots=True)
class Entidade:
    consultado: CadastroObtido
    matriz: CadastroObtido | None
    situacao_matriz: SituacaoMatriz
    coleta_matriz: Coleta[Cadastro] | None

    @property
    def avaliado(self) -> CadastroObtido:
        return self.matriz if self.matriz is not None else self.consultado

    @property
    def eh_filial(self) -> bool:
        return not self.consultado.cadastro.matriz

    @property
    def fontes(self) -> tuple[RefFonte, ...]:
        if self.matriz is None or self.matriz is self.consultado:
            return (self.consultado.fonte,)
        return (self.consultado.fonte, self.matriz.fonte)

    @property
    def cnaes(self) -> tuple[str | None, tuple[str, ...]]:
        avaliado = self.avaliado.cadastro
        if self.matriz is None or self.matriz is self.consultado:
            return avaliado.cnae_principal, avaliado.cnaes_secundarios
        consultado = self.consultado.cadastro
        extras = tuple(c for c in (consultado.cnae_principal, *consultado.cnaes_secundarios) if c)
        vistos: dict[str, None] = dict.fromkeys((*avaliado.cnaes_secundarios, *extras))
        vistos.pop(avaliado.cnae_principal or "", None)
        return avaliado.cnae_principal, tuple(vistos)


def resolver_entidade(consultado: Obtido[Cadastro], matriz: Coleta[Cadastro] | None) -> Entidade:
    obtido = CadastroObtido(consultado.dados, referencia_fonte(consultado))
    if consultado.dados.matriz:
        return Entidade(obtido, obtido, SituacaoMatriz.CONSULTADA_E_MATRIZ, None)
    match matriz:
        case Obtido(dados=dados) if dados.matriz and dados.cnpj != consultado.dados.cnpj:
            return Entidade(
                obtido, CadastroObtido(dados, referencia_fonte(matriz)), SituacaoMatriz.OBTIDA, matriz
            )
        case Obtido() | NaoEncontrado() | None:
            return Entidade(obtido, None, SituacaoMatriz.NAO_IDENTIFICADA, matriz)
        case _:
            return Entidade(obtido, None, SituacaoMatriz.INDISPONIVEL, matriz)
