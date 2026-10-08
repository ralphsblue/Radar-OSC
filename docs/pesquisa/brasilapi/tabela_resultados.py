"""
tabela_resultados.py - gera tabela Markdown (caso x fonte) a partir de respostas/,
e conta as falhas arquivadas em respostas/falhas/ por fonte.

Uso: python tabela_resultados.py
"""

import json
import statistics
from collections import defaultdict

from comum import FONTES, OUT

linhas = defaultdict(dict)
for p in sorted(OUT.glob("*_*_*.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    if "resumo" in d or "descartado" in d.get("caso", ""):
        continue
    c = d.get("corpo") if isinstance(d.get("corpo"), dict) else {}
    if d.get("http") == 200:
        nat = c.get("codigo_natureza_juridica", c.get("natureza_juridica"))
        sit = c.get("situacao_cadastral")
        mf = c.get("identificador_matriz_filial", c.get("matriz_filial"))
        cel = f"200 ({d['ms']} ms) nat={nat} sit={sit} mf={mf}"
    else:
        cel = f"{d.get('http')} ({d['ms']} ms) {json.dumps(c, ensure_ascii=False)[:60]}"
    linhas[(d["caso"], d["cnpj_consultado"])][d["fonte"]] = cel

print("| Caso | CNPJ | " + " | ".join(FONTES) + " |")
print("|---|---|" + "---|" * len(FONTES))
for (caso, cnpj), f in linhas.items():
    print(f"| {caso} | {cnpj} | " + " | ".join(f.get(x, "-") for x in FONTES) + " |")

print("\nFalhas arquivadas (respostas/falhas):")
falhas = defaultdict(list)
for p in (OUT / "falhas").glob("*.json"):
    d = json.loads(p.read_text(encoding="utf-8"))
    falhas[d["fonte"]].append((d.get("http"), d.get("ms")))
for f, xs in falhas.items():
    cod = defaultdict(int)
    for h, _ in xs:
        cod[h] += 1
    print(
        f"  {f}: {len(xs)} falhas, codigos={dict(cod)}, ms medio={round(statistics.mean(m for _, m in xs))}"
    )

print("\nLatencia das respostas definitivas (200/400/404) por fonte, fora do T6:")
for fonte in FONTES:
    ms = [
        json.loads(p.read_text(encoding="utf-8"))["ms"]
        for p in OUT.glob(f"{fonte}_*.json")
        if "T6" not in p.name
        and "descartado" not in p.name
        and json.loads(p.read_text(encoding="utf-8")).get("http") in (200, 400, 404)
    ]
    if ms:
        print(
            f"  {fonte}: n={len(ms)} media={round(statistics.mean(ms))} mediana={round(statistics.median(ms))} max={max(ms)}"
        )
