"""Procura entidades ATIVAS e de natureza elegível com cada tipo de restrição.

Motivo: vários casos de sanção das fichas (Paripueira, Ilumina Terra, ITS, IMDC,
Pacaembu, AVAPE, Bom Jesus) estão INAPTOS ou BAIXADOS na Receita. Pelo fluxo do
spec (2.2: situação != ATIVA -> INAPTA, fim) as verificações de sanção nem
chegariam a rodar, então esses casos não testam CEPIM/CEIS/CNEP/TCU/CNIA.

Para cada categoria, percorre candidatos dos arquivos oficiais e consulta só o
OpenCNPJ cadastral (barato) até achar `ALVO` entidades Ativas com natureza 3999,
3069 ou 3220. Para o CNIA, as ativas encontradas são confirmadas no TCU
(limite global de consultas ao TCU, somando as de buscar_cnia.py).
Também testa o QSA de cada ativa contra PF do CEIS/CNEP (D15), para achar um
caso de dirigente.

Uso: .venv/Scripts/python fase0/casos/buscar_ativos.py
Saída: respostas/busca_ativos/opencnpj_<cnpj>.json, tcu_<cnpj>.json e _resumo.json
"""

from __future__ import annotations

import csv
import json
from datetime import date

from comum import RAIZ, RESPOSTAS, baixar, cliente_http
from fatos import NATUREZA_TEXTO_CODIGO, dirigentes

PORTAL = RAIZ / "fase0" / "portal" / "downloads"
INIDONEOS = RAIZ / "fase0" / "portal" / "tcu" / "inidoneos_completo.json"
PASTA = RESPOSTAS / "busca_ativos"
REF = date(2026, 10, 1)
ELEGIVEIS = {3999, 3069, 3220}
ALVO = 2
MAX_OPENCNPJ_POR_CATEGORIA = 40
MAX_TCU = 50  # 60 no total menos as consultas já feitas em buscar_cnia.py
OSC = (
    "ASSOC",
    "INSTITUTO",
    "FUNDA",
    "SOCIEDADE",
    "CENTRO",
    "IGREJA",
    "CLUBE",
    "ONG",
    "MOVIMENTO",
    "OBRA",
    "LAR ",
    "CASA",
    "HOSPITAL",
    "SANTA CASA",
    "IRMANDADE",
    "GRUPO",
    "UNIAO",
    "FEDERA",
    "CONSELHO",
)
NAO_OSC = ("LTDA", "EIRELI", "ADVOGADOS", "COMERCIO", "S/A", "S.A", " ME", "EPP", "ENGENHARIA", "CONSTRU")
JA_USADOS = {
    "14112015000156",
    "00688001000170",
    "06287661000126",
    "02393242000118",
    "03126200000183",
    "07408449000132",
    "09058351000128",
    "08928169000118",
    "03463763000167",
    "43337682000135",
    "53524534000183",
    "21145289000107",
    "25705450000100",
}


def _d(s: str) -> date | None:
    try:
        return date(int(s[6:10]), int(s[3:5]), int(s[:2])) if s else None
    except ValueError, IndexError:
        return None


def _parece_osc(nome: str) -> bool:
    n = nome.upper()
    return any(p in n for p in OSC) and not any(p in n for p in NAO_OSC)


def _ler(cad: str) -> list[dict]:
    arq = next(PORTAL.glob(f"*_{cad}.csv"))
    return list(csv.DictReader(arq.open(encoding="latin1"), delimiter=";"))


