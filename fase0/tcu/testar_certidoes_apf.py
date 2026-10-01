"""Testa a API JSON publica por tras de https://certidoes-apf.apps.tcu.gov.br/.

Endpoints descobertos no bundle JS (assets/index-*.js).
O de certidoes tambem e documentado oficialmente em https://sites.tcu.gov.br/dados-abertos/webservices-tcu/
(parametro opcional ?seEmitirPDF=true|false):
  GET /api/rest/publico/tipos-certidoes
  GET /api/rest/publico/certidoes/{cnpj}            (Accept: application/json)
  GET /api/rest/publico/certidoes/{cnpj}            (Accept: application/pdf -> PDF da certidao)
  GET /api/publico/url-pesquisa-integrada

Uso: .venv\\Scripts\\python fase0\\tcu\\testar_certidoes_apf.py [cnpj ...]
Salva as respostas brutas em fase0/tcu/respostas/ com URL, data, status, tempo e sha256.
"""

import hashlib
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

UA = "validador-osc-ifsp/0.1 (projeto academico de extensao)"
BASE = "https://certidoes-apf.apps.tcu.gov.br"
OUT = Path(__file__).parent / "respostas"
OUT.mkdir(exist_ok=True)


def salvar(nome: str, r: httpx.Response, segundos: float) -> None:
    corpo = r.content
    meta = {
        "url": str(r.request.url),
        "metodo": r.request.method,
        "headers_enviados": dict(r.request.headers),
        "status": r.status_code,
        "headers_resposta": dict(r.headers),
        "tempo_s": round(segundos, 3),
        "data_utc": datetime.now(UTC).isoformat(),
        "sha256": hashlib.sha256(corpo).hexdigest(),
    }
    ext = "pdf" if r.headers.get("content-type", "").startswith("application/pdf") else "json"
    (OUT / f"{nome}.{ext}").write_bytes(corpo)
    (OUT / f"{nome}.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"{r.status_code} {segundos:.2f}s {r.request.method} {r.request.url} -> {nome}.{ext} ({len(corpo)} bytes)"
    )


def get(c: httpx.Client, nome: str, path: str, **kw) -> httpx.Response:
    t = time.perf_counter()
    r = c.get(BASE + path, **kw)
    salvar(nome, r, time.perf_counter() - t)
    time.sleep(2)
    return r


def main(cnpjs: list[str]) -> None:
    # Headers minimos: apenas User-Agent (sem cookies, sem Referer, sem token).
    with httpx.Client(headers={"User-Agent": UA}, timeout=120) as c:
        get(c, "apf_tipos-certidoes", "/api/rest/publico/tipos-certidoes")
        get(c, "apf_url-pesquisa-integrada", "/api/publico/url-pesquisa-integrada")
        for cnpj in cnpjs:
            get(
                c,
                f"apf_certidoes_{re.sub(r'\W', '_', cnpj)}",
                f"/api/rest/publico/certidoes/{cnpj}?seEmitirPDF=false",
                headers={"Accept": "application/json"},
            )


if __name__ == "__main__":
    main(sys.argv[1:] or ["19131243000197"])
