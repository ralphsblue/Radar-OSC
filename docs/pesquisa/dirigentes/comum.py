"""Utilidades dos scripts de fase0/dirigentes.

Cliente HTTP com User-Agent do projeto, pausa mínima entre chamadas,
validação de CPF e máscara no padrão do QSA (***XXXXXX**).
Arquivos brutos com CPF completo vão para downloads/ (fora do versionamento).
"""

from __future__ import annotations

import re
import time
import unicodedata
from datetime import date
from pathlib import Path

import httpx

PASTA = Path(__file__).parent
RAIZ = PASTA.parents[1]
DOWNLOADS = PASTA / "downloads"
AMOSTRAS = PASTA / "amostras"
UA = "validador-osc-ifsp/0.1 (projeto academico de extensao)"
PAUSA = 2.0

_ultimo = 0.0


def esperar() -> None:
    global _ultimo
    falta = PAUSA - (time.monotonic() - _ultimo)
    if falta > 0:
        time.sleep(falta)
    _ultimo = time.monotonic()


def cliente() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": UA}, timeout=120, follow_redirects=True)


def digitos(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")


def cpf_valido(cpf: str) -> bool:
    if len(cpf) != 11 or not cpf.isdigit() or cpf == cpf[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(cpf[i]) * (n + 1 - i) for i in range(n))
        dv = (soma * 10) % 11 % 10
        if dv != int(cpf[n]):
            return False
    return True


def mascarar_cpf(cpf: str) -> str:
    """Mesmo padrão do QSA nos dados abertos: só os 6 dígitos do meio."""
    d = digitos(cpf)
    if len(d) != 11:
        return "*" * len(d)
    return f"***{d[3:9]}**"


def normalizar_nome(nome: str) -> str:
    s = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Z ]", " ", s.upper())
    return re.sub(r"\s+", " ", s).strip()


def data_br(s: str | None) -> date | None:
    """DD/MM/AAAA (ou AAAA-MM-DD) para date, sem datetime ingênuo; None se inválida."""
    s = (s or "").strip()
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", s)
    try:
        if m:
            return date(int(m[3]), int(m[2]), int(m[1]))
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
        return date(int(m[1]), int(m[2]), int(m[3])) if m else None
    except ValueError:
        return None
