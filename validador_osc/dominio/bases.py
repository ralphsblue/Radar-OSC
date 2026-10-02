from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class CargaAtiva:
    id: int
    fonte: str
    data_base: date | None
    concluida_em: datetime
    arquivo_sha256: str | None


@dataclass(frozen=True, slots=True)
class ConsultaLocal[T]:
    carga: CargaAtiva
    registros: tuple[T, ...]
