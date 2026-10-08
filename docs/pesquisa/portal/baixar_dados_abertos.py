"""Baixa os arquivos de dados abertos (CEPIM, CEIS, CNEP) do Portal da Transparencia.

Fluxo descoberto na fase 0:
1. GET https://portaldatransparencia.gov.br/download-de-dados/<cadastro>
   O HTML traz a data mais recente em um trecho JS:
   arquivos.push({"ano" : "2026", "mes" : "09", "dia" : "28", "origem" :  "CEPIM"});
2. GET https://portaldatransparencia.gov.br/download-de-dados/<cadastro>/AAAAMMDD
   responde 302 para
   https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/<cadastro>/AAAAMMDD_<CADASTRO>.zip
   Nenhuma chave, cookie ou CAPTCHA e necessario para esses dois passos.

Uso: .venv/Scripts/python fase0/portal/baixar_dados_abertos.py
"""

from __future__ import annotations

import json
import re
import time
import zipfile
from pathlib import Path

import httpx

UA = "validador-osc-ifsp/0.1 (projeto academico de extensao)"
BASE = "https://portaldatransparencia.gov.br/download-de-dados"
CADASTROS = ["cepim", "ceis", "cnep"]
DESTINO = Path(__file__).parent / "downloads"
PADRAO_DATA = re.compile(
    r'arquivos\.push\(\{"ano"\s*:\s*"(\d{4})",\s*"mes"\s*:\s*"(\d{2})",\s*"dia"\s*:\s*"(\d{2})"'
)


def data_mais_recente(cliente: httpx.Client, cadastro: str) -> str:
    r = cliente.get(f"{BASE}/{cadastro}")
    r.raise_for_status()
    datas = ["".join(m) for m in PADRAO_DATA.findall(r.text)]
    if not datas:
        raise RuntimeError(f"data nao encontrada na pagina de {cadastro}")
    return max(datas)


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    resumo = {}
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=120) as cliente:
        for cadastro in CADASTROS:
            data = data_mais_recente(cliente, cadastro)
            time.sleep(1.5)
            r = cliente.get(f"{BASE}/{cadastro}/{data}")
            r.raise_for_status()
            arquivo = DESTINO / f"{data}_{cadastro.upper()}.zip"
            arquivo.write_bytes(r.content)
            with zipfile.ZipFile(arquivo) as z:
                membros = [(i.filename, i.file_size) for i in z.infolist()]
                z.extractall(DESTINO)
            resumo[cadastro] = {
                "data_arquivo": data,
                "url_pagina": f"{BASE}/{cadastro}/{data}",
                "url_final": str(r.url),
                "last_modified": r.headers.get("last-modified"),
                "tamanho_zip": len(r.content),
                "membros": membros,
            }
            print(cadastro, json.dumps(resumo[cadastro], ensure_ascii=False))
            time.sleep(1.5)
    (DESTINO / "resumo_download.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
