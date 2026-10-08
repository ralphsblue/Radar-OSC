"""Extrai das respostas salvas os fatos que as regras usam, num formato interno único.

Usado por montar_casos.py e também como script para inspeção:
    .venv/Scripts/python fase0/casos/fatos.py [cnpj ...]
"""

from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from datetime import date
from functools import cache, lru_cache

from comum import RAIZ, RESPOSTAS, ler

# Mapeamento texto do OpenCNPJ -> código da tabela de natureza jurídica (D17).
# Só as naturezas que aparecem nos casos; desconhecida = None (vira ALERTA, nunca NÃO ELEGÍVEL).
NATUREZA_TEXTO_CODIGO = {
    "associação privada": 3999,
    "fundação privada": 3069,
    "organização religiosa": 3220,
    "cooperativa": 2143,
    "organização social (os)": 3301,
    "sociedade de economia mista": 2038,
    "sociedade empresária limitada": 2062,
    "serviço social autônomo": 3077,
    "estabelecimento, no brasil, de fundação ou associação estrangeiras": 3204,
}
SITUACAO_TEXTO_CODIGO = {"nula": 1, "ativa": 2, "suspensa": 3, "inapta": 4, "baixada": 8}


def _data(s: str | None) -> date | None:
    if not s:
        return None
    s = s[:10]
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return date.fromisoformat(s)
        if re.fullmatch(r"\d{2}/\d{2}/\d{4}", s):
            return date(int(s[6:]), int(s[3:5]), int(s[:2]))
    except ValueError:
        pass
    return None


def _sem_acento(s: str) -> str:
    return (
        "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").upper().strip()
    )


def cadastro(cnpj: str) -> dict | None:
    """Modelo interno da verificação 2 a 5 e 10 a partir do OpenCNPJ.

    Devolve {"http": status, ...}. Para 404 devolve só o status.
    """
    reg = ler(RESPOSTAS / cnpj / "opencnpj.json")
    if reg is None:
        return None
    status = reg["meta"]["status"]
    if status != 200:
        return {"http": status}
    c = reg["corpo"]
    nat_txt = c.get("natureza_juridica", "")
    return {
        "http": 200,
        "cnpj": c["cnpj"],
        "razao_social": c.get("razao_social"),
        "situacao_texto": c.get("situacao_cadastral"),
        "situacao": SITUACAO_TEXTO_CODIGO.get(str(c.get("situacao_cadastral", "")).lower()),
        "data_situacao": c.get("data_situacao_cadastral") or None,
        "motivo": (c.get("motivo_situacao_cadastral") or {}).get("descricao")
        if isinstance(c.get("motivo_situacao_cadastral"), dict)
        else c.get("motivo_situacao_cadastral"),
        "matriz": c.get("matriz_filial") == "Matriz",
        "natureza_texto": nat_txt,
        "natureza": NATUREZA_TEXTO_CODIGO.get(nat_txt.lower()),
        "cnae_principal": c.get("cnae_principal"),
        "cnaes_secundarios": [s for s in (c.get("cnaes_secundarios") or []) if s and s.strip("0")],
        "inicio": c.get("data_inicio_atividade"),
        "qsa": [
            {
                "nome": q.get("nome_socio"),
                "doc": q.get("cnpj_cpf_socio"),
                "tipo": q.get("identificador_socio"),
                "qualificacao": q.get("qualificacao_socio"),
            }
            for q in (c.get("QSA") or [])
        ],
    }


def sancoes_opencnpj(cnpj: str) -> dict | None:
    reg = ler(RESPOSTAS / cnpj / "opencnpj_datasets.json")
    if reg is None or reg["meta"]["status"] != 200:
        return None
    return reg["corpo"]


def tcu(cnpj: str) -> dict | None:
    reg = ler(RESPOSTAS / cnpj / "tcu.json")
    if reg is None or reg["meta"]["status"] != 200 or not isinstance(reg["corpo"], dict):
        return None
    c = reg["corpo"]
    return {
        "encontrado": c.get("seCnpjEncontradoNaBaseTcu"),
        "razao_social": c.get("razaoSocial"),
        "certidoes": {
            x["tipo"]: {"situacao": x["situacao"], "observacao": x.get("observacao")}
            for x in c.get("certidoes", [])
        },
    }


def mapa(cnpj: str) -> dict | None:
    reg = ler(RESPOSTAS / cnpj / "mapa_busca.json")
    if reg is None or reg["meta"]["status"] != 200 or not isinstance(reg["corpo"], list):
        return None
    exatos = [i for i in reg["corpo"] if str(i.get("cd_identificador_osc", "")).zfill(14) == cnpj]
    if not exatos:
        return {"presente": False, "itens_prefixo": len(reg["corpo"])}
    item = exatos[0]
    preenchido = _perfil_preenchido(cnpj)
    return {
        "presente": True,
        "id_osc": item["id_osc"],
        "cd_situacao_cadastral": item.get("cd_situacao_cadastral"),
        "perfil": "preenchido_pela_osc" if preenchido else "so_dados_automaticos",
        "campos_autodeclarados": preenchido,
    }


