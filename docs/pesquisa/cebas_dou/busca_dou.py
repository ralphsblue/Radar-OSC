"""Cliente da busca publica do portal da Imprensa Nacional (sem login).

A pagina https://www.in.gov.br/consulta/-/buscar/dou devolve HTML com os
resultados em JSON embutido em
<script id="_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params" type="application/json">.
Paginacao por cursor: newPage, score, id (classPK) e displayDate (displayDateSortable)
do ultimo item da pagina atual.

Uso:
    python busca_dou.py '"50.798.453/0001-83"'                # todas as datas, todas as secoes
    python busca_dou.py 'CEBAS' do1 01/08/2026 31/08/2026     # periodo personalizado (mesmo ano)
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

UA = "validador-osc-ifsp/0.1 (projeto academico de extensao)"
URL = "https://www.in.gov.br/consulta/-/buscar/dou"
PAUSA_S = 2.0
RE_JSON = re.compile(
    r'<script id="_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params" type="application/json">(.*?)</script>',
    re.S,
)
RE_TOTAL = re.compile(r"Exibindo\s+\d+\s*-\s*\d+\s+de\s+([\d.]+)\s+resultados")
RE_PAGINAS = re.compile(r"totalPages\s*:\s*(\d+)")


def url_ato(item: dict) -> str:
    return f"https://www.in.gov.br/web/dou/-/{item['urlTitle']}"


def buscar(
    q: str,
    secao: str = "todos",
    de: str | None = None,
    ate: str | None = None,
    delta: int = 50,
    max_paginas: int = 20,
    salvar_em: Path | None = None,
) -> tuple[list[dict], int]:
    params: dict = {
        "q": q,
        "s": secao,
        "exactDate": "personalizado" if de else "all",
        "sortType": "0",
        "delta": delta,
    }
    if de:
        params.update(publishFrom=de, publishTo=ate or de)
    itens: list[dict] = []
    total = 0
    with httpx.Client(headers={"User-Agent": UA}, timeout=60, follow_redirects=True) as c:
        pagina = 1
        while True:
            r = c.get(URL, params=params)
            r.raise_for_status()
            if salvar_em:
                salvar_em.mkdir(parents=True, exist_ok=True)
                h = hashlib.sha256(r.content).hexdigest()[:12]
                (salvar_em / f"busca_p{pagina}_{h}.html").write_bytes(r.content)
            m = RE_JSON.search(r.text)
            lote = json.loads(m.group(1))["jsonArray"] if m else []
            mt = RE_TOTAL.search(r.text)
            total = int(mt.group(1).replace(".", "")) if mt else len(lote)
            itens.extend(lote)
            mp = RE_PAGINAS.search(r.text)
            total_paginas = int(mp.group(1)) if mp else 1
            if not lote or pagina >= total_paginas or pagina >= max_paginas:
                break
            ultimo = lote[-1]
            params.update(
                currentPage=pagina,
                newPage=pagina + 1,
                score=ultimo["score"],
                id=ultimo["classPK"],
                displayDate=ultimo["displayDateSortable"],
            )
            pagina += 1
            time.sleep(PAUSA_S)
    return itens, total


def main() -> None:
    q = sys.argv[1]
    secao = sys.argv[2] if len(sys.argv) > 2 else "todos"
    de = sys.argv[3] if len(sys.argv) > 3 else None
    ate = sys.argv[4] if len(sys.argv) > 4 else None
    t0 = time.perf_counter()
    itens, total = buscar(q, secao, de, ate)
    out = {
        "consulta": {"q": q, "s": secao, "de": de, "ate": ate},
        "consultado_em": datetime.now(UTC).isoformat(),
        "duracao_s": round(time.perf_counter() - t0, 2),
        "total_informado": total,
        "itens": [
            {
                k: it.get(k)
                for k in (
                    "pubDate",
                    "pubName",
                    "title",
                    "hierarchyStr",
                    "artType",
                    "numberPage",
                    "editionNumber",
                )
            }
            | {"url": url_ato(it), "content": re.sub(r"<[^>]+>", "", it.get("content", ""))}
            for it in itens
        ],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
