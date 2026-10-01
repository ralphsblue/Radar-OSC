"""Verificação 1 - dígito verificador (DV) do CNPJ.

Implementa o capítulo 4 e o Apêndice B da especificação do MVP.
Aceita o formato numérico e o alfanumérico (IN RFB 2.229/2024): as 12 primeiras
posições podem ser [0-9A-Z] e os 2 DVs são sempre numéricos.
O valor de cada caractere no cálculo é o código ASCII - 48 ('0'..'9' = 0..9, 'A'..'Z' = 17..42).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

PESOS_DV1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
PESOS_DV2 = (6, *PESOS_DV1)

# Separadores removidos na normalização: espaços, ponto, barra, hífen e os traços
# Unicode que aparecem quando o CNPJ é copiado de PDF ou editor de texto.
_SEPARADORES = re.compile(r"[\s./\-‐-―−]")
# Só a-z ASCII vira maiúscula: str.upper() transformaria 'ı' (U+0131) em 'I'
# e deixaria passar entrada não ASCII.
_MAIUSCULAS = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
# [0-9] explícito: \d aceitaria dígitos de outros alfabetos (ex.: '٣').
_BASE = re.compile(r"[0-9A-Z]{12}")
_CNPJ = re.compile(r"[0-9A-Z]{12}[0-9]{2}")


class Motivo(StrEnum):
    FORMATO = "formato"
    REPETIDO = "repetido"
    DV = "dv"


@dataclass(frozen=True, slots=True)
class ResultadoDV:
    cnpj: str
    """CNPJ normalizado (sem pontuação, em maiúsculas)."""
    valido: bool
    motivo: Motivo | None = None
    dv_esperado: str | None = None
    """Preenchido quando motivo == Motivo.DV."""


def normalizar(cnpj: str) -> str:
    """Remove pontuação e espaços e converte letras para maiúsculas."""
    return _SEPARADORES.sub("", cnpj).translate(_MAIUSCULAS)


def _digito(valores: list[int], pesos: tuple[int, ...]) -> int:
    resto = sum(v * p for v, p in zip(valores, pesos, strict=True)) % 11
    return 0 if resto < 2 else 11 - resto


def calcular_dvs(base12: str) -> str:
    """Calcula os 2 DVs a partir das 12 primeiras posições (raiz + ordem).

    Levanta ValueError se a base normalizada não tiver 12 caracteres [0-9A-Z].
    """
    base = normalizar(base12)
    if not _BASE.fullmatch(base):
        raise ValueError(f"base do CNPJ deve ter 12 caracteres [0-9A-Z]: {base12!r}")
    valores = [ord(c) - 48 for c in base]
    dv1 = _digito(valores, PESOS_DV1)
    dv2 = _digito([*valores, dv1], PESOS_DV2)
    return f"{dv1}{dv2}"


def cnpj_da_matriz(cnpj: str) -> str:
    """Monta o CNPJ da matriz (ordem 0001) a partir da raiz de qualquer estabelecimento."""
    base = normalizar(cnpj)[:8] + "0001"
    return base + calcular_dvs(base)


def validar(cnpj: str) -> ResultadoDV:
    """Valida formato, sequência repetida e DVs, nessa ordem."""
    normalizado = normalizar(cnpj)
    if not _CNPJ.fullmatch(normalizado):
        return ResultadoDV(normalizado, False, Motivo.FORMATO)
    base, dvs = normalizado[:12], normalizado[12:]
    # Base com um único caractere repetido nunca é inscrição real, mesmo com DV correto
    # (ex.: 11111111111180).
    if len(set(base)) == 1:
        return ResultadoDV(normalizado, False, Motivo.REPETIDO)
    esperado = calcular_dvs(base)
    if dvs != esperado:
        return ResultadoDV(normalizado, False, Motivo.DV, esperado)
    return ResultadoDV(normalizado, True)
