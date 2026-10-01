"""Testa os filtros dos endpoints oficiais do TCU para pessoa física.

Pergunta: dá para consultar on-line com o que o QSA oferece (nome + CPF mascarado)?
Pega um registro real da lista baixada e testa variações de filtro.
Imprime só contagens (sem CPF nem nome completo).

Uso: .venv/Scripts/python fase0/dirigentes/testar_tcu_filtros.py
"""

from __future__ import annotations

import json

from comum import DOWNLOADS, PASTA, cliente, digitos, esperar

BASE = "https://certidoes.apps.tcu.gov.br/api/publico"


def main() -> None:
    itens = json.loads(
        (DOWNLOADS / "tcu_responsaveis-contas-irregulares.json").read_text(
            encoding="utf-8"
        )
    )
    alvo = next(
        i
        for i in itens
        if i.get("tipoRegistro") == "CPF"
        and len(digitos(i.get("numeroRegistro"))) == 11
        and len(i["nome"].split()) >= 3
    )
    cpf = digitos(alvo["numeroRegistro"])
    nome = alvo["nome"]
    partes = nome.split()
    esperado = sum(1 for i in itens if digitos(i.get("numeroRegistro")) == cpf)
    casos = {
        "cpf_formatado": {"cpf": f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"},
        "cpf_digitos": {"cpf": cpf},
        "cpf_mascarado_qsa": {"cpf": f"***{cpf[3:9]}**"},
        "cpf_mascarado_formatado": {"cpf": f"***.{cpf[3:6]}.{cpf[6:9]}-**"},
        "cpf_meio_6": {"cpf": cpf[3:9]},
        "nome_completo": {"parteNome": nome},
        "nome_minusculo": {"parteNome": nome.lower()},
        "nome_primeiro_e_ultimo": {"parteNome": f"{partes[0]} {partes[-1]}"},
        "nome_sobrenome_do_meio": {"parteNome": partes[1]},
    }
    resultado = {"registros_esperados_para_o_cpf": esperado, "casos": {}}
    with cliente() as c:
        for rotulo, corpo in casos.items():
            esperar()
            r = c.post(f"{BASE}/responsaveis-contas-irregulares", json=corpo)
            try:
                dados = r.json()
                n = len(dados) if isinstance(dados, list) else None
                mesmo_cpf = (
                    sum(1 for d in dados if digitos(d.get("numeroRegistro")) == cpf)
                    if isinstance(dados, list)
                    else None
                )
            except ValueError:
                n, mesmo_cpf = None, None
            resultado["casos"][rotulo] = {
                "status": r.status_code,
                "itens": n,
                "itens_do_cpf_alvo": mesmo_cpf,
                "segundos": round(r.elapsed.total_seconds(), 2),
                "erro": None if r.status_code == 200 else r.text[:200],
            }
            print(rotulo, resultado["casos"][rotulo])
    (PASTA / "teste_filtros_tcu.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
