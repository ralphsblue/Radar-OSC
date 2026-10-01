from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum


class Estado(StrEnum):
    OK = "OK"
    RESTRICAO = "RESTRICAO"
    ALERTA = "ALERTA"
    INDISPONIVEL = "INDISPONIVEL"
    NAO_VERIFICADO = "NAO_VERIFICADO"


class TipoVerificacao(StrEnum):
    ELIMINATORIA = "ELIMINATORIA"
    ALERTA = "ALERTA"
    INFORMATIVA = "INFORMATIVA"


class StatusFinal(StrEnum):
    CNPJ_INVALIDO = "CNPJ_INVALIDO"
    INAPTA = "INAPTA"
    INCONCLUSIVA = "INCONCLUSIVA"
    APTA_COM_RESSALVAS = "APTA_COM_RESSALVAS"
    APTA = "APTA"


class Esfera(StrEnum):
    MUNICIPIO = "municipio"
    ESTADO = "estado"
    UNIAO = "uniao"


@dataclass(frozen=True, slots=True)
class Contexto:
    data_referencia: date
    esfera: Esfera | None = None


@dataclass(frozen=True, slots=True)
class Achado:
    tipo: str
    dados: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RefFonte:
    fonte: str
    obtida_em: datetime | None = None
    data_base: date | None = None
    de_cache: bool = False
    evidencia_id: int | None = None
    carga_id: int | None = None
    sha256: str | None = None


@dataclass(frozen=True, slots=True)
class DefinicaoVerificacao:
    id: str
    spec: int
    nome: str
    tipo: TipoVerificacao


@dataclass(frozen=True, slots=True)
class ResultadoVerificacao:
    definicao: DefinicaoVerificacao
    estado: Estado
    mensagem: str
    achados: tuple[Achado, ...] = ()
    fontes: tuple[RefFonte, ...] = ()
    situacao: str | None = None

    @property
    def id(self) -> str:
        return self.definicao.id

    @property
    def tipo(self) -> TipoVerificacao:
        return self.definicao.tipo


@dataclass(frozen=True, slots=True)
class Avaliacao:
    status: StatusFinal
    motivos: tuple[str, ...]
    avisos: tuple[str, ...]
    verificacoes: tuple[ResultadoVerificacao, ...]
