"""Inspeciona os arquivos da pagina Base de Dados do Mapa das OSCs.
- HEAD em todos (tamanho, Last-Modified, tipo)
- baixa os pequenos (<= 20 MB): dicionario e planilhas CEBAS
- baixa so os primeiros 256 KB da base principal (CSV ~336 MB) via Range, para ver cabecalho e amostra
"""

import json
import pathlib
import time

import httpx

UA = "validador-osc-ifsp/0.1 (projeto academico de extensao)"
B = "https://mapaosc.ipea.gov.br/"
OUT = pathlib.Path(__file__).resolve().parent.parent / "respostas" / "downloads"
ARQS = [
    "download/20260806_MOSC_baseDivulgacao.csv",
    "arquivos/subitems/4038-dicionario-de-dados-mapa-oscs.xlsx",
    "download/Dicionario_Dados.xls",
    "download/area_subarea.xlsx",
    "arquivos/subitems/4168-baseprojetososcantiga.xlsx",
    "arquivos/subitems/4600-conselhoconferencia.xls",
    "download/CNES_MJ.zip",
    "arquivos/subitems/8420-cebaseducacao.xlsx",
    "arquivos/subitems/1434-cebassaude.xlsx",
    "arquivos/subitems/7684-cebassuas.xlsx",
    "arquivos/subitems/6793-certificadolistaantiga.xls",
    "arquivos/subitems/4786-recursososc.xls",
    "arquivos/subitems/1754-20250718analiseoscinternacionais3204.xlsx",
]
BAIXAR = {
    "arquivos/subitems/4038-dicionario-de-dados-mapa-oscs.xlsx",
    "arquivos/subitems/8420-cebaseducacao.xlsx",
    "arquivos/subitems/1434-cebassaude.xlsx",
    "arquivos/subitems/7684-cebassuas.xlsx",
}
c = httpx.Client(headers={"User-Agent": UA}, timeout=120, follow_redirects=True)
res = []
for a in ARQS:
    time.sleep(1.5)
    h = c.head(B + a)
    info = {
        "arquivo": a,
        "status": h.status_code,
        "bytes": h.headers.get("content-length"),
        "last_modified": h.headers.get("last-modified"),
        "tipo": h.headers.get("content-type"),
        "accept_ranges": h.headers.get("accept-ranges"),
    }
    res.append(info)
    print(info)
    nome = a.split("/")[-1]
    if a in BAIXAR:
        time.sleep(1.5)
        (OUT / nome).write_bytes(c.get(B + a).content)
    elif a.endswith(".csv"):
        time.sleep(1.5)
        r = c.get(B + a, headers={"Range": "bytes=0-262143"})
        print("range status", r.status_code, len(r.content))
        (OUT / ("amostra_256KB_" + nome)).write_bytes(r.content[:262144])
(OUT / "_head_arquivos.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
