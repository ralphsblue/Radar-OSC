"""Baixa a estrutura completa da CNAE (subclasses) da API de serviços de dados do IBGE.

Gera ibge_cnae_subclasses.json com os cinco níveis (seções, divisões, grupos,
classes e subclasses), exatamente como a API devolve, mais metadados de coleta.

Uso:
    .venv/Scripts/python fase0/cnae/baixar_cnae.py
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

BASE_URL = "https://servicodados.ibge.gov.br/api/v2/cnae"
NIVEIS = ("secoes", "divisoes", "grupos", "classes", "subclasses")
SAIDA = Path(__file__).with_name("ibge_cnae_subclasses.json")


def baixar() -> dict:
    dados: dict = {}
    with httpx.Client(timeout=120, follow_redirects=True) as cliente:
        for nivel in NIVEIS:
            resposta = cliente.get(f"{BASE_URL}/{nivel}")
            resposta.raise_for_status()
            itens = resposta.json()
            itens.sort(key=lambda item: item["id"])
            dados[nivel] = itens
    return dados


def main() -> None:
    dados = baixar()
    contagens = {nivel: len(dados[nivel]) for nivel in NIVEIS}
    documento = {
        "metadados": {
            "fonte": BASE_URL,
            "endpoints": [f"{BASE_URL}/{nivel}" for nivel in NIVEIS],
            "versao_cnae": "CNAE-Subclasses 2.3 (estrutura vigente servida pela API v2 do IBGE)",
            "baixado_em": datetime.now(UTC).isoformat(timespec="seconds"),
            "contagens": contagens,
        },
        **dados,
    }
    SAIDA.write_text(json.dumps(documento, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Salvo em {SAIDA}")
    for nivel, total in contagens.items():
        print(f"  {nivel}: {total}")


if __name__ == "__main__":
    main()
