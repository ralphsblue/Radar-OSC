"""Classifica subclasses CNAE em faixas de aderência à relevância pública e social.

Duas responsabilidades:
1. Faixa por subclasse (ALTA / MEDIA / BAIXA), pela regra de prefixo mais
   específica de regras_cnae.json (subclasse > classe > grupo > divisão > padrão).
2. Avaliação de uma entidade (cap. 7.4 do spec) e a regra separada de alerta
   para organizações religiosas (art. 2º, I, c da Lei 13.019/2014).

Uso como script: gera cnae_classificado.csv e imprime as contagens por faixa.
    .venv/Scripts/python fase0/cnae/classificar_cnae.py
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PASTA = Path(__file__).parent
ARQ_IBGE = PASTA / "ibge_cnae_subclasses.json"
ARQ_REGRAS = PASTA / "regras_cnae.json"
ARQ_CSV = PASTA / "cnae_classificado.csv"

FAIXAS = ("ALTA", "MEDIA", "BAIXA")
NIVEL_POR_TAMANHO = {2: "divisao", 3: "grupo", 5: "classe", 7: "subclasse"}
NIVEL_PARA_COLECAO = {"divisao": "divisoes", "grupo": "grupos", "classe": "classes", "subclasse": "subclasses"}

NATUREZA_ORGANIZACAO_RELIGIOSA = 3220
SUBCLASSE_RELIGIOSA = "9491000"


@dataclass(frozen=True)
class Regra:
    prefixo: str
    nivel: str
    faixa: str
    justificativa: str


@dataclass(frozen=True)
class Classificacao:
    subclasse: str
    faixa: str
    regra: Regra | None  # None = padrão

    @property
    def regra_aplicada(self) -> str:
        if self.regra is None:
            return "padrao"
        return f"{formatar_prefixo(self.regra.prefixo)} ({self.regra.nivel})"


# ---------------------------------------------------------------- utilidades


def normalizar_cnae(valor: str | int) -> str:
    """Aceita 9430800, '9430800', '94.30-8-00', '9430-8/00' e o inteiro sem zero
    à esquerda que a BrasilAPI devolve para as divisões 01 a 09 (ex.: 111301)."""
    digitos = re.sub(r"\D", "", str(valor))
    if not 6 <= len(digitos) <= 7:
        raise ValueError(f"CNAE inválido: {valor!r}")
    return digitos.zfill(7)


def formatar_prefixo(prefixo: str) -> str:
    """'94308' -> '94.30-8'; '9430800' -> '9430-8/00'; '941' -> '94.1'."""
    if len(prefixo) == 2:
        return prefixo
    if len(prefixo) == 3:
        return f"{prefixo[:2]}.{prefixo[2]}"
    if len(prefixo) == 5:
        return f"{prefixo[:2]}.{prefixo[2:4]}-{prefixo[4]}"
    return f"{prefixo[:4]}-{prefixo[4]}/{prefixo[5:]}"


# ----------------------------------------------------------- carga e validação


@lru_cache(maxsize=1)
def carregar_ibge() -> dict:
    return json.loads(ARQ_IBGE.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def carregar_regras() -> tuple[tuple[Regra, ...], str, str]:
    bruto = json.loads(ARQ_REGRAS.read_text(encoding="utf-8"))
    regras = tuple(Regra(**r) for r in bruto["regras"])
    validar_regras(regras, carregar_ibge())
    return regras, bruto["padrao"]["faixa"], bruto["padrao"]["justificativa"]


def validar_regras(regras: tuple[Regra, ...], ibge: dict) -> None:
    """Falha cedo se uma regra estiver mal formada, duplicada ou apontar para
    um código que não existe na estrutura oficial do IBGE."""
    ids_por_nivel = {
        nivel: {item["id"] for item in ibge[colecao]} for nivel, colecao in NIVEL_PARA_COLECAO.items()
    }
    vistos: set[str] = set()
    for regra in regras:
        if regra.faixa not in FAIXAS:
            raise ValueError(f"Faixa inválida em {regra.prefixo}: {regra.faixa}")
        if NIVEL_POR_TAMANHO.get(len(regra.prefixo)) != regra.nivel:
            raise ValueError(f"Nível '{regra.nivel}' não confere com o prefixo {regra.prefixo}")
        if regra.prefixo not in ids_por_nivel[regra.nivel]:
            raise ValueError(f"Prefixo {regra.prefixo} não existe no nível {regra.nivel} da CNAE do IBGE")
        if regra.prefixo in vistos:
            raise ValueError(f"Prefixo duplicado: {regra.prefixo}")
        if not regra.justificativa.strip():
            raise ValueError(f"Regra {regra.prefixo} sem justificativa")
        vistos.add(regra.prefixo)


# ------------------------------------------------------------- classificação


def classificar(cnae: str | int) -> Classificacao:
    subclasse = normalizar_cnae(cnae)
    regras, faixa_padrao, _ = carregar_regras()
    candidatas = [r for r in regras if subclasse.startswith(r.prefixo)]
    if not candidatas:
        return Classificacao(subclasse, faixa_padrao, None)
    vencedora = max(candidatas, key=lambda r: len(r.prefixo))
    return Classificacao(subclasse, vencedora.faixa, vencedora)


@dataclass(frozen=True)
class AvaliacaoCnae:
    faixa_principal: str
    melhor_faixa: str
    alerta_cnae: str | None
    alerta_religiosa: str | None


def avaliar_entidade(
    natureza_juridica: int, cnae_principal: str | int, cnaes_secundarios: list[str | int]
) -> AvaliacaoCnae:
    """Verificação 4 (cap. 7.4) + regra separada do art. 2º, I, c.

    Alerta CNAE: nenhum CNAE (principal ou secundário) em ALTA ou MEDIA.
    Alerta religiosa: (natureza 322-0 OU CNAE principal 94.91-0) E nenhum CNAE em ALTA.
    """
    principal = classificar(cnae_principal)
    todos = [principal, *(classificar(c) for c in cnaes_secundarios)]
    faixas = {c.faixa for c in todos}
    melhor = next(f for f in FAIXAS if f in faixas)

    alerta_cnae = None
    if melhor == "BAIXA":
        alerta_cnae = (
            "Nenhuma atividade cadastrada tem relação direta com relevância social; confira o estatuto."
        )

    eh_religiosa = (
        natureza_juridica == NATUREZA_ORGANIZACAO_RELIGIOSA or principal.subclasse == SUBCLASSE_RELIGIOSA
    )
    alerta_religiosa = None
    if eh_religiosa and "ALTA" not in faixas:
        alerta_religiosa = (
            "Organização religiosa sem atividade social de alta aderência no CNAE: a Lei 13.019/2014, "
            "art. 2º, I, c, exige atividades de interesse público e de cunho social distintas das "
            "exclusivamente religiosas; confira estatuto e plano de trabalho."
        )

    return AvaliacaoCnae(principal.faixa, melhor, alerta_cnae, alerta_religiosa)


# -------------------------------------------------------------------- script


def gerar_csv() -> Counter:
    subclasses = carregar_ibge()["subclasses"]
    contagem: Counter = Counter()
    with ARQ_CSV.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["subclasse", "subclasse_formatada", "descricao", "faixa", "regra_aplicada"])
        for item in subclasses:
            c = classificar(item["id"])
            contagem[c.faixa] += 1
            escritor.writerow([c.subclasse, formatar_prefixo(c.subclasse), item["descricao"], c.faixa, c.regra_aplicada])
    return contagem


def main() -> None:
    contagem = gerar_csv()
    total = sum(contagem.values())
    print(f"Gerado {ARQ_CSV} com {total} subclasses")
    for faixa in FAIXAS:
        print(f"  {faixa}: {contagem[faixa]}")


if __name__ == "__main__":
    main()