def _perfil_preenchido(cnpj: str) -> list[str]:
    """Regra da ficha do Mapa: valor não vazio com ft_* == 'Representante de OSC'."""
    campos: list[str] = []
    for secao in ("mapa_dados_gerais", "mapa_descricao"):
        reg = ler(RESPOSTAS / cnpj / f"{secao}.json")
        if not reg or not isinstance(reg["corpo"], dict):
            continue
        corpo = reg["corpo"]
        for chave, valor in corpo.items():
            if chave.startswith("ft_") or valor in (None, "", [], {}):
                continue
            if secao == "mapa_descricao" and chave.startswith("tx_"):
                campos.append(chave)  # seção só existe por autodeclaração (ficha do Mapa)
                continue
            fonte = corpo.get(
                "ft_" + chave.removeprefix("tx_").removeprefix("dt_").removeprefix("nr_").removeprefix("cd_")
            ) or corpo.get("ft_" + chave)
            if fonte == "Representante de OSC":
                campos.append(chave)
    return sorted(set(campos))


# ---------------------------------------------------------------- CEBAS (D16)


@lru_cache(maxsize=1)
def _siscebas() -> dict[str, dict]:
    import xlrd

    arq = (
        RAIZ
        / "fase0"
        / "cebas_dou"
        / "downloads"
        / "bases_abertas"
        / "siscebas_saude_20260930_ListaEntidadeSituacaoAtual.xls"
    )
    planilha = xlrd.open_workbook(arq, ignore_workbook_corruption=True).sheet_by_index(0)
    cab = [_sem_acento(str(h)) for h in planilha.row_values(0)]
    linhas: dict[str, dict] = {}
    for i in range(1, planilha.nrows):
        d = dict(zip(cab, planilha.row_values(i)))
        linhas[re.sub(r"\D", "", str(d["CNPJ REQUERENTE"]))] = d
    return linhas


@lru_cache(maxsize=1)
def _dou() -> dict[str, list[dict]]:
    por_cnpj: dict[str, list[dict]] = {}
    for mes in ("06", "07", "08"):
        arq = RAIZ / "fase0" / "cebas_dou" / f"cebas_S01{mes}2026.csv"
        for linha in csv.DictReader(arq.open(encoding="utf-8-sig"), delimiter=";"):
            por_cnpj.setdefault(linha.get("cnpj", ""), []).append(linha)
    return por_cnpj


def _xlsx_cnpjs(nome: str) -> dict[str, list[str]]:
    """CNPJs presentes numa planilha do Mapa (MEC/MDS), com a linha como texto."""
    import zipfile
    from xml.etree import ElementTree as ET

    arq = RAIZ / "fase0" / "mapa_osc" / "respostas" / "downloads" / nome
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(arq) as z:
        compartilhadas = []
        if "xl/sharedStrings.xml" in z.namelist():
            raiz = ET.fromstring(z.read("xl/sharedStrings.xml"))
            compartilhadas = [
                "".join(t.text or "" for t in si.iter(f"{{{ns['m']}}}t")) for si in raiz.findall("m:si", ns)
            ]
        resultado: dict[str, list[str]] = {}
        for folha in [n for n in z.namelist() if n.startswith("xl/worksheets/sheet")]:
            raiz = ET.fromstring(z.read(folha))
            for row in raiz.iter(f"{{{ns['m']}}}row"):
                valores = []
                for c in row.findall("m:c", ns):
                    v = c.find("m:v", ns)
                    if v is None:
                        continue
                    valores.append(compartilhadas[int(v.text)] if c.get("t") == "s" else v.text)
                texto = " | ".join(str(x) for x in valores)
                for m in re.findall(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}|\b\d{13,14}\b", texto):
                    resultado.setdefault(re.sub(r"\D", "", m).zfill(14), []).append(f"{folha}: {texto[:300]}")
    return resultado


@lru_cache(maxsize=1)
def _planilhas_mapa() -> dict[str, dict[str, list[str]]]:
    return {"MEC": _xlsx_cnpjs("8420-cebaseducacao.xlsx"), "MDS": _xlsx_cnpjs("7684-cebassuas.xlsx")}


