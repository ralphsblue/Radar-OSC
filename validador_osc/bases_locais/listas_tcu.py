import json
import re
import shutil
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from functools import partial
from pathlib import Path
from typing import Any, BinaryIO, cast

import httpx
from sqlalchemy import Table

from validador_osc.bases_locais.carga import (
    ArquivoObtido,
    DefinicaoBase,
    ErroArquivo,
    Leitura,
    Obtencao,
    Sanidade,
)
from validador_osc.bases_locais.obtencao import com_tentativas
from validador_osc.dominio.sancoes import ListaTcu, RegistroListaTcu
from validador_osc.persistencia.bases import FONTES_LISTA_TCU
from validador_osc.persistencia.modelos import ListaTcuRegistro
from validador_osc.pessoa_fisica import FragmentoCpf, fragmento_cpf, mascarar_cpfs, normalizar_nome

URL_API = "https://certidoes.apps.tcu.gov.br/api/publico"
EXTENSAO = "json"
TAMANHO_RAIZ = 8
PAUSA_TENTATIVA_S = 2.0
TIPO_CPF = "CPF"
TIPO_CNPJ = "CNPJ"

_PADRAO_DATA = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
_PADRAO_PROCESSO = re.compile(r"(?:TC-?)?(\d{1,3})\.?(\d{3})/(\d{4})-?(\d)")
_PADRAO_ACORDAO = re.compile(r"(?:AC-?)?(\d{1,5})/(\d{4})-?(PL|1C|2C)")
_PADRAO_CNPJ = re.compile(r"[0-9A-Z]{12}\d{2}")
_PADRAO_DATA_ARQUIVO = re.compile(r"^(\d{8})_")
_PONTUACAO = re.compile(r"[./\-\s]")
_ESPACOS = re.compile(r"\s+")
_CONTROLE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

_COLUNAS_COMUNS = (
    "codigoProcesso",
    "dataTransitoEmJulgado",
    "linkAcompanhamentoProcesso",
    "linkDeliberacoesProcesso",
    "municipio",
    "nome",
    "numeroAcordaoFormatado",
    "numeroProcessoFormatado",
    "numeroRegistro",
    "seProcessoGestao",
    "tipoRegistro",
    "uf",
)
COLUNAS_CONTAS_IRREGULARES = _COLUNAS_COMUNS
COLUNAS_COM_SANCAO = tuple(sorted((*_COLUNAS_COMUNS, "dataAcordao", "dataFinalSancao")))


@dataclass(frozen=True, slots=True)
class FonteTcu:
    lista: ListaTcu
    recurso: str
    colunas: tuple[str, ...]
    sanidade: Sanidade

    @property
    def fonte(self) -> str:
        return FONTES_LISTA_TCU[self.lista]

    @property
    def url(self) -> str:
        return f"{URL_API}/{self.recurso}"


FONTES_TCU: dict[str, FonteTcu] = {
    fonte.fonte: fonte
    for fonte in (
        FonteTcu(
            ListaTcu.INIDONEOS, "responsaveis-inidoneos", COLUNAS_COM_SANCAO, Sanidade(minimo_linhas=80)
        ),
        FonteTcu(
            ListaTcu.CONTAS_IRREGULARES,
            "responsaveis-contas-irregulares",
            COLUNAS_CONTAS_IRREGULARES,
            Sanidade(minimo_linhas=40_000),
        ),
        FonteTcu(
            ListaTcu.INABILITADOS,
            "responsaveis-inabilitados",
            COLUNAS_COM_SANCAO,
            Sanidade(minimo_linhas=600),
        ),
    )
}


@dataclass(frozen=True, slots=True)
class RegistroTcu:
    registro: RegistroListaTcu
    tipo_registro: str
    nome_normalizado: str
    cpf: FragmentoCpf | None
    linha: dict[str, Any]

    def para_tabela(self) -> dict[str, Any]:
        r = self.registro
        return {
            "lista": r.lista.value,
            "tipo_registro": self.tipo_registro,
            "documento": r.documento,
            "raiz": r.raiz,
            "nome": r.nome,
            "nome_normalizado": self.nome_normalizado,
            "cpf_meio": self.cpf.meio if self.cpf is not None else None,
            "cpf_dv_final": self.cpf.dv_final if self.cpf is not None else None,
            "processo": r.processo,
            "acordao": r.acordao,
            "data_acordao": r.data_acordao,
            "data_transito": r.data_transito,
            "data_final": r.data_final,
            "linha": self.linha,
        }


