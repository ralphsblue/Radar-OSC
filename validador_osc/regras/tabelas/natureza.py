import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from types import MappingProxyType

from validador_osc.regras.tabelas.leitura import (
    ErroTabela,
    ler_enum,
    ler_json,
    ler_lista,
    ler_objeto,
    ler_texto,
)

ARQUIVO_NATUREZA = "natureza_juridica.json"

NATUREZA_ORGANIZACAO_RELIGIOSA = 3220
MENOR_CODIGO_NATUREZA = 1000
MAIOR_CODIGO_NATUREZA = 9999

_NAO_ALFANUMERICO = re.compile(r"[\W_]+")
_PESOS_DV_NATUREZA = (4, 3, 2)
_MODULO_DV_NATUREZA = 11


class RegraNatureza(StrEnum):
    ELEGIVEL = "ELEGIVEL"
    ELEGIVEL_COM_ALERTA_RELIGIOSO = "ELEGIVEL_COM_ALERTA_RELIGIOSO"
    REVISAO_MANUAL = "REVISAO_MANUAL"
    NAO_ELEGIVEL = "NAO_ELEGIVEL"


@dataclass(frozen=True, slots=True)
class NaturezaJuridica:
    codigo: int
    codigo_formatado: str
    descricao: str
    sinonimos: tuple[str, ...]
    regra: RegraNatureza
    justificativa: str


@dataclass(frozen=True, slots=True)
class TabelaNatureza:
    versao: str
    naturezas: Mapping[int, NaturezaJuridica]
    por_descricao: Mapping[str, NaturezaJuridica]


def formatar_natureza(codigo: int) -> str:
    radical, digito = divmod(codigo, 10)
    return f"{radical:03d}-{digito}"


def digito_natureza(radical: int) -> int:
    soma = sum(int(d) * p for d, p in zip(f"{radical:03d}", _PESOS_DV_NATUREZA, strict=True))
    resto = soma % _MODULO_DV_NATUREZA
    return 0 if resto <= 1 else _MODULO_DV_NATUREZA - resto


def normalizar_descricao_natureza(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return _NAO_ALFANUMERICO.sub(" ", sem_acento.casefold()).strip()


def resolver_natureza(
    tabela: TabelaNatureza, codigo: int | None, descricao: str | None
) -> NaturezaJuridica | None:
    if codigo is not None and (natureza := tabela.naturezas.get(codigo)) is not None:
        return natureza
    if descricao is None:
        return None
    return tabela.por_descricao.get(normalizar_descricao_natureza(descricao))


def montar_tabela_natureza(bruto: object) -> TabelaNatureza:
    objeto = ler_objeto(bruto, ARQUIVO_NATUREZA)
    itens = ler_lista(objeto.get("naturezas"), f"{ARQUIVO_NATUREZA}.naturezas")
    if not itens:
        raise ErroTabela(f"{ARQUIVO_NATUREZA}.naturezas: lista vazia")
    naturezas: dict[int, NaturezaJuridica] = {}
    por_descricao: dict[str, NaturezaJuridica] = {}
    for indice, item in enumerate(itens):
        natureza = _natureza(item, f"{ARQUIVO_NATUREZA}.naturezas[{indice}]")
        if natureza.codigo in naturezas:
            raise ErroTabela(f"Código de natureza duplicado: {natureza.codigo_formatado}")
        naturezas[natureza.codigo] = natureza
        for texto in (natureza.descricao, *natureza.sinonimos):
            chave = normalizar_descricao_natureza(texto)
            if not chave:
                raise ErroTabela(f"Descrição sem conteúdo após normalizar: {texto!r}")
            if chave in por_descricao:
                raise ErroTabela(
                    f"Descrição {texto!r} de {natureza.codigo_formatado} repete "
                    f"{por_descricao[chave].codigo_formatado}"
                )
            por_descricao[chave] = natureza
    return TabelaNatureza(
        versao=ler_texto(objeto.get("versao"), f"{ARQUIVO_NATUREZA}.versao"),
        naturezas=MappingProxyType(naturezas),
        por_descricao=MappingProxyType(por_descricao),
    )


@cache
def carregar_tabela_natureza() -> TabelaNatureza:
    return montar_tabela_natureza(ler_json(ARQUIVO_NATUREZA))


def _natureza(bruto: object, onde: str) -> NaturezaJuridica:
    objeto = ler_objeto(bruto, onde)
    esperados = {"codigo", "codigo_formatado", "descricao", "sinonimos", "regra", "justificativa"}
    if set(objeto) != esperados:
        raise ErroTabela(f"{onde}: campos esperados {sorted(esperados)}, encontrados {sorted(objeto)}")
    codigo = objeto["codigo"]
    if (
        not isinstance(codigo, int)
        or isinstance(codigo, bool)
        or not MENOR_CODIGO_NATUREZA <= codigo <= MAIOR_CODIGO_NATUREZA
    ):
        raise ErroTabela(f"{onde}.codigo: esperado inteiro de 4 dígitos, encontrado {codigo!r}")
    formatado = ler_texto(objeto["codigo_formatado"], f"{onde}.codigo_formatado")
    if formatado != formatar_natureza(codigo):
        raise ErroTabela(f"{onde}: código formatado {formatado!r} não confere com {codigo}")
    radical, digito = divmod(codigo, 10)
    if digito_natureza(radical) != digito:
        raise ErroTabela(f"{onde}: dígito verificador inválido em {formatado}")
    sinonimos = tuple(
        ler_texto(s, f"{onde}.sinonimos[{i}]")
        for i, s in enumerate(ler_lista(objeto["sinonimos"], f"{onde}.sinonimos"))
    )
    return NaturezaJuridica(
        codigo=codigo,
        codigo_formatado=formatado,
        descricao=ler_texto(objeto["descricao"], f"{onde}.descricao"),
        sinonimos=sinonimos,
        regra=ler_enum(RegraNatureza, objeto["regra"], f"{onde}.regra"),
        justificativa=ler_texto(objeto["justificativa"], f"{onde}.justificativa"),
    )
