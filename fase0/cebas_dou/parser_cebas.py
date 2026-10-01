"""Extrai decisoes de CEBAS do XML mensal do DOU (Secao 1).

Uso:
    python parser_cebas.py downloads/S01082026.zip [saida.csv]

Unidades usadas:
- materia: um arquivo XML do ZIP (<article>), identificado por idMateria.
  Uma materia pode conter varios atos (ex.: o MDS publica 5 portarias numa
  so materia) e um ato pode ter partes em arquivos "-1", "-2"...
- ato: trecho da materia iniciado por <p class="identifica"> (portaria,
  despacho, decisao).
- decisao: uma linha por entidade decidida.
  Uma portaria do MDS lista centenas de entidades em itens "N) NOME, CNPJ...".

Regras de classificacao (tipo_ato segue o modelo 22.6 do spec):
CONCESSAO | RENOVACAO | INDEFERIMENTO | CANCELAMENTO | RECONSIDERACAO | OUTRO
O campo "detalhe" guarda nuances (recurso negado, sub judice, judicial...).
"""

from __future__ import annotations

import csv
import re
import sys
import unicodedata
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterator

from lxml import etree, html

# ---------------------------------------------------------------- filtros

# \b evita casar "DCEBAS" (sigla do departamento citada em atos de outros programas, ex.: PROSUS).
# \s* porque textos antigos (2016) vem com palavras coladas ("EntidadeBeneficente").
TERMO_CEBAS = re.compile(r"\bCEBAS\b|Entidades?\s*Beneficentes?", re.I)
# Despachos do MDS que abrem consulta publica sobre processos de certificacao
# citam so a lei (12.101/2009 ou LC 187/2021), sem a palavra CEBAS.
TERMO_LEI = re.compile(r"Lei\s+n[ºo°]\s*12\.101|Complementar\s+n[ºo°]\s*187", re.I)

ORGAOS = {
    "Ministério da Saúde": "SAUDE",
    "Ministério da Educação": "EDUCACAO",
    "Ministério do Desenvolvimento e Assistência Social": "ASSISTENCIA",
}

# ---------------------------------------------------------------- CNPJ

_C = r"[0-9A-Z]"  # CNPJ alfanumerico (IN RFB 2.229/2024): 12 primeiras posicoes podem ter letras
_S = r"\s?"
CNPJ_FORMATADO = re.compile(
    rf"(?<![0-9A-Za-z])({_C}{{2}}){_S}\.{_S}({_C}{{3}}){_S}\.{_S}({_C}{{3}}){_S}/{_S}({_C}{{4}}){_S}[-–]{_S}(\d{{2}})(?!\d)"
)
CNPJ_MEIO_FORMATADO = re.compile(r"(?<!\d)(\d{8})/(\d{4})-(\d{2})(?!\d)")
CNPJ_CRU = re.compile(r"CNPJ[^0-9]{0,25}(?<!\d)(\d{14})(?!\d)", re.I)


def dv_cnpj_ok(cnpj: str) -> bool:
    if len(cnpj) != 14 or not cnpj[12:].isdigit() or len(set(cnpj)) == 1:
        return False
    vals = [ord(c) - 48 for c in cnpj]
    for pos in (12, 13):
        pesos = list(range(pos - 7, 1, -1)) + list(range(9, 1, -1))
        soma = sum(v * p for v, p in zip(vals[:pos], pesos))
        dv = 0 if soma % 11 < 2 else 11 - soma % 11
        if vals[pos] != dv:
            return False
    return True


def achar_cnpjs(texto: str) -> list[tuple[str, int, int]]:
    """Retorna (cnpj14, inicio, fim) sem repeticao, na ordem do texto."""
    achados: list[tuple[str, int, int]] = []
    for rx in (CNPJ_FORMATADO, CNPJ_MEIO_FORMATADO, CNPJ_CRU):
        for m in rx.finditer(texto):
            cnpj = "".join(g for g in m.groups() if g).upper()
            ini = m.start(1) if rx is CNPJ_CRU else m.start()
            if any(ini < f and m.end() > i for _, i, f in achados):
                continue
            achados.append((cnpj, ini, m.end()))
    achados.sort(key=lambda a: a[1])
    return achados


