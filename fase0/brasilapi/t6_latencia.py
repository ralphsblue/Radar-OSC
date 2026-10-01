"""
t6_latencia.py - T6 do roteiro 18.3: rajada de consultas sem pausa.

- BrasilAPI: 20 consultas seguidas, sem pausa.
- Fallbacks (minhareceita, opencnpj): no maximo 5 seguidas.
Mede tempo medio, p95, codigos HTTP (procura 429) e headers de rate limit.
Salva respostas/{fonte}_T6_{cnpj}.json com a lista de chamadas (sem o corpo
repetido; o corpo da primeira chamada vai inteiro como amostra).

Uso:
    python t6_latencia.py [CNPJ] [--fontes brasilapi,opencnpj,minhareceita]
    python t6_latencia.py --distintos --sufixo b   # T6b: CNPJs diferentes a cada chamada (forca cache miss)

Com --distintos, cada chamada usa uma filial diferente da Santa Casa de SP (raiz 62779145,
ordens 0101 em diante, com DV calculado), para medir o caminho sem cache.
Ordens inexistentes tambem servem: a resposta 404 exige consulta ao banco da fonte.
"""
import argparse
import json
import statistics
import time

import httpx

from comum import OUT, completar_dv, consultar

N = {"brasilapi": 20, "minhareceita": 5, "opencnpj": 5}

ap = argparse.ArgumentParser()
ap.add_argument("cnpj", nargs="?", default="19131243000197")
ap.add_argument("--fontes", default="brasilapi,opencnpj,minhareceita")
ap.add_argument("--sufixo", default="", help="sufixo do nome do arquivo (ex.: b)")
ap.add_argument("--distintos", action="store_true")
a = ap.parse_args()


def p95(xs):
    xs = sorted(xs)
    return xs[max(0, round(0.95 * len(xs)) - 1)]


with httpx.Client() as client:
    for i, fonte in enumerate(a.fontes.split(",")):
        if i:
            time.sleep(1)  # pausa apenas entre fontes, nunca dentro da rajada
        chamadas = []
        amostra = None
        for j in range(N[fonte]):
            cnpj = completar_dv(f"62779145{101 + j:04d}") if a.distintos else a.cnpj
            r = consultar(client, fonte, cnpj)
            r["cnpj"] = cnpj
            amostra = amostra or r
            chamadas.append({k: r.get(k) for k in ("cnpj", "consultado_em", "http", "ms", "headers_relevantes", "erro")})
        ms = [c["ms"] for c in chamadas]
        codigos = {}
        for c in chamadas:
            codigos[str(c["http"])] = codigos.get(str(c["http"]), 0) + 1
        rl = sorted({k for c in chamadas for k in (c["headers_relevantes"] or {})
                     if k.lower().startswith(("x-rate", "ratelimit", "retry"))})
        resumo = {"n": len(ms), "media_ms": round(statistics.mean(ms)), "mediana_ms": round(statistics.median(ms)),
                  "p95_ms": p95(ms), "min_ms": min(ms), "max_ms": max(ms), "codigos_http": codigos,
                  "houve_429": "429" in codigos, "headers_rate_limit": rl}
        out = {"caso": f"T6{a.sufixo}", "cnpj_consultado": "distintos" if a.distintos else a.cnpj, "fonte": fonte, "resumo": resumo,
               "chamadas": chamadas, "amostra_primeira_resposta": amostra}
        (OUT / f"{fonte}_T6{a.sufixo}_{'62779145xxxxxx' if a.distintos else a.cnpj}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                                                encoding="utf-8")
        print(fonte, json.dumps(resumo, ensure_ascii=False), flush=True)
