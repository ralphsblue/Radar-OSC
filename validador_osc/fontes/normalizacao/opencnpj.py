import re
import unicodedata
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from validador_osc.dominio.tipos import Cadastro, Dirigente, SituacaoCadastral

FONTE = "opencnpj"
_FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")
_TAMANHO_CNAE = 7
_VALORES_NULOS = frozenset({"", "0"})
_DATA_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
_SITUACOES = {
    "ativa": SituacaoCadastral.ATIVA,
    "baixada": SituacaoCadastral.BAIXADA,
    "inapta": SituacaoCadastral.INAPTA,
    "suspensa": SituacaoCadastral.SUSPENSA,
    "nula": SituacaoCadastral.NULA,
}
_MATRIZ_FILIAL = {"matriz": True, "filial": False}
_PESSOA_FISICA = "pessoa física"


class ErroFormato(ValueError):
    pass


class _Modelo(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True, frozen=True)


class _CodigoDescricao(_Modelo):
    codigo: str | int = ""
    descricao: str = ""


class _Socio(_Modelo):
    nome_socio: str
    cnpj_cpf_socio: str = ""
    qualificacao_socio: str = ""
    data_entrada_sociedade: str = ""
    identificador_socio: str = ""


class _Estabelecimento(_Modelo):
    cnpj: str
    razao_social: str
    nome_fantasia: str = ""
    situacao_cadastral: str
    data_situacao_cadastral: str = ""
    motivo_situacao_cadastral: _CodigoDescricao | None = None
    matriz_filial: str
    natureza_juridica: str = ""
    cnae_principal: str | int = ""
    cnaes_secundarios: list[str | int] = Field(default_factory=list)
    data_inicio_atividade: str = ""
    uf: str = ""
    municipio: str = ""
    qsa: list[_Socio] | None = Field(default=None, alias="QSA")


class _Info(_Modelo):
    last_updated: str = ""


def normalizar_cadastro(corpo: bytes, data_base: date | None) -> Cadastro:
    bruto = _validar(_Estabelecimento, corpo)
    motivo = bruto.motivo_situacao_cadastral
    return Cadastro(
        cnpj=bruto.cnpj.strip().upper(),
        razao_social=bruto.razao_social.strip(),
        nome_fantasia=_texto(bruto.nome_fantasia),
        situacao=_situacao(bruto.situacao_cadastral),
        situacao_data=_data(bruto.data_situacao_cadastral, "data_situacao_cadastral"),
        motivo_codigo=_motivo_codigo(motivo.codigo) if motivo is not None else None,
        motivo_descricao=_texto(motivo.descricao) if motivo is not None else None,
        matriz=_matriz(bruto.matriz_filial),
        natureza_codigo=None,
        natureza_descricao=_texto(bruto.natureza_juridica),
        cnae_principal=_cnae(bruto.cnae_principal, "cnae_principal"),
        cnaes_secundarios=_cnaes_secundarios(bruto.cnaes_secundarios),
        data_inicio=_data(bruto.data_inicio_atividade, "data_inicio_atividade"),
        uf=_texto(bruto.uf),
        municipio=_texto(bruto.municipio),
        qsa=tuple(_dirigente(socio) for socio in bruto.qsa or ()),
        fonte=FONTE,
        data_base=data_base,
    )


def extrair_data_base(corpo_info: bytes) -> date | None:
    texto = _validar(_Info, corpo_info).last_updated.strip()
    if not texto:
        return None
    try:
        instante = datetime.fromisoformat(texto)
    except ValueError as erro:
        raise ErroFormato(f"OpenCNPJ /info: last_updated inválido {texto!r}") from erro
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=UTC)
    return instante.astimezone(_FUSO_BRASILIA).date()


def _validar[M: _Modelo](modelo: type[M], corpo: bytes) -> M:
    try:
        return modelo.model_validate_json(corpo)
    except ValidationError as erro:
        detalhes = "; ".join(
            f"{'.'.join(str(parte) for parte in item['loc']) or '(raiz)'}: {item['msg']}"
            for item in erro.errors(include_url=False, include_input=False)
        )
        raise ErroFormato(f"OpenCNPJ: resposta fora do formato esperado ({detalhes})") from erro


def _chave(valor: str) -> str:
    return unicodedata.normalize("NFC", valor).strip().casefold()


def _texto(valor: str) -> str | None:
    limpo = valor.strip()
    return limpo or None


def _situacao(valor: str) -> SituacaoCadastral:
    situacao = _SITUACOES.get(_chave(valor))
    if situacao is None:
        raise ErroFormato(f"OpenCNPJ: situacao_cadastral desconhecida {valor!r}")
    return situacao


def _matriz(valor: str) -> bool:
    matriz = _MATRIZ_FILIAL.get(_chave(valor))
    if matriz is None:
        raise ErroFormato(f"OpenCNPJ: matriz_filial desconhecido {valor!r}")
    return matriz


def _data(valor: str, campo: str) -> date | None:
    texto = valor.strip()
    if texto in _VALORES_NULOS:
        return None
    if _DATA_ISO.fullmatch(texto) is None:
        raise ErroFormato(f"OpenCNPJ: {campo} com data inválida {texto!r}")
    try:
        return date.fromisoformat(texto)
    except ValueError as erro:
        raise ErroFormato(f"OpenCNPJ: {campo} com data inválida {texto!r}") from erro


def _motivo_codigo(valor: str | int) -> int | None:
    texto = str(valor).strip()
    if not texto:
        return None
    if not texto.isdecimal():
        raise ErroFormato(f"OpenCNPJ: motivo_situacao_cadastral.codigo inválido {texto!r}")
    return int(texto)


def _cnae(valor: str | int, campo: str) -> str | None:
    texto = str(valor).strip()
    if texto in _VALORES_NULOS:
        return None
    if not texto.isdecimal() or len(texto) > _TAMANHO_CNAE:
        raise ErroFormato(f"OpenCNPJ: {campo} inválido {texto!r}")
    return texto.zfill(_TAMANHO_CNAE)


def _cnaes_secundarios(valores: list[str | int]) -> tuple[str, ...]:
    cnaes = (_cnae(valor, "cnaes_secundarios") for valor in valores)
    return tuple(cnae for cnae in cnaes if cnae is not None)


def _dirigente(socio: _Socio) -> Dirigente:
    return Dirigente(
        nome=socio.nome_socio.strip(),
        qualificacao=_texto(socio.qualificacao_socio),
        data_entrada=_data(socio.data_entrada_sociedade, "QSA.data_entrada_sociedade"),
        documento_mascarado=_texto(socio.cnpj_cpf_socio),
        pessoa_fisica=_chave(socio.identificador_socio) == _PESSOA_FISICA,
    )
