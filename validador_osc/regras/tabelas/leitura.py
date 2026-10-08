import json
from collections.abc import Mapping
from enum import StrEnum
from importlib.resources import files


class ErroTabela(ValueError):
    pass


def ler_json(nome: str) -> object:
    texto = files("validador_osc").joinpath("dados", nome).read_text(encoding="utf-8")
    resultado: object = json.loads(texto)
    return resultado


def ler_enum[E: StrEnum](tipo: type[E], valor: object, onde: str) -> E:
    texto = ler_texto(valor, onde)
    try:
        return tipo(texto)
    except ValueError:
        raise ErroTabela(f"{onde}: valor inválido {texto!r}") from None


def ler_objeto(valor: object, onde: str) -> Mapping[str, object]:
    if not isinstance(valor, dict):
        raise ErroTabela(f"{onde}: esperado objeto JSON")
    return {str(chave): item for chave, item in valor.items()}


def ler_lista(valor: object, onde: str) -> list[object]:
    if not isinstance(valor, list):
        raise ErroTabela(f"{onde}: esperada lista JSON")
    return list(valor)


def ler_texto(valor: object, onde: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ErroTabela(f"{onde}: esperado texto não vazio")
    return valor
