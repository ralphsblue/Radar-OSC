"""Baixa e perfila as relações de contas julgadas irregulares do TCE-SP.

Página: https://www.tce.sp.gov.br/relacao-de-responsaveis-por-contas-julgadas-irregulares
Planilhas xlsx atualizadas mensalmente, com CPF "anonimizado".
A relação "Prest_Contas" é a de prestação de contas de repasses ao Terceiro Setor,
ou seja, contas de parcerias (art. 39, VI e VII, a, da Lei 13.019/2014).

Saída: downloads/tcesp_*.xlsx (bruto, fora do versionamento) e analise_tcesp.json
(cabeçalhos, contagens, formato do CPF, colisões de nome + 6 dígitos; sem dados pessoais).

Uso: .venv/Scripts/python fase0/dirigentes/baixar_tcesp.py
"""

from __future__ import annotations

import collections
import json
import re
from datetime import date

import openpyxl

from comum import AMOSTRAS, DOWNLOADS, PASTA, cliente, data_br, esperar, normalizar_nome

HOJE = date(2026, 10, 1)

BASE = "https://www.tce.sp.gov.br/sites/default/files/portal/"
ARQUIVOS = {
    "fe_completa": "contas%20irregulares%20de%2001-09-2018%20a%2001-09-2026_FE_CPF_anonimizado_Completa.xlsx",
    "contas_anuais": "contas%20irregulares%20de%2001-01-1900%20a%2001-09-2026_Contas_Anuais_CPF_anonimizado.xlsx",
    "prest_contas_terceiro_setor": "contas%20irregulares%20de%2001-01-1900%20a%2001-09-2026_Prest_Contas_CPF_anonimizado.xlsx",
}


def formato_doc(v: str) -> str:
    return re.sub(r"\d", "9", v)


def ler_registros(caminho) -> list[dict]:
    """Layout observado em 01/10/2026: cabeçalho com Responsável(agrupador), #, Responsável,
    CPF, Processo TC, Matéria, Origem, Trânsito em Julgado, Exercício. Linhas de dados têm
    CPF no formato 999.XXX.XXX-99; a coluna 0 só é preenchida na primeira linha de cada pessoa."""
    ws = openpyxl.load_workbook(caminho, read_only=True).worksheets[0]
    regs = []
    for row in ws.iter_rows(values_only=True):
        x = [("" if c is None else str(c)).strip() for c in row]
        if len(x) > 8 and re.fullmatch(r"\d{3}\.XXX\.XXX-\d{2}", x[3]):
            regs.append(
                {
                    "nome": x[2],
                    "cpf_parcial": x[3],
                    "processo": x[4],
                    "materia": x[5],
                    "origem": x[6],
                    "transito": x[7],
                    "exercicio": x[8],
                }
            )
    return regs


def perfil(caminho) -> dict:
    regs = ler_registros(caminho)
    ws = openpyxl.load_workbook(caminho, read_only=True).worksheets[0]
    cab = next(
        (
            [("" if c is None else str(c)).strip() for c in r]
            for r in ws.iter_rows(values_only=True)
            if r and any(str(c or "").strip() == "CPF" for c in r)
        ),
        [],
    )
    ds = [d for d in (data_br(r["transito"]) for r in regs) if d]
    limite = date(HOJE.year - 8, HOJE.month, HOJE.day)
    pessoas = collections.defaultdict(set)
    for r in regs:
        pessoas[normalizar_nome(r["nome"])].add(r["cpf_parcial"])
    return {
        "cabecalho": cab,
        "registros": len(regs),
        "formatos_cpf": dict(
            collections.Counter(formato_doc(r["cpf_parcial"]) for r in regs)
        ),
        "nomes_distintos": len(pessoas),
        "cpf_parciais_distintos": len({r["cpf_parcial"] for r in regs}),
        "nomes_com_mais_de_um_cpf_parcial": sum(len(v) > 1 for v in pessoas.values()),
        "transito_min": min(ds).isoformat() if ds else None,
        "transito_max": max(ds).isoformat() if ds else None,
        "registros_ultimos_8_anos": sum(d >= limite for d in ds),
        "nomes_ultimos_8_anos": len(
            {
                normalizar_nome(r["nome"])
                for r in regs
                if (d := data_br(r["transito"])) and d >= limite
            }
        ),
        "materias": dict(
            collections.Counter(r["materia"] for r in regs).most_common(10)
        ),
        "origens_distintas": len({r["origem"] for r in regs}),
    }


def gravar_amostra(rotulo: str, caminho) -> None:
    """Amostra versionável: primeiro nome + ***, CPF totalmente mascarado."""
    regs = ler_registros(caminho)
    amostra = []
    for r in regs[:: max(1, len(regs) // 8)][:8]:
        x = dict(r)
        x["nome"] = x["nome"].split(" ")[0] + " ***"
        x["cpf_parcial"] = "***.XXX.XXX-**"
        amostra.append(x)
    AMOSTRAS.mkdir(exist_ok=True)
    (AMOSTRAS / f"amostra_tcesp_{rotulo}.json").write_text(
        json.dumps(amostra, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def main() -> None:
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    resultado = {}
    with cliente() as c:
        for rotulo, nome in ARQUIVOS.items():
            esperar()
            r = c.get(BASE + nome)
            destino = DOWNLOADS / f"tcesp_{rotulo}.xlsx"
            reg = {
                "url": BASE + nome,
                "status": r.status_code,
                "bytes": len(r.content),
                "last_modified": r.headers.get("last-modified"),
            }
            if r.status_code == 200:
                destino.write_bytes(r.content)
                reg.update(perfil(destino))
                gravar_amostra(rotulo, destino)
            resultado[rotulo] = reg
            print(rotulo, reg["status"], reg["bytes"])
    (PASTA / "analise_tcesp.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(resultado, ensure_ascii=False, indent=1)[:6000])


if __name__ == "__main__":
    main()
