"""Monta o conjunto de casos de referência com o resultado esperado por verificação.

Aplica as regras do spec v1.2, das decisões D1 a D20 e da revisão pré-código
(`revisao_pre_codigo.md`, Q1 a Q44) sobre as respostas reais salvas em
respostas/ (coletar.py) e sobre as bases locais da Fase 0, e grava:
- fase0/casos_referencia.json  (fixture dos testes do motor)
- fase0/casos_referencia.md    (versão legível)

O catálogo usa os ids textuais da arquitetura (Q25), com o número do spec como
atributo. As regras que ainda dependem do orientador (Q14 a Q24) estão em
REGRAS_ORIENTADOR: trocar a regra é mudar o valor ali e gerar de novo. Cada
verificação cujo esperado depende de uma regra provisória ou pendente traz o
marcador em `depende_de` ("ORIENTADOR Q16", "PENDENTE X17").

Dirigentes (D15, opção C do Q8): QSA x CEIS/CNEP (fatos.dirigentes) e x listas
do TCU (contas irregulares, inabilitados) e do TCE-SP Terceiro Setor, com o
índice e o casamento de fase0/dirigentes/casar_dirigentes.py. O CPF completo
das listas e o CPF reconstituído do TCE-SP só existem em memória; a saída traz
só nome, fonte, processo e datas, e main() confere que nenhum CPF foi gravado.

Uso: .venv/Scripts/python fase0/casos/montar_casos.py
"""

from __future__ import annotations

import importlib
import json
import re
import sys
from collections import Counter
from datetime import date
from functools import cache

import fatos
from casos_def import CASOS, DATA_REFERENCIA
from classificar_cnae import avaliar_entidade, classificar
from comum import RAIZ, RESPOSTAS, cnpj_da_matriz, validar

SAIDA_JSON = RAIZ / "fase0" / "casos_referencia.json"
SAIDA_MD = RAIZ / "fase0" / "casos_referencia.md"

# ------------------------------------------------------------------ parâmetros

# Regras provisórias do ORIENTADOR (revisão pré-código, seção 2.2).
# O valor padrão é a recomendação da revisão; a alternativa está no comentário.
REGRAS_ORIENTADOR = {
    # Q16: categoria do CNEP sem prazo que não está no art. 39, V (multa e publicação extraordinária).
    # "alerta" (recomendado: ALERTA) | "restricao" (spec 1.1: todo CNEP vigente reprova).
    "Q16_cnep_multa": "alerta",
    # Q17: sanção vigente com abrangência limitada ao órgão ou à esfera do sancionador.
    # "restricao" (recomendado: sempre RESTRICAO, abrangência em destaque) | "alerta".
    "Q17_abrangencia_limitada": "restricao",
    # Q18: CEPIM em parceria municipal ou estadual.
    # "qualquer_esfera" (recomendado: sempre RESTRICAO) | "so_uniao" (ALERTA com esfera municipio ou estado).
    "Q18_cepim": "qualquer_esfera",
    # Q19: CNIA (só traz o número do processo).
    # "vigencia" (recomendado: RESTRICAO só com proibição vigente achada no CEIS pelo processo; senão ALERTA)
    # | "qualquer_registro" (casos v1.1: todo registro reprova).
    "Q19_cnia": "vigencia",
    # Q20: sanção registrada em outro estabelecimento da mesma raiz (busca por raiz no CSV local).
    # "restricao" (recomendado, opção A) | "alerta" (opção B) | "exato" (opção C, só o CNPJ consultado e a matriz).
    "Q20_raiz": "restricao",
    # Q21: contas da própria OSC julgadas irregulares pelo TCU (art. 39, VI), verificação nova.
    # "alerta" (recomendado) | "restricao" | "nao_usar" (sem a verificação).
    "Q21_contas_irregulares_osc": "alerta",
    # Q22: achado de dirigente (fontes decididas no Q8, opção C).
    # "ficha" (recomendado: só vigente ou dentro da janela de 8 anos, categorias de servidor sem ALERTA) | "qualquer_vigente".
    "Q22_dirigentes": "ficha",
    # Q23: tempo com cadastro ativo quando há sinal de reativação.
    # "inicio_atividade" (recomendado) | "reativacao" (conta desde data_situacao_cadastral).
    "Q23_tempo": "inicio_atividade",
    # Q24: CEBAS com validade vencida e sem ato novo.
    # None (recomendado: sem limite, com a idade no texto) | número de anos (depois disso, situação desconhecida).
    "Q24_cebas_limite_anos": None,
}

# Q14 (ORIENTADOR): tabela de natureza jurídica, como no spec 6.3.
NATUREZA_ELEGIVEL = {3999, 3069, 3220}
NATUREZA_REVISAO = {2143, 3301, 3204}
NATUREZA_ORIENTADOR = NATUREZA_REVISAO | {3077}

# Q15 (ORIENTADOR): prefixos CNAE dos 8 pontos de fase0/cnae/proposta.md, seção 8.
PREFIXOS_Q15 = (
    "94936",
    "86",
    "931",
    "7500",
    "91031",
    "0220906",
    "38114",
    "383",
    "6499905",
    "60101",
    "7490103",
    "59111",
    "59146",
    "85937",
    "8599603",
    "8599604",
    "8599605",
    "8711505",
    "9001905",
    "8599601",
    "8599602",
    "9001906",
)

# Q6 (DONO, D19): idade máxima das bases (dias) e do espelho cadastral.
IDADE_MAXIMA_DIAS = {
    "CEIS": 3,
    "CNEP": 3,
    "CEPIM": 7,
    "INIDONEOS_TCU": 3,
    "CONTAS_IRREGULARES_TCU": 7,
    "INABILITADOS_TCU": 7,
    "TCESP_TERCEIRO_SETOR": 45,
    "SISCEBAS_SAUDE": 7,
    "DOU": 75,
}
# Datas das bases de dirigentes que fatos.DATA_BASE não traz (fase0/dirigentes/downloads/):
# inabilitados do TCU baixados em 01/10/2026; planilha do TCE-SP com dados até 01/09/2026.
DATA_BASE = {
    **fatos.DATA_BASE,
    "INABILITADOS_TCU": date(2026, 10, 1),
    "TCESP_TERCEIRO_SETOR": date(2026, 9, 1),
}
LIMITE_ESPELHO_DIAS = 60
DATA_ESPELHO_OPENCNPJ = date(2026, 9, 15)
# As idades são medidas na data da coleta; as variantes mudam só a data de referência das vigências.
DATA_COLETA = date.fromisoformat(DATA_REFERENCIA)

JANELA_CONTAS_IRREGULARES_ANOS = 8

# Catálogo (Q25): id, número no spec, nome, tipo.
CATALOGO = [
    ("dv", 1, "Dígito verificador", "ELIMINATORIA"),
    ("situacao", 2, "Situação cadastral", "ELIMINATORIA"),
    ("natureza", 3, "Natureza jurídica", "ELIMINATORIA"),
    ("cnae", 4, "CNAE de relevância social", "ALERTA"),
    ("religiosa", 4, "Organização religiosa (art. 2º, I, c)", "ALERTA"),
    ("tempo", 5, "Tempo de existência", "ALERTA"),
    ("estabelecimento", 2, "Estabelecimento consultado (filial ou matriz)", "INFORMATIVA"),
    ("cepim", 6, "CEPIM", "ELIMINATORIA"),
    ("ceis", 7, "CEIS", "ELIMINATORIA"),
    ("cnep", 8, "CNEP", "ELIMINATORIA"),
    ("tcu_inidoneos", 9, "Licitantes inidôneos (TCU)", "ELIMINATORIA"),
    ("cnj_cnia", 9, "Improbidade (CNJ, CNIA)", "ELIMINATORIA"),
    ("dirigentes", 10, "Dirigentes (QSA)", "ALERTA"),
    ("mapa_osc", 11, "Mapa das OSCs", "INFORMATIVA"),
    ("cebas", 12, "CEBAS", "INFORMATIVA"),
]
if REGRAS_ORIENTADOR["Q21_contas_irregulares_osc"] != "nao_usar":
    tipo_q21 = "ELIMINATORIA" if REGRAS_ORIENTADOR["Q21_contas_irregulares_osc"] == "restricao" else "ALERTA"
    CATALOGO.insert(
        12, ("tcu_contas_irregulares", 9, "Contas julgadas irregulares (TCU, art. 39, VI)", tipo_q21)
    )
IDS = [c[0] for c in CATALOGO]
META = {c[0]: c for c in CATALOGO}
ROTULO_CURTO = {
    "dv": "dv",
    "situacao": "sit",
    "natureza": "nat",
    "cnae": "cnae",
    "religiosa": "rel",
    "tempo": "tempo",
    "estabelecimento": "estab",
    "cepim": "cepim",
    "ceis": "ceis",
    "cnep": "cnep",
    "tcu_inidoneos": "inid",
    "cnj_cnia": "cnia",
    "tcu_contas_irregulares": "ctas",
    "dirigentes": "dir",
    "mapa_osc": "mapa",
    "cebas": "cebas",
}
PRAZO_ESFERA = {"municipio": 1, "estado": 2, "uniao": 3}
NOME_ESFERA = {"municipio": "municípios", "estado": "estados/DF", "uniao": "União"}
ABRANGENCIA_TOTAL = ("todas as esferas em todos os poderes", "", "sem informação", "sem informacao")
CATEGORIAS_CNEP_SEM_PRAZO_FORA_ART39 = ("multa", "publicação extraordinária")
CATEGORIAS_PF_FORA_ART39 = ("demissão", "suspensão")
PRIORIDADE_CEBAS = {
    "ATIVO": 6,
    "EM_RENOVACAO": 5,
    "NAO_VIGENTE": 4,
    "PEDIDO_EM_ANALISE": 3,
    "DESCONHECIDA": 2,
    "NAO_ENCONTRADO": 1,
}

# ----------------------------------------------------------- ambiguidades (A01-A17)

