"""Analisa os CSVs de CEPIM, CEIS e CNEP baixados por baixar_dados_abertos.py.

Gera:
- estatisticas de formato (tipo de pessoa, mascaramento de CPF, datas vazias);
- candidatos a CNPJs de referencia (entidades sem fins lucrativos por nome);
- amostras pequenas em fase0/portal/amostras/ (cabecalho + algumas linhas).

Uso: PYTHONIOENCODING=utf-8 .venv/Scripts/python fase0/portal/analisar_dados_abertos.py
"""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

PASTA = Path(__file__).parent
DOWNLOADS = PASTA / "downloads"
AMOSTRAS = PASTA / "amostras"
HOJE = date(2026, 9, 30)
OSC = re.compile(
    r"\b(ASSOCIA[CÇ][AÃ]O|INSTITUTO|FUNDA[CÇ][AÃ]O|SOCIEDADE BENEFICENTE|OBRA SOCIAL|"
    r"CENTRO COMUNITARIO|ONG|OSCIP|APAE|CRUZ VERMELHA|IRMANDADE|SANTA CASA|"
    r"CASA DE APOIO|CLUBE|SINDICATO|FEDERA[CÇ][AÃ]O|CONFEDERA[CÇ][AÃ]O|COOPERATIVA)\b"
)


def ler(nome: str) -> tuple[list[str], list[dict[str, str]]]:
    arq = next(DOWNLOADS.glob(f"*_{nome}.csv"))
    with arq.open(encoding="latin-1", newline="") as fh:
        leitor = csv.DictReader(fh, delimiter=";")
        linhas = list(leitor)
    return leitor.fieldnames or [], linhas


def data_br(s: str) -> date | None:
    s = s.strip()
    return datetime.strptime(s, "%d/%m/%Y").date() if s else None


def vigente(fim: date | None) -> bool:
    return fim is None or fim >= HOJE


