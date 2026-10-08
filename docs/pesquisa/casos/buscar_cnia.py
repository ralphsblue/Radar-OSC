"""Procura uma PJ com ocorrência no CNIA (CNJ) pela Consulta Consolidada do TCU.

Candidatos: pessoas jurídicas do CEIS (download de 30/09/2026) cuja origem da
informação é o Conselho Nacional de Justiça, ou seja, condenações por improbidade
lançadas pelo CNJ no CEIS. Prioriza nomes típicos de OSC (associação, instituto,
fundação etc.).

Limites: no máximo 60 consultas, 2 s entre elas; para depois de achar 3 OSCs
com CNIA = CONSTAM_REGISTROS.

Uso: .venv/Scripts/python fase0/casos/buscar_cnia.py
Saída: respostas/cnia_busca/tcu_<cnpj>.json e respostas/cnia_busca/_resumo.json
"""

from __future__ import annotations

import csv
import json

from comum import RAIZ, RESPOSTAS, baixar, cliente_http

CEIS = RAIZ / "fase0" / "portal" / "downloads" / "20260930_CEIS.csv"
URL_TCU = "https://certidoes-apf.apps.tcu.gov.br/api/rest/publico/certidoes/{}?seEmitirPDF=false"
PALAVRAS_OSC = ("ASSOC", "INSTITUTO", "FUNDA", "SOCIEDADE", "CENTRO", "IGREJA", "CLUBE", "ONG", "MOVIMENTO")
NAO_OSC = ("LTDA", "EIRELI", "ADVOGADOS", "COMERCIO", "S/A", "S.A", "ME ")
MAX_CONSULTAS = 60
PARAR_COM = 3
# Já identificado nas fichas como CEIS vigente de origem CNJ: entra primeiro.
PRIORITARIOS = ["06287661000126"]


def candidatos() -> list[tuple[str, str]]:
    linhas = list(csv.reader(CEIS.open(encoding="latin1"), delimiter=";"))[1:]
    vistos: dict[str, str] = {}
    for x in linhas:
        if x[2] != "J" or "CNJ" not in x[22]:
            continue
        nome = x[4].upper()
        if any(p in nome for p in NAO_OSC) or not any(p in nome for p in PALAVRAS_OSC):
            continue
        vistos.setdefault(x[3], x[4])
    ordem = [c for c in PRIORITARIOS if c in vistos] + [c for c in vistos if c not in PRIORITARIOS]
    return [(c, vistos[c]) for c in ordem]


def main() -> None:
    pasta = RESPOSTAS / "cnia_busca"
    resumo = []
    achados = 0
    with cliente_http() as cliente:
        for cnpj, nome in candidatos()[:MAX_CONSULTAS]:
            reg = baixar(cliente, URL_TCU.format(cnpj), pasta / f"tcu_{cnpj}.json")
            corpo = reg["corpo"] if isinstance(reg["corpo"], dict) else {}
            situacoes = {c["tipo"]: c["situacao"] for c in corpo.get("certidoes", [])}
            resumo.append(
                {"cnpj": cnpj, "nome": nome, "status": reg["meta"]["status"], "situacoes": situacoes}
            )
            if situacoes.get("CNIA") == "CONSTAM_REGISTROS":
                achados += 1
                print(f"  CNIA CONSTAM: {cnpj} {nome}")
                if achados >= PARAR_COM:
                    break
    (pasta / "_resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(resumo)} consultas, {achados} com CNIA CONSTAM_REGISTROS")


if __name__ == "__main__":
    main()
