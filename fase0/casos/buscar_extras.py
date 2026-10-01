"""Buscas complementares para casos que faltaram depois de buscar_ativos.py.

1. Dirigente sancionado em entidade sem sanção vigente própria: PJ (nome de OSC)
   do CEIS cujas sanções já expiraram, Ativa no OpenCNPJ, com QSA casando nome +
   6 dígitos do meio do CPF com PF do CEIS/CNEP (D15).
2. Ausente do Mapa das OSCs: associações Ativas marcadas `removida_do_mosc = sim`
   nas fatias da base CSV do Mapa, conferidas na API do Mapa e no OpenCNPJ.
3. Matriz da IDEAS (24.006.302/0001-35), porque a 0004-88 voltou como Matriz.

Uso: .venv/Scripts/python fase0/casos/buscar_extras.py
Saída: respostas/busca_extras/
"""

from __future__ import annotations

import csv
import json
from datetime import date

from comum import RAIZ, RESPOSTAS, baixar, cliente_http
from fatos import NATUREZA_TEXTO_CODIGO, dirigentes

PASTA = RESPOSTAS / "busca_extras"
REF = date(2026, 10, 1)
MAX_DIRIGENTE = 40
MAX_MAPA = 15
OSC = ("ASSOC", "INSTITUTO", "FUNDA", "SOCIEDADE", "CENTRO", "IGREJA", "CLUBE", "ONG", "MOVIMENTO")
NAO_OSC = ("LTDA", "EIRELI", "ADVOGADOS", "COMERCIO", "S/A", "S.A", " ME", "EPP")


def _d(s: str) -> date | None:
    try:
        return date(int(s[6:10]), int(s[3:5]), int(s[:2])) if s else None
    except (ValueError, IndexError):
        return None


def _qsa(c: dict) -> list[dict]:
    return [{"nome": q.get("nome_socio"), "doc": q.get("cnpj_cpf_socio"), "tipo": q.get("identificador_socio"),
             "qualificacao": q.get("qualificacao_socio")} for q in c.get("QSA") or []]


def candidatos_dirigente() -> list[str]:
    arq = RAIZ / "fase0" / "portal" / "downloads" / "20260930_CEIS.csv"
    por_cnpj: dict[str, list[dict]] = {}
    for x in csv.DictReader(arq.open(encoding="latin1"), delimiter=";"):
        if x["TIPO DE PESSOA"] == "J":
            por_cnpj.setdefault(x["CPF OU CNPJ DO SANCIONADO"], []).append(x)
    saida = []
    for cnpj, linhas in por_cnpj.items():
        nome = linhas[0]["NOME DO SANCIONADO"].upper()
        if not any(p in nome for p in OSC) or any(p in nome for p in NAO_OSC):
            continue
        if all((_d(x["DATA FINAL SANÇÃO"]) or date.max) < REF for x in linhas):
            saida.append(cnpj)
    return saida


def candidatos_mapa() -> list[str]:
    saida = []
    for arq in sorted((RESPOSTAS / "mapa_base").glob("*.csv")):
        for r in csv.DictReader(arq.open(encoding="latin1"), delimiter=";"):
            if (r["removida_do_mosc"] == "sim" and r["situacao_cadastral"] == "Ativa" and r["natureza_juridica"] == "3999"
                    and r["matriz_filial"] == "Matriz"):
                saida.append(r["cnpj"].zfill(14))
    return saida


def main() -> None:
    resumo: dict = {"dirigente": [], "ausente_mapa": []}
    with cliente_http() as cliente:
        baixar(cliente, "https://api.opencnpj.org/24006302000135", PASTA / "opencnpj_24006302000135.json")

        for cnpj in candidatos_dirigente()[:MAX_DIRIGENTE]:
            reg = baixar(cliente, f"https://api.opencnpj.org/{cnpj}", PASTA / f"opencnpj_{cnpj}.json")
            c = reg["corpo"] if reg["meta"]["status"] == 200 else None
            if not c or c.get("situacao_cadastral") != "Ativa":
                continue
            d = dirigentes(_qsa(c))
            if d["fortes"] or d["so_nome"]:
                resumo["dirigente"].append({"cnpj": cnpj, "razao_social": c["razao_social"], "dirigentes": d})
                print(f"  DIRIGENTE: {cnpj} {c['razao_social']} fortes={len(d['fortes'])} so_nome={len(d['so_nome'])}")
                if d["fortes"]:
                    break

        for cnpj in candidatos_mapa()[:MAX_MAPA]:
            busca = baixar(cliente, f"https://mapaosc.ipea.gov.br/api/api/busca/cnpj/{cnpj.lstrip('0')}", PASTA / f"mapa_{cnpj}.json")
            itens = busca["corpo"] if isinstance(busca["corpo"], list) else []
            if any(str(i.get("cd_identificador_osc", "")).zfill(14) == cnpj for i in itens):
                continue
            reg = baixar(cliente, f"https://api.opencnpj.org/{cnpj}", PASTA / f"opencnpj_{cnpj}.json")
            c = reg["corpo"] if reg["meta"]["status"] == 200 else None
            if c and c.get("situacao_cadastral") == "Ativa" and NATUREZA_TEXTO_CODIGO.get(c.get("natureza_juridica", "").lower()) == 3999:
                resumo["ausente_mapa"].append({"cnpj": cnpj, "razao_social": c["razao_social"], "inicio": c.get("data_inicio_atividade"),
                                               "cnae": c.get("cnae_principal")})
                print(f"  AUSENTE DO MAPA: {cnpj} {c['razao_social']}")
                if len(resumo["ausente_mapa"]) >= 2:
                    break
    (PASTA / "_resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
