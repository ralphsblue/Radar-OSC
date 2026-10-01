from dataclasses import dataclass
from datetime import date
from enum import IntEnum


class SituacaoCadastral(IntEnum):
    NULA = 1
    ATIVA = 2
    SUSPENSA = 3
    INAPTA = 4
    BAIXADA = 8


@dataclass(frozen=True, slots=True)
class Dirigente:
    nome: str
    qualificacao: str | None
    data_entrada: date | None
    documento_mascarado: str | None
    pessoa_fisica: bool


@dataclass(frozen=True, slots=True)
class Cadastro:
    cnpj: str
    razao_social: str
    nome_fantasia: str | None
    situacao: SituacaoCadastral
    situacao_data: date | None
    motivo_codigo: int | None
    motivo_descricao: str | None
    matriz: bool
    natureza_codigo: int | None
    natureza_descricao: str | None
    cnae_principal: str | None
    cnaes_secundarios: tuple[str, ...]
    data_inicio: date | None
    uf: str | None
    municipio: str | None
    qsa: tuple[Dirigente, ...]
    fonte: str
    data_base: date | None