def definicao(fonte: FonteTcu, sanidade: Sanidade | None = None) -> DefinicaoBase:
    return DefinicaoBase(
        fonte=fonte.fonte,
        tabela=cast(Table, ListaTcuRegistro.__table__),
        colunas_esperadas=fonte.colunas,
        sanidade=sanidade or fonte.sanidade,
        ler=partial(ler_arquivo, lista=fonte.lista),
    )


def _limpo(valor: str) -> str:
    return _CONTROLE.sub("", valor).strip()


def _texto(item: Mapping[str, Any], chave: str, numero: int) -> str | None:
    valor = item.get(chave)
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise ErroArquivo(f"registro {numero}: {chave} deveria ser texto, veio {valor!r}")
    limpo = _limpo(valor)
    return limpo or None


def _data(item: Mapping[str, Any], chave: str, numero: int) -> date | None:
    valor = _texto(item, chave, numero)
    if valor is None:
        return None
    encontrada = _PADRAO_DATA.fullmatch(valor)
    try:
        if encontrada is None:
            raise ValueError(valor)
        dia, mes, ano = encontrada.groups()
        return date(int(ano), int(mes), int(dia))
    except ValueError as erro:
        raise ErroArquivo(f"registro {numero}: {chave} com data inválida {valor!r}") from erro


def normalizar_processo(valor: str) -> str | None:
    encontrado = _PADRAO_PROCESSO.fullmatch(_ESPACOS.sub("", valor).upper())
    if encontrado is None:
        return None
    numero, sequencial, ano, dv = encontrado.groups()
    return f"{int(numero):03d}.{sequencial}/{ano}-{dv}"


def normalizar_acordao(valor: str) -> str | None:
    encontrado = _PADRAO_ACORDAO.fullmatch(_ESPACOS.sub("", valor).upper())
    if encontrado is None:
        return None
    numero, ano, colegiado = encontrado.groups()
    return f"{int(numero)}/{ano}-{colegiado}"


def _normalizado(
    item: Mapping[str, Any], chave: str, numero: int, normalizar: Callable[[str], str | None]
) -> str | None:
    valor = _texto(item, chave, numero)
    if valor is None:
        return None
    normalizado = normalizar(valor)
    if normalizado is None:
        raise ErroArquivo(f"registro {numero}: {chave} em formato inesperado {valor!r}")
    return normalizado


def _cnpj(valor: str, numero: int) -> str:
    limpo = _PONTUACAO.sub("", valor).upper()
    if _PADRAO_CNPJ.fullmatch(limpo) is None:
        raise ErroArquivo(f"registro {numero}: numeroRegistro não é CNPJ ({mascarar_cpfs(valor)!r})")
    return limpo


def _valor_linha(valor: Any) -> Any:
    if isinstance(valor, str):
        return mascarar_cpfs(_CONTROLE.sub("", valor))
    if valor is None or isinstance(valor, bool | int | float):
        return valor
    return mascarar_cpfs(json.dumps(valor, ensure_ascii=False))