def candidatos() -> dict[str, list[str]]:
    ceis, cnep, cepim = _ler("CEIS"), _ler("CNEP"), _ler("CEPIM")
    pj = lambda linhas: [
        x for x in linhas if x["TIPO DE PESSOA"] == "J" and _parece_osc(x["NOME DO SANCIONADO"])
    ]
    ceis_pj, cnep_pj = pj(ceis), pj(cnep)
    cnpjs_ceis = {x["CPF OU CNPJ DO SANCIONADO"] for x in ceis}
    cnpjs_cnep = {x["CPF OU CNPJ DO SANCIONADO"] for x in cnep}
    cnpjs_cepim = {x["CNPJ ENTIDADE"] for x in cepim}

    def uniq(seq):
        vistos = []
        for c in seq:
            if c not in vistos and c not in JA_USADOS:
                vistos.append(c)
        return vistos

    inid = json.loads(INIDONEOS.read_text(encoding="utf-8"))
    return {
        "cepim": uniq(
            x["CNPJ ENTIDADE"]
            for x in cepim
            if _parece_osc(x["NOME ENTIDADE"]) and x["CNPJ ENTIDADE"] not in cnpjs_ceis | cnpjs_cnep
        ),
        "ceis_fim_futuro": uniq(
            x["CPF OU CNPJ DO SANCIONADO"]
            for x in ceis_pj
            if (_d(x["DATA FINAL SANÇÃO"]) or date.min) > REF
            and x["CPF OU CNPJ DO SANCIONADO"] not in cnpjs_cnep | cnpjs_cepim
        ),
        "cnep": uniq(
            x["CPF OU CNPJ DO SANCIONADO"]
            for x in cnep_pj
            if x["CPF OU CNPJ DO SANCIONADO"] not in cnpjs_ceis | cnpjs_cepim
        ),
        "tcu_inidoneo": uniq(
            "".join(ch for ch in i["cpf_cnpj"] if ch.isdigit())
            for i in inid
            if len("".join(ch for ch in i["cpf_cnpj"] if ch.isdigit())) == 14 and _parece_osc(i["nome"])
        ),
        "cnia": uniq(x["CPF OU CNPJ DO SANCIONADO"] for x in ceis_pj if "CNJ" in x["ORIGEM INFORMAÇÕES"]),
    }


def main() -> None:
    resumo: dict = {}
    tcu_feitas = 0
    with cliente_http() as cliente:
        for categoria, lista in candidatos().items():
            achados, consultados = [], 0
            for cnpj in lista:
                if len(achados) >= ALVO or consultados >= MAX_OPENCNPJ_POR_CATEGORIA:
                    break
                consultados += 1
                reg = baixar(cliente, f"https://api.opencnpj.org/{cnpj}", PASTA / f"opencnpj_{cnpj}.json")
                c = reg["corpo"] if reg["meta"]["status"] == 200 else None
                if not c or c.get("situacao_cadastral") != "Ativa":
                    continue
                if NATUREZA_TEXTO_CODIGO.get(c.get("natureza_juridica", "").lower()) not in ELEGIVEIS:
                    continue
                qsa = [
                    {
                        "nome": q.get("nome_socio"),
                        "doc": q.get("cnpj_cpf_socio"),
                        "tipo": q.get("identificador_socio"),
                        "qualificacao": q.get("qualificacao_socio"),
                    }
                    for q in c.get("QSA") or []
                ]
                item = {
                    "cnpj": cnpj,
                    "razao_social": c["razao_social"],
                    "matriz_filial": c.get("matriz_filial"),
                    "inicio": c.get("data_inicio_atividade"),
                    "dirigentes": dirigentes(qsa),
                }
                if categoria == "cnia":
                    if tcu_feitas >= MAX_TCU:
                        break
                    tcu_feitas += 1
                    t = baixar(
                        cliente,
                        f"https://certidoes-apf.apps.tcu.gov.br/api/rest/publico/certidoes/{cnpj}?seEmitirPDF=false",
                        PASTA / f"tcu_{cnpj}.json",
                    )
                    sit = (
                        {x["tipo"]: x["situacao"] for x in (t["corpo"] or {}).get("certidoes", [])}
                        if isinstance(t["corpo"], dict)
                        else {}
                    )
                    item["tcu"] = sit
                    if sit.get("CNIA") != "CONSTAM_REGISTROS":
                        continue
                achados.append(item)
                print(f"  ACHADO {categoria}: {cnpj} {c['razao_social']}")
            resumo[categoria] = {"consultados_opencnpj": consultados, "achados": achados}
    resumo["tcu_consultas"] = tcu_feitas
    (PASTA / "_resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        json.dumps(
            {
                k: (v if k == "tcu_consultas" else [a["cnpj"] for a in v["achados"]])
                for k, v in resumo.items()
            },
            indent=1,
        )
    )


if __name__ == "__main__":
    main()
