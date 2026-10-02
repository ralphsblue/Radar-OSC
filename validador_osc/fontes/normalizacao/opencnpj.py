from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from pydantic import Field

from validador_osc.dominio.tipos import Cadastro, Dirigente, SituacaoCadastral
from validador_osc.fontes.normalizacao.comum import (
    ErroFormato,
    ModeloBruto,
    chave,
    cnae,
    cnaes,
    data_iso,
    texto,
    validar,
)

__all__ = ["ErroFormato", "extrair_data_base", "normalizar_cadastro"]

FONTE = "opencnpj"
ROTULO = "OpenCNPJ"
_FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")
_DATAS_NULAS = frozenset({"", "0"})
_SITUACOES = {
    "ativa": SituacaoCadastral.ATIVA,
    "baixada": SituacaoCadastral.BAIXADA,
    "inapta": SituacaoCadastral.INAPTA,
    "suspensa": SituacaoCadastral.SUSPENSA,
    "nula": SituacaoCadastral.NULA,
}
_MATRIZ_FILIAL = {"matriz": True, "filial": False}
_PESSOA_FISICA = "pessoa física"


class _CodigoDescricao(ModeloBruto):
    codigo: str | int = ""
    descricao: str = ""


class _Socio(ModeloBruto):
    nome_socio: str
    cnpj_cpf_socio: str = ""
    qualificacao_socio: str = ""
    data_entrada_sociedade: str = ""
    identificador_socio: str = ""


class _Estabelecimento(ModeloBruto):
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


class _Info(ModeloBruto):
    last_updated: str = ""


def normalizar_cadastro(corpo: bytes, data_base: date | None) -> Cadastro:
    bruto = validar(_Estabelecimento, corpo, ROTULO)
    motivo = bruto.motivo_situacao_cadastral
    return Cadastro(
        cnpj=bruto.cnpj.strip().upper(),
        razao_social=bruto.razao_social.strip(),
        nome_fantasia=texto(bruto.nome_fantasia),
        situacao=_situacao(bruto.situacao_cadastral),
        situacao_data=_data(bruto.data_situacao_cadastral, "data_situacao_cadastral"),
        motivo_codigo=_motivo_codigo(motivo.codigo) if motivo is not None else None,
        motivo_descricao=texto(motivo.descricao) if motivo is not None else None,
        matriz=_matriz(bruto.matriz_filial),
        natureza_codigo=None,
        natureza_descricao=texto(bruto.natureza_juridica),
        cnae_principal=cnae(bruto.cnae_principal, "cnae_principal", ROTULO),
        cnaes_secundarios=cnaes(bruto.cnaes_secundarios, "cnaes_secundarios", ROTULO),
        data_inicio=_data(bruto.data_inicio_atividade, "data_inicio_atividade"),
        uf=texto(bruto.uf),
        municipio=texto(bruto.municipio),
        qsa=tuple(_dirigente(socio) for socio in bruto.qsa or ()),
        fonte=FONTE,
        data_base=data_base,
    )


def extrair_data_base(corpo_info: bytes) -> date | None:
    valor = validar(_Info, corpo_info, ROTULO).last_updated.strip()
    if not valor:
        return None
    try:
        instante = datetime.fromisoformat(valor)
    except ValueError as erro:
        raise ErroFormato(f"OpenCNPJ /info: last_updated inválido {valor!r}") from erro
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=UTC)
    return instante.astimezone(_FUSO_BRASILIA).date()


def _situacao(valor: str) -> SituacaoCadastral:
    situacao = _SITUACOES.get(chave(valor))
    if situacao is None:
        raise ErroFormato(f"OpenCNPJ: situacao_cadastral desconhecida {valor!r}")
    return situacao


def _matriz(valor: str) -> bool:
    matriz = _MATRIZ_FILIAL.get(chave(valor))
    if matriz is None:
        raise ErroFormato(f"OpenCNPJ: matriz_filial desconhecido {valor!r}")
    return matriz


def _data(valor: str, campo: str) -> date | None:
    if valor.strip() in _DATAS_NULAS:
        return None
    return data_iso(valor, campo, ROTULO)


def _motivo_codigo(valor: str | int) -> int | None:
    limpo = str(valor).strip()
    if not limpo:
        return None
    if not limpo.isdecimal():
        raise ErroFormato(f"OpenCNPJ: motivo_situacao_cadastral.codigo inválido {limpo!r}")
    return int(limpo)


def _dirigente(socio: _Socio) -> Dirigente:
    return Dirigente(
        nome=socio.nome_socio.strip(),
        qualificacao=texto(socio.qualificacao_socio),
        data_entrada=_data(socio.data_entrada_sociedade, "QSA.data_entrada_sociedade"),
        documento_mascarado=texto(socio.cnpj_cpf_socio),
        pessoa_fisica=chave(socio.identificador_socio) == _PESSOA_FISICA,
    )
