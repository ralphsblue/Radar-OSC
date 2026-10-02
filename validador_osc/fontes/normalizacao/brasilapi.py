from datetime import date

from validador_osc.dominio.tipos import Cadastro, Dirigente, SituacaoCadastral
from validador_osc.fontes.normalizacao.comum import (
    ErroFormato,
    ModeloBruto,
    cnae,
    cnaes,
    data_iso,
    texto,
    validar,
)

__all__ = ["ErroFormato", "normalizar_cadastro"]

FONTE = "brasilapi"
ROTULO = "BrasilAPI"
_MATRIZ_FILIAL = {1: True, 2: False}
_SOCIO_PESSOA_FISICA = 2
_NATUREZA_MINIMA = 1000
_NATUREZA_MAXIMA = 9999


class _CnaeSecundario(ModeloBruto):
    codigo: int | str


class _Socio(ModeloBruto):
    nome_socio: str
    cnpj_cpf_do_socio: str | None = None
    qualificacao_socio: str | None = None
    data_entrada_sociedade: str | None = None
    identificador_de_socio: int | None = None


class _Estabelecimento(ModeloBruto):
    cnpj: str
    razao_social: str
    nome_fantasia: str | None = None
    situacao_cadastral: int
    data_situacao_cadastral: str | None = None
    motivo_situacao_cadastral: int | None = None
    descricao_motivo_situacao_cadastral: str | None = None
    identificador_matriz_filial: int
    codigo_natureza_juridica: int | None = None
    natureza_juridica: str | None = None
    cnae_fiscal: int | str | None = None
    cnaes_secundarios: list[_CnaeSecundario] | None = None
    data_inicio_atividade: str | None = None
    uf: str | None = None
    municipio: str | None = None
    qsa: list[_Socio] | None = None


def normalizar_cadastro(corpo: bytes) -> Cadastro:
    bruto = validar(_Estabelecimento, corpo, ROTULO)
    return Cadastro(
        cnpj=bruto.cnpj.strip().upper(),
        razao_social=bruto.razao_social.strip(),
        nome_fantasia=texto(bruto.nome_fantasia),
        situacao=_situacao(bruto.situacao_cadastral),
        situacao_data=_data(bruto.data_situacao_cadastral, "data_situacao_cadastral"),
        motivo_codigo=_motivo_codigo(bruto.motivo_situacao_cadastral),
        motivo_descricao=texto(bruto.descricao_motivo_situacao_cadastral),
        matriz=_matriz(bruto.identificador_matriz_filial),
        natureza_codigo=_natureza_codigo(bruto.codigo_natureza_juridica),
        natureza_descricao=texto(bruto.natureza_juridica),
        cnae_principal=_cnae_principal(bruto.cnae_fiscal),
        cnaes_secundarios=cnaes(
            [item.codigo for item in bruto.cnaes_secundarios or ()], "cnaes_secundarios", ROTULO
        ),
        data_inicio=_data(bruto.data_inicio_atividade, "data_inicio_atividade"),
        uf=texto(bruto.uf),
        municipio=texto(bruto.municipio),
        qsa=tuple(_dirigente(socio) for socio in bruto.qsa or ()),
        fonte=FONTE,
        data_base=None,
    )


def _situacao(valor: int) -> SituacaoCadastral:
    try:
        return SituacaoCadastral(valor)
    except ValueError as erro:
        raise ErroFormato(f"BrasilAPI: situacao_cadastral desconhecida {valor!r}") from erro


def _matriz(valor: int) -> bool:
    matriz = _MATRIZ_FILIAL.get(valor)
    if matriz is None:
        raise ErroFormato(f"BrasilAPI: identificador_matriz_filial desconhecido {valor!r}")
    return matriz


def _data(valor: str | None, campo: str) -> date | None:
    if valor is None or not valor.strip():
        return None
    return data_iso(valor, campo, ROTULO)


def _motivo_codigo(valor: int | None) -> int | None:
    if valor is None:
        return None
    if valor < 0:
        raise ErroFormato(f"BrasilAPI: motivo_situacao_cadastral inválido {valor!r}")
    return valor


def _natureza_codigo(valor: int | None) -> int | None:
    if valor is None:
        return None
    if not _NATUREZA_MINIMA <= valor <= _NATUREZA_MAXIMA:
        raise ErroFormato(f"BrasilAPI: codigo_natureza_juridica inválido {valor!r}")
    return valor


def _cnae_principal(valor: int | str | None) -> str | None:
    if valor is None:
        return None
    return cnae(valor, "cnae_fiscal", ROTULO)


def _dirigente(socio: _Socio) -> Dirigente:
    return Dirigente(
        nome=socio.nome_socio.strip(),
        qualificacao=texto(socio.qualificacao_socio),
        data_entrada=_data(socio.data_entrada_sociedade, "qsa.data_entrada_sociedade"),
        documento_mascarado=texto(socio.cnpj_cpf_do_socio),
        pessoa_fisica=socio.identificador_de_socio == _SOCIO_PESSOA_FISICA,
    )
