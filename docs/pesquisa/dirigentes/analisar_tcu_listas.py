"""Perfila as listas de responsáveis do TCU baixadas por baixar_tcu_listas.py.

Não imprime nem grava CPF completo: só contagens e amostras mascaradas.
Saída: analise_tcu.json (versionável) e amostras/amostra_tcu_<lista>.json (CPF mascarado).

Uso: .venv/Scripts/python fase0/dirigentes/analisar_tcu_listas.py
"""

from __future__ import annotations

import collections
import json
from datetime import date

from comum import (
    AMOSTRAS,
    DOWNLOADS,
    PASTA,
    cpf_valido,
    data_br,
    digitos,
    mascarar_cpf,
    normalizar_nome,
)

LISTAS = [
    "responsaveis-contas-irregulares",
    "responsaveis-inabilitados",
    "responsaveis-fins-eleitorais",
]
HOJE = date(2026, 10, 1)


def perfil(lista: str) -> dict:
    itens = json.loads((DOWNLOADS / f"tcu_{lista}.json").read_text(encoding="utf-8"))
    campos = collections.Counter(k for it in itens for k in it)
    tipo = collections.Counter(it.get("tipoRegistro") for it in itens)
    p: dict = {"itens": len(itens), "campos": dict(campos), "tipoRegistro": dict(tipo)}

    docs_pf = []
    formatos = collections.Counter()
    for it in itens:
        reg = it.get("numeroRegistro") or ""
        d = digitos(reg)
        if it.get("tipoRegistro") in ("CPF", None) and len(d) == 11:
            docs_pf.append(d)
            formatos["cpf_formatado" if "." in reg else "cpf_digitos"] += 1
        elif "*" in reg:
            formatos["mascarado"] += 1
        elif len(d) == 14:
            formatos["cnpj"] += 1
        else:
            formatos[f"outro_{len(d)}"] += 1
    p["formato_documento"] = dict(formatos)
    p["cpf_total"] = len(docs_pf)
    p["cpf_dv_valido"] = sum(cpf_valido(d) for d in docs_pf)
    p["cpf_distintos"] = len(set(docs_pf))
    p["nome_vazio"] = sum(not (it.get("nome") or "").strip() for it in itens)

    # colisões que importam para o casamento nome + 6 dígitos do meio
    chave = collections.defaultdict(set)
    meio = collections.defaultdict(set)
    for it in itens:
        d = digitos(it.get("numeroRegistro"))
        if len(d) == 11:
            chave[(normalizar_nome(it.get("nome", "")), d[3:9])].add(d)
            meio[d[3:9]].add(d)
    p["chaves_nome_meio"] = len(chave)
    p["chaves_nome_meio_com_mais_de_um_cpf"] = sum(len(v) > 1 for v in chave.values())
    p["meio_com_mais_de_um_cpf"] = sum(len(v) > 1 for v in meio.values())

    for campo in (
        "dataTransitoEmJulgado",
        "dataFinalSancao",
        "dataFinalFinsEleitorais",
        "dataAcordao",
    ):
        ds = [data_br(it.get(campo)) for it in itens if campo in it]
        ds = [x for x in ds if x]
        if not ds:
            continue
        info = {
            "preenchidos": len(ds),
            "min": ds[0].isoformat(),
            "max": ds[0].isoformat(),
        }
        info["min"] = min(ds).isoformat()
        info["max"] = max(ds).isoformat()
        info["futuras"] = sum(x > HOJE for x in ds)
        if campo == "dataTransitoEmJulgado":
            limite = date(HOJE.year - 8, HOJE.month, HOJE.day)
            info["ultimos_8_anos"] = sum(x >= limite for x in ds)
            info["por_decada"] = dict(
                sorted(collections.Counter(f"{x.year // 10 * 10}s" for x in ds).items())
            )
        p[campo] = info

    p["uf"] = dict(collections.Counter(it.get("uf") for it in itens).most_common(30))
    p["processos_distintos"] = len({it.get("numeroProcessoFormatado") for it in itens})

    # amostra mascarada
    AMOSTRAS.mkdir(exist_ok=True)
    amostra = []
    for it in itens[:: max(1, len(itens) // 8)][:8]:
        x = dict(it)
        if len(digitos(x.get("numeroRegistro"))) == 11:
            x["numeroRegistro"] = mascarar_cpf(x["numeroRegistro"])
        x["nome"] = (x.get("nome") or "").split(" ")[0] + " ***"
        amostra.append(x)
    (AMOSTRAS / f"amostra_tcu_{lista}.json").write_text(
        json.dumps(amostra, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    # CSV: cabeçalho e codificação
    csv_bruto = (DOWNLOADS / f"tcu_{lista}.csv").read_bytes()
    for enc in ("utf-8", "cp1252"):
        try:
            texto = csv_bruto.decode(enc)
            p["csv_encoding"] = enc
            break
        except UnicodeDecodeError:
            continue
    linhas = texto.splitlines()
    p["csv_primeiras_linhas_sem_dados"] = (
        linhas[:2] if linhas and linhas[0].startswith("sep=") else linhas[:1]
    )
    p["csv_linhas"] = len(linhas)
    return p


def main() -> None:
    saida = {lista: perfil(lista) for lista in LISTAS}

    # sobreposição entre listas (por CPF), só contagens
    conjuntos = {}
    for lista in LISTAS:
        itens = json.loads((DOWNLOADS / f"tcu_{lista}.json").read_text(encoding="utf-8"))
        conjuntos[lista] = {
            digitos(i.get("numeroRegistro")) for i in itens if len(digitos(i.get("numeroRegistro"))) == 11
        }
    saida["sobreposicao_cpf"] = {
        "fins_eleitorais_dentro_de_contas_irregulares": len(
            conjuntos["responsaveis-fins-eleitorais"] & conjuntos["responsaveis-contas-irregulares"]
        ),
        "fins_eleitorais_total": len(conjuntos["responsaveis-fins-eleitorais"]),
        "inabilitados_dentro_de_contas_irregulares": len(
            conjuntos["responsaveis-inabilitados"] & conjuntos["responsaveis-contas-irregulares"]
        ),
        "inabilitados_total": len(conjuntos["responsaveis-inabilitados"]),
    }
    (PASTA / "analise_tcu.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(saida, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
