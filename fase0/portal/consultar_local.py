"""Consulta local (plano B sem chave) de um ou mais CNPJs/CPFs nos CSVs de CEPIM, CEIS e CNEP.

Busca exata pelo documento de 14 (ou 11) digitos e, separadamente, pela raiz (8 digitos)
para mostrar registros de outros estabelecimentos do mesmo grupo.
Vigente = sem data final ou data final >= data de referencia.

Uso: PYTHONIOENCODING=utf-8 .venv/Scripts/python fase0/portal/consultar_local.py 53524534000183 [...]
"""

from __future__ import annotations

import csv
import re
import sys
from datetime import date, datetime
from pathlib import Path

DOWNLOADS = Path(__file__).parent / "downloads"
HOJE = date(2026, 9, 30)


def ler(nome: str) -> list[dict[str, str]]:
    arq = next(DOWNLOADS.glob(f"*_{nome}.csv"))
    with arq.open(encoding="latin-1", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def situacao(fim: str) -> str:
    if not fim.strip():
        return "VIGENTE (sem data final)"
    d = datetime.strptime(fim.strip(), "%d/%m/%Y").date()
    return "VIGENTE" if d >= HOJE else "EXPIRADA"


def main(docs: list[str]) -> None:
    cepim, ceis, cnep = ler("CEPIM"), ler("CEIS"), ler("CNEP")
    for bruto in docs:
        doc = re.sub(r"\D", "", bruto)
        raiz = doc[:8]
        print(f"\n######## {doc}")
        for l in cepim:
            if l["CNPJ ENTIDADE"] == doc:
                print("  CEPIM exato:", l["NOME ENTIDADE"], "| convenio", l["NÚMERO CONVÊNIO"], "|", l["ÓRGÃO CONCEDENTE"], "|", l["MOTIVO DO IMPEDIMENTO"])
            elif len(doc) == 14 and l["CNPJ ENTIDADE"][:8] == raiz:
                print("  CEPIM mesma raiz:", l["CNPJ ENTIDADE"], l["NOME ENTIDADE"])
        for rot, linhas in (("CEIS", ceis), ("CNEP", cnep)):
            for l in linhas:
                d = l["CPF OU CNPJ DO SANCIONADO"]
                tipo = "exato" if d == doc else ("mesma raiz " + d if len(doc) == 14 and len(d) == 14 and d[:8] == raiz else None)
                if not tipo:
                    continue
                multa = f' | multa {l["VALOR DA MULTA"]}' if "VALOR DA MULTA" in l else ""
                print(
                    f"  {rot} {tipo}: cod {l['CÓDIGO DA SANÇÃO']} | {l['NOME DO SANCIONADO']} | {l['CATEGORIA DA SANÇÃO']}"
                    f" | {l['DATA INÍCIO SANÇÃO']} -> {l['DATA FINAL SANÇÃO'] or '(vazio)'} = {situacao(l['DATA FINAL SANÇÃO'])}"
                    f" | {l['ÓRGÃO SANCIONADOR']} ({l['ESFERA ÓRGÃO SANCIONADOR']}/{l['UF ÓRGÃO SANCIONADOR']})"
                    f" | abrangencia: {l['ABRAGÊNCIA DA SANÇÃO']} | processo {l['NÚMERO DO PROCESSO']}{multa}"
                    f" | origem: {l['ORIGEM INFORMAÇÕES']}"
                )


if __name__ == "__main__":
    main(sys.argv[1:])
