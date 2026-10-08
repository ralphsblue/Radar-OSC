from dataclasses import dataclass

from validador_osc.regras.parametros import (
    Limites,
    RegrasOrientador,
    carregar_limites,
    carregar_regras_orientador,
)
from validador_osc.regras.tabelas.cnae import TabelaCnae, carregar_tabela_cnae
from validador_osc.regras.tabelas.natureza import TabelaNatureza, carregar_tabela_natureza


@dataclass(frozen=True, slots=True)
class Tabelas:
    cnae: TabelaCnae
    natureza: TabelaNatureza
    orientador: RegrasOrientador
    limites: Limites


def carregar_tabelas() -> Tabelas:
    return Tabelas(
        cnae=carregar_tabela_cnae(),
        natureza=carregar_tabela_natureza(),
        orientador=carregar_regras_orientador(),
        limites=carregar_limites(),
    )