AMBIGUIDADES = [
    {
        "id": "A01",
        "titulo": "Estado das verificações não executadas depois de uma eliminatória no portão cadastral",
        "regra": "Spec 1.1, 2.2: DV inválido, situação diferente de ATIVA e natureza não elegível levavam a INAPTA (fim), sem dizer o estado das demais.",
        "resolucao": "Q1 (DONO, D19): sem parada antecipada. Com DV válido e cadastro encontrado, tudo é avaliado e o relatório mostra todas as restrições; o status continua INAPTA. A coluna `estado_sem_parada` deixou de existir.",
        "situacao": "resolvida",
    },
    {
        "id": "A02",
        "titulo": "Status final quando uma eliminatória fica NAO_VERIFICADO",
        "regra": "Spec 1.1, 2.5 só definia INCONCLUSIVA para eliminatória INDISPONIVEL; D4 manda o alfanumérico para NAO_VERIFICADO.",
        "resolucao": "Q2 (DONO, D19): INCONCLUSIVA com mensagem própria do alfanumérico; spec 1.2, 2.5 inclui NAO_VERIFICADO.",
        "situacao": "resolvida",
    },
    {
        "id": "A03",
        "titulo": "CNPJ com DV válido que não existe na base cadastral",
        "regra": "Spec 1.1, 5.4 usava INDISPONIVEL para 'não encontrado' e para 'fonte fora do ar'.",
        "resolucao": "Q26 (TECNICO, D20): `situacao` INDISPONIVEL com motivo NAO_ENCONTRADO e texto 'não encontrado no espelho de DD/MM/AAAA'; fan-out não roda; demais NAO_VERIFICADO; status INCONCLUSIVA.",
        "situacao": "resolvida",
    },
    {
        "id": "A04",
        "titulo": "Filial com situação diferente da matriz",
        "regra": "D5 só fechava o caso de matriz baixada.",
        "resolucao": "Q4 (DONO, D19): matriz ativa e filial não ativa = ALERTA na verificação `estabelecimento`; `situacao` avalia a entidade (matriz).",
        "situacao": "resolvida",
    },
    {
        "id": "A05",
        "titulo": "Qual CNPJ consultar no Mapa das OSCs e no CEBAS quando a entrada é filial",
        "regra": "D5 não definia Mapa nem CEBAS.",
        "resolucao": "Q28 (TECNICO, D20): Mapa pela matriz; CEBAS pela matriz e pelo estabelecimento consultado (vale o mais informativo).",
        "situacao": "resolvida",
    },
    {
        "id": "A06",
        "titulo": "Matriz que não tem ordem 0001",
        "regra": "D5 não dizia em qual verificação cai o ALERTA nem como seguir.",
        "resolucao": "Q27 (TECNICO, D20): matriz detectada só por `matriz_filial`; se raiz + 0001 for filial, ALERTA em `estabelecimento` pedindo o CNPJ da matriz, e avaliação com os dados do estabelecimento consultado (tempo pela data dele, com aviso).",
        "situacao": "resolvida",
    },
    {
        "id": "A07",
        "titulo": "Em qual verificação cai o alerta de organização religiosa",
        "regra": "Spec 1.1, 6.3 e 7.5 e casos v1.1 punham o alerta na verificação 4.",
        "resolucao": "Q25 (TECNICO, D20): verificação própria `religiosa` (spec 4).",
        "situacao": "resolvida",
    },
    {
        "id": "A08",
        "titulo": "Contagem de anos na fronteira do art. 33, V, a",
        "regra": "Spec e D6 não diziam se o dia do aniversário conta.",
        "resolucao": "Q29 (TECNICO, D20): anos completos, com o aniversário contando; 29/02 faz aniversário em 28/02 em ano não bissexto.",
        "situacao": "resolvida",
    },
    {
        "id": "A09",
        "titulo": "Tempo 'com cadastro ativo' quando a entidade foi reativada",
        "regra": "Art. 33, V, a pede tempo 'com cadastro ativo'; spec 8.1 usa data_inicio_atividade.",
        "resolucao": "[ORIENTADOR Q23] provisório: conta desde data_inicio_atividade e cita a data da situação no texto (parâmetro Q23_tempo).",
        "situacao": "provisória",
    },
    {
        "id": "A10",
        "titulo": "Sanção no último dia de vigência",
        "regra": "Spec 10.4: vigente sem data de fim ou com data de fim igual ou posterior a hoje (a v1.1 dos casos citava por engano o 10.3).",
        "resolucao": "Q30 (TECNICO, D20): vigente até a data final inclusive. C31 em 22/11/2026 é RESTRICAO; em 23/11/2026 é OK com histórico.",
        "situacao": "resolvida",
    },
    {
        "id": "A11",
        "titulo": "CNIA sem datas",
        "regra": "A resposta do CNIA traz só o número do processo, sem data nem prazo.",
        "resolucao": "[ORIENTADOR Q19] provisório: RESTRICAO só se o processo do CNIA tiver proibição de contratar vigente no CEIS (mesmo número de processo); registro achado só expirado ou sem correspondência no CEIS = ALERTA. Q42: o achado indica 'mesma decisão listada em ceis'.",
        "situacao": "provisória",
    },
    {
        "id": "A12",
        "titulo": "Dirigentes: correspondência só por nome e sanção expirada",
        "regra": "Spec 13.5 usa nome + 6 dígitos do meio do CPF (a v1.1 dos casos citava por engano o 13.4 como busca só por nome).",
        "resolucao": "[ORIENTADOR Q22] provisório: ALERTA só para nome + 6 dígitos (TCE-SP: nome + DV) com sanção vigente ou trânsito em julgado nos últimos 8 anos e hipótese do art. 39; categorias de servidor (Demissão, Suspensão), achados fora da janela e só nome ficam como informação. Fontes do Q8 (DONO, opção C, D15): CEIS, CNEP, TCU contas irregulares, TCU inabilitados e TCE-SP Terceiro Setor.",
        "situacao": "provisória",
    },
    {
        "id": "A13",
        "titulo": "CEBAS com renovação tempestiva pendente ou vigência vencida",
        "regra": "D16: validade vencida sem ato novo = 'possível renovação em análise'.",
        "resolucao": "[ORIENTADOR Q24] provisório: sem limite de tempo, com a idade explícita no texto. Q40: `situacao` EM_RENOVACAO. Casos de planilha MDS/MEC marcados [PENDENTE X17] até a carga do DOU desde 12/2023 (Q39).",
        "situacao": "provisória",
    },
    {
        "id": "A14",
        "titulo": "CEBAS com pedido sem decisão e linhas de processo",
        "regra": "Spec 15.3: nenhuma decisão encontrada = NAO_VERIFICADO.",
        "resolucao": "Q31 (TECNICO, D20): NAO_VERIFICADO com 'há pedido em análise sem decisão publicada' (`situacao` PEDIDO_EM_ANALISE); linha só na aba de processos da planilha MDS fica NAO_ENCONTRADO com a observação.",
        "situacao": "resolvida",
    },
    {
        "id": "A15",
        "titulo": "TCU devolve CEIS/CNEP CONSTAM_REGISTROS para sanções expiradas (D18)",
        "regra": "D3 original mandava RESTRICAO em qualquer divergência.",
        "resolucao": "Q7 (DONO, D18 aprovado) e Q35 (TECNICO): vigência pelas datas dos registros (CSV local e OpenCNPJ); só depois a divergência. TCU com registro e nenhuma base local com registro: data entre parênteses da `observacao`; todas passadas = OK com aviso 'registro só no TCU'; alguma futura ou ilegível = RESTRICAO.",
        "situacao": "resolvida",
    },
    {
        "id": "A16",
        "titulo": "Sanção registrada só em outro estabelecimento da mesma raiz",
        "regra": "D5 não tratava sanção de filial quando a entrada é a matriz; com D14 o CSV local permite busca por raiz.",
        "resolucao": "[ORIENTADOR Q20] provisório: registro em qualquer estabelecimento da raiz conta como o do consultado (RESTRICAO), com o estabelecimento indicado no texto (parâmetro Q20_raiz).",
        "situacao": "provisória",
    },
    {
        "id": "A17",
        "titulo": "Dado de origem inconsistente ou duplicado",
        "regra": "D14: vigência pela data, nunca pela categoria.",
        "resolucao": "Q32 (TECNICO, D20): 'com prazo determinado' sem data final = vigente com aviso; duplicados agrupados por categoria + datas + órgão; '0' e '' em datas = nulo.",
        "situacao": "resolvida",
    },
]

REGRAS_PROVISORIAS_TEXTO = {
    "ORIENTADOR Q14": "Tabela de natureza jurídica (revisão manual de 214-3, 330-1, 320-4; 307-7 não elegível).",
    "ORIENTADOR Q15": "Faixas CNAE dos 8 pontos de fase0/cnae/proposta.md e gatilho religioso pelo CNAE 94.91-0.",
    "ORIENTADOR Q16": "CNEP: multa e publicação extraordinária vigentes = ALERTA; demais categorias = RESTRICAO.",
    "ORIENTADOR Q17": "Abrangência limitada continua RESTRICAO, com a abrangência em destaque.",
    "ORIENTADOR Q18": "CEPIM = RESTRICAO em qualquer esfera.",
    "ORIENTADOR Q19": "CNIA = RESTRICAO só com proibição vigente achada no CEIS pelo processo; senão ALERTA.",
    "ORIENTADOR Q20": "Sanção em outro estabelecimento da raiz = RESTRICAO, indicando o estabelecimento.",
    "ORIENTADOR Q21": "Verificação `tcu_contas_irregulares` (OSC na lista do TCU com trânsito em julgado nos últimos 8 anos) = ALERTA.",
    "ORIENTADOR Q22": "Dirigentes: só sanção vigente (CEIS, CNEP, TCU inabilitados) ou trânsito em julgado nos últimos 8 anos (TCU contas irregulares, TCE-SP) e categoria que é hipótese do art. 39.",
    "ORIENTADOR Q23": "Tempo desde data_inicio_atividade, citando a data da situação.",
    "ORIENTADOR Q24": "CEBAS vencido sem ato novo = possível renovação, sem limite, com a idade no texto.",
    "PENDENTE X17": "Esperado de CEBAS MDS/MEC sem os atos do DOU de 12/2023 a 05/2026 (Q39); gerar de novo depois da carga.",
}


# ---------------------------------------------------------------- utilidades


def _data(s: str | None) -> date | None:
    if not s or s in ("0", "-") or str(s).strip().lower().startswith("sem inform"):
        return None
    return fatos._data(str(s))


