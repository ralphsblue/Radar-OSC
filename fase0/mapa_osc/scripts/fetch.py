"""Baixa uma URL com UA do projeto, salva bruto em respostas/ e imprime resumo.
Uso: python fetch.py URL NOME_ARQUIVO [--insecure]
"""

import datetime
import hashlib
import pathlib
import sys
import time

import httpx

UA = "validador-osc-ifsp/0.1 (projeto academico de extensao)"
OUT = pathlib.Path(__file__).resolve().parent.parent / "respostas"
url, nome = sys.argv[1], sys.argv[2]
verify = "--insecure" not in sys.argv
time.sleep(1.5)
t0 = time.time()
try:
    r = httpx.get(
        url, headers={"User-Agent": UA, "Accept": "*/*"}, timeout=40, follow_redirects=True, verify=verify
    )
except Exception as e:
    print("ERRO", type(e).__name__, e)
    sys.exit(1)
dt = time.time() - t0
(OUT / nome).write_bytes(r.content)
meta = f"url={url}\nfinal={r.url}\nstatus={r.status_code}\ntempo_s={dt:.2f}\ndata={datetime.datetime.now().isoformat()}\nsha256={hashlib.sha256(r.content).hexdigest()}\nheaders={dict(r.headers)}\n"
(OUT / (nome + ".meta.txt")).write_text(meta, encoding="utf-8")
print(meta)
print(r.text[:1500])