def cebas(cnpj: str) -> dict:
    s = _siscebas().get(cnpj)
    sis = None
    if s:
        sis = {
            k: s.get(k)
            for k in (
                "NOME",
                "ASSUNTO",
                "TIPO DE DECISAO",
                "NUMERO DA PORTARIA",
                "DATA DA PUBLICACAO",
                "DATA DE INICIO DA VIGENCIA",
                "DATA FINAL DA VIGENCIA",
                "CEBAS",
                "SITUACAO ATUAL",
                "DATA ATUALIZACAO",
            )
        }
    planilhas = {area: linhas.get(cnpj, []) for area, linhas in _planilhas_mapa().items()}
    dou = [
        {
            k: d.get(k)
            for k in ("tipo_ato", "deferido", "area", "data_publicacao", "identificacao_ato", "validade")
        }
        for d in _dou().get(cnpj, [])
    ]
    return {
        "siscebas_saude": sis,
        "planilhas_mapa": {k: v for k, v in planilhas.items() if v},
        "dou_jun_ago_2026": dou,
    }


# ------------------------------------------------------ dirigentes (D15)


@lru_cache(maxsize=1)
def _pessoas_sancionadas() -> dict[str, list[dict]]:
    """Nome normalizado -> registros de PF do CEIS e do CNEP (CPF completo)."""
    por_nome: dict[str, list[dict]] = {}
    for cad in ("20260930_CEIS.csv", "20260930_CNEP.csv"):
        arq = RAIZ / "fase0" / "portal" / "downloads" / cad
        linhas = csv.reader(arq.open(encoding="latin1"), delimiter=";")
        cab = next(linhas)
        i_tipo, i_doc, i_nome = (
            cab.index("TIPO DE PESSOA"),
            cab.index("CPF OU CNPJ DO SANCIONADO"),
            cab.index("NOME DO SANCIONADO"),
        )
        i_ini, i_fim = cab.index("DATA INÍCIO SANÇÃO"), cab.index("DATA FINAL SANÇÃO")
        i_cat, i_proc = cab.index("CATEGORIA DA SANÇÃO"), cab.index("NÚMERO DO PROCESSO")
        for x in linhas:
            if x[i_tipo] != "F":
                continue
            por_nome.setdefault(_sem_acento(x[i_nome]), []).append(
                {
                    "cadastro": cad[9:13],
                    "cpf_meio": x[i_doc][3:9],
                    "inicio": x[i_ini],
                    "fim": x[i_fim],
                    "categoria": x[i_cat],
                    "processo": x[i_proc],
                }
            )
    return por_nome


# ------------------------------------------- bases locais de sanção (D14, Q34, Q21)

# Data de cada base local, para a regra de idade máxima (Q6).
DATA_BASE = {
    "CEIS": date(2026, 9, 30),
    "CNEP": date(2026, 9, 30),
    "CEPIM": date(2026, 9, 28),
    "INIDONEOS_TCU": date(2026, 9, 30),
    "CONTAS_IRREGULARES_TCU": date(2026, 10, 1),
    "SISCEBAS_SAUDE": date(2026, 9, 30),
    "DOU": date(2026, 8, 31),
}
_CSV_CGU = {"CEIS": "20260930_CEIS.csv", "CNEP": "20260930_CNEP.csv", "CEPIM": "20260928_CEPIM.csv"}


