"""Utilidades compartilhadas pelos scripts de fase0/casos.

Cliente HTTP com User-Agent do projeto, pausa mínima por host e gravação da
resposta bruta com metadados (URL, status, tempo, data, sha256).
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "fase0" / "cnae"))

from validador_osc.cnpj import cnpj_da_matriz, validar

PASTA = Path(__file__).parent
RESPOSTAS = PASTA / "respostas"
UA = "validador-osc-ifsp/0.1 (projeto academico de extensao)"

PAUSA_POR_HOST = {
    "api.opencnpj.org": 1.2,
    "certidoes-apf.apps.tcu.gov.br": 2.0,
    "mapaosc.ipea.gov.br": 1.5,
}

_ultimo: dict[str, float] = {}


def _esperar(host: str) -> None:
    pausa = PAUSA_POR_HOST.get(host, 2.0)
    decorrido = time.monotonic() - _ultimo.get(host, 0.0)
    if decorrido < pausa:
        time.sleep(pausa - decorrido)


def baixar(cliente: httpx.Client, url: str, destino: Path) -> dict:
    """GET com pausa por host. Salva corpo em `destino` (JSON) e devolve o registro.

    O arquivo salvo tem a forma {"meta": {...}, "corpo": <json ou texto>}.
    Erros de rede viram status None com a mensagem em meta.erro.
    """
    host = urlparse(url).hostname or ""
    _esperar(host)
    inicio = time.perf_counter()
    meta: dict = {"url": url, "data_utc": datetime.now(UTC).isoformat()}
    try:
        r = cliente.get(url)
        meta["status"] = r.status_code
        meta["sha256"] = hashlib.sha256(r.content).hexdigest()
        try:
            corpo = r.json()
        except ValueError:
            corpo = r.text
    except httpx.HTTPError as erro:
        meta["status"] = None
        meta["erro"] = f"{type(erro).__name__}: {erro}"
        corpo = None
    meta["tempo_ms"] = round((time.perf_counter() - inicio) * 1000)
    _ultimo[host] = time.monotonic()
    registro = {"meta": meta, "corpo": corpo}
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(registro, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{meta['status']} {meta['tempo_ms']:>6} ms {url}")
    return registro


def cliente_http() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": UA, "Accept": "application/json"}, timeout=40)


def ler(caminho: Path) -> dict | None:
    if not caminho.exists():
        return None
    return json.loads(caminho.read_text(encoding="utf-8"))


__all__ = ["PASTA", "RAIZ", "RESPOSTAS", "baixar", "cliente_http", "cnpj_da_matriz", "ler", "validar"]
