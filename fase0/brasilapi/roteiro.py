"""
roteiro.py - executa o roteiro 18.3 (T1-T5, T7 e extras do 25.1) nas tres fontes.

1 s de pausa entre chamadas. T6 (latencia) fica em t6_latencia.py.
Uso:
    python roteiro.py                 # todos os casos, todas as fontes
    python roteiro.py --casos T1,T7   # subconjunto
    python roteiro.py --fontes minhareceita
    python roteiro.py --so-pendentes  # refaz so o que nao teve resposta definitiva (200/400/404)

Respostas nao definitivas (5xx, timeout) sao arquivadas em respostas/falhas/ antes de
serem sobrescritas, para documentar a instabilidade das fontes.
"""
import argparse
import json
import time

import httpx

from comum import FONTES, OUT, consultar, gerar_aleatorio, resumo, salvar, valida

# T3: raiz aleatoria (semente fixa para reprodutibilidade) + 0001 + DVs (cap. 4)
# Observacao: com seed 2026 (15881399000134) e seeds 1 a 4 a raiz sorteada EXISTE na base
# (cerca de 60 milhoes de raizes ocupadas); seed 5 foi a primeira a dar 404 no OpenCNPJ.
T3_CNPJ = gerar_aleatorio(seed=5)  # 94580730000152

CASOS = [
    ("T1", "19131243000197", "OSC regular (Open Knowledge Brasil)"),
    ("T2", "00000000000191", "Banco do Brasil - natureza nao elegivel"),
    ("T3", T3_CNPJ, "CNPJ inexistente com DV valido"),
    ("T3b", "19131243000198", "DV invalido (a API valida DV?)"),
    ("T4", "08942107000160", "Associacao BAIXADA"),
    ("T5", "12ABC34501DE35", "Alfanumerico (exemplo oficial da Receita)"),
    ("T5r", "00000000E08G12", "Alfanumerico REAL: filial do Banco do Brasil, primeiro CNPJ alfanumerico (31/07/2026)"),
    ("T7", "62779145000270", "Filial ATIVA da Santa Casa de SP"),
    ("T7m", "62779145000190", "Matriz da Santa Casa de SP (raiz + 0001 da filial T7)"),
    ("T7b", "04955882000523", "Filial BAIXADA de associacao com matriz ativa (Instituto GRPCOM)"),
    ("T7bm", "04955882000108", "Matriz do Instituto GRPCOM (raiz + 0001 da filial T7b)"),
    ("E1", "65478551000100", "Associacao aberta ha menos de 1 ano"),
    ("E2", "00108217000110", "Organizacao religiosa (3220)"),
    ("E3", "04311762000160", "Cooperativa (2143)"),
]

ap = argparse.ArgumentParser()
ap.add_argument("--casos", default="")
ap.add_argument("--fontes", default=",".join(FONTES))
ap.add_argument("--so-pendentes", action="store_true")
a = ap.parse_args()
DEFINITIVOS = {200, 400, 404}
FALHAS = OUT / "falhas"


def anterior(fonte, caso, cnpj):
    p = OUT / f"{fonte}_{caso}_{cnpj}.json"
    return (p, json.loads(p.read_text(encoding="utf-8"))) if p.exists() else (p, None)


def arquivar(p, dados):
    FALHAS.mkdir(exist_ok=True)
    carimbo = dados["consultado_em"].replace(":", "").replace("+0000", "Z")
    (FALHAS / f"{p.stem}_{carimbo}.json").write_text(p.read_text(encoding="utf-8"), encoding="utf-8")


filtro = set(a.casos.split(",")) if a.casos else None

with httpx.Client() as client:
    primeira = True
    for caso, cnpj, desc in CASOS:
        if filtro and caso not in filtro:
            continue
        print(f"\n== {caso} {cnpj} ({desc}) DV={valida(cnpj)}", flush=True)
        for fonte in a.fontes.split(","):
            p, velho = anterior(fonte, caso, cnpj)
            if a.so_pendentes and velho and velho.get("http") in DEFINITIVOS:
                continue
            if velho and velho.get("http") not in DEFINITIVOS:
                arquivar(p, velho)
            if not primeira:
                time.sleep(1)
            primeira = False
            res = consultar(client, fonte, cnpj)
            if velho and velho.get("http") in DEFINITIVOS and res.get("http") not in DEFINITIVOS:
                # nao sobrescreve resposta boa com falha; so arquiva a falha
                FALHAS.mkdir(exist_ok=True)
                carimbo = res["consultado_em"].replace(":", "").replace("+0000", "Z")
                (FALHAS / f"{p.stem}_{carimbo}.json").write_text(
                    json.dumps({"caso": caso, "cnpj_consultado": cnpj, **res}, ensure_ascii=False, indent=2),
                    encoding="utf-8")
            else:
                salvar(res, caso, cnpj)
            print("   ", resumo(res), flush=True)