def _so_digitos(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")


@cache
def sancoes_csv(cadastro: str) -> dict[str, list[dict]]:
    """CSV diário oficial da CGU (observação principal, D14): raiz -> registros de PJ.

    Os campos usam os mesmos nomes do `?datasets=` do OpenCNPJ, para as duas
    observações poderem ser combinadas pelo código da sanção.
    """
    arq = RAIZ / "fase0" / "portal" / "downloads" / _CSV_CGU[cadastro]
    linhas = csv.reader(arq.open(encoding="latin1"), delimiter=";")
    cab = next(linhas)
    por_raiz: dict[str, list[dict]] = {}
    if cadastro == "CEPIM":
        for x in linhas:
            doc = _so_digitos(x[0])
            if len(doc) == 14:
                por_raiz.setdefault(doc[:8], []).append(
                    {
                        "cnpj_registro": doc,
                        "nome_entidade": x[1],
                        "numero_convenio": x[2],
                        "orgao_concedente": x[3],
                        "motivo": x[4],
                        "fontes": ["csv"],
                    }
                )
        return por_raiz
    i = {n: cab.index(n) for n in cab}
    for x in linhas:
        doc = _so_digitos(x[i["CPF OU CNPJ DO SANCIONADO"]])
        if len(doc) != 14 or x[i["TIPO DE PESSOA"]] == "F":
            continue
        por_raiz.setdefault(doc[:8], []).append(
            {
                "cnpj_registro": doc,
                "codigo": x[i["CÓDIGO DA SANÇÃO"]],
                "categoria": x[i["CATEGORIA DA SANÇÃO"]],
                "data_inicio": x[i["DATA INÍCIO SANÇÃO"]],
                "data_final": x[i["DATA FINAL SANÇÃO"]],
                "orgao_sancionador": x[i["ÓRGÃO SANCIONADOR"]],
                "esfera_orgao_sancionador": x[i["ESFERA ÓRGÃO SANCIONADOR"]],
                "abrangencia": x[i["ABRAGÊNCIA DA SANÇÃO"]],
                "numero_processo": x[i["NÚMERO DO PROCESSO"]],
                "origem_informacoes": x[i["ORIGEM INFORMAÇÕES"]],
                "valor_multa": x[i["VALOR DA MULTA"]] if "VALOR DA MULTA" in i else None,
                "fontes": ["csv"],
            }
        )
    return por_raiz


def _csv_tcu(arq) -> list[dict]:
    texto = arq.read_text(encoding="cp1252").splitlines()
    if texto and texto[0].startswith("sep="):
        texto = texto[1:]
    cab = [c.strip() for c in texto[0].split("|")]
    return [
        dict(zip(cab, (v.strip().strip("'") for v in linha.split("|"))))
        for linha in texto[1:]
        if linha.strip()
    ]


@lru_cache(maxsize=1)
def inidoneos_csv() -> dict[str, list[dict]]:
    """Plataforma de Certidões do TCU, lista de inidôneos (Q34): raiz -> registros de PJ."""
    por_raiz: dict[str, list[dict]] = {}
    for r in _csv_tcu(RAIZ / "fase0" / "tcu" / "respostas" / "inidoneos_lista_completa.csv"):
        doc = _so_digitos(r.get("CPF/CNPJ"))
        if len(doc) == 14:
            por_raiz.setdefault(doc[:8], []).append(
                {
                    "cnpj_registro": doc,
                    "nome": r.get("Nome"),
                    "processo": r.get("Processo"),
                    "acordao": r.get("Acórdão"),
                    "data_acordao": r.get("Data do acórdão"),
                    "transito": r.get("Trânsito em julgado"),
                    "data_final": r.get("Data final da sanção"),
                }
            )
    return por_raiz


@lru_cache(maxsize=1)
def contas_irregulares_csv() -> dict[str, list[dict]]:
    """Lista de responsáveis com contas julgadas irregulares do TCU (Q21): raiz -> registros de PJ."""
    por_raiz: dict[str, list[dict]] = {}
    for r in _csv_tcu(
        RAIZ / "fase0" / "dirigentes" / "downloads" / "tcu_responsaveis-contas-irregulares.csv"
    ):
        doc = _so_digitos(r.get("CPF/CNPJ"))
        if len(doc) == 14:
            por_raiz.setdefault(doc[:8], []).append(
                {
                    "cnpj_registro": doc,
                    "nome": r.get("Nome"),
                    "processo": r.get("Processo"),
                    "transito": r.get("Trânsito em julgado"),
                }
            )
    return por_raiz


def dirigentes(qsa: list[dict]) -> dict:
    fortes, so_nome = [], []
    for q in qsa:
        if q.get("tipo") != "Pessoa Física" or not q.get("nome"):
            continue
        meio = _so_digitos(q.get("doc"))
        for r in _pessoas_sancionadas().get(_sem_acento(q["nome"]), []):
            alvo = {"nome": q["nome"], "qualificacao": q.get("qualificacao"), **r}
            (fortes if meio and meio == r["cpf_meio"] else so_nome).append(alvo)
    return {
        "pf_no_qsa": sum(1 for q in qsa if q.get("tipo") == "Pessoa Física"),
        "fortes": fortes,
        "so_nome": so_nome,
    }


def tudo(cnpj: str) -> dict:
    cad = cadastro(cnpj)
    return {
        "cadastro": cad,
        "sancoes_opencnpj": sancoes_opencnpj(cnpj),
        "tcu": tcu(cnpj),
        "mapa": mapa(cnpj),
        "cebas": cebas(cnpj) if cnpj.isdigit() else None,
        "dirigentes": dirigentes(cad["qsa"]) if cad and cad.get("http") == 200 else None,
    }


if __name__ == "__main__":
    from casos_def import CASOS

    alvos = sys.argv[1:] or [c["cnpj"] for c in CASOS]
    for alvo in alvos:
        print("=" * 20, alvo)
        f = tudo(alvo)
        if f["cadastro"] and f["cadastro"].get("qsa"):
            f["cadastro"]["qsa"] = f"{len(f['cadastro']['qsa'])} pessoas"
        print(json.dumps(f, ensure_ascii=False, indent=1, default=str)[:4000])
