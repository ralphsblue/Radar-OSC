import re
from datetime import date

from pydantic import Field

from validador_osc.dominio.sancoes import (
    CertidaoTcu,
    RespostaTcu,
    SituacaoCertidaoTcu,
    TipoCertidaoTcu,
)
from validador_osc.fontes.normalizacao.comum import ErroFormato, ModeloBruto, chave, texto, validar

__all__ = ["ErroFormato", "normalizar_certidoes"]

ROTULO = "TCU"
CNPJ_NAO_ENCONTRADO = "CNPJ_NAO_ENCONTRADO_NO_TCU"
_TIPOS = {
    (chave("TCU"), chave("Inidôneos")): TipoCertidaoTcu.INIDONEOS,
    (chave("CNJ"), chave("CNIA")): TipoCertidaoTcu.CNIA,
    (chave("Portal da Transparência"), chave("CEIS")): TipoCertidaoTcu.CEIS,
    (chave("Portal da Transparência"), chave("CNEP")): TipoCertidaoTcu.CNEP,
}
_SITUACOES = {
    "NADA_CONSTA": SituacaoCertidaoTcu.NADA_CONSTA,
    "CONSTAM_REGISTROS": SituacaoCertidaoTcu.CONSTAM_REGISTROS,
    "ERRO": SituacaoCertidaoTcu.INDISPONIVEL,
    "SISTEMA_INDISPONIVEL": SituacaoCertidaoTcu.INDISPONIVEL,
    "ALFANUMERICO_NAO_SUPORTADO": SituacaoCertidaoTcu.NAO_SUPORTADO,
    CNPJ_NAO_ENCONTRADO: SituacaoCertidaoTcu.NADA_CONSTA,
}
_DATA_ENTRE_PARENTESES = re.compile(r"\(\s*(\d{2})/(\d{2})/(\d{4})\s*\)")
_PROCESSO_CNJ = re.compile(r"(?<![\d.-])(?:\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}|\d{10,25})(?![\d.-])")
_CNPJ = re.compile(r"[0-9A-Z]{12}\d{2}")
_PONTUACAO_CNPJ = re.compile(r"[./-]")


class _Certidao(ModeloBruto):
    emissor: str
    tipo: str
    situacao: str
    observacao: str | None = None
    link_consulta_manual: str | None = Field(default=None, alias="linkConsultaManual")


class _Resposta(ModeloBruto):
    cnpj: str
    razao_social: str | None = Field(default=None, alias="razaoSocial")
    encontrado: bool = Field(alias="seCnpjEncontradoNaBaseTcu")
    certidoes: list[_Certidao] = Field(min_length=1)


def normalizar_certidoes(corpo: bytes) -> RespostaTcu:
    bruto = validar(_Resposta, corpo, ROTULO)
    certidoes = tuple(_certidao(item) for item in bruto.certidoes)
    tipos = [certidao.tipo for certidao in certidoes]
    repetidos = sorted({tipo for tipo in tipos if tipos.count(tipo) > 1})
    if repetidos:
        raise ErroFormato(f"{ROTULO}: certidões repetidas {', '.join(repetidos)}")
    nao_encontrado = any(item.situacao.strip() == CNPJ_NAO_ENCONTRADO for item in bruto.certidoes)
    return RespostaTcu(
        cnpj=_cnpj(bruto.cnpj),
        razao_social=texto(bruto.razao_social),
        cnpj_encontrado=bruto.encontrado and not nao_encontrado,
        certidoes=certidoes,
    )


def _cnpj(valor: str) -> str:
    limpo = _PONTUACAO_CNPJ.sub("", valor.strip()).upper()
    if _CNPJ.fullmatch(limpo) is None:
        raise ErroFormato(f"{ROTULO}: cnpj inválido {valor!r}")
    return limpo


def _certidao(item: _Certidao) -> CertidaoTcu:
    tipo = _tipo(item.emissor, item.tipo)
    observacao = texto(item.observacao)
    return CertidaoTcu(
        tipo=tipo,
        situacao=_situacao(item.situacao),
        observacao=observacao,
        datas_observacao=_datas(observacao),
        processos=_processos(observacao) if tipo is TipoCertidaoTcu.CNIA else (),
        link_manual=texto(item.link_consulta_manual),
    )


def _tipo(emissor: str, tipo: str) -> TipoCertidaoTcu:
    encontrado = _TIPOS.get((chave(emissor), chave(tipo)))
    if encontrado is None:
        raise ErroFormato(f"{ROTULO}: certidão desconhecida (emissor {emissor!r}, tipo {tipo!r})")
    return encontrado


def _situacao(valor: str) -> SituacaoCertidaoTcu:
    situacao = _SITUACOES.get(valor.strip())
    if situacao is None:
        raise ErroFormato(f"{ROTULO}: situacao desconhecida {valor!r}")
    return situacao


def _datas(observacao: str | None) -> tuple[date, ...]:
    if observacao is None:
        return ()
    return tuple(_data(*grupos) for grupos in _DATA_ENTRE_PARENTESES.findall(observacao))


def _data(dia: str, mes: str, ano: str) -> date:
    try:
        return date(int(ano), int(mes), int(dia))
    except ValueError as erro:
        raise ErroFormato(f"{ROTULO}: observacao com data inválida {dia}/{mes}/{ano}") from erro


def _processos(observacao: str | None) -> tuple[str, ...]:
    if observacao is None:
        return ()
    numeros = (re.sub(r"\D", "", achado) for achado in _PROCESSO_CNJ.findall(observacao))
    return tuple(dict.fromkeys(numeros))
