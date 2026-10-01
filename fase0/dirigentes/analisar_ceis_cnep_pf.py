"""Perfila as pessoas físicas do CEIS e do CNEP (CSV oficial do Portal da Transparência).

Reaproveita os CSVs baixados por fase0/portal/baixar_dados_abertos.py (fora do versionamento).
Confirma CPF completo, conta por origem e categoria (para ver o que já cobre improbidade CNJ
e inabilitação TCU) e mede a sobreposição com as listas do TCU, só com contagens.

Saída: analise_ceis_cnep_pf.json (versionável, sem CPF).

Uso: .venv/Scripts/python fase0/dirigentes/analisar_ceis_cnep_pf.py
"""

from __future__ import annotations

import collections
import csv
import json
from datetime import date

from comum import DOWNLOADS, PASTA, RAIZ, cpf_valido, data_br, digitos, normalizar_nome

PORTAL = RAIZ / "fase0" / "portal" / "downloads"
HOJE = date(2026, 10, 1)


def ler(nome: str) -> list[dict]:
    arq = max(PORTAL.glob(f"*_{nome}.csv"))
    with arq.open(encoding="latin-1", newline="") as f:
        return list(csv.DictReader(f, delimiter=";")), arq.name


def perfil(nome: str) -> tuple[dict, set[str]]:
    linhas, arquivo = ler(nome)
    pf = [x for x in linhas if x["TIPO DE PESSOA"] == "F"]
    docs = [digitos(x["CPF OU CNPJ DO SANCIONADO"]) for x in pf]
    vig = []
    for x in pf:
        fim = data_br(x["DATA FINAL SANÇÃO"])
        vig.append(fim is None or fim >= HOJE)
    origem = collections.Counter(x["ORIGEM INFORMAÇÕES"] for x in pf)
    origem_vig = collections.Counter(
        x["ORIGEM INFORMAÇÕES"] for x, v in zip(pf, vig) if v
    )
    categoria = collections.Counter(x["CATEGORIA DA SANÇÃO"] for x in pf)
    categoria_vig = collections.Counter(
        x["CATEGORIA DA SANÇÃO"] for x, v in zip(pf, vig) if v
    )
    fund_improb = sum(
        "8.429" in x["FUNDAMENTAÇÃO LEGAL"] or "8429" in x["FUNDAMENTAÇÃO LEGAL"]
        for x in pf
    )
    chave = collections.defaultdict(set)
    for x, d in zip(pf, docs):
        chave[(normalizar_nome(x["NOME DO SANCIONADO"]), d[3:9])].add(d)
    p = {
        "arquivo": arquivo,
        "linhas_total": len(linhas),
        "linhas_pf": len(pf),
        "pf_cpf_11_digitos": sum(len(d) == 11 for d in docs),
        "pf_cpf_dv_valido": sum(cpf_valido(d) for d in docs),
        "pf_cpf_mascarado": sum("*" in x["CPF OU CNPJ DO SANCIONADO"] for x in pf),
        "pf_cpf_distintos": len(set(docs)),
        "pf_nome_vazio": sum(not x["NOME DO SANCIONADO"].strip() for x in pf),
        "pf_linhas_vigentes": sum(vig),
        "pf_cpf_distintos_vigentes": len({d for d, v in zip(docs, vig) if v}),
        "pf_sem_data_final": sum(not x["DATA FINAL SANÇÃO"].strip() for x in pf),
        "pf_fundamentacao_cita_lei_8429": fund_improb,
        "chaves_nome_meio_com_mais_de_um_cpf": sum(len(v) > 1 for v in chave.values()),
        "origem_pf": dict(origem.most_common(15)),
        "origem_pf_vigentes": dict(origem_vig.most_common(15)),
        "categoria_pf": dict(categoria.most_common()),
        "categoria_pf_vigentes": dict(categoria_vig.most_common()),
    }
    return p, {d for d in docs if len(d) == 11}


def main() -> None:
    ceis, cpfs_ceis = perfil("CEIS")
    cnep, cpfs_cnep = perfil("CNEP")
    saida = {"CEIS": ceis, "CNEP": cnep}
    tcu = {}
    for lista in (
        "responsaveis-contas-irregulares",
        "responsaveis-inabilitados",
        "responsaveis-fins-eleitorais",
    ):
        arq = DOWNLOADS / f"tcu_{lista}.json"
        if arq.exists():
            itens = json.loads(arq.read_text(encoding="utf-8"))
            tcu[lista] = {
                digitos(i.get("numeroRegistro"))
                for i in itens
                if len(digitos(i.get("numeroRegistro"))) == 11
            }
    saida["sobreposicao_cpf_com_tcu"] = {
        lista: {
            "cpfs_tcu": len(c),
            "tambem_no_ceis": len(c & cpfs_ceis),
            "tambem_no_cnep": len(c & cpfs_cnep),
            "so_no_tcu": len(c - cpfs_ceis - cpfs_cnep),
        }
        for lista, c in tcu.items()
    }
    uniao_tcu = set().union(*tcu.values()) if tcu else set()
    saida["universo_pf"] = {
        "ceis_ou_cnep": len(cpfs_ceis | cpfs_cnep),
        "tcu_tres_listas": len(uniao_tcu),
        "uniao_total": len(cpfs_ceis | cpfs_cnep | uniao_tcu),
    }
    (PASTA / "analise_ceis_cnep_pf.json").write_text(
        json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(saida, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
