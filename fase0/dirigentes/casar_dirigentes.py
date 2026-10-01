"""Protótipo da verificação 10 ampliada: casa dirigentes do QSA com listas públicas de PF.

Fontes locais (baixadas pelos outros scripts desta pasta e de fase0/portal):
- CEIS e CNEP (CSV do Portal; CPF completo)                      -> art. 39, V (via OSC) e VII, c (CNJ no CEIS)
- TCU contas irregulares (CADIRREG; CPF completo)                -> art. 39, VII, a (parcial: não diz se é parceria)
- TCU inabilitados (CPF completo)                                -> art. 39, VII, b
- TCE-SP prestação de contas do Terceiro Setor (CPF 999.XXX.XXX-99) -> art. 39, VII, a (SP, parcerias)

Regra de casamento:
- Fontes com CPF completo: nome normalizado igual E 6 dígitos do meio iguais aos do QSA.
- TCE-SP: nome normalizado igual E dígitos verificadores calculados com
  (3 primeiros do TCE-SP + 6 do meio do QSA) iguais aos 2 últimos do TCE-SP.
  As duas máscaras são complementares, então isso corrobora sem expor o CPF:
  o CPF reconstituído só existe em memória para o cálculo e nunca é gravado.
- CPF completo informado pelo usuário (opcional): igualdade exata de CPF.

Filtro temporal (data de referência = hoje):
- contas irregulares (TCU e TCE-SP): trânsito em julgado nos últimos 8 anos;
- inabilitados TCU: data final da sanção >= hoje;
- CEIS/CNEP: data final vazia ou >= hoje.

Uso como script (teste E2E): ver testar_e2e.py.
"""

from __future__ import annotations

import collections
import csv
import json
import re
from dataclasses import dataclass, field
from datetime import date

import openpyxl

from comum import DOWNLOADS, RAIZ, cpf_valido, data_br, digitos, normalizar_nome

PORTAL = RAIZ / "fase0" / "portal" / "downloads"


def _menos_8_anos(hoje: date) -> date:
    try:
        return hoje.replace(year=hoje.year - 8)
    except ValueError:  # 29/02
        return hoje.replace(year=hoje.year - 8, day=28)


def dv_cpf(base9: str) -> str:
    d = base9
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        d += str((soma * 10) % 11 % 10)
    return d[9:]


@dataclass
class Registro:
    fonte: str
    hipotese: str  # inciso/alinea do art. 39
    nome: str
    cpf: str | None  # completo (só em memória)
    cpf_parcial: str | None  # TCE-SP: 999.XXX.XXX-99
    processo: str
    data_ref: date | None  # trânsito em julgado ou data final
    vigente: bool
    detalhe: dict = field(default_factory=dict)


@dataclass
class Indice:
    hoje: date
    por_nome_meio: dict = field(default_factory=lambda: collections.defaultdict(list))
    por_cpf: dict = field(default_factory=lambda: collections.defaultdict(list))
    tcesp_por_nome: dict = field(default_factory=lambda: collections.defaultdict(list))
    contagem: dict = field(default_factory=dict)

    def _add(self, r: Registro) -> None:
        if r.cpf:
            self.por_nome_meio[(normalizar_nome(r.nome), r.cpf[3:9])].append(r)
            self.por_cpf[r.cpf].append(r)
        else:
            self.tcesp_por_nome[normalizar_nome(r.nome)].append(r)
        self.contagem[r.fonte] = self.contagem.get(r.fonte, 0) + 1


