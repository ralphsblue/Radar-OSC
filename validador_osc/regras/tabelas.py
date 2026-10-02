import json
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from importlib.resources import files
from types import MappingProxyType

from validador_osc.regras.parametros import (
    Limites,
    RegrasOrientador,
    carregar_limites,
    carregar_regras_orientador,
)

ARQUIVO_REGRAS_CNAE = "regras_cnae.json"
ARQUIVO_ESTRUTURA_CNAE = "cnae_subclasses.json"
ARQUIVO_NATUREZA = "natureza_juridica.json"

NATUREZA_ORGANIZACAO_RELIGIOSA = 3220
SUBCLASSE_RELIGIOSA = "9491000"
DIGITOS_SUBCLASSE = 7
DIGITOS_MINIMOS_INFORMADOS = 6
MENOR_CODIGO_NATUREZA = 1000
MAIOR_CODIGO_NATUREZA = 9999

_NAO_DIGITO = re.compile(r"\D")
_NAO_ALFANUMERICO = re.compile(r"[\W_]+")
_PESOS_DV_NATUREZA = (4, 3, 2)
_MODULO_DV_NATUREZA = 11


class ErroTabela(ValueError):
    pass


class Faixa(StrEnum):
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAIXA = "BAIXA"


ORDEM_FAIXAS: tuple[Faixa, ...] = (Faixa.ALTA, Faixa.MEDIA, Faixa.BAIXA)


class NivelCnae(StrEnum):
    DIVISAO = "divisao"
    GRUPO = "grupo"
    CLASSE = "classe"
    SUBCLASSE = "subclasse"

    @property
    def tamanho(self) -> int:
        return _TAMANHO_POR_NIVEL[self]

    @property
    def colecao(self) -> str:
        return _COLECAO_POR_NIVEL[self]


_TAMANHO_POR_NIVEL: Mapping[NivelCnae, int] = MappingProxyType(
    {NivelCnae.DIVISAO: 2, NivelCnae.GRUPO: 3, NivelCnae.CLASSE: 5, NivelCnae.SUBCLASSE: 7}
)
_COLECAO_POR_NIVEL: Mapping[NivelCnae, str] = MappingProxyType(
    {
        NivelCnae.DIVISAO: "divisoes",
        NivelCnae.GRUPO: "grupos",
        NivelCnae.CLASSE: "classes",
        NivelCnae.SUBCLASSE: "subclasses",
    }
)
_NIVEL_POR_TAMANHO: Mapping[int, NivelCnae] = MappingProxyType({n.tamanho: n for n in NivelCnae})
_TAMANHOS_DO_MAIS_ESPECIFICO: tuple[int, ...] = tuple(sorted(_NIVEL_POR_TAMANHO, reverse=True))


@dataclass(frozen=True, slots=True)
class RegraCnae:
    prefixo: str
    nivel: NivelCnae
    faixa: Faixa
    justificativa: str

    @property
    def rotulo(self) -> str:
        return f"{formatar_cnae(self.prefixo)} ({self.nivel})"


@dataclass(frozen=True, slots=True)
class ClassificacaoCnae:
    subclasse: str
    faixa: Faixa
    regra: RegraCnae | None

    @property
    def regra_aplicada(self) -> str:
        return "padrao" if self.regra is None else self.regra.rotulo


@dataclass(frozen=True, slots=True)
class EstruturaCnae:
    versao: str
    divisoes: Mapping[str, str]
    grupos: Mapping[str, str]
    classes: Mapping[str, str]
    subclasses: Mapping[str, str]

    def codigos(self, nivel: NivelCnae) -> Mapping[str, str]:
        match nivel:
            case NivelCnae.DIVISAO:
                return self.divisoes
            case NivelCnae.GRUPO:
                return self.grupos
            case NivelCnae.CLASSE:
                return self.classes
            case NivelCnae.SUBCLASSE:
                return self.subclasses


@dataclass(frozen=True, slots=True)
class TabelaCnae:
    versao: str
    regras: Mapping[str, RegraCnae]
    faixa_padrao: Faixa
    justificativa_padrao: str
    estrutura: EstruturaCnae


@dataclass(frozen=True, slots=True)
class AvaliacaoCnae:
    principal: ClassificacaoCnae
    secundarios: tuple[ClassificacaoCnae, ...]
    melhor_faixa: Faixa
    alerta_cnae: bool
    gatilho_religioso: bool
    alerta_religiosa: bool


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


@dataclass(frozen=True, slots=True)
class Tabelas:
    cnae: TabelaCnae
    natureza: TabelaNatureza
    orientador: RegrasOrientador
    limites: Limites


def normalizar_cnae(valor: str | int) -> str:
    if isinstance(valor, bool):
        raise ValueError(f"CNAE inválido: {valor!r}")
    digitos = _NAO_DIGITO.sub("", str(valor))
    if not DIGITOS_MINIMOS_INFORMADOS <= len(digitos) <= DIGITOS_SUBCLASSE:
        raise ValueError(f"CNAE inválido: {valor!r}")
    return digitos.zfill(DIGITOS_SUBCLASSE)


