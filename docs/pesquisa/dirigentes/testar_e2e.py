"""Teste ponta a ponta do casamento de dirigentes (casar_dirigentes.py) com QSA real.

Dois grupos de OSCs:
1. Positivos prováveis: OSCs (nome típico de associação/instituto/fundação) que aparecem como
   PJ na lista de contas irregulares do TCU com trânsito nos últimos 8 anos e cujo processo também
   lista ao menos uma pessoa física. O QSA vem da OpenCNPJ (mesma fonte do MVP), e o esperado
   é que algum dirigente atual seja um dos responsáveis PF daquele processo.
2. Controle: os CNPJs de fase0/casos (QSA já salvo), quase todos sem sanção conhecida.

Não grava nomes nem CPFs em arquivos versionáveis: o resumo usa só contagens, fonte,
critério, qualificação e se o processo do achado é o mesmo em que a OSC foi condenada.
QSA bruto vai para downloads/qsa/ (fora do versionamento).

Uso: .venv/Scripts/python fase0/dirigentes/testar_e2e.py [max_osc=25]
"""

from __future__ import annotations

import collections
import json
import sys
from datetime import date

from casar_dirigentes import carregar_indice, casar
from comum import DOWNLOADS, PASTA, RAIZ, cliente, data_br, digitos, esperar

PALAVRAS_OSC = (
    "ASSOC",
    "INSTITUTO",
    "FUNDACAO",
    "FUNDAÇÃO",
    "SOCIEDADE",
    "CENTRO",
    "OSCIP",
    "ONG ",
    "MOVIMENTO",
    "CONSELHO COMUNIT",
)
NAO_OSC = (
    "LTDA",
    "EIRELI",
    " S/A",
    " S.A",
    "EPP",
    " ME",
    "PREFEITURA",
    "MUNICIPIO",
    "CAMARA",
    "CONSORCIO",
    "COOPERATIVA",
)


def candidatos(maximo: int) -> list[tuple[str, set[str]]]:
    itens = json.loads((DOWNLOADS / "tcu_responsaveis-contas-irregulares.json").read_text(encoding="utf-8"))
    corte = date(2018, 10, 1)
    pf_por_proc = collections.defaultdict(set)
    for i in itens:
        if i.get("tipoRegistro") == "CPF":
            pf_por_proc[i.get("numeroProcessoFormatado")].add(digitos(i.get("numeroRegistro")))
    vistos: dict[str, set[str]] = {}
    for i in sorted(
        itens,
        key=lambda i: data_br(i["dataTransitoEmJulgado"]),
        reverse=True,
    ):
        if i.get("tipoRegistro") != "CNPJ":
            continue
        nome = (i.get("nome") or "").upper()
        if not any(p in nome for p in PALAVRAS_OSC) or any(p in nome for p in NAO_OSC):
            continue
        if data_br(i["dataTransitoEmJulgado"]) < corte:
            continue
        proc = i.get("numeroProcessoFormatado")
        if not pf_por_proc.get(proc):
            continue
        vistos.setdefault(digitos(i["numeroRegistro"]), set()).add(proc)
        if len(vistos) >= maximo:
            break
    return list(vistos.items())


def qsa_opencnpj(c, cnpj: str) -> tuple[int, list[dict], dict]:
    destino = DOWNLOADS / "qsa" / f"opencnpj_{cnpj}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        corpo = json.loads(destino.read_text(encoding="utf-8"))
        return 200, corpo.get("QSA") or [], corpo
    esperar()
    r = c.get(f"https://api.opencnpj.org/{cnpj}")
    if r.status_code != 200:
        return r.status_code, [], {}
    destino.write_bytes(r.content)
    corpo = r.json()
    return 200, corpo.get("QSA") or [], corpo


def resumir_achados(achados, processos_osc: set[str] | None) -> list[dict]:
    out = []
    for a in achados:
        r = a.registro
        out.append(
            {
                "fonte": r.fonte,
                "hipotese": r.hipotese,
                "criterio": a.criterio,
                "vigente_ou_8_anos": r.vigente,
                "qualificacao": a.qualificacao,
                "data_entrada": a.data_entrada,
                "data_ref": r.data_ref.isoformat() if r.data_ref else None,
                "mesmo_processo_da_osc": bool(processos_osc and r.processo in processos_osc),
                "categoria": r.detalhe.get("categoria"),
            }
        )
    return out


def main() -> None:
    maximo = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    ix = carregar_indice()
    resultado: dict = {"indice": ix.contagem, "positivos_provaveis": [], "controle": []}
    with cliente() as c:
        for cnpj, procs in candidatos(maximo):
            st, qsa, corpo = qsa_opencnpj(c, cnpj)
            pf = [s for s in qsa if len(digitos(s.get("cnpj_cpf_socio"))) == 6]
            achados = casar(ix, qsa)
            resultado["positivos_provaveis"].append(
                {
                    "cnpj": cnpj,
                    "status_opencnpj": st,
                    "situacao": corpo.get("situacao_cadastral"),
                    "natureza": corpo.get("natureza_juridica"),
                    "dirigentes_pf": len(pf),
                    "achados": resumir_achados(achados, procs),
                }
            )
            print(
                cnpj,
                st,
                len(pf),
                [(a.registro.fonte, a.criterio, a.registro.processo in procs) for a in achados],
            )

    casos = RAIZ / "fase0" / "casos" / "respostas"
    for arq in sorted(casos.glob("*/opencnpj.json")):
        d = json.loads(arq.read_text(encoding="utf-8"))
        corpo = d.get("corpo", d) if isinstance(d, dict) else {}
        if not isinstance(corpo, dict):
            continue
        qsa = corpo.get("QSA") or []
        pf = [s for s in qsa if len(digitos(s.get("cnpj_cpf_socio"))) == 6]
        achados = casar(ix, qsa)
        resultado["controle"].append(
            {
                "cnpj": arq.parent.name,
                "dirigentes_pf": len(pf),
                "achados": resumir_achados(achados, None),
            }
        )
        print(
            "controle",
            arq.parent.name,
            len(pf),
            [(a.registro.fonte, a.criterio) for a in achados],
        )

    pos = resultado["positivos_provaveis"]
    resultado["sintese"] = {
        "osc_positivas_testadas": len(pos),
        "osc_com_qsa_pf": sum(p["dirigentes_pf"] > 0 for p in pos),
        "osc_com_algum_achado": sum(bool(p["achados"]) for p in pos),
        "osc_com_achado_no_mesmo_processo": sum(
            any(a["mesmo_processo_da_osc"] for a in p["achados"]) for p in pos
        ),
        "achados_por_fonte": dict(collections.Counter(a["fonte"] for p in pos for a in p["achados"])),
        "achados_por_criterio": dict(collections.Counter(a["criterio"] for p in pos for a in p["achados"])),
        "controle_osc": len(resultado["controle"]),
        "controle_dirigentes_pf": sum(x["dirigentes_pf"] for x in resultado["controle"]),
        "controle_com_achado": sum(bool(x["achados"]) for x in resultado["controle"]),
    }
    (PASTA / "teste_e2e.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(resultado["sintese"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
