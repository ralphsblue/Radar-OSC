import re
import unicodedata
from datetime import date

from pydantic import BaseModel, ConfigDict, ValidationError

TAMANHO_CNAE = 7
_VALORES_NULOS = frozenset({"", "0"})
_DATA_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")


class ErroFormato(ValueError):
    pass


class ModeloBruto(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True, frozen=True)


def validar[M: ModeloBruto](modelo: type[M], corpo: bytes, rotulo: str) -> M:
    try:
        return modelo.model_validate_json(corpo)
    except ValidationError as erro:
        detalhes = "; ".join(
            f"{'.'.join(str(parte) for parte in item['loc']) or '(raiz)'}: {item['msg']}"
            for item in erro.errors(include_url=False, include_input=False)
        )
        raise ErroFormato(f"{rotulo}: resposta fora do formato esperado ({detalhes})") from erro


def chave(valor: str) -> str:
    return unicodedata.normalize("NFC", valor).strip().casefold()


def texto(valor: str | None) -> str | None:
    if valor is None:
        return None
    limpo = valor.strip()
    return limpo or None


def data_iso(valor: str, campo: str, rotulo: str) -> date:
    limpo = valor.strip()
    if _DATA_ISO.fullmatch(limpo) is None:
        raise ErroFormato(f"{rotulo}: {campo} com data inválida {limpo!r}")
    try:
        return date.fromisoformat(limpo)
    except ValueError as erro:
        raise ErroFormato(f"{rotulo}: {campo} com data inválida {limpo!r}") from erro


def cnae(valor: str | int, campo: str, rotulo: str) -> str | None:
    limpo = str(valor).strip()
    if limpo in _VALORES_NULOS:
        return None
    if not limpo.isdecimal() or len(limpo) > TAMANHO_CNAE:
        raise ErroFormato(f"{rotulo}: {campo} inválido {limpo!r}")
    return limpo.zfill(TAMANHO_CNAE)


def cnaes(valores: list[str | int], campo: str, rotulo: str) -> tuple[str, ...]:
    normalizados = (cnae(valor, campo, rotulo) for valor in valores)
    return tuple(codigo for codigo in normalizados if codigo is not None)
