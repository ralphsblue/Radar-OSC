import json
from collections.abc import Mapping

from validador_osc.dominio.tipos import PerfilMapa
from validador_osc.fontes.normalizacao.comum import ErroFormato

AUTODECLARACAO = "representante de osc"
PREFIXOS_VALOR = ("tx", "nr", "dt", "cd")
CNPJ_DIGITOS = 14


def _json(corpo: bytes, onde: str) -> object:
    try:
        valor: object = json.loads(corpo)
    except ValueError as erro:
        raise ErroFormato(f"{onde}: JSON inválido") from erro
    return valor


def _objeto(valor: object, onde: str) -> Mapping[str, object]:
    if not isinstance(valor, dict):
        raise ErroFormato(f"{onde}: esperado objeto")
    return valor


def _preenchido(valor: object) -> bool:
    if valor is None:
        return False
    if isinstance(valor, str):
        return bool(valor.strip())
    return True


def localizar_osc(corpo: bytes, cnpj: str) -> tuple[int, int | None] | None:
    itens = _json(corpo, "busca/cnpj")
    if not isinstance(itens, list):
        raise ErroFormato("busca/cnpj: esperada lista")
    for item in itens:
        registro = _objeto(item, "busca/cnpj[]")
        identificador = str(registro.get("cd_identificador_osc") or "").zfill(CNPJ_DIGITOS)
        if identificador != cnpj:
            continue
        id_osc = registro.get("id_osc")
        if isinstance(id_osc, bool) or not isinstance(id_osc, int):
            raise ErroFormato("busca/cnpj: id_osc ausente")
        situacao = registro.get("cd_situacao_cadastral")
        return id_osc, situacao if isinstance(situacao, int) and not isinstance(situacao, bool) else None
    return None


def _campos_autodeclarados_dados_gerais(bruto: Mapping[str, object]) -> list[str]:
    campos = []
    for chave, fonte in bruto.items():
        if not chave.startswith("ft_") or not isinstance(fonte, str):
            continue
        if fonte.strip().casefold() != AUTODECLARACAO:
            continue
        nome = chave.removeprefix("ft_")
        valores = [bruto.get(f"{prefixo}_{nome}") for prefixo in PREFIXOS_VALOR]
        if any(_preenchido(v) for v in valores):
            campos.append(f"dados_gerais.{nome}")
    return campos


def _campos_descricao(bruto: Mapping[str, object]) -> list[str]:
    return [
        f"descricao.{chave.removeprefix('tx_')}"
        for chave, v in bruto.items()
        if chave.startswith("tx_") and _preenchido(v)
    ]


def _indice(bruto: Mapping[str, object]) -> float | None:
    valor = bruto.get("transparencia_osc")
    if isinstance(valor, bool) or not isinstance(valor, int | float | str):
        return None
    try:
        return float(valor)
    except ValueError:
        return None


def normalizar_perfil(
    id_osc: int,
    cnpj: str,
    situacao_cadastral: int | None,
    dados_gerais: bytes,
    descricao: bytes,
    areas_rep: bytes,
    indice: bytes,
) -> PerfilMapa:
    campos = _campos_autodeclarados_dados_gerais(_objeto(_json(dados_gerais, "dados_gerais"), "dados_gerais"))
    campos += _campos_descricao(_objeto(_json(descricao, "descricao"), "descricao"))
    areas = _json(areas_rep, "areas_atuacao_rep")
    if isinstance(areas, list) and areas:
        campos.append("areas_atuacao_rep")
    elif not isinstance(areas, list | dict):
        raise ErroFormato("areas_atuacao_rep: formato inesperado")
    return PerfilMapa(
        id_osc=id_osc,
        cnpj=cnpj,
        situacao_cadastral=situacao_cadastral,
        indice_preenchimento=_indice(_objeto(_json(indice, "indice_preenchimento"), "indice_preenchimento")),
        campos_autodeclarados=tuple(sorted(campos)),
    )
