import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from functools import cache
from importlib.resources import files
from types import MappingProxyType

ARQUIVO_ORIENTADOR = "regras_orientador.json"
ARQUIVO_LIMITES = "limites.json"


class ErroParametros(ValueError):
    pass


class CnepMulta(StrEnum):
    ALERTA = "alerta"
    RESTRICAO = "restricao"


class AbrangenciaLimitada(StrEnum):
    RESTRICAO = "restricao"
    ALERTA = "alerta"


class CepimEsfera(StrEnum):
    QUALQUER_ESFERA = "qualquer_esfera"
    SO_UNIAO = "so_uniao"


class Cnia(StrEnum):
    VIGENCIA = "vigencia"
    QUALQUER_REGISTRO = "qualquer_registro"


class Raiz(StrEnum):
    RESTRICAO = "restricao"
    ALERTA = "alerta"
    EXATO = "exato"


class ContasIrregulares(StrEnum):
    ALERTA = "alerta"
    RESTRICAO = "restricao"
    NAO_USAR = "nao_usar"


@dataclass(frozen=True, slots=True)
class RegrasOrientador:
    versao: str
    cnep_multa: CnepMulta
    abrangencia_limitada: AbrangenciaLimitada
    cepim: CepimEsfera
    cnia: Cnia
    raiz: Raiz
    contas_irregulares: ContasIrregulares


@dataclass(frozen=True, slots=True)
class Limites:
    versao: str
    idade_maxima: Mapping[str, timedelta]
    idade_maxima_espelho: timedelta
    janela_contas_irregulares_anos: int
    abrangencia_total: frozenset[str]
    categorias_cnep_fora_art39: tuple[str, ...]

    def idade_maxima_de(self, fonte: str) -> timedelta:
        try:
            return self.idade_maxima[fonte]
        except KeyError as erro:
            raise ErroParametros(f"fonte sem idade máxima em {ARQUIVO_LIMITES}: {fonte}") from erro


def _ler(nome: str) -> Mapping[str, object]:
    bruto: object = json.loads(files("validador_osc").joinpath("dados", nome).read_text(encoding="utf-8"))
    if not isinstance(bruto, dict):
        raise ErroParametros(f"{nome}: esperado objeto")
    return bruto


def _objeto(valor: object, onde: str) -> Mapping[str, object]:
    if not isinstance(valor, dict):
        raise ErroParametros(f"{onde}: esperado objeto")
    return valor


def _enum[E: StrEnum](tipo: type[E], regras: Mapping[str, object], chave: str) -> E:
    regra = _objeto(regras.get(chave), f"{ARQUIVO_ORIENTADOR}:{chave}")
    valor = regra.get("valor")
    try:
        return tipo(str(valor))
    except ValueError as erro:
        raise ErroParametros(f"{ARQUIVO_ORIENTADOR}:{chave}: valor inválido {valor!r}") from erro


def montar_regras_orientador(bruto: Mapping[str, object]) -> RegrasOrientador:
    regras = _objeto(bruto.get("regras"), f"{ARQUIVO_ORIENTADOR}:regras")
    return RegrasOrientador(
        versao=str(bruto.get("versao")),
        cnep_multa=_enum(CnepMulta, regras, "Q16_cnep_multa"),
        abrangencia_limitada=_enum(AbrangenciaLimitada, regras, "Q17_abrangencia_limitada"),
        cepim=_enum(CepimEsfera, regras, "Q18_cepim"),
        cnia=_enum(Cnia, regras, "Q19_cnia"),
        raiz=_enum(Raiz, regras, "Q20_raiz"),
        contas_irregulares=_enum(ContasIrregulares, regras, "Q21_contas_irregulares_osc"),
    )


def _inteiro_positivo(valor: object, onde: str) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        raise ErroParametros(f"{onde}: esperado inteiro positivo")
    return valor


def _textos(valor: object, onde: str) -> tuple[str, ...]:
    if not isinstance(valor, list) or not all(isinstance(v, str) for v in valor):
        raise ErroParametros(f"{onde}: esperada lista de textos")
    return tuple(v.casefold() for v in valor)


def montar_limites(bruto: Mapping[str, object]) -> Limites:
    idades = _objeto(bruto.get("idade_maxima_dias"), f"{ARQUIVO_LIMITES}:idade_maxima_dias")
    return Limites(
        versao=str(bruto.get("versao")),
        idade_maxima=MappingProxyType(
            {
                fonte: timedelta(days=_inteiro_positivo(dias, f"{ARQUIVO_LIMITES}:{fonte}"))
                for fonte, dias in idades.items()
            }
        ),
        idade_maxima_espelho=timedelta(
            days=_inteiro_positivo(bruto.get("idade_maxima_espelho_cadastral_dias"), ARQUIVO_LIMITES)
        ),
        janela_contas_irregulares_anos=_inteiro_positivo(
            bruto.get("janela_contas_irregulares_anos"), ARQUIVO_LIMITES
        ),
        abrangencia_total=frozenset(_textos(bruto.get("abrangencia_total"), ARQUIVO_LIMITES)),
        categorias_cnep_fora_art39=_textos(bruto.get("categorias_cnep_fora_art39"), ARQUIVO_LIMITES),
    )


@cache
def carregar_regras_orientador() -> RegrasOrientador:
    return montar_regras_orientador(_ler(ARQUIVO_ORIENTADOR))


@cache
def carregar_limites() -> Limites:
    return montar_limites(_ler(ARQUIVO_LIMITES))
