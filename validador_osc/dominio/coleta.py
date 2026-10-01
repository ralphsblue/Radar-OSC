from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class MotivoFalha(StrEnum):
    TIMEOUT = "TIMEOUT"
    CONEXAO = "CONEXAO"
    HTTP_5XX = "HTTP_5XX"
    HTTP_4XX = "HTTP_4XX"
    HTTP_429 = "HTTP_429"
    FORMATO_INESPERADO = "FORMATO_INESPERADO"
    NAO_SUPORTADO = "NAO_SUPORTADO"
    BASE_VENCIDA = "BASE_VENCIDA"
    PRAZO_ESGOTADO = "PRAZO_ESGOTADO"


@dataclass(frozen=True, slots=True)
class RefEvidencia:
    id: int
    fonte: str
    sha256: str | None
    recebida_em: datetime
    de_cache: bool = False


@dataclass(frozen=True, slots=True)
class Obtido[T]:
    dados: T
    evidencia: RefEvidencia


@dataclass(frozen=True, slots=True)
class NaoEncontrado:
    evidencia: RefEvidencia | None
    data_base: date | None = None


@dataclass(frozen=True, slots=True)
class Falha:
    motivo: MotivoFalha
    detalhe: str
    evidencia: RefEvidencia | None = None


type Coleta[T] = Obtido[T] | NaoEncontrado | Falha