def formatar_cnae(codigo: str) -> str:
    match len(codigo):
        case 2:
            return codigo
        case 3:
            return f"{codigo[:2]}.{codigo[2]}"
        case 5:
            return f"{codigo[:2]}.{codigo[2:4]}-{codigo[4]}"
        case 7:
            return f"{codigo[:4]}-{codigo[4]}/{codigo[5:]}"
        case _:
            raise ValueError(f"Código CNAE com tamanho inválido: {codigo!r}")


def descrever_subclasse(tabela: TabelaCnae, cnae: str | int) -> str | None:
    return tabela.estrutura.subclasses.get(normalizar_cnae(cnae))


def classificar_subclasse(tabela: TabelaCnae, cnae: str | int) -> ClassificacaoCnae:
    subclasse = normalizar_cnae(cnae)
    for tamanho in _TAMANHOS_DO_MAIS_ESPECIFICO:
        regra = tabela.regras.get(subclasse[:tamanho])
        if regra is not None:
            return ClassificacaoCnae(subclasse, regra.faixa, regra)
    return ClassificacaoCnae(subclasse, tabela.faixa_padrao, None)


def melhor_faixa(classificacoes: Iterable[ClassificacaoCnae]) -> Faixa:
    faixas = {c.faixa for c in classificacoes}
    if not faixas:
        raise ValueError("Nenhuma classificação CNAE informada")
    return next(f for f in ORDEM_FAIXAS if f in faixas)


def eh_gatilho_religioso(natureza_codigo: int | None, cnae_principal: str | int) -> bool:
    return (
        natureza_codigo == NATUREZA_ORGANIZACAO_RELIGIOSA
        or normalizar_cnae(cnae_principal) == SUBCLASSE_RELIGIOSA
    )


def avaliar_cnaes(
    tabela: TabelaCnae,
    natureza_codigo: int | None,
    cnae_principal: str | int,
    cnaes_secundarios: Iterable[str | int],
) -> AvaliacaoCnae:
    principal = classificar_subclasse(tabela, cnae_principal)
    secundarios = tuple(classificar_subclasse(tabela, c) for c in cnaes_secundarios)
    melhor = melhor_faixa((principal, *secundarios))
    gatilho = eh_gatilho_religioso(natureza_codigo, principal.subclasse)
    return AvaliacaoCnae(
        principal=principal,
        secundarios=secundarios,
        melhor_faixa=melhor,
        alerta_cnae=melhor is Faixa.BAIXA,
        gatilho_religioso=gatilho,
        alerta_religiosa=gatilho and melhor is not Faixa.ALTA,
    )


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


def montar_estrutura_cnae(bruto: object) -> EstruturaCnae:
    objeto = _objeto(bruto, ARQUIVO_ESTRUTURA_CNAE)
    niveis = {
        nivel: _codigos(objeto, nivel, f"{ARQUIVO_ESTRUTURA_CNAE}.{nivel.colecao}") for nivel in NivelCnae
    }
    for nivel, superior in zip(tuple(NivelCnae)[1:], tuple(NivelCnae)[:-1], strict=True):
        for codigo in niveis[nivel]:
            if codigo[: superior.tamanho] not in niveis[superior]:
                raise ErroTabela(f"{nivel} {codigo} sem {superior} correspondente na estrutura CNAE")
    return EstruturaCnae(
        versao=_texto(objeto.get("versao_cnae"), f"{ARQUIVO_ESTRUTURA_CNAE}.versao_cnae"),
        divisoes=niveis[NivelCnae.DIVISAO],
        grupos=niveis[NivelCnae.GRUPO],
        classes=niveis[NivelCnae.CLASSE],
        subclasses=niveis[NivelCnae.SUBCLASSE],
    )


def montar_tabela_cnae(bruto_regras: object, estrutura: EstruturaCnae) -> TabelaCnae:
    objeto = _objeto(bruto_regras, ARQUIVO_REGRAS_CNAE)
    onde_padrao = f"{ARQUIVO_REGRAS_CNAE}.padrao"
    padrao = _objeto(objeto.get("padrao"), onde_padrao)
    regras: dict[str, RegraCnae] = {}
    for indice, item in enumerate(_lista(objeto.get("regras"), f"{ARQUIVO_REGRAS_CNAE}.regras")):
        regra = _regra(item, f"{ARQUIVO_REGRAS_CNAE}.regras[{indice}]", estrutura)
        if regra.prefixo in regras:
            raise ErroTabela(f"Prefixo duplicado: {regra.prefixo}")
        regras[regra.prefixo] = regra
    return TabelaCnae(
        versao=_texto(objeto.get("versao"), f"{ARQUIVO_REGRAS_CNAE}.versao"),
        regras=MappingProxyType(regras),
        faixa_padrao=_faixa(padrao.get("faixa"), f"{onde_padrao}.faixa"),
        justificativa_padrao=_texto(
            padrao.get("justificativa"), f"{ARQUIVO_REGRAS_CNAE}.padrao.justificativa"
        ),
        estrutura=estrutura,
    )


