"""Baixa o OpenAPI do Portal da Transparencia (sem chave), extrai as rotas de sancoes
e testa o comportamento das rotas sem chave e com chave invalida (T6 do 19.4).

Saidas:
- portal-openapi.json (contrato oficial, versionar);
- openapi_sancoes.txt (parametros e schemas resolvidos de /cepim, /ceis, /cnep e afins);
- exemplos/erro_*.txt (status, headers e corpo das chamadas sem chave e com chave invalida).

Uso: PYTHONIOENCODING=utf-8 .venv/Scripts/python fase0/portal/portal_openapi.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

UA = "validador-osc-ifsp/0.1 (projeto academico de extensao)"
HOST = "https://api.portaldatransparencia.gov.br"
PASTA = Path(__file__).parent
PAUSA = 1.5
ROTAS = ("/cepim", "/ceis", "/cnep")


def resolver(spec: dict, schema: dict, prof: int = 0, vistos: tuple = ()) -> list[str]:
    """Achata um schema em linhas 'caminho: tipo' seguindo $ref."""
    linhas: list[str] = []
    ind = "  " * prof
    if "$ref" in schema:
        nome = schema["$ref"].split("/")[-1]
        if nome in vistos:
            return [f"{ind}(ref circular {nome})"]
        return [f"{ind}<{nome}>"] + resolver(spec, spec["components"]["schemas"][nome], prof, vistos + (nome,))
    tipo = schema.get("type")
    if tipo == "array":
        return [f"{ind}array de:"] + resolver(spec, schema["items"], prof + 1, vistos)
    for campo, sub in (schema.get("properties") or {}).items():
        desc = sub.get("type") or ("$ref " + sub["$ref"].split("/")[-1] if "$ref" in sub else "")
        fmt = f" ({sub['format']})" if "format" in sub else ""
        linhas.append(f"{ind}- {campo}: {desc}{fmt}")
        if "$ref" in sub or sub.get("type") == "array":
            linhas += resolver(spec, sub, prof + 1, vistos)
    return linhas


def main() -> None:
    (PASTA / "exemplos").mkdir(exist_ok=True)
    with httpx.Client(headers={"User-Agent": UA}, timeout=60) as c:
        r = c.get(f"{HOST}/v3/api-docs")
        r.raise_for_status()
        spec = r.json()
        (PASTA / "portal-openapi.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

        out: list[str] = [f"OpenAPI {spec.get('openapi')} - {spec['info'].get('title')} - versao {spec['info'].get('version')}"]
        out.append(f"servers: {spec.get('servers')}")
        out.append(f"securitySchemes: {json.dumps(spec.get('components', {}).get('securitySchemes'), ensure_ascii=False)}")
        out.append(f"security global: {spec.get('security')}")
        relevantes = [p for p in spec["paths"] if any(k in p for k in ("cepim", "ceis", "cnep", "acordos-leniencia", "sancionado", "cnpj"))]
        out.append("\nRotas relacionadas: " + ", ".join(relevantes))
        for p in relevantes:
            for metodo, op in spec["paths"][p].items():
                out.append(f"\n=== {metodo.upper()} {p}  tags={op.get('tags')}  summary={op.get('summary')}")
                if op.get("description"):
                    out.append(f"descricao: {op['description']}")
                for par in op.get("parameters", []):
                    sch = par.get("schema", {})
                    out.append(
                        f"  param {par['name']} in={par['in']} required={par.get('required', False)}"
                        f" type={sch.get('type')} fmt={sch.get('format')} default={sch.get('default')}"
                        f" desc={par.get('description')}"
                    )
                for cod, resp in op.get("responses", {}).items():
                    for ct, corpo in (resp.get("content") or {}).items():
                        out.append(f"  resposta {cod} {ct}:")
                        out += ["    " + l for l in resolver(spec, corpo.get("schema", {}))]
        (PASTA / "openapi_sancoes.txt").write_text("\n".join(out), encoding="utf-8")
        print(f"{len(spec['paths'])} rotas no total; relevantes: {relevantes}")

        # T6: chamadas sem chave e com chave invalida
        base = f"{HOST}/api-de-dados"
        casos = [
            ("sem_chave_ceis", f"{base}/ceis", {"codigoSancionado": "19131243000197", "pagina": 1}, {}),
            ("sem_chave_cepim", f"{base}/cepim", {"cnpjSancionado": "19131243000197", "pagina": 1}, {}),
            ("chave_invalida_ceis", f"{base}/ceis", {"codigoSancionado": "19131243000197", "pagina": 1}, {"chave-api-dados": "00000000000000000000000000000000"}),
        ]
        for nome, url, params, hdr in casos:
            time.sleep(PAUSA)
            t0 = time.perf_counter()
            r = c.get(url, params=params, headers=hdr)
            dt = time.perf_counter() - t0
            txt = (
                f"GET {r.request.url}\nheaders extras: {hdr}\nHTTP {r.status_code} em {dt:.2f}s\n"
                + "\n".join(f"{k}: {v}" for k, v in r.headers.items())
                + f"\n\n{r.text}"
            )
            (PASTA / "exemplos" / f"erro_{nome}.txt").write_text(txt, encoding="utf-8")
            print(nome, r.status_code, r.headers.get("content-type"), r.text[:300].replace("\n", " "))


if __name__ == "__main__":
    main()