def salvar_amostra(nome: str, campos: list[str], linhas: list[dict[str, str]]) -> None:
    AMOSTRAS.mkdir(exist_ok=True)
    # O arquivo original traz o CPF completo de pessoas fisicas; a amostra versionada mascara no padrao ***.123.456-**.
    doc = "CPF OU CNPJ DO SANCIONADO"
    linhas = [
        {**l, doc: f"***.{l[doc][3:6]}.{l[doc][6:9]}-**"} if doc in l and len(l[doc]) == 11 else l
        for l in linhas
    ]
    with (AMOSTRAS / f"amostra_{nome}.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, delimiter=";")
        w.writeheader()
        w.writerows(linhas)


def perfil_sancoes(nome: str, campos: list[str], linhas: list[dict[str, str]]) -> None:
    print(f"\n===== {nome}: {len(linhas)} linhas")
    print("TIPO DE PESSOA:", Counter(l["TIPO DE PESSOA"] for l in linhas))
    doc = "CPF OU CNPJ DO SANCIONADO"
    fmt = Counter()
    for l in linhas:
        d = l[doc]
        fmt[(l["TIPO DE PESSOA"], len(d), "*" in d or "." in d)] += 1
    print("formato documento (tipo, len, tem mascara):", fmt)
    pf = [l for l in linhas if l["TIPO DE PESSOA"] == "F"][:3]
    for l in pf:
        print("  PF exemplo:", f"***.{l[doc][3:6]}.{l[doc][6:9]}-** (no arquivo vem completo)", "|", l["NOME DO SANCIONADO"])
    print("DATA FINAL vazia:", sum(1 for l in linhas if not l["DATA FINAL SANÇÃO"].strip()))
    print("CATEGORIAS:", Counter(l["CATEGORIA DA SANÇÃO"] for l in linhas).most_common(12))
    print("ABRANGENCIA:", Counter(l["ABRAGÊNCIA DA SANÇÃO"] for l in linhas).most_common(8))
    print("Codigos de sancao unicos:", len({l["CÓDIGO DA SANÇÃO"] for l in linhas}))


def main() -> None:
    cep_c, cepim = ler("CEPIM")
    ceis_c, ceis = ler("CEIS")
    cnep_c, cnep = ler("CNEP")
    salvar_amostra("CEPIM", cep_c, cepim[:10])
    # amostra CEIS: PF, PJ vigente, PJ expirada
    pj = [l for l in ceis if l["TIPO DE PESSOA"] == "J"]
    salvar_amostra("CEIS", ceis_c, ceis[:3] + pj[:4] + [l for l in pj if data_br(l["DATA FINAL SANÇÃO"]) and not vigente(data_br(l["DATA FINAL SANÇÃO"]))][:3])
    salvar_amostra("CNEP", cnep_c, cnep[:3] + [l for l in cnep if l["TIPO DE PESSOA"] == "J"][:7])

    print("===== CEPIM:", len(cepim), "linhas,", len({l["CNPJ ENTIDADE"] for l in cepim}), "CNPJs distintos")
    print("tamanhos CNPJ:", Counter(len(l["CNPJ ENTIDADE"]) for l in cepim))
    print("MOTIVOS:", Counter(l["MOTIVO DO IMPEDIMENTO"] for l in cepim).most_common(8))
    cnt = Counter(l["CNPJ ENTIDADE"] for l in cepim)
    print("CNPJ com mais convenios:", cnt.most_common(3))
    print("filiais no CEPIM:", sum(1 for c in cnt if c[8:12] != "0001"))

    perfil_sancoes("CEIS", ceis_c, ceis)
    perfil_sancoes("CNEP", cnep_c, cnep)

    doc = "CPF OU CNPJ DO SANCIONADO"
    nome_s = "NOME DO SANCIONADO"

    print("\n===== CANDIDATOS CEPIM (OSC por nome, 1 convenio)")
    for l in [l for l in cepim if OSC.search(l["NOME ENTIDADE"]) and cnt[l["CNPJ ENTIDADE"]] == 1][:8]:
        print(" ", l["CNPJ ENTIDADE"], "|", l["NOME ENTIDADE"], "|", l["NÚMERO CONVÊNIO"], "|", l["ÓRGÃO CONCEDENTE"], "|", l["MOTIVO DO IMPEDIMENTO"])

    def osc_pj(linhas):
        return [l for l in linhas if l["TIPO DE PESSOA"] == "J" and OSC.search(l[nome_s] + " " + l["RAZÃO SOCIAL - CADASTRO RECEITA"])]

    por_cnpj_ceis = defaultdict(list)
    for l in ceis:
        por_cnpj_ceis[l[doc]].append(l)

    print("\n===== CEIS OSC vigente (CNPJ com todas as sancoes vigentes)")
    vist = set()
    for l in osc_pj(ceis):
        c = l[doc]
        if c in vist:
            continue
        vist.add(c)
        regs = por_cnpj_ceis[c]
        if all(vigente(data_br(r["DATA FINAL SANÇÃO"])) for r in regs) and len(regs) == 1:
            print(" ", c, "|", l[nome_s], "|", l["CATEGORIA DA SANÇÃO"], "|", l["DATA INÍCIO SANÇÃO"], "->", l["DATA FINAL SANÇÃO"] or "(sem fim)", "|", l["ÓRGÃO SANCIONADOR"][:50], "|", l["ABRAGÊNCIA DA SANÇÃO"])
            if len(vist) > 400:
                break

    print("\n===== CEIS OSC expirada (CNPJ so com sancoes expiradas)")
    n = 0
    for c, regs in por_cnpj_ceis.items():
        l = regs[0]
        if l["TIPO DE PESSOA"] != "J" or not OSC.search(l[nome_s]):
            continue
        if all(not vigente(data_br(r["DATA FINAL SANÇÃO"])) for r in regs):
            print(" ", c, "|", l[nome_s], "|", len(regs), "reg |", "; ".join(f'{r["DATA INÍCIO SANÇÃO"]}->{r["DATA FINAL SANÇÃO"]}' for r in regs), "|", l["CATEGORIA DA SANÇÃO"])
            n += 1
            if n >= 15:
                break

    print("\n===== CNEP PJ (OSC por nome primeiro)")
    for l in osc_pj(cnep)[:10]:
        print(" ", l[doc], "|", l[nome_s], "|", l["CATEGORIA DA SANÇÃO"], "|", l["VALOR DA MULTA"], "|", l["DATA INÍCIO SANÇÃO"], "->", l["DATA FINAL SANÇÃO"] or "(sem fim)", "|", l["ÓRGÃO SANCIONADOR"][:50])
    print("  CNEP PJ total:", sum(1 for l in cnep if l["TIPO DE PESSOA"] == "J"))

    print("\n===== Multi-cadastro")
    s_cepim = {l["CNPJ ENTIDADE"] for l in cepim}
    s_ceis = {l[doc] for l in ceis if l["TIPO DE PESSOA"] == "J"}
    s_cnep = {l[doc] for l in cnep if l["TIPO DE PESSOA"] == "J"}
    nomes = {l["CNPJ ENTIDADE"]: l["NOME ENTIDADE"] for l in cepim}
    nomes.update({l[doc]: l[nome_s] for l in ceis + cnep})
    for rot, s in [("CEPIM&CEIS", s_cepim & s_ceis), ("CEPIM&CNEP", s_cepim & s_cnep), ("CEIS&CNEP", s_ceis & s_cnep), ("TODOS", s_cepim & s_ceis & s_cnep)]:
        lst = sorted(s)
        print(f"  {rot}: {len(lst)}")
        for c in sorted(lst, key=lambda c: not OSC.search(nomes.get(c, "")))[:6]:
            print("    ", c, "|", nomes.get(c))

    print("\n===== Filial / raiz no CEIS e CNEP")
    for rot, linhas in [("CEIS", ceis), ("CNEP", cnep)]:
        pjs = [l for l in linhas if l["TIPO DE PESSOA"] == "J"]
        print(f"  {rot} tamanhos doc PJ:", Counter(len(l[doc]) for l in pjs))
        filiais = [l for l in pjs if len(l[doc]) == 14 and l[doc][8:12] != "0001"]
        print(f"  {rot} filiais (ordem != 0001): {len(filiais)}")
        for l in sorted(filiais, key=lambda l: not OSC.search(l[nome_s]))[:6]:
            raiz = l[doc][:8]
            outros = sorted({x[doc] for x in pjs if x[doc][:8] == raiz} - {l[doc]})
            print("    ", l[doc], "|", l[nome_s], "|", l["DATA INÍCIO SANÇÃO"], "->", l["DATA FINAL SANÇÃO"] or "(sem fim)", "| outros do mesmo grupo:", outros[:4])
        so_raiz = [l for l in pjs if len(l[doc]) != 14]
        for l in so_raiz[:5]:
            print("    so raiz/formato estranho:", repr(l[doc]), l[nome_s])

    print("\n===== Nomes de PF (CEIS) - presenca de nome e documento")
    pf = [l for l in ceis if l["TIPO DE PESSOA"] == "F"]
    print("  PF total:", len(pf), "com nome:", sum(1 for l in pf if l[nome_s].strip()), "com CPF 11 digitos:", sum(1 for l in pf if re.fullmatch(r"\d{11}", l[doc])))
    print("  CPF com mascara (*):", sum(1 for l in pf if "*" in l[doc]))


if __name__ == "__main__":
    main()
