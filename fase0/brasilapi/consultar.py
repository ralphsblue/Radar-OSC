"""
consultar.py - consulta um ou mais CNPJs em uma ou mais fontes, com 1 s entre chamadas.

Uso:
    python consultar.py CASO CNPJ [CNPJ ...] [--fontes brasilapi,minhareceita,opencnpj] [--nao-salvar]
Exemplo:
    python consultar.py T1 19131243000197
"""
import argparse
import time

import httpx

from comum import FONTES, consultar, resumo, salvar

ap = argparse.ArgumentParser()
ap.add_argument("caso")
ap.add_argument("cnpjs", nargs="+")
ap.add_argument("--fontes", default=",".join(FONTES))
ap.add_argument("--nao-salvar", action="store_true")
a = ap.parse_args()

with httpx.Client(http2=False) as client:
    primeira = True
    for cnpj in a.cnpjs:
        cnpj = "".join(ch for ch in cnpj if ch.isalnum()).upper()
        for fonte in a.fontes.split(","):
            if not primeira:
                time.sleep(1)
            primeira = False
            res = consultar(client, fonte, cnpj)
            if not a.nao_salvar:
                salvar(res, a.caso, cnpj)
            print(f"[{a.caso}] {cnpj} {resumo(res)}", flush=True)
