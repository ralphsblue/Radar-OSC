"""Baixa fatias (HTTP Range) da base CSV do Mapa das OSCs para achar candidatos.

A base inteira tem 344 MB; aqui baixamos só algumas fatias de 8 MB em pontos
diferentes do arquivo, o suficiente para achar associações INAPTAS, recentes,
igrejas como associação e CNAEs comerciais.

Uso: .venv/Scripts/python fase0/casos/amostra_mapa.py
Saída: fase0/casos/respostas/mapa_base/fatia_<offset>.csv (cabeçalho repetido em cada fatia).
"""

from __future__ import annotations

import time
from pathlib import Path

import httpx

URL = "https://mapaosc.ipea.gov.br/download/20260806_MOSC_baseDivulgacao.csv"
UA = "validador-osc-ifsp/0.1 (projeto academico de extensao)"
TAMANHO_TOTAL = 343_956_497
FATIA = 8 * 1024 * 1024
OFFSETS = [int(TAMANHO_TOTAL * p) for p in (0.30, 0.60, 0.80, 0.97)]
SAIDA = Path(__file__).parent / "respostas" / "mapa_base"


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    with httpx.Client(headers={"User-Agent": UA}, timeout=120) as cliente:
        cab = cliente.get(URL, headers={"Range": "bytes=0-4095"}).content
        cabecalho = cab.split(b"\r\n", 1)[0] + b"\r\n"
        for inicio in OFFSETS:
            fim = min(inicio + FATIA - 1, TAMANHO_TOTAL - 1)
            r = cliente.get(URL, headers={"Range": f"bytes={inicio}-{fim}"})
            r.raise_for_status()
            corpo = r.content
            # descarta a primeira e a última linha (cortadas no meio)
            corpo = corpo.split(b"\r\n", 1)[1].rsplit(b"\r\n", 1)[0] + b"\r\n"
            destino = SAIDA / f"fatia_{inicio}.csv"
            destino.write_bytes(cabecalho + corpo)
            print(destino, r.status_code, len(corpo))
            time.sleep(2)


if __name__ == "__main__":
    main()