def _br(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else "-"


def _excel(serial: str) -> date | None:
    try:
        return date.fromordinal(date(1899, 12, 30).toordinal() + int(float(serial)))
    except TypeError, ValueError:
        return None


def _digitos(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")


def _cnpj_fmt(c: str) -> str:
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}" if len(c) == 14 else c


def anos_completos(inicio: date, ref: date) -> int:
    anos = ref.year - inicio.year
    try:
        aniversario = inicio.replace(year=ref.year)
    except ValueError:  # 29/02 em ano não bissexto
        aniversario = date(ref.year, 2, 28)
    return anos - (1 if ref < aniversario else 0)


def _idade_texto(desde: date, ref: date) -> str:
    meses = (ref.year - desde.year) * 12 + (ref.month - desde.month) - (1 if ref.day < desde.day else 0)
    anos, resto = divmod(max(meses, 0), 12)
    partes = ([f"{anos} ano(s)"] if anos else []) + ([f"{resto} mês(es)"] if resto else [])
    return " e ".join(partes) or "menos de 1 mês"


def _pior(a: str, b: str) -> str:
    ordem = ("OK", "ALERTA", "RESTRICAO")
    return max(a, b, key=ordem.index)


def _perto_do_aniversario(marco: date, ref: date) -> bool:
    try:
        aniversario = marco.replace(year=ref.year)
    except ValueError:  # 29/02
        aniversario = date(ref.year, 2, 28)
    return abs((aniversario - ref).days) <= 1


def _base_valida(nome: str) -> bool:
    return (DATA_COLETA - DATA_BASE[nome]).days <= IDADE_MAXIMA_DIAS[nome]


class Avaliacao:
    def __init__(self) -> None:
        self.v: dict[str, dict] = {}
        self.ambiguidades: set[str] = set()
        self.depende: set[str] = set()

    def set(
        self,
        vid: str,
        estado: str,
        motivo: str,
        *amb: str,
        depende: tuple[str, ...] | list[str] = (),
        propaga: bool = True,
        **extra,
    ) -> None:
        _, spec, nome, tipo = META[vid]
        if tipo in ("ALERTA", "INFORMATIVA") and estado == "RESTRICAO":
            raise AssertionError(f"{vid}: verificação {tipo} não pode dar RESTRICAO")
        self.v[vid] = {
            "id": vid,
            "spec": spec,
            "nome": nome,
            "tipo": tipo,
            "estado": estado,
            "motivo": motivo,
            **extra,
        }
        if amb:
            self.v[vid]["ambiguidades"] = sorted(set(amb))
            self.ambiguidades.update(amb)
        if depende:
            self.v[vid]["depende_de"] = sorted(set(depende))
            if propaga:
                self.depende.update(depende)

    def lista(self) -> list[dict]:
        return [self.v[i] for i in IDS]


# ------------------------------------------------------------ sanções (D14, D18)


def _escopo(cnpj_reg: str, consultado: str, matriz: str | None) -> str:
    if cnpj_reg == consultado:
        return "consultado"
    if cnpj_reg == matriz:
        return "matriz"
    return "outro_estabelecimento"


def _registros_datados(chave: str, consultados: list[str], raiz: str) -> tuple[list[dict], list[str], bool]:
    """Combina CSV local (principal, busca por raiz) e OpenCNPJ `?datasets=` (adicional, exato)."""
    cad = chave.upper()
    fontes_ok: list[str] = []
    por_codigo: dict[str, dict] = {}
    if _base_valida(cad):
        fontes_ok.append(f"CSV {cad} de {_br(fatos.DATA_BASE[cad])}")
        for r in fatos.sancoes_csv(cad).get(raiz, []):
            if REGRAS_ORIENTADOR["Q20_raiz"] == "exato" and r["cnpj_registro"] not in consultados:
                continue
            por_codigo[r["codigo"]] = {**r, "fontes": ["csv"]}
    for c in consultados:
        ds = fatos.sancoes_opencnpj(c)
        if ds is None:
            continue
        if "OpenCNPJ ?datasets=" not in fontes_ok:
            fontes_ok.append("OpenCNPJ ?datasets=")
        for r in (ds.get(chave) or {}).get("sancoes") or []:
            atual = por_codigo.get(r.get("codigo"))
            if atual:
                atual["fontes"].append("opencnpj")
            else:
                por_codigo[r.get("codigo") or f"oc{len(por_codigo)}"] = {
                    **r,
                    "cnpj_registro": c,
                    "fontes": ["opencnpj"],
                }
    # A17/Q32: duplicados com códigos diferentes e o mesmo conteúdo são agrupados.
    vistos, saida = set(), []
    for r in por_codigo.values():
        k = (
            r["cnpj_registro"],
            r.get("categoria"),
            r.get("data_inicio"),
            r.get("data_final"),
            r.get("orgao_sancionador"),
            r.get("valor_multa"),
        )
        if k not in vistos:
            vistos.add(k)
            saida.append(r)
    return saida, fontes_ok, len(saida) != len(por_codigo)


def _tcu_item(cnpj: str, tipo: str) -> dict | None:
    t = fatos.tcu(cnpj)
    if t is None:
        return None
    return t["certidoes"].get(tipo)


def avaliar_sancao_datada(
    a: Avaliacao, vid: str, chave: str, tipo_tcu: str, cnpj: str, matriz: str | None, raiz: str, ref: date
) -> list[dict]:
    consultados = [cnpj] + ([matriz] if matriz else [])
    regs, fontes_ok, duplicado = _registros_datados(chave, consultados, raiz)
    amb: list[str] = ["A17"] if duplicado else []
    dep: list[str] = []
    vigentes, historico = [], []
    pior = "OK"
    for r in regs:
        fim = _data(r.get("data_final"))
        esc = _escopo(r["cnpj_registro"], cnpj, matriz)
        abr = (r.get("abrangencia") or "").strip()
        resumo = (
            f"{r.get('categoria')} ({r.get('data_inicio')} a {r.get('data_final') or 'sem data final'}) - {r.get('orgao_sancionador')}"
            + (f" - multa R$ {r['valor_multa']}" if r.get("valor_multa") not in (None, "", "0,00") else "")
            + (f" - abrangência: {abr}" if abr.lower() not in ABRANGENCIA_TOTAL else "")
            + (
                f" [estabelecimento {_cnpj_fmt(r['cnpj_registro'])}, {esc.replace('_', ' ')}]"
                if esc != "consultado"
                else ""
            )
            + f" (fontes: {', '.join(r['fontes'])})"
        )
        if fim is not None and fim < ref:
            historico.append(resumo)
            continue
        estado = "RESTRICAO"
        cat = (r.get("categoria") or "").lower()
        if fim is None and "com prazo" in cat:
            amb.append("A17")
            resumo += (
                " [categoria 'com prazo determinado' sem data final: vigente pela regra de data, revisar]"
            )
        if chave == "cnep" and cat.startswith(CATEGORIAS_CNEP_SEM_PRAZO_FORA_ART39):
            dep.append("ORIENTADOR Q16")
            if REGRAS_ORIENTADOR["Q16_cnep_multa"] == "alerta":
                estado = "ALERTA"
                resumo += " [fora do art. 39, V: ALERTA]"
        if abr.lower() not in ABRANGENCIA_TOTAL:
            dep.append("ORIENTADOR Q17")
            if REGRAS_ORIENTADOR["Q17_abrangencia_limitada"] == "alerta":
                estado = "ALERTA"
        if esc == "outro_estabelecimento":
            amb.append("A16")
            dep.append("ORIENTADOR Q20")
            if REGRAS_ORIENTADOR["Q20_raiz"] == "alerta":
                estado = "ALERTA"
        vigentes.append(f"{resumo} => {estado}")
        pior = _pior(pior, estado)
    # TCU (observação adicional): vigência primeiro, divergência depois (D18, Q35).
    tcu_constam, tcu_sem_registro_local, notas = [], [], []
    tcu_resp = 0
    for c in consultados:
        item = _tcu_item(c, tipo_tcu)
        if item is None:
            continue
        tcu_resp += 1
        if item["situacao"] == "CONSTAM_REGISTROS":
            tcu_constam.append(c)
            if not any(r["cnpj_registro"] == c for r in regs):
                tcu_sem_registro_local.append((c, item.get("observacao") or ""))
    if tcu_resp:
        fontes_ok.append("TCU Consulta Consolidada")
    for c, obs in tcu_sem_registro_local:
        amb.append("A15")
        datas = [_data(d) for d in re.findall(r"\((\d{2}/\d{2}/\d{4})\)", obs)]
        legivel = bool(datas) and all(datas) and len(datas) == obs.count("(")
        if legivel and all(d < ref for d in datas):
            notas.append(
                f"Registro só no TCU para {_cnpj_fmt(c)}, com todas as datas finais passadas ({', '.join(_br(d) for d in datas)}): OK com histórico (Q35)."
            )
        else:
            pior = "RESTRICAO"
            vigentes.append(
                f"Registro só no TCU para {_cnpj_fmt(c)}: '{obs}' (data futura ou ilegível, D3 e Q35) => RESTRICAO"
            )
    if tcu_constam and not vigentes and historico:
        amb.append("A15")
        notas.append(
            f"TCU devolve CONSTAM_REGISTROS para o {tipo_tcu}, mas todas as datas finais já passaram (D18): não é divergência."
        )
    vig_consultados = [
        r
        for r in regs
        if r["cnpj_registro"] in consultados and (_data(r.get("data_final")) or date.max) >= ref
    ]
    nada_tcu = [c for c in consultados if (_tcu_item(c, tipo_tcu) or {}).get("situacao") == "NADA_CONSTA"]
    if vig_consultados and nada_tcu:
        notas.append(
            f"Fontes divergem: TCU NADA_CONSTA para {', '.join(_cnpj_fmt(c) for c in nada_tcu)} e registro vigente nas bases locais; vale a restrição (D3)."
        )
    detalhe = {
        "vigentes": vigentes,
        "historico": historico,
        "fontes": fontes_ok,
        "tcu_constam_registros": bool(tcu_constam),
    }
    if not fontes_ok:
        a.set(
            vid,
            "INDISPONIVEL",
            f"Nenhuma fonte do {tipo_tcu} respondeu dentro da validade.",
            *amb,
            depende=dep,
            detalhe=detalhe,
        )
        return regs
    if vigentes:
        motivo = f"{len(vigentes)} registro(s) vigente(s) em {_br(ref)}: " + "; ".join(vigentes) + "."
    elif historico:
        motivo = "Só sanções expiradas (histórico): " + "; ".join(historico) + "."
    else:
        motivo = f"Nenhum registro no {tipo_tcu} ({', '.join(fontes_ok)})."
    if notas:
        motivo += " " + " ".join(notas)
    a.set(vid, pior if vigentes else "OK", motivo, *amb, depende=dep if vigentes else (), detalhe=detalhe)
    return regs


def avaliar_cepim(a: Avaliacao, cnpj: str, matriz: str | None, raiz: str, esfera: str | None) -> None:
    consultados = [cnpj] + ([matriz] if matriz else [])
    regs: dict[tuple, dict] = {}
    fontes_ok = []
    if _base_valida("CEPIM"):
        fontes_ok.append(f"CSV CEPIM de {_br(fatos.DATA_BASE['CEPIM'])}")
        for r in fatos.sancoes_csv("CEPIM").get(raiz, []):
            if REGRAS_ORIENTADOR["Q20_raiz"] == "exato" and r["cnpj_registro"] not in consultados:
                continue
            regs[(r["cnpj_registro"], r["numero_convenio"])] = {**r, "fontes": ["csv"]}
    for c in consultados:
        ds = fatos.sancoes_opencnpj(c)
        if ds is None:
            continue
        if "OpenCNPJ ?datasets=" not in fontes_ok:
            fontes_ok.append("OpenCNPJ ?datasets=")
        for r in (ds.get("cepim") or {}).get("impedimentos") or []:
            k = (c, r.get("numero_convenio"))
            if k in regs:
                regs[k]["fontes"].append("opencnpj")
            else:
                regs[k] = {**r, "cnpj_registro": c, "fontes": ["opencnpj"]}
    if not fontes_ok:
        a.set("cepim", "INDISPONIVEL", "Nenhuma fonte do CEPIM respondeu dentro da validade.")
        return
    if not regs:
        a.set("cepim", "OK", f"Nenhum registro no CEPIM ({', '.join(fontes_ok)}).")
        return
    dep = ["ORIENTADOR Q18"]
    estado = "RESTRICAO"
    if REGRAS_ORIENTADOR["Q18_cepim"] == "so_uniao" and esfera in ("municipio", "estado"):
        estado = "ALERTA"
    itens, outros = [], False
    for r in regs.values():
        esc = _escopo(r["cnpj_registro"], cnpj, matriz)
        if esc == "outro_estabelecimento":
            outros = True
        itens.append(
            f"convênio {r.get('numero_convenio') or '?'} - {r.get('orgao_concedente') or '?'} - {r.get('motivo') or '?'}"
            + (
                f" [estabelecimento {_cnpj_fmt(r['cnpj_registro'])}, {esc.replace('_', ' ')}]"
                if esc != "consultado"
                else ""
            )
            + f" (fontes: {', '.join(r['fontes'])})"
        )
    amb = []
    if outros:
        amb.append("A16")
        dep.append("ORIENTADOR Q20")
        if REGRAS_ORIENTADOR["Q20_raiz"] == "alerta" and all(
            _escopo(r["cnpj_registro"], cnpj, matriz) == "outro_estabelecimento" for r in regs.values()
        ):
            estado = "ALERTA"
    a.set(
        "cepim",
        estado,
        f"{len(regs)} registro(s) no CEPIM (art. 39; o CEPIM não tem datas, registro presente é impedimento): "
        + "; ".join(itens),
        *amb,
        depende=dep,
        detalhe={"registros": len(regs), "fontes": fontes_ok},
    )


def _ligacoes(processo: str, ceis: list[dict]) -> list[dict]:
    """Q42: registros do CEIS com o mesmo número de processo."""
    alvo = _digitos(processo)
    if len(alvo) < 10:
        return []
    return [r for r in ceis if alvo in _digitos(r.get("numero_processo"))]


def avaliar_tcu_inidoneos(
    a: Avaliacao, cnpj: str, matriz: str | None, raiz: str, ref: date, ceis: list[dict]
) -> None:
    consultados = [cnpj] + ([matriz] if matriz else [])
    ocorr, notas, dep, amb = [], [], [], []
    fontes_ok = []
    tcu_ok = True
    for c in consultados:
        t = fatos.tcu(c)
        if t is None:
            tcu_ok = False
            continue
        if not t["encontrado"]:
            notas.append(
                f"seCnpjEncontradoNaBaseTcu false para {_cnpj_fmt(c)}, com o CNPJ confirmado pelo cadastro: informativo (Q33)."
            )
        item = _tcu_item(c, "Inidôneos") or {}
        if item.get("situacao") == "CONSTAM_REGISTROS":
            obs = item.get("observacao") or ""
            ligados = _ligacoes(obs.split(" - ")[1] if " - " in obs else obs, ceis)
            ocorr.append(
                f"TCU Consulta Consolidada ({_cnpj_fmt(c)}): {obs}"
                + (
                    f" [mesma decisão já listada em ceis: {ligados[0].get('categoria')} até {ligados[0].get('data_final') or 'sem data final'}]"
                    if ligados
                    else ""
                )
            )
        elif item.get("situacao") not in (None, "NADA_CONSTA"):
            tcu_ok = False
    if tcu_ok:
        fontes_ok.append("TCU Consulta Consolidada")
    if _base_valida("INIDONEOS_TCU"):
        fontes_ok.append(f"lista de inidôneos do TCU de {_br(fatos.DATA_BASE['INIDONEOS_TCU'])}")
        for r in fatos.inidoneos_csv().get(raiz, []):
            esc = _escopo(r["cnpj_registro"], cnpj, matriz)
            if esc == "outro_estabelecimento" and REGRAS_ORIENTADOR["Q20_raiz"] == "exato":
                continue
            fim = _data(r.get("data_final"))
            if fim is not None and fim < ref:
                notas.append(
                    f"Lista de inidôneos: sanção de {_cnpj_fmt(r['cnpj_registro'])} encerrada em {_br(fim)} (histórico)."
                )
                continue
            if esc == "outro_estabelecimento":
                amb.append("A16")
                dep.append("ORIENTADOR Q20")
            ocorr.append(
                f"Lista de inidôneos ({_cnpj_fmt(r['cnpj_registro'])}): processo {r['processo']}, acórdão {r['acordao']}, sanção até {r.get('data_final') or 'sem data'}"
            )
    if not fontes_ok:
        a.set(
            "tcu_inidoneos",
            "INDISPONIVEL",
            "Consulta Consolidada do TCU e lista de inidôneos sem resposta válida.",
        )
        return
    nota = (" " + " ".join(notas)) if notas else ""
    if ocorr:
        a.set(
            "tcu_inidoneos",
            "RESTRICAO",
            "; ".join(ocorr) + "." + nota,
            *amb,
            depende=dep,
            detalhe={"fontes": fontes_ok},
        )
    else:
        a.set(
            "tcu_inidoneos",
            "OK",
            f"Nada consta ({', '.join(fontes_ok)}); vale para hoje, com as ressalvas do spec 12.4." + nota,
            detalhe={"fontes": fontes_ok},
        )


def avaliar_cnia(a: Avaliacao, cnpj: str, matriz: str | None, ref: date, ceis: list[dict]) -> None:
    consultados = [cnpj] + ([matriz] if matriz else [])
    achados, pior, indisponivel = [], "OK", False
    for c in consultados:
        item = _tcu_item(c, "CNIA")
        if item is None:
            indisponivel = True
            continue
        if item["situacao"] == "NADA_CONSTA":
            continue
        if item["situacao"] != "CONSTAM_REGISTROS":
            indisponivel = True
            continue
        processos = re.findall(r"\d{15,}", item.get("observacao") or "")
        for p in processos:
            if REGRAS_ORIENTADOR["Q19_cnia"] == "qualquer_registro":
                achados.append(f"processo {p} ({_cnpj_fmt(c)}) => RESTRICAO")
                pior = "RESTRICAO"
                continue
            ligados = _ligacoes(p, ceis)
            vig = [r for r in ligados if (_data(r.get("data_final")) or date.max) >= ref]
            if vig:
                estado = "RESTRICAO"
                txt = f"proibição de contratar vigente até {vig[0].get('data_final') or 'sem data final'} (mesma decisão já listada em ceis)"
            elif ligados:
                estado = "ALERTA"
                txt = f"proibição de contratar já encerrada em {ligados[0].get('data_final')} (mesma decisão listada em ceis, histórico)"
            else:
                estado = "ALERTA"
                txt = "sem data no CNIA nem registro correspondente no CEIS; confira as penas na página de detalhe do CNIA"
            achados.append(f"processo {p} ({_cnpj_fmt(c)}): {txt} => {estado}")
            pior = _pior(pior, estado)
    if achados:
        a.set(
            "cnj_cnia",
            pior,
            "CNIA com registro: " + "; ".join(achados) + ".",
            "A11",
            depende=("ORIENTADOR Q19",),
        )
    elif indisponivel:
        a.set("cnj_cnia", "INDISPONIVEL", "Item CNIA da Consulta Consolidada sem resposta válida.")
    else:
        a.set("cnj_cnia", "OK", "CNIA: NADA_CONSTA na Consulta Consolidada do TCU.")


def avaliar_contas_irregulares(a: Avaliacao, cnpj: str, matriz: str | None, raiz: str, ref: date) -> None:
    if "tcu_contas_irregulares" not in META:
        return
    if not _base_valida("CONTAS_IRREGULARES_TCU"):
        a.set(
            "tcu_contas_irregulares",
            "INDISPONIVEL",
            "Lista de contas irregulares do TCU mais velha que o limite.",
        )
        return
    limite = _limite_8_anos(ref)
    dentro, fora, dep = [], [], ["ORIENTADOR Q21"]
    for r in fatos.contas_irregulares_csv().get(raiz, []):
        esc = _escopo(r["cnpj_registro"], cnpj, matriz)
        if esc == "outro_estabelecimento" and REGRAS_ORIENTADOR["Q20_raiz"] == "exato":
            continue
        tr = _data(r.get("transito"))
        txt = f"processo {r['processo']}, trânsito em julgado {r.get('transito')}" + (
            f" [estabelecimento {_cnpj_fmt(r['cnpj_registro'])}]" if esc != "consultado" else ""
        )
        (dentro if tr and limite <= tr <= ref else fora).append(txt)
    fonte = f"lista de contas irregulares do TCU de {_br(fatos.DATA_BASE['CONTAS_IRREGULARES_TCU'])}"
    if dentro:
        estado = "RESTRICAO" if REGRAS_ORIENTADOR["Q21_contas_irregulares_osc"] == "restricao" else "ALERTA"
        a.set(
            "tcu_contas_irregulares",
            estado,
            f"CNPJ na {fonte} com trânsito em julgado nos últimos {JANELA_CONTAS_IRREGULARES_ANOS} anos: "
            + "; ".join(dentro)
            + ". A lista não informa se a conta é de parceria (art. 39, VI); confira o acórdão.",
            depende=dep,
        )
    else:
        a.set(
            "tcu_contas_irregulares",
            "OK",
            f"Nada na {fonte} nos últimos {JANELA_CONTAS_IRREGULARES_ANOS} anos"
            + (f" (histórico fora da janela: {'; '.join(fora)})" if fora else "")
            + ".",
            depende=dep,
            propaga=False,
        )


# ------------------------------------------- dirigentes: listas do TCU e do TCE-SP (D15, Q8)

PASTA_DIRIGENTES = RAIZ / "fase0" / "dirigentes"
# fonte do casar_dirigentes -> (base para a idade máxima, nome no texto, hipótese do art. 39)
LISTAS_DIRIGENTES = {
    "TCU contas irregulares": (
        "CONTAS_IRREGULARES_TCU",
        "na lista de contas irregulares do TCU",
        "art. 39, VII, a",
    ),
    "TCU inabilitados": ("INABILITADOS_TCU", "na lista de inabilitados do TCU", "art. 39, VII, b"),
    "TCE-SP terceiro setor": (
        "TCESP_TERCEIRO_SETOR",
        "na relação do TCE-SP de contas do Terceiro Setor julgadas irregulares",
        "art. 39, VII, a",
    ),
}


@cache
def _casar_dirigentes():
    """Importa fase0/dirigentes/casar_dirigentes.py e carrega o índice uma vez.

    As duas pastas têm um módulo `comum`; o de fase0/dirigentes é usado só durante o import
    e o de fase0/casos volta para sys.modules logo depois.
    """
    salvo = sys.modules.pop("comum", None)
    sys.path.insert(0, str(PASTA_DIRIGENTES))
    try:
        mod = importlib.import_module("casar_dirigentes")
    finally:
        sys.path.remove(str(PASTA_DIRIGENTES))
        sys.modules.pop("comum", None)
        if salvo is not None:
            sys.modules["comum"] = salvo
    return mod, mod.carregar_indice(DATA_COLETA)


@cache
def _listas_por_nome() -> dict[str, list[tuple[str, list]]]:
    """Nome normalizado -> [(6 dígitos do meio, registros)] das listas do TCU (sem CEIS/CNEP, que vêm de fatos)."""
    _, ix = _casar_dirigentes()
    por_nome: dict[str, list[tuple[str, list]]] = {}
    for (nome, meio), regs in ix.por_nome_meio.items():
        regs = [x for x in regs if x.fonte in LISTAS_DIRIGENTES]
        if regs:
            por_nome.setdefault(nome, []).append((meio, regs))
    return por_nome


def _limite_8_anos(ref: date) -> date:
    try:
        return ref.replace(year=ref.year - JANELA_CONTAS_IRREGULARES_ANOS)
    except ValueError:  # 29/02
        return date(ref.year - JANELA_CONTAS_IRREGULARES_ANOS, 2, 28)


def dirigentes_listas(qsa: list[dict], raiz: str, ref: date) -> dict:
    """QSA x listas do TCU e do TCE-SP com a regra de casar_dirigentes.py.

    Devolve textos sem CPF: só qualificação, nome, fonte, processo e datas.
    """
    mod, ix = _casar_dirigentes()
    validas = {f for f, (base, _, _) in LISTAS_DIRIGENTES.items() if _base_valida(base)}
    socios = [
        {
            "nome_socio": q["nome"],
            "cnpj_cpf_socio": q.get("doc") or "",
            "qualificacao_socio": q.get("qualificacao") or "",
        }
        for q in qsa
        if q.get("tipo") == "Pessoa Física" and q.get("nome")
    ]
    processos_osc = {_digitos(r["processo"]) for r in fatos.contas_irregulares_csv().get(raiz, [])}
    limite = _limite_8_anos(ref)
    # Agrupa por (dirigente, fonte, dentro ou fora da janela) para citar todos os processos numa frase.
    grupos: dict[tuple, list[tuple[date | None, str]]] = {}
    for ach in mod.casar(ix, socios):
        r = ach.registro
        if r.fonte not in validas:
            continue
        if r.fonte == "TCU inabilitados":
            dentro = bool(r.data_ref and r.data_ref >= ref)
            item = f"processo {r.processo}, inabilitação até {_br(r.data_ref)}"
        else:
            dentro = bool(r.data_ref and limite <= r.data_ref <= ref)
            item = f"processo {r.processo}, trânsito em julgado {_br(r.data_ref)}"
        if r.fonte == "TCU contas irregulares" and _digitos(r.processo) in processos_osc:
            item += ", também condenou a própria OSC"
        chave = (ach.qualificacao, ach.dirigente, r.fonte, ach.criterio, dentro)
        grupos.setdefault(chave, []).append((r.data_ref, item))
    alerta, info, so_nome = [], [], 0
    for (qual, nome, fonte, criterio, dentro), itens in grupos.items():
        _, onde, hip = LISTAS_DIRIGENTES[fonte]
        como = (
            "com nome e dígito verificador do CPF conferidos"
            if criterio == "nome+6+dv"
            else "com os mesmos 6 dígitos centrais do CPF"
        )
        itens.sort(key=lambda x: x[0] or date.min, reverse=True)
        extra = (
            "; a lista não informa se a conta é de parceria, confira o acórdão"
            if fonte == "TCU contas irregulares"
            else ""
        )
        txt = f"{qual} {nome} aparece {onde} {como} ({hip}; " + "; ".join(i for _, i in itens) + extra + ")"
        if dentro:
            alerta.append(txt)
        elif fonte == "TCU inabilitados":
            info.append(txt + " [inabilitação encerrada]")
        else:
            info.append(txt + f" [fora da janela de {JANELA_CONTAS_IRREGULARES_ANOS} anos]")
    # Homônimos só por nome (6 dígitos ou DV diferentes): informação, nunca achado.
    for s in socios:
        nn = mod.normalizar_nome(s["nome_socio"])
        meio = _digitos(s["cnpj_cpf_socio"])
        if len(meio) != 6:
            continue
        for m2, regs in _listas_por_nome().get(nn, []):
            if m2 != meio:
                so_nome += sum(1 for x in regs if x.fonte in validas)
        for x in ix.tcesp_por_nome.get(nn, []):
            p = _digitos(x.cpf_parcial)
            if x.fonte in validas and mod.dv_cpf(p[:3] + meio) != p[3:]:
                so_nome += 1
    vencidas = [LISTAS_DIRIGENTES[f][0] for f in LISTAS_DIRIGENTES if f not in validas]
    return {"alerta": alerta, "info": info, "so_nome": so_nome, "vencidas": vencidas}


# ------------------------------------------------------------------ CEBAS (D16)


def _cebas_um(cnpj: str, ref: date) -> dict:
    c = fatos.cebas(cnpj)
    sis = c["siscebas_saude"]
    limite = REGRAS_ORIENTADOR["Q24_cebas_limite_anos"]
    if sis and sis.get("CEBAS") == "SIM":
        sit = sis.get("SITUACAO ATUAL", "")
        fim = _data(sis.get("DATA FINAL DA VIGENCIA"))
        pend = ["PENDENTE X17"] if ("MEC" in sit or "MDS" in sit) else []
        if "VIGENTE" in sit and "NÃO VIGENTE" not in sit and (fim is None or fim >= ref):
            port = sis.get("NUMERO DA PORTARIA")
            port = int(float(port)) if str(port).replace(".", "").isdigit() else port
            return {
                "estado": "OK",
                "situacao": "ATIVO",
                "cnpj": cnpj,
                "depende": pend,
                "motivo": f"CEBAS ativo (saúde) segundo SisCEBAS de {sis.get('DATA ATUALIZACAO')}: portaria {port} publicada em {sis.get('DATA DA PUBLICACAO')}, vigência {sis.get('DATA DE INICIO DA VIGENCIA')} a {sis.get('DATA FINAL DA VIGENCIA')}.",
                "detalhe": {"fonte": "SisCEBAS Saúde", "dou_jun_ago_2026": c["dou_jun_ago_2026"]},
            }
        idade = f", vencida há {_idade_texto(fim, ref)}" if fim and fim < ref else ""
        return {
            "estado": "OK",
            "situacao": "EM_RENOVACAO",
            "cnpj": cnpj,
            "amb": ["A13"],
            "depende": ["ORIENTADOR Q24", *pend],
            "motivo": f"CEBAS = SIM no SisCEBAS de {sis.get('DATA ATUALIZACAO')}, situação '{sit}', vigência até {sis.get('DATA FINAL DA VIGENCIA') or '-'}{idade}: possível renovação em análise; o requerimento tempestivo mantém a validade até a decisão; confirme com o ministério (D16).",
            "detalhe": {"fonte": "SisCEBAS Saúde"},
        }
    if sis and str(sis.get("SITUACAO ATUAL", "")).startswith("PUBLICADO"):
        return {
            "estado": "OK",
            "situacao": "NAO_VIGENTE",
            "cnpj": cnpj,
            "motivo": f"CEBAS não vigente (saúde): último ato '{sis.get('TIPO DE DECISAO')}' ({sis.get('ASSUNTO')}), publicado em {sis.get('DATA DA PUBLICACAO')}; situação '{sis.get('SITUACAO ATUAL')}' no SisCEBAS de {sis.get('DATA ATUALIZACAO')}.",
            "detalhe": {"fonte": "SisCEBAS Saúde"},
        }
    # MDS: aba de situação (sheet2) tem a certificação; aba de processos (sheet1) não é decisão.
    for linha in c["planilhas_mapa"].get("MDS", []):
        if not linha.startswith("xl/worksheets/sheet2.xml"):
            continue
        partes = [p.strip() for p in linha.split(":", 1)[1].split("|")]
        status = next((p for p in partes if p.upper() in ("VIGENTE", "VÁLIDA", "VALIDA")), None)
        datas = [_excel(p) for p in partes[partes.index(status) + 1 :]] if status else []
        fim = datas[1] if len(datas) > 1 else None
        if status and fim and fim >= ref:
            return {
                "estado": "OK",
                "situacao": "ATIVO",
                "cnpj": cnpj,
                "depende": ["PENDENTE X17"],
                "motivo": f"CEBAS ativo (assistência social) segundo planilha MDS de 24/10/2024: {status}, fim {_br(fim)}; DOU carregado só de jun a ago/2026 [PENDENTE X17].",
                "detalhe": {"fonte": "planilha MDS (Mapa das OSCs)"},
            }
        if status:
            if limite is not None and fim and anos_completos(fim, ref) >= limite:
                return {
                    "estado": "NAO_VERIFICADO",
                    "situacao": "DESCONHECIDA",
                    "cnpj": cnpj,
                    "amb": ["A13"],
                    "depende": ["ORIENTADOR Q24", "PENDENTE X17"],
                    "motivo": f"Planilha MDS de 24/10/2024: CEBAS {status} vencido em {_br(fim)}, há mais de {limite} ano(s) sem ato novo: situação desconhecida [PENDENTE X17].",
                    "detalhe": {"fonte": "planilha MDS (Mapa das OSCs)"},
                }
            return {
                "estado": "OK",
                "situacao": "EM_RENOVACAO",
                "cnpj": cnpj,
                "amb": ["A13"],
                "depende": ["ORIENTADOR Q24", "PENDENTE X17"],
                "motivo": f"Planilha MDS de 24/10/2024: CEBAS {status} com vigência até {_br(fim)}, vencida há {_idade_texto(fim, ref) if fim else '?'}, sem ato posterior encontrado no DOU carregado (só jun a ago/2026): possível renovação em análise; o requerimento tempestivo mantém a validade até a decisão; confirme com o ministério (D16). [PENDENTE X17]: faltam os atos do DOU de 12/2023 a 05/2026.",
                "detalhe": {"fonte": "planilha MDS (Mapa das OSCs)"},
            }
    base = "SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026"
    if sis:
        return {
            "estado": "NAO_VERIFICADO",
            "situacao": "PEDIDO_EM_ANALISE",
            "cnpj": cnpj,
            "amb": ["A14"],
            "depende": ["PENDENTE X17"]
            if ("MEC" in str(sis.get("SITUACAO ATUAL")) or "MDS" in str(sis.get("SITUACAO ATUAL")))
            else [],
            "motivo": f"Há pedido em análise sem decisão publicada (SisCEBAS: '{sis.get('SITUACAO ATUAL')}'). Ausência de decisão não significa que a entidade não possui CEBAS ({base}).",
        }
    if c["planilhas_mapa"]:
        return {
            "estado": "NAO_VERIFICADO",
            "situacao": "NAO_ENCONTRADO",
            "cnpj": cnpj,
            "amb": ["A14"],
            "depende": ["PENDENTE X17"],
            "motivo": f"Não foi encontrada decisão de certificação CEBAS ({base}); o CNPJ aparece só na aba de processos da planilha MDS, sem decisão [PENDENTE X17: o DOU de 12/2023 a 05/2026 pode ter a decisão].",
        }
    return {
        "estado": "NAO_VERIFICADO",
        "situacao": "NAO_ENCONTRADO",
        "cnpj": cnpj,
        "motivo": f"Não foi encontrada certificação CEBAS nas bases consultadas ({base}); isso não significa que a entidade não possui CEBAS.",
    }


def avaliar_cebas(a: Avaliacao, cnpjs: list[str], ref: date) -> None:
    """Q28: CEBAS pela matriz e pelo estabelecimento consultado; vale o mais informativo."""
    resultados = [_cebas_um(c, ref) for c in dict.fromkeys(cnpjs)]
    r = max(resultados, key=lambda x: PRIORIDADE_CEBAS[x["situacao"]])
    amb = list(r.get("amb", []))
    motivo = r["motivo"]
    if len(resultados) > 1:
        amb.append("A05")
        motivo += f" (CNPJ usado: {_cnpj_fmt(r['cnpj'])}; consultados matriz e estabelecimento, Q28.)"
    extra = {"detalhe": r["detalhe"]} if "detalhe" in r else {}
    a.set(
        "cebas",
        r["estado"],
        motivo,
        *amb,
        depende=r.get("depende", []),
        situacao_cebas=r["situacao"],
        **extra,
    )


# ------------------------------------------------------------------ avaliação


def avaliar(cnpj: str, ref: date, esfera: str | None) -> tuple[Avaliacao, dict]:
    a = Avaliacao()
    contexto: dict = {}
    dv = validar(cnpj)

    def resto(estado: str, motivo: str, *amb: str) -> None:
        for vid in IDS:
            if vid not in a.v:
                a.set(vid, estado, motivo, *amb)

    if not dv.valido:
        msg = {
            "formato": "formato inválido (esperado 12 caracteres [0-9A-Z] + 2 dígitos)",
            "repetido": "base de 12 posições repetida",
            "dv": f"dígito verificador não confere (esperado {dv.dv_esperado})",
        }[dv.motivo.value]
        a.set("dv", "RESTRICAO", f"CNPJ inválido: {msg}. Erro de digitação, sem relatório de entidade (Q3).")
        resto("NAO_VERIFICADO", "CNPJ inválido: nenhuma fonte é consultada.")
        return a, contexto
    a.set("dv", "OK", "Formato e dígitos verificadores conferem.")

    if not cnpj.isdigit():
        resto(
            "NAO_VERIFICADO",
            "CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2).",
            "A02",
        )
        return a, contexto

    cad = fatos.cadastro(cnpj)
    if cad is None or cad.get("http") != 200:
        a.set(
            "situacao",
            "INDISPONIVEL",
            f"CNPJ não encontrado no espelho do OpenCNPJ de {_br(DATA_ESPELHO_OPENCNPJ)} (HTTP {cad and cad.get('http')}); pode ser CNPJ inexistente ou recém-criado. "
            "No motor a BrasilAPI também é consultada antes de concluir (Q26).",
            "A03",
            motivo_falha="NAO_ENCONTRADO",
        )
        t = fatos.tcu(cnpj)
        contexto["tcu_seCnpjEncontradoNaBaseTcu"] = t and t["encontrado"]
        resto(
            "NAO_VERIFICADO",
            "Sem cadastro não há QSA nem raiz; fan-out não executado (o TCU daria um 'nada consta' enganoso, D13).",
            "A03",
        )
        return a, contexto

    # ---- filial (D5, Q4, Q27, Q44)
    raiz = cnpj[:8]
    entidade = cad
    filial = not cad["matriz"]
    matriz_resolvida = None
    matriz_indisponivel = False
    if filial:
        mc = cnpj_da_matriz(cnpj)
        m = fatos.cadastro(mc) if mc != cnpj else {"http": 200, "matriz": False}
        if m is None:
            matriz_indisponivel = True
        elif m.get("http") == 200 and m["matriz"]:
            matriz_resolvida = mc
            entidade = m
    contexto.update({"filial": filial, "matriz": matriz_resolvida, "razao_social": cad["razao_social"]})

    def sit(c: dict) -> str:
        return f"{c['situacao_texto'].upper()} desde {_br(_data(c['data_situacao']))}" + (
            f" (motivo: {c['motivo']})" if c.get("motivo") and c["motivo"] != "SEM MOTIVO" else ""
        )

    # ---- situacao (entidade) e estabelecimento
    idade_espelho = (DATA_COLETA - DATA_ESPELHO_OPENCNPJ).days
    aviso_espelho = idade_espelho > LIMITE_ESPELHO_DIAS
    if matriz_indisponivel:
        a.set(
            "situacao",
            "INDISPONIVEL",
            "Consulta partiu de filial e o cadastro da matriz não respondeu: sem a matriz não dá para concluir (Q44).",
        )
    elif entidade["situacao"] != 2:
        quem = f"Matriz {_cnpj_fmt(matriz_resolvida)} " if matriz_resolvida else ""
        a.set("situacao", "RESTRICAO", f"{quem}Situação {sit(entidade)}.")
    elif aviso_espelho:
        a.set(
            "situacao",
            "ALERTA",
            f"ATIVA, mas dados cadastrais de {_br(DATA_ESPELHO_OPENCNPJ)}, mais velhos que {LIMITE_ESPELHO_DIAS} dias (Q6).",
        )
    else:
        txt = "ATIVA" + (f" (matriz {_cnpj_fmt(matriz_resolvida)})" if matriz_resolvida else "")
        if filial and not matriz_resolvida:
            txt += "; matriz não identificada, avaliado o estabelecimento consultado (Q27)"
        a.set("situacao", "OK", txt + f"; espelho cadastral de {_br(DATA_ESPELHO_OPENCNPJ)}.")

    if not filial:
        ordem = cnpj[8:12]
        a.set(
            "estabelecimento",
            "OK",
            "Consulta feita pela matriz"
            + (
                "."
                if ordem == "0001"
                else f" com ordem {ordem}, detectada por `matriz_filial`, não pela ordem (Q27)."
            ),
            *(("A06",) if ordem != "0001" else ()),
        )
    elif matriz_resolvida:
        if cad["situacao"] != 2:
            a.set(
                "estabelecimento",
                "ALERTA",
                f"O estabelecimento informado (filial) está {sit(cad)}; a entidade (matriz {_cnpj_fmt(matriz_resolvida)}) está ativa. Confira se o CNPJ informado é o correto (Q4).",
                "A04",
            )
        else:
            a.set(
                "estabelecimento",
                "OK",
                f"Consulta partiu da filial (ATIVA); entidade avaliada pela matriz {_cnpj_fmt(matriz_resolvida)} (D5).",
            )
    elif matriz_indisponivel:
        a.set(
            "estabelecimento",
            "INDISPONIVEL",
            "Consulta partiu de filial; o cadastro da matriz não respondeu (Q44).",
        )
    else:
        a.set(
            "estabelecimento",
            "ALERTA",
            f"O estabelecimento é FILIAL e {_cnpj_fmt(cnpj_da_matriz(cnpj))} (raiz + 0001) não é a matriz: informe o CNPJ da matriz. Avaliação feita com os dados do estabelecimento consultado (Q27).",
            "A06",
        )

    # ---- natureza (Q14)
    nat = entidade["natureza"]
    dep_nat = ("ORIENTADOR Q14",) if nat in NATUREZA_ORIENTADOR else ()
    if nat in NATUREZA_ELEGIVEL:
        a.set("natureza", "OK", f"Natureza {nat} ({entidade['natureza_texto']}) elegível.")
    elif nat in NATUREZA_REVISAO:
        a.set(
            "natureza",
            "ALERTA",
            f"Natureza {nat} ({entidade['natureza_texto']}) exige revisão manual (spec 6.3).",
            depende=dep_nat,
        )
    elif nat is None:
        a.set(
            "natureza",
            "ALERTA",
            f"Natureza '{entidade['natureza_texto']}' sem mapeamento para código: revisão manual (D17).",
        )
    else:
        a.set(
            "natureza",
            "RESTRICAO",
            f"Natureza jurídica {nat} ({entidade['natureza_texto']}) não é compatível com OSC (Lei 13.019/2014, art. 2º, I).",
            depende=dep_nat,
        )

    # ---- cnae e religiosa (D7, Q15; filial: CNAEs dos dois estabelecimentos)
    principal = entidade["cnae_principal"]
    secundarios = list(
        dict.fromkeys(
            entidade["cnaes_secundarios"]
            + ([cad["cnae_principal"], *cad["cnaes_secundarios"]] if entidade is not cad else [])
        )
    )
    secundarios = [s for s in secundarios if s != principal]
    av = avaliar_entidade(nat or 0, principal, secundarios)
    faixa_p = classificar(principal)
    # Q15: o esperado depende do orientador quando um dos 8 pontos pode mudar o estado.
    classes = [classificar(x) for x in [principal, *secundarios]]

    def contestado(cl) -> bool:
        return bool(cl.regra and cl.regra.prefixo.startswith(PREFIXOS_Q15))

    sociais = [cl for cl in classes if cl.faixa in ("ALTA", "MEDIA")]
    altas = [cl for cl in classes if cl.faixa == "ALTA"]
    if av.alerta_cnae:
        dep_cnae = ("ORIENTADOR Q15",) if any(contestado(cl) for cl in classes) else ()
    else:
        dep_cnae = ("ORIENTADOR Q15",) if all(contestado(cl) for cl in sociais) else ()
    religiosa_alvo = nat == 3220 or principal == "9491000"
    dep_rel = (
        ("ORIENTADOR Q15",)
        if religiosa_alvo and (nat != 3220 or (altas and all(contestado(cl) for cl in altas)))
        else ()
    )
    if av.alerta_cnae:
        a.set(
            "cnae",
            "ALERTA",
            f"CNAE principal {principal} ({faixa_p.faixa}); melhor faixa {av.melhor_faixa}. {av.alerta_cnae}",
            depende=dep_cnae,
        )
    else:
        a.set(
            "cnae",
            "OK",
            f"CNAE principal {principal} ({faixa_p.faixa}, regra {faixa_p.regra_aplicada}); melhor faixa {av.melhor_faixa}.",
            depende=dep_cnae,
        )
    if av.alerta_religiosa:
        gatilho = "natureza 3220" if nat == 3220 else "CNAE principal 94.91-0"
        a.set(
            "religiosa",
            "ALERTA",
            f"Gatilho: {gatilho}; nenhum CNAE em ALTA. {av.alerta_religiosa}",
            "A07",
            depende=dep_rel,
        )
    elif religiosa_alvo:
        a.set(
            "religiosa",
            "OK",
            "Organização religiosa com CNAE em ALTA: atividade social indicada no cadastro.",
            depende=dep_rel,
        )
    else:
        a.set(
            "religiosa",
            "OK",
            "Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0.",
        )

    # ---- tempo (D6, Q23, Q27)
    inicio = _data(entidade["inicio"])
    data_sit = _data(entidade.get("data_situacao"))
    amb5, dep5 = [], []
    reativada = bool(
        data_sit and data_sit > inicio and entidade["situacao"] == 2 and (ref - data_sit).days < 3 * 365 + 1
    )
    if reativada:
        amb5.append("A09")
        dep5.append("ORIENTADOR Q23")
    conta_reativacao = reativada and REGRAS_ORIENTADOR["Q23_tempo"] == "reativacao"
    marco = data_sit if conta_reativacao else inicio
    anos = anos_completos(marco, ref)
    if _perto_do_aniversario(marco, ref):
        amb5.append("A08")
    atende = [e for e, p in PRAZO_ESFERA.items() if anos >= p]
    base5 = (
        f"{'Reativação' if conta_reativacao else 'Início'} {_br(marco)} ({anos} ano(s) completo(s) em {_br(ref)}"
        + (", data da matriz" if matriz_resolvida else "")
        + (
            ", data do estabelecimento consultado porque a matriz não foi identificada (Q27)"
            if filial and not matriz_resolvida
            else ""
        )
        + ")"
    )
    if reativada and not conta_reativacao:
        base5 += f"; situação ATIVA desde {_br(data_sit)}, possível reativação (contado desde o início, Q23)"
    if esfera:
        if esfera in atende:
            e5 = (
                "OK",
                f"{base5}: atinge o prazo para {NOME_ESFERA[esfera]} ({PRAZO_ESFERA[esfera]} ano(s)).",
            )
        else:
            e5 = (
                "ALERTA",
                f"{base5}: não atinge o prazo de {PRAZO_ESFERA[esfera]} ano(s) exigido para {NOME_ESFERA[esfera]}; o gestor pode reduzir o prazo (art. 33, V, a).",
            )
    elif anos >= 3:
        e5 = ("OK", f"{base5}: atinge o prazo para União, estados e municípios.")
    elif atende:
        e5 = (
            "ALERTA",
            f"{base5}: atinge {', '.join(NOME_ESFERA[e] for e in atende)}; "
            + "; ".join(
                f"{NOME_ESFERA[e]} exige {p} anos" for e, p in PRAZO_ESFERA.items() if e not in atende
            )
            + ".",
        )
    else:
        e5 = ("ALERTA", f"{base5}: ainda não atinge o prazo mínimo para nenhuma esfera.")
    a.set("tempo", e5[0], e5[1], *amb5, depende=dep5)

    # ---- dirigentes (D15 com a opção C do Q8, Q22 provisório)
    d = fatos.dirigentes(entidade["qsa"])
    dep10: list[str] = []
    if d["pf_no_qsa"] == 0:
        a.set(
            "dirigentes",
            "NAO_VERIFICADO",
            "O cadastro não informa dirigentes pessoas físicas (B22).",
            propaga=False,
        )
    else:
        alerta, info = [], []
        for x in d["fortes"]:
            vig = (_data(x["fim"]) or date.max) >= ref
            fora39 = (x.get("categoria") or "").lower() in CATEGORIAS_PF_FORA_ART39
            txt = f"{x['qualificacao']} {x['nome']} aparece no {x['cadastro']} com os mesmos 6 dígitos centrais do CPF ({x.get('categoria')}, {x['inicio']} a {x['fim'] or 'sem data final'})"
            if REGRAS_ORIENTADOR["Q22_dirigentes"] == "ficha" and (not vig or fora39):
                info.append(txt + (" [expirada]" if not vig else " [categoria fora do art. 39]"))
            elif vig:
                alerta.append(txt)
        lst = dirigentes_listas(entidade["qsa"], raiz, ref)
        alerta += lst["alerta"]
        info += lst["info"]
        so_nome = len(d["so_nome"]) + lst["so_nome"]
        if alerta or info or so_nome:
            dep10.append("ORIENTADOR Q22")
        fontes10 = (
            "CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor"
        )
        extra_info = (f" Informação sem alerta: {'; '.join(info)}." if info else "") + (
            f" {so_nome} homônimo(s) só por nome, sem os dígitos do CPF: sem alerta." if so_nome else ""
        )
        if lst["vencidas"]:
            extra_info += (
                f" Base(s) mais velha(s) que o limite, não consultada(s): {', '.join(lst['vencidas'])}."
            )
        extra_info += " Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados."
        if alerta:
            a.set(
                "dirigentes",
                "ALERTA",
                "Possível correspondência: "
                + "; ".join(alerta)
                + "; confira o CPF no documento oficial."
                + extra_info,
                "A12",
                depende=dep10,
            )
        else:
            a.set(
                "dirigentes",
                "OK",
                f"{d['pf_no_qsa']} dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em {fontes10}."
                + extra_info,
                *(("A12",) if (info or so_nome) else ()),
                depende=dep10,
                propaga=bool(info or so_nome),
            )

    # ---- fan-out (Q1: sempre, com DV válido e cadastro encontrado)
    ceis = avaliar_sancao_datada(a, "ceis", "ceis", "CEIS", cnpj, matriz_resolvida, raiz, ref)
    avaliar_sancao_datada(a, "cnep", "cnep", "CNEP", cnpj, matriz_resolvida, raiz, ref)
    avaliar_cepim(a, cnpj, matriz_resolvida, raiz, esfera)
    avaliar_tcu_inidoneos(a, cnpj, matriz_resolvida, raiz, ref, ceis)
    avaliar_cnia(a, cnpj, matriz_resolvida, ref, ceis)
    avaliar_contas_irregulares(a, cnpj, matriz_resolvida, raiz, ref)

    cnpj_ent = matriz_resolvida or cnpj
    mp = fatos.mapa(cnpj_ent)
    amb11 = ("A05",) if matriz_resolvida else ()
    if mp is None:
        a.set("mapa_osc", "INDISPONIVEL", "Mapa das OSCs sem resposta válida.", situacao_mapa=None)
    elif mp["presente"]:
        preenchido = mp["perfil"] == "preenchido_pela_osc"
        perfil = (
            ("perfil preenchido pela OSC (" + ", ".join(mp["campos_autodeclarados"]) + ")")
            if preenchido
            else "só dados automáticos da Receita (sugerir que a OSC complete o perfil)"
        )
        a.set(
            "mapa_osc",
            "OK",
            f"Presente no Mapa (id_osc {mp['id_osc']}{', CNPJ da matriz' if amb11 else ''}), {perfil}.",
            *amb11,
            situacao_mapa="PREENCHIDO" if preenchido else "AUTOMATICO",
        )
    else:
        a.set(
            "mapa_osc",
            "ALERTA",
            "CNPJ ausente do Mapa das OSCs: possível divergência de classificação; conferir natureza (D2).",
            *amb11,
            situacao_mapa="AUSENTE",
        )
    avaliar_cebas(a, [cnpj_ent, cnpj], ref)
    return a, contexto


def status_final(a: Avaliacao) -> tuple[str, list[str], list[str]]:
    """Spec 2.5 v1.2 (Q2, Q3): devolve (status, motivos, avisos)."""
    v = a.v
    avisos = [i for i in IDS if v[i]["tipo"] != "ELIMINATORIA" and v[i]["estado"] == "INDISPONIVEL"]  # Q5
    if v["dv"]["estado"] == "RESTRICAO":
        return "CNPJ_INVALIDO", ["dv"], []
    elim = [i for i in IDS if v[i]["tipo"] == "ELIMINATORIA"]
    restr = [i for i in elim if v[i]["estado"] == "RESTRICAO"]
    if restr:
        return "INAPTA", restr, avisos
    pend = [i for i in elim if v[i]["estado"] in ("INDISPONIVEL", "NAO_VERIFICADO")]
    if pend:
        return "INCONCLUSIVA", pend, avisos
    alertas = [i for i in IDS if v[i]["estado"] == "ALERTA"]
    if alertas:
        return "APTA_COM_RESSALVAS", alertas, avisos
    return "APTA", [], avisos


# ------------------------------------------------------------------ saída


def montar() -> dict:
    ref_padrao = date.fromisoformat(DATA_REFERENCIA)
    casos_saida = []
    datas_coleta = []
    for caso in CASOS:
        cnpj = caso["cnpj"]
        a, ctx = avaliar(cnpj, ref_padrao, None)
        st, motivos, avisos = status_final(a)
        evid = (
            sorted(str(p.relative_to(RAIZ)).replace("\\", "/") for p in (RESPOSTAS / cnpj).glob("*.json"))
            if (RESPOSTAS / cnpj).exists()
            else []
        )
        if ctx.get("matriz") and (RESPOSTAS / ctx["matriz"]).exists():
            evid += sorted(
                str(p.relative_to(RAIZ)).replace("\\", "/")
                for p in (RESPOSTAS / ctx["matriz"]).glob("*.json")
            )
        for p in evid:
            reg = json.loads((RAIZ / p).read_text(encoding="utf-8"))
            datas_coleta.append(reg["meta"]["data_utc"])
        saida = {
            "id": caso["id"],
            "cnpj": cnpj,
            "titulo": caso["titulo"],
            "testa": caso["testa"],
            "entidade": ctx.get("razao_social"),
            "parametros": {"data_referencia": DATA_REFERENCIA, "esfera": None},
            "status_final": st,
            "motivos": motivos,
            "avisos": avisos,
            "verificacoes": a.lista(),
            "ambiguidades": sorted(a.ambiguidades),
            "depende_de": sorted(a.depende),
            "contexto": ctx,
            "evidencias": evid,
            "variantes": [],
        }
        for var in caso.get("variantes", []):
            ref = date.fromisoformat(var.get("data_referencia", DATA_REFERENCIA))
            av, _ = avaliar(cnpj, ref, var.get("esfera"))
            stv, motv, avv = status_final(av)
            mudou = [
                av.v[i]
                for i in IDS
                if av.v[i]["estado"] != a.v[i]["estado"] or av.v[i]["motivo"] != a.v[i]["motivo"]
            ]
            saida["variantes"].append(
                {
                    "parametros": {"data_referencia": ref.isoformat(), "esfera": var.get("esfera")},
                    "status_final": stv,
                    "motivos": motv,
                    "avisos": avv,
                    "verificacoes_diferentes": mudou,
                    "verificacoes": av.lista(),
                    "depende_de": sorted(av.depende),
                }
            )
        casos_saida.append(saida)
    return {
        "descricao": "Casos de referência do validador de OSC (spec 1.2, 25.1). Resultado esperado por verificação, gerado por fase0/casos/montar_casos.py a partir das respostas reais em fase0/casos/respostas/ e das bases locais da Fase 0.",
        "versao": "1.2",
        "data_referencia": DATA_REFERENCIA,
        "data_coleta": {"inicio_utc": min(datas_coleta), "fim_utc": max(datas_coleta)},
        "fontes": {
            "cadastral": f"OpenCNPJ https://api.opencnpj.org/{{cnpj}} (espelho de {_br(DATA_ESPELHO_OPENCNPJ)})",
            "cepim_ceis_cnep": "CSV diário oficial da CGU (CEIS e CNEP de 30/09/2026, CEPIM de 28/09/2026), observação principal com busca por raiz (D14); OpenCNPJ ?datasets=ceis,cepim,cnep como observação adicional",
            "tcu": "Consulta Consolidada https://certidoes-apf.apps.tcu.gov.br/api/rest/publico/certidoes/{cnpj}?seEmitirPDF=false",
            "tcu_inidoneos_lista": "Plataforma de Certidões do TCU, CSV de inidôneos de 30/09/2026 (Q34)",
            "tcu_contas_irregulares": "Plataforma de Certidões do TCU, CSV de responsáveis com contas irregulares de 01/10/2026 (Q21, provisório)",
            "mapa_osc": "https://mapaosc.ipea.gov.br/api/api/busca/cnpj/{cnpj sem zeros}",
            "cebas": "SisCEBAS Saúde (lista de 30/09/2026), planilhas MDS 24/10/2024 e MEC 2023 do Mapa das OSCs, DOU jun a ago/2026 (falta 12/2023 a 05/2026, X17)",
            "dirigentes": "QSA do OpenCNPJ x pessoas físicas do CSV CEIS e CNEP de 30/09/2026, das listas do TCU de contas irregulares e inabilitados de 01/10/2026 (Plataforma de Certidões) e da relação do TCE-SP de contas do Terceiro Setor julgadas irregulares (planilha com dados até 01/09/2026); D15, opção C do Q8",
        },
        "catalogo": [{"id": i, "spec": s, "nome": n, "tipo": t} for i, s, n, t in CATALOGO],
        "estados": ["OK", "RESTRICAO", "ALERTA", "INDISPONIVEL", "NAO_VERIFICADO"],
        "status_finais": ["CNPJ_INVALIDO", "INAPTA", "INCONCLUSIVA", "APTA_COM_RESSALVAS", "APTA"],
        "regras_adotadas": {
            "status_final": "CNPJ_INVALIDO se `dv` falhar (Q3); senão INAPTA se eliminatória em RESTRICAO; senão INCONCLUSIVA se eliminatória INDISPONIVEL ou NAO_VERIFICADO (Q2); senão APTA_COM_RESSALVAS se qualquer verificação em ALERTA (inclui `mapa_osc`, D2); senão APTA. `motivos` lista os ids que decidiram; `avisos` lista as não eliminatórias INDISPONIVEL, mostradas em destaque (Q5).",
            "sem_parada_antecipada": "Com DV válido e cadastro encontrado, todas as verificações são avaliadas, inclusive de entidade já INAPTA (Q1). CNPJ não encontrado: fan-out não roda (Q26).",
            "vigencia_sancao": "Vigente se sem data final ou data final >= data de referência (Q30); datas do CSV local e do OpenCNPJ ?datasets=; TCU CONSTAM_REGISTROS com tudo expirado não é divergência (D18); registro só no TCU segue Q35.",
            "idade_das_bases": f"Medida na data da coleta ({_br(DATA_COLETA)}), com os limites do Q6; as variantes mudam só a data de referência das vigências.",
            "regras_orientador": {k: v for k, v in REGRAS_ORIENTADOR.items()},
        },
        "regras_provisorias": REGRAS_PROVISORIAS_TEXTO,
        "ambiguidades": AMBIGUIDADES,
        "casos": casos_saida,
    }


NAO_ENCONTRADOS = """## Casos não encontrados

| Caso procurado | O que foi tentado | Cobertura parcial no conjunto |
|---|---|---|
| Associação ATIVA e elegível ausente do Mapa das OSCs (D2 isolado) | Todas as associações ativas consultadas (mais de 30) estavam no Mapa. As 15 marcadas `removida_do_mosc = sim` e 'Ativa' nas fatias da base do Mapa estão BAIXADAS hoje na Receita. 300 raízes sorteadas depois da última carga do Mapa (`buscar_ausente_mapa.py`, sementes 20261001 e 7) não trouxeram nenhuma associação (só MEI, LTDA e afins). | C14 (cooperativa ausente do Mapa, ALERTA junto com a natureza) e C24 (filial ausente, matriz presente, Q28). |
| OSC ATIVA declarada inidônea pelo TCU | A lista de inidôneos tem 128 CNPJs e só 2 OSCs (ITS e IMDC), ambas INAPTAS na Receita. | C40 e C42 cobrem `tcu_inidoneos` em RESTRICAO, agora avaliado mesmo com a entidade INAPTA (Q1). |
| Dirigente com sanção em entidade sem sanção própria | 5 PJs do CEIS com todas as sanções expiradas e ativas na Receita: nenhum dirigente casou nome + CPF. Com as listas do TCU e do TCE-SP (Q8), todos os achados caíram em entidades já sancionadas ou INAPTAS. | C36, C39 a C42, C44 e C46 têm dirigente com achado, mas a própria entidade também é sancionada ou INAPTA; C28 tem achado no TCU só fora da janela de 8 anos. |
| Associação com situação NULA (código 1) | Não apareceu nas fatias da base do Mapa (o Mapa agrupa 'Nula ou Baixada'). | C08 a C10 cobrem BAIXADA, INAPTA e SUSPENSA. |
| CEBAS da Educação (MEC) | Nenhum CNPJ do conjunto está na planilha MEC de 2023 nem em ato do MEC no DOU de jun a ago/2026. | CEBAS saúde (C47, C48, C25) e assistência social (C16). |
| Certificado autodeclarado no Mapa | Pendência P4 (não procurado nesta rodada). | Perfil preenchido pela OSC em C16 e outros. |
| Fonte INDISPONIVEL e base local vencida | Não é reproduzível com um CNPJ real: depende de falha da fonte ou de data. | Os testes do motor precisam injetar timeout, 5xx, `SISTEMA_INDISPONIVEL` e `ERRO` do TCU, matriz sem resposta (Q44) e base mais velha que o limite (Q6). |
| CNIA com proibição já encerrada no CEIS | Nos 6 casos com CNIA, a proibição de contratar no CEIS está vigente. | O caminho ALERTA do Q19 está no código, sem caso real. |

Encontrados na rodada de 01/10/2026: associação INAPTA (C09), associação SUSPENSA (C10), Organização Social 3301 (C15), ocorrência no CNIA (C35 e C36, também C39 e C46), CNAE comercial BAIXA (C17), igreja como associação (C13), fronteiras de 1 e 2 anos (C21, C22), matriz fora da ordem 0001 (C26, C27).

## Achados da coleta que afetam fichas e decisões

- Muitos casos de sanção das fichas anteriores estão INAPTOS ou BAIXADOS na Receita: Paripueira, ITS, IMDC, Pacaembu, AVAPE, Ilumina Terra, Associação Plural e Bom Jesus (BAIXADA). Com Q1 eles mostram todas as restrições (C39 a C46).
- O CNPJ 07.408.449/0001-32 se chama hoje INSTITUTO ATUAR (no CEIS ainda aparece como INSTITUTO CAMINHADA).
- Na IDEAS (24.006.302), o estabelecimento 0004-88 é a matriz e o 0001-35 é filial: o motor precisa usar `matriz_filial` e não a ordem (Q27).
- A IDEAS tem a mesma sanção do TRF4 registrada em 5 estabelecimentos; com a busca por raiz (Q20) todos aparecem.
- O OpenCNPJ devolve `data_situacao_cadastral` = '0' para a matriz do Instituto GRPCOM e registros de sanção duplicados no `?datasets=` (CNEP do IPCIM, CEIS da IDEAS).
- O CNIA devolve só o número do processo, sem data; o mesmo número aparece no CEIS de origem CNJ com as datas (Q19, Q42).
- A Consulta Consolidada do TCU devolve CEIS CONSTAM_REGISTROS também para sanções expiradas (D18), confirmado em C31 (variante de 23/11/2026), C32 e C44.
- Dirigentes com as fontes do Q8 (opção C): TCU contas irregulares em C40 e C42 (em C42, todos os processos também condenaram a própria OSC), TCE-SP Terceiro Setor em C41, C44 e C46 (nome + DV), e só fora da janela de 8 anos em C28 e C36; nenhum achado na lista de inabilitados do TCU.

## Como reproduzir

A partir da raiz do projeto:

1. `.venv/Scripts/python fase0/casos/coletar.py` consulta OpenCNPJ, OpenCNPJ `?datasets=`, TCU e Mapa para todos os casos e salva em `fase0/casos/respostas/<cnpj>/`.
2. `.venv/Scripts/python fase0/casos/montar_casos.py` aplica as regras e gera `fase0/casos_referencia.json` e este arquivo. As bases locais usadas são os CSVs da CGU em `fase0/portal/downloads/`, a lista de inidôneos em `fase0/tcu/respostas/`, as listas do TCU (contas irregulares e inabilitados) e a planilha do TCE-SP em `fase0/dirigentes/downloads/` (lidas com `fase0/dirigentes/casar_dirigentes.py`) e as bases de CEBAS de `fase0/cebas_dou/` e `fase0/mapa_osc/`.
3. Para trocar uma regra provisória do orientador, mudar o valor em `REGRAS_ORIENTADOR` no início de `montar_casos.py` e rodar o passo 2.
4. Scripts de busca usados para achar os casos: `amostra_mapa.py` (fatias da base do Mapa), `buscar_cnia.py`, `buscar_ativos.py`, `buscar_extras.py` e `buscar_ausente_mapa.py`.

Os dados mudam: antes de usar como teste E2E contra as fontes reais, rodar de novo os dois primeiros passos e revisar a diferença no JSON.
Para o teste de regressão do motor, usar as respostas salvas como mocks das fontes.
"""

ROTULO = {
    "APTA": "APTA",
    "APTA_COM_RESSALVAS": "APTA COM RESSALVAS",
    "INAPTA": "INAPTA",
    "INCONCLUSIVA": "INCONCLUSIVA",
    "CNPJ_INVALIDO": "CNPJ INVÁLIDO",
}


def _md_celula(s: str) -> str:
    return s.replace("|", "/").replace("\n", " ").replace("<br/>", "; ")


def gerar_md(dados: dict) -> str:
    linhas: list[str] = []
    w = linhas.append
    w("# Casos de referência do validador de OSC")
    w("")
    w("Conjunto de CNPJs do spec 25.1, ampliado com os casos das fichas da Fase 0 e das decisões D1 a D20.")
    w(
        f"Cada caso traz o resultado esperado de cada uma das {len(IDS)} verificações do catálogo (Q25) e o status final."
    )
    w("Ele é a fonte do teste de regressão e E2E do motor; a versão para máquina é `casos_referencia.json`.")
    w("")
    w(
        f"- Versão 1.2 do conjunto, alinhada ao spec 1.2. Data de referência das regras: {_br(date.fromisoformat(dados['data_referencia']))}."
    )
    w(
        f"- Coleta das fontes: {dados['data_coleta']['inicio_utc'][:16].replace('T', ' ')} a {dados['data_coleta']['fim_utc'][:16].replace('T', ' ')} (UTC)."
    )
    w(
        "- Gerado por `fase0/casos/montar_casos.py` a partir das respostas reais salvas em `fase0/casos/respostas/` e das bases locais da Fase 0."
    )
    w("- Não editar à mão: alterar a regra no script e gerar de novo.")
    w("")
    w("## Catálogo de verificações (Q25)")
    w("")
    w("| Coluna | id | Spec | Nome | Tipo |")
    w("|---|---|---|---|---|")
    for item in dados["catalogo"]:
        w(
            f"| {ROTULO_CURTO[item['id']]} | `{item['id']}` | {item['spec']} | {item['nome']} | {item['tipo']} |"
        )
    w("")
    w("## Fontes consultadas")
    w("")
    w("| Uso | Fonte |")
    w("|---|---|")
    for k, v in dados["fontes"].items():
        w(f"| {k} | {v} |")
    w("")
    w("## Regras adotadas na geração")
    w("")
    for k, v in dados["regras_adotadas"].items():
        if k == "regras_orientador":
            continue
        w(f"- **{k}**: {v}")
    w("- `natureza` em REVISÃO MANUAL e natureza sem mapeamento viram ALERTA; o fluxo continua.")
    w(
        "- Filial (D5, Q4, Q27, Q28): `situacao` avalia a entidade (matriz); `estabelecimento` avisa da filial não ativa ou da matriz não identificada; natureza, tempo e QSA da matriz; CNAEs dos dois; sanções da filial, da matriz e da raiz (Q20); Mapa pela matriz; CEBAS pela matriz e pelo consultado."
    )
    w(
        "- CEBAS (D16, Q31, Q40): SisCEBAS Saúde primeiro; depois aba de situação da planilha MDS; aba de processos não é decisão. O campo `situacao_cebas` traz o rótulo próprio."
    )
    w("")
    w("## Regras provisórias e pendentes")
    w("")
    w(
        "Os esperados marcados com estes códigos (coluna 'Depende de' e campo `depende_de` do JSON) podem mudar se a regra mudar."
    )
    w(
        "Toda `tcu_contas_irregulares` existe por [ORIENTADOR Q21] e toda `dirigentes` com achado ou homônimo depende de [ORIENTADOR Q22]; no resumo esses dois marcadores só aparecem quando há achado."
    )
    w(
        "As regras do orientador ficam em `REGRAS_ORIENTADOR` no início de `montar_casos.py`; trocar a regra é mudar um valor e gerar de novo."
    )
    w("")
    w("| Marcador | Regra adotada agora | Parâmetro |")
    w("|---|---|---|")
    for k, v in dados["regras_provisorias"].items():
        q = k.split()[-1]
        par = next(
            (
                f"`{p}` = `{val}`"
                for p, val in dados["regras_adotadas"]["regras_orientador"].items()
                if p.startswith(q + "_")
            ),
            "-",
        )
        w(f"| [{k}] | {v} | {par} |")
    w("")
    w("## Resumo")
    w("")
    w("Legenda: `OK` ok, `R` restrição, `A` alerta, `I` indisponível, `-` não verificado.")
    w("")
    cab = " | ".join(ROTULO_CURTO[i] for i in IDS)
    w(f"| Caso | CNPJ | O que testa | {cab} | Status final esperado | Depende de |")
    w("|---|---|---|" + "---|" * len(IDS) + "---|---|")
    sig = {"OK": "OK", "RESTRICAO": "R", "ALERTA": "A", "INDISPONIVEL": "I", "NAO_VERIFICADO": "-"}
    for c in dados["casos"]:
        cel = " | ".join(sig[v["estado"]] for v in c["verificacoes"])
        dep = (
            ", ".join(x.replace("ORIENTADOR ", "O-").replace("PENDENTE ", "P-") for x in c["depende_de"])
            or "-"
        )
        w(
            f"| {c['id']} | {_cnpj_fmt(c['cnpj'])} | {_md_celula(c['titulo'])} | {cel} | **{ROTULO[c['status_final']]}** | {dep} |"
        )
    w("")
    w("Na coluna 'Depende de', `O-Qxx` é [ORIENTADOR Qxx] e `P-xx` é [PENDENTE xx].")
    n_var = sum(len(c["variantes"]) for c in dados["casos"])
    cont = Counter(c["status_final"] for c in dados["casos"])
    w(
        f"Total: {len(dados['casos'])} casos e {n_var} variantes (mesmo CNPJ com outra data de referência ou esfera)."
    )
    w("Distribuição do status final: " + ", ".join(f"{ROTULO[k]} {v}" for k, v in sorted(cont.items())) + ".")
    w("")
    w("## Casos")
    for c in dados["casos"]:
        w("")
        w(f"### {c['id']} - {c['titulo']}")
        w("")
        w(f"- CNPJ: `{_cnpj_fmt(c['cnpj'])}`.")
        if c["entidade"]:
            w(f"- Entidade: {c['entidade']}.")
        w(f"- O que testa: {c['testa']}")
        w(
            f"- Status final esperado: **{ROTULO[c['status_final']]}**"
            + (f", motivos: {', '.join('`' + m + '`' for m in c['motivos'])}." if c["motivos"] else ".")
        )
        if c["avisos"]:
            w(f"- Avisos em destaque (Q5): {', '.join(c['avisos'])}.")
        if c["ambiguidades"]:
            w(f"- Ambiguidades envolvidas: {', '.join(c['ambiguidades'])}.")
        if c["depende_de"]:
            w(f"- Depende de: {', '.join('[' + d + ']' for d in c['depende_de'])}.")
        w("")
        w("| id | Spec | Verificação | Estado esperado | Justificativa |")
        w("|---|---|---|---|---|")
        for v in c["verificacoes"]:
            just = _md_celula(v["motivo"])
            if v.get("depende_de"):
                just += " " + " ".join(f"[{d}]" for d in v["depende_de"])
            w(f"| `{v['id']}` | {v['spec']} | {v['nome']} | {v['estado']} | {just} |")
        for var in c["variantes"]:
            p = var["parametros"]
            desc = ", ".join(f"{k} = {v}" for k, v in p.items() if v)
            w("")
            w(f"Variante ({desc}): status **{ROTULO[var['status_final']]}**.")
            for v in var["verificacoes_diferentes"]:
                w(f"`{v['id']}`: {v['estado']} - {_md_celula(v['motivo'])}")
    w("")
    w("## Ambiguidades encontradas nas regras e como foram resolvidas")
    w("")
    w("Cada item é um ponto em que o spec 1.1 e as decisões não fechavam o resultado esperado.")
    w(
        "A resolução cita a pergunta da revisão pré-código (`revisao_pre_codigo.md`) que a fechou; as marcadas como provisórias seguem a recomendação da revisão até o orientador responder."
    )
    for amb in dados["ambiguidades"]:
        casos = [c["id"] for c in dados["casos"] if amb["id"] in c["ambiguidades"]]
        w("")
        w(f"### {amb['id']} - {amb['titulo']} ({amb['situacao']})")
        w("")
        w(f"- Regra antes: {amb['regra']}")
        w(f"- Resolução: {amb['resolucao']}")
        w(
            f"- Casos afetados: {', '.join(casos) if casos else 'nenhum caso do conjunto (regra registrada para o motor)'}."
        )
    w("")
    return "\n".join(linhas)


def conferir_sem_cpf(texto: str) -> None:
    """Nenhum CPF completo das listas nem CPF parcial do TCE-SP pode sair nos arquivos gerados."""
    _, ix = _casar_dirigentes()
    candidatos = set(re.findall(r"(?<!\d)\d{11}(?!\d)", texto))
    candidatos |= {_digitos(c) for c in re.findall(r"\d{3}\.\d{3}\.\d{3}-\d{2}", texto)}
    vazados = candidatos & set(ix.por_cpf)
    assert not vazados, f"{len(vazados)} CPF(s) completo(s) no texto gerado"
    assert not re.search(r"\d{3}\.XXX\.XXX-\d{2}", texto), "CPF parcial do TCE-SP no texto gerado"


def main() -> None:
    dados = montar()
    SAIDA_JSON.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    md = gerar_md(dados) + "\n" + NAO_ENCONTRADOS
    assert chr(0x2014) not in md and chr(0x2013) not in md, "travessão proibido no texto gerado"
    conferir_sem_cpf(json.dumps(dados, ensure_ascii=False) + md)
    SAIDA_MD.write_text(md, encoding="utf-8")
    print(f"{len(dados['casos'])} casos -> {SAIDA_JSON.name}, {SAIDA_MD.name}")
    for c in dados["casos"]:
        print(
            f"{c['id']} {c['cnpj']} {c['status_final']:<20} "
            + " ".join(v["estado"][:4] for v in c["verificacoes"])
            + "  "
            + ",".join(c["depende_de"])
        )


if __name__ == "__main__":
    main()