def converter(lista: ListaTcu, item: Mapping[str, Any], numero: int) -> RegistroTcu:
    tipo = (_texto(item, "tipoRegistro", numero) or "").upper()
    if tipo not in {TIPO_CPF, TIPO_CNPJ}:
        raise ErroArquivo(f"registro {numero}: tipoRegistro desconhecido {tipo!r}")
    numero_registro = _texto(item, "numeroRegistro", numero)
    cpf: FragmentoCpf | None = None
    documento: str | None = None
    if tipo == TIPO_CPF and numero_registro is not None:
        cpf = fragmento_cpf(numero_registro)
        if cpf is None:
            raise ErroArquivo(f"registro {numero}: numeroRegistro não é CPF")
    elif tipo == TIPO_CNPJ and numero_registro is not None:
        documento = _cnpj(numero_registro, numero)
    nome_bruto = _texto(item, "nome", numero)
    if nome_bruto is None:
        raise ErroArquivo(f"registro {numero}: nome vazio")
    nome = mascarar_cpfs(nome_bruto)

    linha = {chave: _valor_linha(valor) for chave, valor in item.items()}
    if tipo == TIPO_CPF and "numeroRegistro" in linha:
        linha["numeroRegistro"] = cpf.mascarado if cpf is not None else None

    registro = RegistroListaTcu(
        lista=lista,
        documento=documento,
        raiz=documento[:TAMANHO_RAIZ] if documento is not None else None,
        nome=nome,
        processo=_normalizado(item, "numeroProcessoFormatado", numero, normalizar_processo),
        acordao=_normalizado(item, "numeroAcordaoFormatado", numero, normalizar_acordao),
        data_acordao=_data(item, "dataAcordao", numero),
        data_transito=_data(item, "dataTransitoEmJulgado", numero),
        data_final=_data(item, "dataFinalSancao", numero),
    )
    return RegistroTcu(registro, tipo, normalizar_nome(nome), cpf, linha)


def _carregar_json(caminho: Path) -> list[Mapping[str, Any]]:
    try:
        dados = json.loads(caminho.read_bytes())
    except (json.JSONDecodeError, UnicodeDecodeError) as erro:
        raise ErroArquivo(f"JSON inválido ({erro})") from erro
    if not isinstance(dados, list):
        raise ErroArquivo(f"JSON deveria ser uma lista, veio {type(dados).__name__}")
    if not dados:
        raise ErroArquivo("lista vazia")
    for numero, item in enumerate(dados, start=1):
        if not isinstance(item, dict):
            raise ErroArquivo(f"registro {numero}: deveria ser um objeto, veio {type(item).__name__}")
    return cast(list[Mapping[str, Any]], dados)


@contextmanager
def ler_registros(caminho: Path, lista: ListaTcu) -> Iterator[tuple[tuple[str, ...], Iterator[RegistroTcu]]]:
    itens = _carregar_json(caminho)
    colunas = tuple(sorted({chave for item in itens for chave in item}))
    yield colunas, (converter(lista, item, numero) for numero, item in enumerate(itens, start=1))


@contextmanager
def ler_arquivo(caminho: Path, lista: ListaTcu) -> Iterator[Leitura]:
    with ler_registros(caminho, lista) as (colunas, registros):
        yield Leitura(colunas, (registro.para_tabela() for registro in registros))


def obtencao_remota(cliente: httpx.Client, fonte: FonteTcu, hoje: Callable[[], date]) -> Obtencao:
    def gravar(destino: BinaryIO) -> ArquivoObtido:
        def baixar() -> str:
            destino.seek(0)
            destino.truncate()
            with cliente.stream("POST", fonte.url, json={}) as resposta:
                resposta.raise_for_status()
                for bloco in resposta.iter_bytes():
                    destino.write(bloco)
                return str(resposta.url)

        url = com_tentativas(baixar, f"download da lista {fonte.lista.value} do TCU", PAUSA_TENTATIVA_S)
        return ArquivoObtido(url, hoje(), EXTENSAO)

    return Obtencao(fonte.url, gravar)


def data_do_nome(nome: str) -> date | None:
    encontrado = _PADRAO_DATA_ARQUIVO.match(nome)
    if encontrado is None:
        return None
    valor = encontrado.group(1)
    try:
        return date(int(valor[:4]), int(valor[4:6]), int(valor[6:]))
    except ValueError:
        return None


def obtencao_local(caminho: Path) -> Obtencao:
    absoluto = caminho.resolve()

    def gravar(destino: BinaryIO) -> ArquivoObtido:
        if absoluto.suffix.lower() != f".{EXTENSAO}":
            raise ErroArquivo(f"extensão não suportada: {absoluto.name} (use .json)")
        with absoluto.open("rb") as origem:
            shutil.copyfileobj(origem, destino)
        return ArquivoObtido(absoluto.as_uri(), data_do_nome(absoluto.name), EXTENSAO)

    return Obtencao(absoluto.as_uri(), gravar)
