"""Metricas da extracao (T1 e item 6) e sorteio da amostra do T2.

Uso:
    python metricas.py cebas_S01082026.csv downloads/S01082026.zip
Gera: metricas_S01082026.json e amostra_t2_S01082026.csv (10 atos sorteados, semente fixa).
"""

from __future__ import annotations

import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

from parser_cebas import TERMO_CEBAS, achar_cnpjs, area_do_orgao, ler_zip

SEMENTE = 20260930


def main() -> None:
    csv_path = Path(sys.argv[1])
    zip_path = Path(sys.argv[2])
    linhas = list(csv.DictReader(csv_path.open(encoding="utf-8-sig"), delimiter=";"))

    # T1: materias com o termo estrito, por orgao
    estrito = Counter()
    estrito_cnpj = Counter()
    for m in ler_zip(zip_path):
        if TERMO_CEBAS.search(m.texto_html):
            area = area_do_orgao(m.categoria)
            estrito[area] += 1
            estrito_cnpj[area] += bool(achar_cnpjs(m.texto_html))

    atos: dict[str, list[dict]] = defaultdict(list)
    for r in linhas:
        atos[r["ref_ato"]].append(r)
    decisorios = {k: v for k, v in atos.items() if not v[0]["detalhe"].startswith("sem decisao")}

    por_area = defaultdict(lambda: Counter())
    for k, v in decisorios.items():
        a = v[0]["area"]
        por_area[a]["atos"] += 1
        por_area[a]["atos_com_cnpj"] += all(r["cnpj"] for r in v)
        por_area[a]["decisoes"] += len(v)
        por_area[a]["decisoes_com_cnpj"] += sum(1 for r in v if r["cnpj"])
        por_area[a]["decisoes_cnpj_dv_ok"] += sum(1 for r in v if r["cnpj_dv_ok"] == "S")
    materias_por_area = defaultdict(set)
    for v in decisorios.values():
        materias_por_area[v[0]["area"]].add(v[0]["id_materia"])

    tipos = Counter((r["area"], r["tipo_ato"], r["deferido"]) for v in decisorios.values() for r in v)
    dias = Counter(v[0]["data_publicacao"] for v in decisorios.values())
    cnpjs_unicos = {r["cnpj"] for v in decisorios.values() for r in v if r["cnpj"]}

    total = Counter()
    for c in por_area.values():
        total.update(c)
    res = {
        "zip": zip_path.name,
        "materias_com_termo_CEBAS_ou_Entidade_Beneficente": dict(estrito),
        "materias_com_termo_e_algum_CNPJ": dict(estrito_cnpj),
        "materias_decisorias_por_area": {a: len(s) for a, s in materias_por_area.items()},
        "por_area": {a: dict(c) for a, c in por_area.items()},
        "total": dict(total),
        "pct_atos_com_cnpj": round(100 * total["atos_com_cnpj"] / total["atos"], 1),
        "pct_decisoes_com_cnpj": round(100 * total["decisoes_com_cnpj"] / total["decisoes"], 1),
        "pct_decisoes_cnpj_dv_valido": round(100 * total["decisoes_cnpj_dv_ok"] / total["decisoes"], 1),
        "cnpjs_unicos": len(cnpjs_unicos),
        "dias_com_publicacao": len(dias),
        "tipos": {" / ".join(k): n for k, n in sorted(tipos.items())},
    }
    destino = csv_path.with_name(f"metricas_{zip_path.stem}.json")
    destino.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))

    # T2: sorteio de 10 atos decisorios
    rnd = random.Random(SEMENTE)
    sorteados = rnd.sample(sorted(decisorios), 10)
    campos = list(linhas[0].keys()) + [
        "conf_cnpj",
        "conf_entidade",
        "conf_tipo",
        "conf_deferido",
        "conf_area",
        "obs",
    ]
    amostra = csv_path.with_name(f"amostra_t2_{zip_path.stem}.csv")
    with amostra.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        w.writeheader()
        for k in sorteados:
            for r in decisorios[k]:
                w.writerow(r)
    print("sorteados:", sorteados, "->", amostra)


if __name__ == "__main__":
    main()