# ---------------------------------------------------------------- texto


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def limpar(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


@dataclass
class Paragrafo:
    texto: str
    classe: str = ""


def paragrafos(texto_html: str) -> list[Paragrafo]:
    if not texto_html.strip():
        return []
    raiz = html.fragment_fromstring(texto_html, create_parent="div")
    saida: list[Paragrafo] = []
    for el in raiz:
        if el.tag == "table":
            for tr in el.iter("tr"):
                celulas = [limpar(td.text_content()) for td in tr if td.tag in ("td", "th")]
                linha = " | ".join(c for c in celulas if c)
                if linha:
                    saida.append(Paragrafo(linha, "tabela"))
        else:
            t = limpar(el.text_content())
            if t:
                saida.append(Paragrafo(t, el.get("class") or ""))
    return saida


# ---------------------------------------------------------------- modelo


@dataclass
class Materia:
    arquivo: str
    id_materia: str
    pub_date: str
    pub_name: str
    edicao: str
    pagina: str
    categoria: str
    art_type: str
    identifica: str
    url_pdf: str
    texto_html: str


@dataclass
class Decisao:
    ref_ato: str = ""
    id_materia: str = ""
    arquivo: str = ""
    data_publicacao: str = ""
    data_ato: str = ""
    identificacao_ato: str = ""
    orgao: str = ""
    area: str = ""
    cnpj: str = ""
    cnpj_dv_ok: str = ""
    entidade: str = ""
    municipio_uf: str = ""
    tipo_ato: str = ""
    deferido: str = ""  # "S", "N" ou "" (nao se aplica / indefinido)
    detalhe: str = ""
    validade: str = ""
    edicao: str = ""
    pagina: str = ""
    url_pdf: str = ""
    fonte: str = "DOU_XML"
    trecho: str = field(default="")


# ---------------------------------------------------------------- leitura


def ler_zip(caminho: Path) -> Iterator[Materia]:
    with zipfile.ZipFile(caminho) as z:
        for nome in sorted(z.namelist()):
            if not nome.endswith(".xml"):
                continue
            raiz = etree.fromstring(z.read(nome))
            for a in raiz.iter("article"):
                yield Materia(
                    arquivo=nome,
                    id_materia=a.get("idMateria") or "",
                    pub_date=a.get("pubDate") or "",
                    pub_name=a.get("pubName") or "",
                    edicao=a.get("editionNumber") or "",
                    pagina=a.get("numberPage") or "",
                    categoria=a.get("artCategory") or "",
                    art_type=a.get("artType") or "",
                    identifica=limpar(a.findtext("body/Identifica") or ""),
                    url_pdf=a.get("pdfPage") or "",
                    texto_html=a.findtext("body/Texto") or "",
                )


def area_do_orgao(categoria: str) -> str:
    for prefixo, area in ORGAOS.items():
        if categoria.startswith(prefixo):
            return area
    return "OUTRA"


def materia_relevante(m: Materia) -> bool:
    if TERMO_CEBAS.search(m.texto_html):
        return True
    return area_do_orgao(m.categoria) != "OUTRA" and bool(TERMO_LEI.search(m.texto_html)) and bool(
        achar_cnpjs(m.texto_html)
    )


def dividir_atos(m: Materia, pars: list[Paragrafo]) -> list[tuple[str, list[Paragrafo]]]:
    atos: list[tuple[str, list[Paragrafo]]] = []
    atual: list[Paragrafo] = []
    titulo = m.identifica
    for p in pars:
        if p.classe == "identifica" or (len(p.texto) < 120 and TITULO_ATO.match(p.texto)):
            if atual:
                atos.append((titulo, atual))
            titulo, atual = p.texto, [p]
        else:
            atual.append(p)
    if atual:
        atos.append((titulo, atual))
    return atos


# ---------------------------------------------------------------- classificacao

MESES = {m: i for i, m in enumerate(
    "janeiro fevereiro marco abril maio junho julho agosto setembro outubro novembro dezembro".split(), 1)}


def data_do_titulo(titulo: str) -> str:
    m = re.search(r"DE\s+(\d{1,2})º?\s+DE\s+([A-Za-zçÇ]+)\s+DE\s+(\d{4})", titulo, re.I)
    if not m:
        return ""
    mes = MESES.get(sem_acento(m.group(2)))
    return f"{m.group(3)}-{mes:02d}-{int(m.group(1)):02d}" if mes else ""


def classificar(decisivo: str, contexto: str = "") -> tuple[str, str, str]:
    """Retorna (tipo_ato, deferido, detalhe) a partir do texto decisorio."""
    d = sem_acento(decisivo)
    c = sem_acento(contexto)
    detalhes = []
    if "sub judice" in d or "decisao judicial" in d or "liminar" in d:
        detalhes.append("judicial")
    objeto = "renovacao" if "renova" in d else ("concessao" if "concess" in d or "conced" in d else "")

    if re.search(r"\bneg(o|ar|ado)(-lhe)? provimento|\bnego-lhe provimento", d):
        base = "CANCELAMENTO" if "cancel" in c or "cancelamento" in d else "INDEFERIMENTO"
        return base, "N", "recurso negado"
    if re.search(r"\bdou provimento|\bdar provimento|\bdado provimento|\bdou-lhe provimento", d):
        return "RECONSIDERACAO", "S", "recurso provido"
    if "prazo" in d and "sanar" in d:
        return "OUTRO", "", "prazo para sanar pendencias (recurso em andamento)"
    if "manifestacao da sociedade civil" in d:
        return "OUTRO", "", "consulta publica do processo"
    if re.search(r"\barquiv(ar|ad[oa]s?|amento)\b", d):
        return "OUTRO", "", "; ".join(["arquivamento", objeto]).strip("; ")
    if re.search(r"abrir prazo", d) and re.search(r"apresentar os documentos|supervis", d + " " + c):
        return "OUTRO", "", "supervisao: prazo para apresentar documentos"
    if re.search(r"\bprorrog", d) and "vigencia" in d:
        # LC 187/2021 art. 40 par. 1o: prorrogacao em lote da vigencia (ex.: Portaria SAES 179/2023)
        return "OUTRO", "S", "prorrogacao de vigencia"
    if "reconsidera" in d:
        nega = re.search(r"\bnao se reconsidera|\bnao reconsidera|\bindefer\w*,? em grau de reconsidera"
                         r"|\bmantid[oa] o indeferimento|\bindefer\w* o pedido de reconsidera", d)
        return "RECONSIDERACAO", "N" if nega else "S", "; ".join([objeto] + detalhes).strip("; ")
    m = re.search(r"determino a (renovacao|concessao)", d)
    if m:
        return ("RENOVACAO" if m.group(1) == "renovacao" else "CONCESSAO"), "S", "; ".join(detalhes)
    if re.search(r"\bcancel", d):
        return "CANCELAMENTO", "N", "; ".join(detalhes)
    if re.search(r"\bindefer", d):
        return "INDEFERIMENTO", "N", "; ".join([objeto] + detalhes).strip("; ")
    if re.search(r"\bdefer|\bdetermino a renova|\bconced", d):
        if objeto == "renovacao":
            return "RENOVACAO", "S", "; ".join(detalhes)
        if objeto == "concessao":
            return "CONCESSAO", "S", "; ".join(detalhes)
    return "OUTRO", "", "; ".join(detalhes)


# ---------------------------------------------------------------- extracao de campos

# Titulo de ato sem class="identifica" (ex.: 4a portaria da materia do MDS)
TITULO_ATO = re.compile(
    r"^(PORTARIA|DESPACHO|DECIS[ÃA]O|RESOLU[ÇC][ÃA]O)\b[^.]{0,60}\bDE\s+\d{1,2}º?\s+DE\s+\w+\s+DE\s+\d{4}\s*$", re.I
)
ITEM_LISTA = re.compile(r"^\s*(\d{1,4})\s*[\)\.\-–]\s*(?=\D)")
PREPOSICOES = r"(?:da|do|de|ao|à|a|o)"
ANEXO = re.compile(r"^ANEXO\s+([IVXL]+|\d+|[ÚU]NICO)\b", re.I)
VERBO_DECISAO = re.compile(r"\b(defer|indefer|cancel|reconsider|arquiv|renova)", re.I)


def nome_em_tabela(linha: str) -> str:
    """Linha de tabela 'c1 | c2 | ...': o nome e a celula textual mais longa."""
    candidatas = [
        c for c in linha.split(" | ")
        if re.search(r"[A-Za-zÀ-ú]{3}", c) and not achar_cnpjs(c) and not re.search(r"\d{2}/\d{2}/\d{4}|\bdias\b", c)
    ]
    return max(candidatas, key=len, default="")


def nome_antes_do_cnpj(texto: str, ini: int) -> str:
    antes = texto[:ini]
    antes = re.sub(
        r"[,;.\s\-–]*(?:inscrit\w*\s+(?:no|sob\s+o)\s+)?(?:CNPJ)?(?:\s*/\s*MF)?\s*(?:sob\s+(?:o\s+)?)?(?:n[ºo°]\.?)?[\s.:]*$",
        "", antes, flags=re.I)
    padroes = [
        r"\(CEBAS\),?\s+(?:" + PREPOSICOES + r"\s+)?(?:entidade\s+)?(.+)$",
        r"Interessad[ao]s?:\s*(.+)$",
        r"interposto pel[ao]\s+(.+)$",
        r".*\bentidade:?\s+(?!Beneficente)(.+)$",
        r"^\s*\d{1,4}\s*[\)\.\-–]\s*(.+)$",
        r"Nome da entidade:\s*(.+)$",
    ]
    for p in padroes:
        m = re.search(p, antes)
        if m:
            nome = m.group(1)
            break
    else:
        nome = re.split(r"[:;]|\b(?:CEBAS|Social)\b\)?,?\s+" + PREPOSICOES + r"\s+", antes)[-1]
    nome = re.sub(r"[,.\s]+$", "", nome)
    return limpar(nome)[:200]


def municipio_uf(texto: str, fim_cnpj: int) -> str:
    depois = texto[fim_cnpj:fim_cnpj + 120]
    m = re.match(r"\s*,\s*([^,/]{2,60}/[A-Z]{2})\b", depois)
    if m:
        return limpar(m.group(1))
    m = re.search(r"com sede (?:em|no|na)\s+([^,(]+?)\s*\(([A-Z]{2})\)", texto)
    if m:
        return f"{limpar(m.group(1))}/{m.group(2)}"
    m = re.search(r"Munic[íi]pio:\s*([^\n]+?/[A-Z]{2})", texto)
    return limpar(m.group(1)) if m else ""


def validade(texto: str) -> str:
    for p in (
        r"validade (?:pelo per[íi]odo )?de\s*(.+?\d{4})\s+[aà]\s+(.+?\d{4})",
        r"per[íi]odo de\s*(.+?\d{4})\s+[aà]\s+(.+?\d{4})",
        r",\s*de\s+(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})",
    ):
        m = re.search(p, texto, re.I)
        if m:
            return f"{limpar(m.group(1))} a {limpar(m.group(2))}"
    m = re.search(r"validade (?:pelo per[íi]odo )?de\s+(\d+\s*\(\w+\)\s*anos[^.]*)", texto, re.I)
    if m:
        return limpar(m.group(1))
    return ""


def texto_decisivo(pars: list[Paragrafo]) -> str:
    """Ementa, ou paragrafo 'Decisao:', ou 'Art. 1'/'resolve'."""
    for p in pars:
        if p.classe == "ementa" and TERMO_CEBAS.search(p.texto):
            return p.texto
    for i, p in enumerate(pars):
        if p.texto.startswith("Decisão:") or p.texto.startswith("Decisao:"):
            # a decisao pode continuar no paragrafo seguinte (ex.: MEC "Determino a renovacao...")
            resto = [q.texto for q in pars[i + 1:] if q.classe not in ("assina", "cargo")]
            return " ".join([p.texto] + resto)
    for p in pars:
        if re.match(r"Art\.\s*1", p.texto):
            return p.texto
    for p in pars:
        if "resolve" in p.texto:
            return p.texto
    return " ".join(p.texto for p in pars[:3])


def extrair_ato(m: Materia, idx: int, titulo: str, pars: list[Paragrafo]) -> list[Decisao]:
    texto_ato = "\n".join(p.texto for p in pars)
    if not (TERMO_CEBAS.search(texto_ato) or TERMO_LEI.search(texto_ato)):
        return []
    base = dict(
        ref_ato=f"{m.id_materia}#{idx}",
        id_materia=m.id_materia,
        arquivo=m.arquivo,
        data_publicacao=re.sub(r"(\d{2})/(\d{2})/(\d{4})", r"\3-\2-\1", m.pub_date),
        data_ato=data_do_titulo(titulo),
        identificacao_ato=titulo,
        orgao=m.categoria,
        area=area_do_orgao(m.categoria),
        edicao=m.edicao,
        pagina=m.pagina,
        url_pdf=m.url_pdf,
    )
    assunto = " ".join(p.texto for p in pars if p.texto.startswith("Assunto:"))

    # 1) Atos em lista: itens "N) NOME, CNPJ ..." governados pelo "Art." anterior,
    #    ou linhas de tabela em anexo governadas pelo "Art." que cita aquele anexo.
    saida: list[Decisao] = []
    artigos = [p.texto for p in pars if re.match(r"Art\.\s*\d", p.texto)]
    governante = ""
    anexo = ""
    for p in pars:
        if re.match(r"Art\.\s*\d", p.texto):
            governante = p.texto
            continue
        m_anexo = ANEXO.match(p.texto)
        if m_anexo:
            anexo = m_anexo.group(1).upper()
            continue
        cnpjs = achar_cnpjs(p.texto)
        if not cnpjs:
            continue
        cnpj, ini, fim = cnpjs[0]
        if p.classe == "tabela":
            regra = next((a for a in artigos if anexo and re.search(rf"ANEXO\s+{anexo}\b", a, re.I)), "")
            regra = regra or next((a for a in artigos if VERBO_DECISAO.search(a)), governante)
            entidade = nome_em_tabela(p.texto)
            mun = ""
        elif ITEM_LISTA.match(p.texto) and governante:
            regra = governante
            entidade = nome_antes_do_cnpj(p.texto, ini)
            mun = municipio_uf(p.texto, fim)
        else:
            continue
        tipo, defer, det = classificar(regra)
        saida.append(Decisao(
            **base, cnpj=cnpj, cnpj_dv_ok="S" if dv_cnpj_ok(cnpj) else "N",
            entidade=entidade, municipio_uf=mun,
            tipo_ato=tipo, deferido=defer, detalhe=det, validade=validade(p.texto),
            trecho=(regra[:160] + " [...] " + p.texto)[:700],
        ))
    if saida:
        return saida

    # 2) Ato individual: uma decisao por CNPJ distinto (normalmente 1).
    decisivo = texto_decisivo(pars)
    tipo, defer, det = classificar(decisivo, assunto)
    if tipo == "OUTRO" and not det and not re.search(
        r"\b(defer|indefer|cancel|reconsider|renova|concess)", sem_acento(texto_ato)
    ):
        det = "sem decisao de certificacao (mencao incidental)"
    cnpjs = achar_cnpjs(texto_ato)
    vistos: set[str] = set()
    corpo = next((p.texto for p in pars if re.match(r"Art\.\s*1|Interessad|Nome da entidade", p.texto) and achar_cnpjs(p.texto)), texto_ato)
    for cnpj, ini, fim in cnpjs or [("", -1, -1)]:
        if cnpj in vistos:
            continue
        vistos.add(cnpj)
        if cnpj:
            local = achar_cnpjs(corpo)
            fonte_nome = corpo if any(c == cnpj for c, _, _ in local) else texto_ato
            i2, f2 = next(((i, f) for c, i, f in achar_cnpjs(fonte_nome) if c == cnpj), (ini, fim))
            entidade = nome_antes_do_cnpj(fonte_nome, i2)
            # MEC: "Interessado: X." aparece antes; o CNPJ vem depois ("da entidade X, inscrita no CNPJ")
            mun = municipio_uf(fonte_nome, f2)
        else:
            entidade = ""
            mi = re.search(r"Interessad[ao]:\s*([^\n]+?)\.?$", texto_ato, re.M)
            me = re.search(r"CEBAS\)?,?\s+" + PREPOSICOES + r"\s+(.+?),\s+com sede", texto_ato)
            if mi:
                entidade = limpar(mi.group(1))
            elif me:
                entidade = limpar(me.group(1))
            mun = municipio_uf(texto_ato, 0)
        # Despachos GM/MS: "Interessado: NOME/UF, CNPJ ..."
        m_uf = re.search(r"\s*/\s*([A-Z]{2})$", entidade)
        if m_uf and not mun:
            entidade, mun = entidade[: m_uf.start()], m_uf.group(1)
        incidental = det.startswith("sem decisao")
        saida.append(Decisao(
            **base, cnpj=cnpj, cnpj_dv_ok=("S" if dv_cnpj_ok(cnpj) else "N") if cnpj else "",
            entidade=entidade, municipio_uf=mun, tipo_ato=tipo, deferido=defer, detalhe=det,
            validade="" if incidental else validade(texto_ato), trecho=limpar(decisivo)[:700],
        ))
    return saida


def extrair(caminho_zip: Path) -> tuple[list[Decisao], dict]:
    decisoes: list[Decisao] = []
    stats = {"materias_total": 0, "materias_relevantes": 0}
    for m in ler_zip(caminho_zip):
        stats["materias_total"] += 1
        if not materia_relevante(m):
            continue
        stats["materias_relevantes"] += 1
        pars = paragrafos(m.texto_html)
        for idx, (titulo, ps) in enumerate(dividir_atos(m, pars), 1):
            decisoes.extend(extrair_ato(m, idx, titulo, ps))
    return decisoes, stats


def gravar_csv(decisoes: list[Decisao], destino: Path) -> None:
    campos = list(Decisao.__dataclass_fields__)
    with destino.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        w.writeheader()
        for d in decisoes:
            w.writerow(asdict(d))


def main() -> None:
    zip_path = Path(sys.argv[1])
    destino = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / f"cebas_{zip_path.stem}.csv"
    decisoes, stats = extrair(zip_path)
    gravar_csv(decisoes, destino)
    print(stats, "decisoes:", len(decisoes), "->", destino)


if __name__ == "__main__":
    main()