@cache
def carregar_tabela_cnae() -> TabelaCnae:
    estrutura = montar_estrutura_cnae(_ler_json(ARQUIVO_ESTRUTURA_CNAE))
    return montar_tabela_cnae(_ler_json(ARQUIVO_REGRAS_CNAE), estrutura)


def montar_tabela_natureza(bruto: object) -> TabelaNatureza:
    objeto = _objeto(bruto, ARQUIVO_NATUREZA)
    itens = _lista(objeto.get("naturezas"), f"{ARQUIVO_NATUREZA}.naturezas")
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
        versao=_texto(objeto.get("versao"), f"{ARQUIVO_NATUREZA}.versao"),
        naturezas=MappingProxyType(naturezas),
        por_descricao=MappingProxyType(por_descricao),
    )


@cache
def carregar_tabela_natureza() -> TabelaNatureza:
    return montar_tabela_natureza(_ler_json(ARQUIVO_NATUREZA))


def carregar_tabelas() -> Tabelas:
    return Tabelas(
        cnae=carregar_tabela_cnae(),
        natureza=carregar_tabela_natureza(),
        orientador=carregar_regras_orientador(),
        limites=carregar_limites(),
    )


def _ler_json(nome: str) -> object:
    texto = files("validador_osc").joinpath("dados", nome).read_text(encoding="utf-8")
    resultado: object = json.loads(texto)
    return resultado


def _regra(bruto: object, onde: str, estrutura: EstruturaCnae) -> RegraCnae:
    objeto = _objeto(bruto, onde)
    esperados = {"prefixo", "nivel", "faixa", "justificativa"}
    if set(objeto) != esperados:
        raise ErroTabela(f"{onde}: campos esperados {sorted(esperados)}, encontrados {sorted(objeto)}")
    prefixo = _texto(objeto["prefixo"], f"{onde}.prefixo")
    nivel = _enum(NivelCnae, objeto["nivel"], f"{onde}.nivel")
    faixa = _faixa(objeto["faixa"], f"{onde}.faixa")
    justificativa = _texto(objeto["justificativa"], f"{onde}.justificativa")
    if _NIVEL_POR_TAMANHO.get(len(prefixo)) is not nivel:
        raise ErroTabela(f"Nível '{nivel}' não confere com o prefixo {prefixo}")
    if prefixo not in estrutura.codigos(nivel):
        raise ErroTabela(f"Prefixo {prefixo} não existe no nível {nivel} da CNAE do IBGE")
    return RegraCnae(prefixo, nivel, faixa, justificativa)


def _natureza(bruto: object, onde: str) -> NaturezaJuridica:
    objeto = _objeto(bruto, onde)
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
    formatado = _texto(objeto["codigo_formatado"], f"{onde}.codigo_formatado")
    if formatado != formatar_natureza(codigo):
        raise ErroTabela(f"{onde}: código formatado {formatado!r} não confere com {codigo}")
    radical, digito = divmod(codigo, 10)
    if digito_natureza(radical) != digito:
        raise ErroTabela(f"{onde}: dígito verificador inválido em {formatado}")
    sinonimos = tuple(
        _texto(s, f"{onde}.sinonimos[{i}]")
        for i, s in enumerate(_lista(objeto["sinonimos"], f"{onde}.sinonimos"))
    )
    return NaturezaJuridica(
        codigo=codigo,
        codigo_formatado=formatado,
        descricao=_texto(objeto["descricao"], f"{onde}.descricao"),
        sinonimos=sinonimos,
        regra=_enum(RegraNatureza, objeto["regra"], f"{onde}.regra"),
        justificativa=_texto(objeto["justificativa"], f"{onde}.justificativa"),
    )


def _codigos(objeto: Mapping[str, object], nivel: NivelCnae, onde: str) -> Mapping[str, str]:
    bruto = _objeto(objeto.get(nivel.colecao), onde)
    codigos: dict[str, str] = {}
    for codigo, descricao in bruto.items():
        if len(codigo) != nivel.tamanho or not codigo.isascii() or not codigo.isdigit():
            raise ErroTabela(f"{onde}: código {codigo!r} inválido para {nivel}")
        codigos[codigo] = _texto(descricao, f"{onde}.{codigo}")
    if not codigos:
        raise ErroTabela(f"{onde}: nível vazio")
    return MappingProxyType(codigos)


def _faixa(valor: object, onde: str) -> Faixa:
    return _enum(Faixa, valor, onde)


def _enum[E: StrEnum](tipo: type[E], valor: object, onde: str) -> E:
    texto = _texto(valor, onde)
    try:
        return tipo(texto)
    except ValueError:
        raise ErroTabela(f"{onde}: valor inválido {texto!r}") from None


def _objeto(valor: object, onde: str) -> Mapping[str, object]:
    if not isinstance(valor, dict):
        raise ErroTabela(f"{onde}: esperado objeto JSON")
    return {str(chave): item for chave, item in valor.items()}


def _lista(valor: object, onde: str) -> list[object]:
    if not isinstance(valor, list):
        raise ErroTabela(f"{onde}: esperada lista JSON")
    return list(valor)


def _texto(valor: object, onde: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ErroTabela(f"{onde}: esperado texto não vazio")
    return valor