def carregar_indice(hoje: date = date(2026, 10, 1)) -> Indice:
    ix = Indice(hoje=hoje)
    corte8 = _menos_8_anos(hoje)

    for cad in ("CEIS", "CNEP"):
        arq = max(PORTAL.glob(f"*_{cad}.csv"))
        with arq.open(encoding="latin-1", newline="") as f:
            for x in csv.DictReader(f, delimiter=";"):
                if x["TIPO DE PESSOA"] != "F":
                    continue
                cpf = digitos(x["CPF OU CNPJ DO SANCIONADO"])
                if not cpf_valido(cpf):
                    continue
                fim = data_br(x["DATA FINAL SANÇÃO"])
                cnj = "CNJ" in x["ORIGEM INFORMAÇÕES"]
                ix._add(
                    Registro(
                        fonte=cad,
                        hipotese="VII, c (improbidade, via CNJ)"
                        if cnj
                        else "sanção à PF (indício; V se aplica à OSC)",
                        nome=x["NOME DO SANCIONADO"],
                        cpf=cpf,
                        cpf_parcial=None,
                        processo=x["NÚMERO DO PROCESSO"],
                        data_ref=fim,
                        vigente=fim is None or fim >= hoje,
                        detalhe={
                            "categoria": x["CATEGORIA DA SANÇÃO"],
                            "orgao": x["ÓRGÃO SANCIONADOR"],
                            "origem": x["ORIGEM INFORMAÇÕES"],
                        },
                    )
                )

    contas = json.loads(
        (DOWNLOADS / "tcu_responsaveis-contas-irregulares.json").read_text(
            encoding="utf-8"
        )
    )
    for i in contas:
        cpf = digitos(i.get("numeroRegistro"))
        if i.get("tipoRegistro") != "CPF" or not cpf_valido(cpf):
            continue
        tj = data_br(i.get("dataTransitoEmJulgado"))
        ix._add(
            Registro(
                fonte="TCU contas irregulares",
                hipotese="VII, a (parcial: natureza da conta não informada)",
                nome=i["nome"],
                cpf=cpf,
                cpf_parcial=None,
                processo=i.get("numeroProcessoFormatado", ""),
                data_ref=tj,
                vigente=bool(tj and tj >= corte8),
                detalhe={
                    "acordao": i.get("numeroAcordaoFormatado"),
                    "uf": i.get("uf"),
                    "municipio": i.get("municipio"),
                },
            )
        )

    inab = json.loads(
        (DOWNLOADS / "tcu_responsaveis-inabilitados.json").read_text(encoding="utf-8")
    )
    for i in inab:
        cpf = digitos(i.get("numeroRegistro"))
        if not cpf_valido(cpf):
            continue
        fim = data_br(i.get("dataFinalSancao"))
        ix._add(
            Registro(
                fonte="TCU inabilitados",
                hipotese="VII, b",
                nome=i["nome"],
                cpf=cpf,
                cpf_parcial=None,
                processo=i.get("numeroProcessoFormatado", ""),
                data_ref=fim,
                vigente=bool(fim and fim >= hoje),
                detalhe={"acordao": i.get("numeroAcordaoFormatado")},
            )
        )

    arq = DOWNLOADS / "tcesp_prest_contas_terceiro_setor.xlsx"
    if arq.exists():
        ws = openpyxl.load_workbook(arq, read_only=True).worksheets[0]
        for row in ws.iter_rows(values_only=True):
            x = [("" if c is None else str(c)).strip() for c in row]
            if len(x) > 8 and re.fullmatch(r"\d{3}\.XXX\.XXX-\d{2}", x[3]):
                tj = data_br(x[7])
                ix._add(
                    Registro(
                        fonte="TCE-SP terceiro setor",
                        hipotese="VII, a (contas de parceria, SP)",
                        nome=x[2],
                        cpf=None,
                        cpf_parcial=x[3],
                        processo=x[4],
                        data_ref=tj,
                        vigente=bool(tj and tj >= corte8),
                        detalhe={"materia": x[5], "origem": x[6], "exercicio": x[8]},
                    )
                )
    return ix


@dataclass
class Achado:
    dirigente: str
    qualificacao: str
    data_entrada: str
    criterio: str  # "cpf_completo" | "nome+6" | "nome+6+dv"
    registro: Registro


def casar(
    ix: Indice, qsa: list[dict], cpfs_informados: dict[str, str] | None = None
) -> list[Achado]:
    """qsa: itens com nome_socio, cnpj_cpf_socio (***XXXXXX**), qualificacao_socio, data_entrada_sociedade.
    cpfs_informados: {nome_normalizado: cpf completo} informado pelo usuário (opcional)."""
    achados = []
    cpfs_informados = cpfs_informados or {}
    for s in qsa:
        nome = s.get("nome_socio") or ""
        mascara = s.get("cnpj_cpf_socio") or s.get("cnpj_cpf_do_socio") or ""
        meio = digitos(mascara)
        if len(meio) != 6:  # sócio PJ ou estrangeiro
            continue
        nn = normalizar_nome(nome)
        base = {
            "dirigente": nome,
            "qualificacao": s.get("qualificacao_socio", ""),
            "data_entrada": s.get("data_entrada_sociedade", ""),
        }
        cpf_user = digitos(cpfs_informados.get(nn, ""))
        if cpf_user and cpf_user[3:9] == meio:
            for r in ix.por_cpf.get(cpf_user, []):
                achados.append(Achado(**base, criterio="cpf_completo", registro=r))
            for r in ix.tcesp_por_nome.get(nn, []):
                p = digitos(r.cpf_parcial)
                if p[:3] == cpf_user[:3] and p[3:] == cpf_user[9:]:
                    achados.append(Achado(**base, criterio="cpf_completo", registro=r))
            continue
        for r in ix.por_nome_meio.get((nn, meio), []):
            achados.append(Achado(**base, criterio="nome+6", registro=r))
        for r in ix.tcesp_por_nome.get(nn, []):
            p = digitos(r.cpf_parcial)
            if dv_cpf(p[:3] + meio) == p[3:]:
                achados.append(Achado(**base, criterio="nome+6+dv", registro=r))
    return achados
