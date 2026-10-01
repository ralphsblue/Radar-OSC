"""Testa a consulta pública do CNIA (CNJ) por pessoa física, sem navegador.

Página: https://www.cnj.jus.br/improbidade_adm/consultar_requerido.php
O CAPTCHA foi retirado do formulário (comentários SEC-029/SEC-031 em consultar_requerido.js).
A busca é feita por chamadas Sajax (POST form-urlencoded com rs=<função> e rsargs[]).

Alvo de teste: uma pessoa física do CEIS com origem CNJ (condenação por improbidade
com proibição de contratar vigente), que precisa aparecer no CNIA.
Testa: CPF completo, nome completo, nome parcial e CPF mascarado do QSA.

Grava as respostas brutas em downloads/ (contêm dados pessoais) e um resumo
sem CPF e sem nome em teste_cnia.json.

Uso: .venv/Scripts/python fase0/dirigentes/testar_cnia.py
"""

from __future__ import annotations

import csv
import json
import re
import time
from urllib.parse import urlencode

from comum import DOWNLOADS, PASTA, RAIZ, cliente, digitos, esperar

URL = "https://www.cnj.jus.br/improbidade_adm/consultar_requerido.php"
CEIS = RAIZ / "fase0" / "portal" / "downloads" / "20260930_CEIS.csv"


def sajax(c, func: str, args: list[str]) -> tuple[int, str, float]:
    esperar()
    corpo = [("rs", func), ("rst", ""), ("rsrnd", str(int(time.time() * 1000)))]
    corpo += [("rsargs[]", a) for a in args]
    t0 = time.perf_counter()
    r = c.post(
        URL,
        content=urlencode(corpo, encoding="latin-1"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return (
        r.status_code,
        r.content.decode("latin-1"),
        round(time.perf_counter() - t0, 2),
    )


def alvo() -> tuple[str, str]:
    with CEIS.open(encoding="latin-1", newline="") as f:
        for x in csv.DictReader(f, delimiter=";"):
            if (
                x["TIPO DE PESSOA"] == "F"
                and "CNJ" in x["ORIGEM INFORMAÇÕES"]
                and len(x["NOME DO SANCIONADO"].split()) >= 3
            ):
                return digitos(x["CPF OU CNPJ DO SANCIONADO"]), x["NOME DO SANCIONADO"]
    raise SystemExit("sem alvo")


def resumir(texto: str, cpf: str, nome: str) -> dict:
    cpfs_vistos = re.findall(r"\d{3}\.\d{3}\.\d{3}-\d{2}", texto)
    mascarados = re.findall(r"[\d*]{3}\.[\d*]{3}\.[\d*]{3}-[\d*]{2}", texto)
    return {
        "tamanho": len(texto),
        "comeca_com_sajax": "+:var " in texto,
        "contem_cpf_alvo_formatado": f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        in texto,
        "contem_nome_alvo": nome.upper() in texto.upper(),
        "cpfs_completos_no_html": len(cpfs_vistos),
        "cpfs_com_asterisco_no_html": len([m for m in mascarados if "*" in m]),
        "linhas_tabela": texto.count("<tr"),
        "palavra_captcha": "captcha" in texto.lower(),
        "nenhum_registro": bool(
            re.search(r"nenhum registro|n.o foram encontrad", texto, re.IGNORECASE)
        ),
    }


def main() -> None:
    cpf, nome = alvo()
    partes = nome.split()
    casos = {
        "cpf_completo": (cpf, ""),
        "nome_completo": ("", nome),
        "nome_primeiro_ultimo": ("", f"{partes[0]} {partes[-1]}"),
        "cpf_mascarado_qsa": (f"***{cpf[3:9]}**", ""),
    }
    resumo: dict = {"alvo": "PF do CEIS com origem CNJ (dados omitidos)", "casos": {}}
    with cliente() as c:
        esperar()
        r = c.get(URL)
        resumo["get_status"] = r.status_code
        resumo["cookies"] = sorted(c.cookies.keys())
        for rotulo, (doc, nm) in casos.items():
            st1, txt1, s1 = sajax(
                c, "verificarCamposPesquisa", ["", "", "", doc, nm, "F", ""]
            )
            st2, txt2, s2 = sajax(
                c,
                "pesquisarRequeridoGetTabela",
                [
                    "",
                    "",
                    "",
                    doc,
                    nm,
                    "F",
                    "I",
                    "0",
                    "POSICAO_INICIAL_PAGINACAO_PHP0",
                    "QUANTIDADE_REGISTROS_PAGINACAO15",
                ],
            )
            (DOWNLOADS / f"cnia_{rotulo}_verificar.txt").write_text(
                txt1, encoding="utf-8"
            )
            (DOWNLOADS / f"cnia_{rotulo}_tabela.html").write_text(
                txt2, encoding="utf-8"
            )
            resumo["casos"][rotulo] = {
                "verificar": {
                    "status": st1,
                    "segundos": s1,
                    "inicio": re.sub(r"\d", "#", txt1[txt1.find("+:") :][:160]),
                },
                "tabela": {"status": st2, "segundos": s2, **resumir(txt2, cpf, nome)},
            }
            print(rotulo, json.dumps(resumo["casos"][rotulo], ensure_ascii=False))
    (PASTA / "teste_cnia.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
