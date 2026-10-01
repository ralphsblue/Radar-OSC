import re
from collections.abc import Callable, Mapping
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from jinja2 import Environment

from validador_osc.dominio.resultado import Esfera, Estado, StatusFinal, TipoVerificacao

_CNPJ = re.compile(r"([0-9A-Z]{2})([0-9A-Z]{3})([0-9A-Z]{3})([0-9A-Z]{4})([0-9]{2})")

_STATUS: Mapping[str, tuple[str, str]] = {
    StatusFinal.CNPJ_INVALIDO: ("CNPJ inválido", "O CNPJ digitado não é válido. Confira os números."),
    StatusFinal.INAPTA: ("Inapta", "Não pode firmar parceria no estado atual."),
    StatusFinal.INCONCLUSIVA: (
        "Inconclusiva",
        "Alguma verificação eliminatória não pôde ser feita. "
        "Tente de novo ou verifique manualmente a fonte indicada.",
    ),
    StatusFinal.APTA_COM_RESSALVAS: (
        "Apta com ressalvas",
        "Apta nos cadastros, mas há pontos para conferir.",
    ),
    StatusFinal.APTA: ("Apta", "Nada consta nos cadastros públicos verificados."),
}

_ESTADOS: Mapping[str, str] = {
    Estado.OK: "OK",
    Estado.RESTRICAO: "Restrição",
    Estado.ALERTA: "Alerta",
    Estado.INDISPONIVEL: "Indisponível",
    Estado.NAO_VERIFICADO: "Não verificado",
}

_TIPOS: Mapping[str, tuple[str, str]] = {
    TipoVerificacao.ELIMINATORIA: (
        "Eliminatórias",
        "Uma restrição aqui impede a parceria.",
    ),
    TipoVerificacao.ALERTA: (
        "De alerta",
        "Pedem revisão humana, sem reprovar a entidade.",
    ),
    TipoVerificacao.INFORMATIVA: (
        "Informativas",
        "Contexto para quem analisa a parceria.",
    ),
}

_ESFERAS: Mapping[str, str] = {
    Esfera.MUNICIPIO: "Município",
    Esfera.ESTADO: "Estado ou Distrito Federal",
    Esfera.UNIAO: "União",
}

_SITUACOES: Mapping[str, str] = {
    "ATIVO": "Ativo",
    "EM_RENOVACAO": "Em renovação",
    "NAO_VIGENTE": "Não vigente",
    "PEDIDO_EM_ANALISE": "Pedido em análise",
    "NAO_ENCONTRADO": "Não encontrado",
    "PREENCHIDO": "Perfil preenchido",
    "AUTOMATICO": "Perfil automático",
    "AUSENTE": "Ausente",
}

_FONTES: Mapping[str, str] = {
    "opencnpj": "OpenCNPJ",
    "brasilapi": "BrasilAPI",
    "portal_transparencia": "Portal da Transparência",
    "cgu_cepim": "CEPIM (CGU)",
    "cgu_ceis": "CEIS (CGU)",
    "cgu_cnep": "CNEP (CGU)",
    "tcu": "TCU",
    "tcu_consolidada": "Consulta Consolidada (TCU)",
    "tce_sp": "TCE-SP",
    "mapa_osc": "Mapa das OSCs (Ipea)",
    "siscebas_saude": "SisCEBAS Saúde",
    "cebas_mds": "CEBAS (MDS)",
    "cebas_mec": "CEBAS (MEC)",
    "dou": "Diário Oficial da União",
}


def _texto(valor: object) -> str:
    return "" if valor is None else str(valor)


def rotulo_status(status: object) -> str:
    return _STATUS.get(_texto(status), (_texto(status), ""))[0]


def descricao_status(status: object) -> str:
    return _STATUS.get(_texto(status), ("", ""))[1]


def rotulo_estado(estado: object) -> str:
    return _ESTADOS.get(_texto(estado), _texto(estado))


def rotulo_tipo(tipo: object) -> str:
    return _TIPOS.get(_texto(tipo), (_texto(tipo), ""))[0]


def descricao_tipo(tipo: object) -> str:
    return _TIPOS.get(_texto(tipo), ("", ""))[1]


def rotulo_esfera(esfera: object) -> str:
    return _ESFERAS.get(_texto(esfera), "Não informada")


def rotulo_situacao(situacao: object) -> str:
    texto = _texto(situacao)
    return _SITUACOES.get(texto, texto.replace("_", " ").capitalize())


def nome_fonte(fonte: object) -> str:
    texto = _texto(fonte)
    return _FONTES.get(texto, texto)


def formatar_cnpj(cnpj: object) -> str:
    texto = _texto(cnpj)
    encontrado = _CNPJ.fullmatch(texto)
    if encontrado is None:
        return texto
    a, b, c, d, dv = encontrado.groups()
    return f"{a}.{b}.{c}/{d}-{dv}"


def formatar_data(valor: date | str | None) -> str:
    if valor is None or valor == "":
        return ""
    if isinstance(valor, str):
        valor = date.fromisoformat(valor[:10])
    return f"{valor:%d/%m/%Y}"


def criar_formatar_instante(fuso: ZoneInfo) -> Callable[[datetime | str | None], str]:
    def formatar_instante(valor: datetime | str | None) -> str:
        if valor is None or valor == "":
            return ""
        if isinstance(valor, str):
            valor = datetime.fromisoformat(valor)
        if valor.tzinfo is not None:
            valor = valor.astimezone(fuso)
        return f"{valor:%d/%m/%Y} às {valor:%H:%M}"

    return formatar_instante


def registrar_filtros(ambiente: Environment, fuso: ZoneInfo) -> None:
    filtros: dict[str, Callable[..., Any]] = {
        "rotulo_status": rotulo_status,
        "descricao_status": descricao_status,
        "rotulo_estado": rotulo_estado,
        "rotulo_tipo": rotulo_tipo,
        "descricao_tipo": descricao_tipo,
        "rotulo_esfera": rotulo_esfera,
        "rotulo_situacao": rotulo_situacao,
        "nome_fonte": nome_fonte,
        "cnpj": formatar_cnpj,
        "data": formatar_data,
        "instante": criar_formatar_instante(fuso),
    }
    ambiente.filters.update(filtros)
