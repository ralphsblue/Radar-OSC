from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class Esfera(StrEnum):
    MUNICIPIO = "municipio"
    ESTADO = "estado"
    UNIAO = "uniao"


@dataclass(frozen=True, slots=True)
class Contexto:
    data_referencia: date
    esfera: Esfera | None = None
