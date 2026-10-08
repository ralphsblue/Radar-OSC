"""Testa a lista publica de Licitantes Inidoneos da Plataforma de Certidoes do TCU.

Endpoints descobertos no bundle JS de https://certidoes.apps.tcu.gov.br/lista-inidoneos:
  POST /api/publico/responsaveis-inidoneos-com-paginacao?paginaAtual=1&tamanhoPagina=10
       corpo JSON: {} (lista completa) ou {"cnpj": "..."} / {"cpf": "..."} (filtro)
  POST /api/publico/responsaveis-inidoneos/exportar-para-csv?paginaAtual=1&tamanhoPagina=50000
       corpo JSON: {} -> CSV com a lista inteira
Nao usam CAPTCHA no frontend.
A certidao individual (POST /api/publico/certidoes/licitantes-inidoneos/pessoa-juridica)
exige token ALTCHA ("captcha") e NAO e chamada aqui.

Uso: .venv\\Scripts\\python fase0\\tcu\\testar_lista_inidoneos.py [cnpj ...]
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
BASE = "https://certidoes.apps.tcu.gov.br"
OUT = Path(__file__).parent / "respostas"
OUT.mkdir(exist_ok=True)


def salvar(nome: str, ext: str, r: httpx.Response, segundos: float, corpo_enviado=None) -> None:
    corpo = r.content
    meta = {
        "url": str(r.request.url),
        "metodo": r.request.method,
        "corpo_enviado": corpo_enviado,
        "headers_enviados": dict(r.request.headers),
        "status": r.status_code,
        "headers_resposta": dict(r.headers),
        "tempo_s": round(segundos, 3),
        "data_utc": datetime.now(UTC).isoformat(),
        "sha256": hashlib.sha256(corpo).hexdigest(),
    }
    (OUT / f"{nome}.{ext}").write_bytes(corpo)
    (OUT / f"{nome}.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"{r.status_code} {segundos:.2f}s {r.request.method} {r.request.url} -> {nome}.{ext} ({len(corpo)} bytes)"
    )


def post(c: httpx.Client, nome: str, ext: str, path: str, corpo: dict) -> httpx.Response:
    t = time.perf_counter()
    r = c.post(BASE + path, json=corpo)
    salvar(nome, ext, r, time.perf_counter() - t, corpo)
    time.sleep(2)
    return r


def main(cnpjs: list[str]) -> None:
    with httpx.Client(headers={"User-Agent": UA, "Accept": "application/json"}, timeout=120) as c:
        post(
            c,
            "inidoneos_lista_pagina1",
            "json",
            "/api/publico/responsaveis-inidoneos-com-paginacao?paginaAtual=1&tamanhoPagina=10",
            {},
        )
        for cnpj in cnpjs:
            # Endpoint documentado oficialmente em https://sites.tcu.gov.br/dados-abertos/webservices-tcu/
            post(
                c,
                f"inidoneos_oficial_cnpj_{re.sub(r'\W', '_', cnpj)}",
                "json",
                "/api/publico/responsaveis-inidoneos",
                {"cnpj": cnpj},
            )
            post(
                c,
                f"inidoneos_lista_cnpj_{re.sub(r'\W', '_', cnpj)}",
                "json",
                "/api/publico/responsaveis-inidoneos-com-paginacao?paginaAtual=1&tamanhoPagina=50",
                {"cnpj": cnpj},
            )
        post(
            c,
            "inidoneos_lista_completa",
            "csv",
            "/api/publico/responsaveis-inidoneos/exportar-para-csv?paginaAtual=1&tamanhoPagina=50000",
            {},
        )


if __name__ == "__main__":
    main(sys.argv[1:] or ["19131243000197"])
