"""
comum.py - utilitarios compartilhados pelos scripts da fase 0 (fontes cadastrais de CNPJ).

Fontes:
- brasilapi:   GET https://brasilapi.com.br/api/cnpj/v1/{cnpj}
- minhareceita: GET https://minhareceita.org/{cnpj}
- opencnpj:    GET https://api.opencnpj.org/{cnpj}

Cada chamada e salva em respostas/{fonte}_{caso}_{cnpj}.json com status HTTP,
tempo em ms, headers relevantes e corpo bruto.
"""

from __future__ import annotations

import json
import random
import re
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

AQUI = Path(__file__).resolve().parent
OUT = AQUI / "respostas"
OUT.mkdir(exist_ok=True)

UA = "validador-osc-ifsp/0.1 (projeto academico de extensao)"
HEADERS = {"User-Agent": UA, "Accept": "application/json"}

FONTES = {
    "brasilapi": "https://brasilapi.com.br/api/cnpj/v1/{cnpj}",
    "minhareceita": "https://minhareceita.org/{cnpj}",
    "opencnpj": "https://api.opencnpj.org/{cnpj}",
}

# headers que interessam para cache, rate limit e diagnostico
PREFIXOS_HEADERS = (
    "x-rate",
    "ratelimit",
    "retry",
    "content-type",
    "cache-control",
    "age",
    "x-vercel-cache",
    "cf-cache-status",
    "server",
    "via",
    "etag",
    "x-cache",
)

# ---------------------------------------------------------------- DV (cap. 4 / apendice B)
P1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
P2 = [6] + P1


def _val(c: str) -> int:
    return ord(c) - 48


def _dv(base: str, pesos: list[int]) -> str:
    r = sum(_val(c) * w for c, w in zip(base, pesos)) % 11
    return "0" if r < 2 else str(11 - r)


def completar_dv(base12: str) -> str:
    """Recebe os 12 primeiros caracteres e devolve o CNPJ de 14 com DVs."""
    base12 = base12.upper()
    d1 = _dv(base12, P1)
    d2 = _dv(base12 + d1, P2)
    return base12 + d1 + d2


def valida(cnpj: str) -> tuple[bool, str]:
    s = re.sub(r"[.\-/ ]", "", cnpj).upper()
    if not re.fullmatch(r"[0-9A-Z]{12}[0-9]{2}", s):
        return False, "formato"
    if len(set(s)) == 1:
        return False, "repetido"
    esperado = completar_dv(s[:12])[12:]
    return s[12:] == esperado, esperado


def gerar_aleatorio(seed: int | None = None, ordem: str = "0001") -> str:
    rnd = random.Random(seed)
    raiz = "".join(str(rnd.randint(0, 9)) for _ in range(8))
    return completar_dv(raiz + ordem)


# ---------------------------------------------------------------- HTTP
def consultar(client: httpx.Client, fonte: str, cnpj: str, timeout: float = 30) -> dict:
    url = FONTES[fonte].format(cnpj=cnpj)
    t0 = time.perf_counter()
    quando = datetime.now(UTC).isoformat(timespec="seconds")
    try:
        r = client.get(url, headers=HEADERS, timeout=timeout)
        ms = round((time.perf_counter() - t0) * 1000)
        try:
            corpo = r.json()
        except ValueError:
            corpo = {"_texto_nao_json": r.text[:3000]}
        hdr = {k: v for k, v in r.headers.items() if k.lower().startswith(PREFIXOS_HEADERS)}
        return {
            "fonte": fonte,
            "url": url,
            "consultado_em": quando,
            "http": r.status_code,
            "ms": ms,
            "headers_relevantes": hdr,
            "corpo": corpo,
        }
    except httpx.HTTPError as e:
        ms = round((time.perf_counter() - t0) * 1000)
        return {"fonte": fonte, "url": url, "consultado_em": quando, "http": None, "ms": ms, "erro": repr(e)}


def salvar(res: dict, caso: str, cnpj: str) -> Path:
    p = OUT / f"{res['fonte']}_{caso}_{cnpj}.json"
    res = {"caso": caso, "cnpj_consultado": cnpj, **res}
    p.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def resumo(res: dict) -> str:
    c = res.get("corpo")
    base = f"{res['fonte']:<12} HTTP {res.get('http')} {res.get('ms')} ms"
    if not isinstance(c, dict):
        return base + f" erro={res.get('erro')}"
    if "razao_social" not in c:
        return base + " corpo=" + json.dumps(c, ensure_ascii=False)[:200]
    nat = c.get("codigo_natureza_juridica", c.get("natureza_juridica"))
    sit = c.get("situacao_cadastral")
    mf = c.get("identificador_matriz_filial", c.get("matriz_filial"))
    return (
        base + f" | {c.get('razao_social')} | nat={nat} sit={sit} mf={mf}"
        f" inicio={c.get('data_inicio_atividade')} cnae={c.get('cnae_fiscal', c.get('cnae_principal'))}"
    )
