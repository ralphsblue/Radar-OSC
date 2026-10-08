import re
from dataclasses import dataclass
from enum import StrEnum

PESOS_DV1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
PESOS_DV2 = (6, *PESOS_DV1)

_SEPARADORES = re.compile(r"[\s./\-\u2010-\u2015\u2212]")
_MAIUSCULAS = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_BASE = re.compile(r"[0-9A-Z]{12}")
_CNPJ = re.compile(r"[0-9A-Z]{12}[0-9]{2}")
_NUMERICO = re.compile(r"[0-9]{14}")
_RESTO_MINIMO = 2
TAMANHO = 14


class Motivo(StrEnum):
    FORMATO = "formato"
    REPETIDO = "repetido"
    DV = "dv"


@dataclass(frozen=True, slots=True)
class ResultadoDV:
    cnpj: str
    valido: bool
    motivo: Motivo | None = None
    dv_esperado: str | None = None


def normalizar(cnpj: str) -> str:
    return _SEPARADORES.sub("", cnpj).translate(_MAIUSCULAS)


def eh_alfanumerico(cnpj: str) -> bool:
    return _NUMERICO.fullmatch(normalizar(cnpj)) is None


def _digito(valores: list[int], pesos: tuple[int, ...]) -> int:
    resto = sum(v * p for v, p in zip(valores, pesos, strict=True)) % 11
    return 0 if resto < _RESTO_MINIMO else 11 - resto


def calcular_dvs(base12: str) -> str:
    base = normalizar(base12)
    if not _BASE.fullmatch(base):
        raise ValueError(f"base do CNPJ deve ter 12 caracteres [0-9A-Z]: {base12!r}")
    valores = [ord(c) - 48 for c in base]
    dv1 = _digito(valores, PESOS_DV1)
    dv2 = _digito([*valores, dv1], PESOS_DV2)
    return f"{dv1}{dv2}"


def cnpj_da_matriz(cnpj: str) -> str:
    base = normalizar(cnpj)[:8] + "0001"
    return base + calcular_dvs(base)


def validar(cnpj: str) -> ResultadoDV:
    normalizado = normalizar(cnpj)
    if not _CNPJ.fullmatch(normalizado):
        return ResultadoDV(normalizado, False, Motivo.FORMATO)
    base, dvs = normalizado[:12], normalizado[12:]
    if len(set(base)) == 1:
        return ResultadoDV(normalizado, False, Motivo.REPETIDO)
    esperado = calcular_dvs(base)
    if dvs != esperado:
        return ResultadoDV(normalizado, False, Motivo.DV, esperado)
    return ResultadoDV(normalizado, True)


def formatar(cnpj: str) -> str:
    valor = normalizar(cnpj)
    if len(valor) != TAMANHO:
        return cnpj
    return f"{valor[:2]}.{valor[2:5]}.{valor[5:8]}/{valor[8:12]}-{valor[12:]}"
