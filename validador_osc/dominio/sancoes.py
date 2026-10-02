from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class CadastroSancao(StrEnum):
    CEPIM = "CEPIM"
    CEIS = "CEIS"
    CNEP = "CNEP"


class TipoPessoa(StrEnum):
    JURIDICA = "J"
    FISICA = "F"


@dataclass(frozen=True, slots=True)
class Sancao:
    cadastro: CadastroSancao
    tipo_pessoa: TipoPessoa | None
    documento: str | None
    raiz: str | None
    nome: str
    categoria: str | None
    data_inicio: date | None
    data_fim: date | None
    orgao: str | None
    esfera: str | None
    uf: str | None
    abrangencia: str | None
    fundamentacao: str | None
    processo: str | None
    valor_multa: Decimal | None
    codigo_sancao: str | None
    origem_informacoes: str | None
    motivo: str | None = None
    convenio: str | None = None


class ListaTcu(StrEnum):
    INIDONEOS = "INIDONEOS"
    CONTAS_IRREGULARES = "CONTAS_IRREGULARES"
    INABILITADOS = "INABILITADOS"


@dataclass(frozen=True, slots=True)
class RegistroListaTcu:
    lista: ListaTcu
    documento: str | None
    raiz: str | None
    nome: str
    processo: str | None
    acordao: str | None
    data_acordao: date | None
    data_transito: date | None
    data_final: date | None


class TipoCertidaoTcu(StrEnum):
    INIDONEOS = "INIDONEOS"
    CNIA = "CNIA"
    CEIS = "CEIS"
    CNEP = "CNEP"


class SituacaoCertidaoTcu(StrEnum):
    NADA_CONSTA = "NADA_CONSTA"
    CONSTAM_REGISTROS = "CONSTAM_REGISTROS"
    INDISPONIVEL = "INDISPONIVEL"
    NAO_SUPORTADO = "NAO_SUPORTADO"


@dataclass(frozen=True, slots=True)
class CertidaoTcu:
    tipo: TipoCertidaoTcu
    situacao: SituacaoCertidaoTcu
    observacao: str | None
    datas_observacao: tuple[date, ...]
    processos: tuple[str, ...]
    link_manual: str | None


@dataclass(frozen=True, slots=True)
class RespostaTcu:
    cnpj: str
    razao_social: str | None
    cnpj_encontrado: bool
    certidoes: tuple[CertidaoTcu, ...]

    def certidao(self, tipo: TipoCertidaoTcu) -> CertidaoTcu | None:
        return next((c for c in self.certidoes if c.tipo is tipo), None)
