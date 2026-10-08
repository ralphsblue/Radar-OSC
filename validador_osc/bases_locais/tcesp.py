import re
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, BinaryIO, cast
from urllib.parse import unquote

import httpx
import openpyxl
from sqlalchemy import Table

from validador_osc.bases_locais.carga import (
    ArquivoObtido,
    DefinicaoBase,
    ErroArquivo,
    Leitura,
    Obtencao,
    Sanidade,
)
from validador_osc.bases_locais.obtencao import ErroObtencao, com_tentativas
from validador_osc.dominio.pessoa_fisica import normalizar_nome
from validador_osc.dominio.sancoes import RegistroTcesp
from validador_osc.persistencia.bases import FONTE_TCESP
from validador_osc.persistencia.modelos import TcespRegistro

PAGINA = "https://www.tce.sp.gov.br/relacao-de-responsaveis-por-contas-julgadas-irregulares"
EXTENSAO = "xlsx"
PAUSA_TENTATIVA_S = 2.0

COLUNAS_TCESP = (
    "Responsável",
    "#",
    "Responsável",
    "CPF",
    "Processo TC",
    "Matéria",
    "Origem",
    "Trânsito em Julgado",
    "Exercício",
    "Matéria",
)

COLUNA_NOME = 2
COLUNA_CPF = 3
COLUNA_PROCESSO = 4
COLUNA_MATERIA = 5
COLUNA_ORIGEM = 6
COLUNA_TRANSITO = 7
COLUNA_EXERCICIO = 8

_PADRAO_CPF_PARCIAL = re.compile(r"(\d{3})\.XXX\.XXX-(\d{2})")
_PADRAO_DATA = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
_PADRAO_LINK_XLSX = re.compile(r'href="([^"]*_Prest_Contas_CPF_anonimizado\.xlsx)"', re.IGNORECASE)
_PADRAO_ULTIMA_ATUALIZACAO = re.compile(r"Última atualização em (\d{2})/(\d{2})/(\d{4})")
_PADRAO_PREFIXO_ARQUIVO = re.compile(r"^(\d{8})_")
_PADRAO_PERIODO_ARQUIVO = re.compile(r"a (\d{2})-(\d{2})-(\d{4})_Prest_Contas", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class BaseTcesp:
    sanidade: Sanidade

    @property
    def fonte(self) -> str:
        return FONTE_TCESP


FONTES_TCESP: dict[str, BaseTcesp] = {
    fonte.fonte: fonte for fonte in (BaseTcesp(Sanidade(minimo_linhas=8_000)),)
}


@dataclass(frozen=True, slots=True)
class RegistroLinhaTcesp:
    registro: RegistroTcesp
    nome_normalizado: str
    linha: dict[str, Any]

    def para_tabela(self) -> dict[str, Any]:
        r = self.registro
        return {
            "nome": r.nome,
            "nome_normalizado": self.nome_normalizado,
            "cpf_inicio": r.cpf_inicio,
            "cpf_fim": r.cpf_fim,
            "processo": r.processo,
            "materia": r.materia,
            "origem": r.origem,
            "data_transito": r.data_transito,
            "exercicio": r.exercicio,
            "linha": self.linha,
        }


def definicao(fonte: BaseTcesp, sanidade: Sanidade | None = None) -> DefinicaoBase:
    return DefinicaoBase(
        fonte=fonte.fonte,
        tabela=cast(Table, TcespRegistro.__table__),
        colunas_esperadas=COLUNAS_TCESP,
        sanidade=sanidade or fonte.sanidade,
        ler=ler_arquivo,
    )


def _texto(valor: object) -> str:
    return "" if valor is None else str(valor).strip()


def _campo(campos: list[str], indice: int) -> str:
    return campos[indice] if indice < len(campos) else ""


def _data(valor: str, numero: int) -> date | None:
    if not valor:
        return None
    encontrada = _PADRAO_DATA.fullmatch(valor)
    if encontrada is None:
        raise ErroArquivo(f"linha {numero}: Trânsito em Julgado com data inválida {valor!r}")
    dia, mes, ano = encontrada.groups()
    try:
        return date(int(ano), int(mes), int(dia))
    except ValueError as erro:
        raise ErroArquivo(f"linha {numero}: Trânsito em Julgado com data inválida {valor!r}") from erro


def converter(linha: tuple[object, ...], numero: int) -> RegistroLinhaTcesp:
    campos = [_texto(valor) for valor in linha]
    nome = _campo(campos, COLUNA_NOME)
    if not nome:
        raise ErroArquivo(f"linha {numero}: nome vazio")
    cpf_bruto = _campo(campos, COLUNA_CPF)
    encontrado = _PADRAO_CPF_PARCIAL.fullmatch(cpf_bruto)
    if encontrado is None:
        raise ErroArquivo(f"linha {numero}: CPF em formato inesperado {cpf_bruto!r}")
    cpf_inicio, cpf_fim = encontrado.groups()
    processo = _campo(campos, COLUNA_PROCESSO) or None
    materia = _campo(campos, COLUNA_MATERIA) or None
    origem = _campo(campos, COLUNA_ORIGEM) or None
    transito_bruto = _campo(campos, COLUNA_TRANSITO)
    transito = _data(transito_bruto, numero)
    exercicio = _campo(campos, COLUNA_EXERCICIO) or None

    registro = RegistroTcesp(
        nome=nome,
        cpf_inicio=cpf_inicio,
        cpf_fim=cpf_fim,
        processo=processo,
        materia=materia,
        origem=origem,
        data_transito=transito,
        exercicio=exercicio,
    )
    linha_json = {
        "nome": nome,
        "cpf": cpf_bruto,
        "processo": processo,
        "materia": materia,
        "origem": origem,
        "transito": transito_bruto or None,
        "exercicio": exercicio,
    }
    return RegistroLinhaTcesp(registro, normalizar_nome(nome), linha_json)


def _e_linha_de_dados(linha: tuple[object, ...]) -> bool:
    return len(linha) > COLUNA_CPF and _PADRAO_CPF_PARCIAL.fullmatch(_texto(linha[COLUNA_CPF])) is not None


def _cabecalho(linhas: list[tuple[object, ...]]) -> tuple[str, ...]:
    for linha in linhas:
        campos = tuple(_texto(valor) for valor in linha)
        if "CPF" in campos:
            return campos
    raise ErroArquivo("cabeçalho com a coluna CPF não encontrado")


def _carregar_planilha(caminho: Path) -> list[tuple[object, ...]]:
    try:
        livro = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    except Exception as erro:
        raise ErroArquivo(f"xlsx inválido ({erro})") from erro
    try:
        return list(livro.worksheets[0].iter_rows(values_only=True))
    finally:
        livro.close()


@contextmanager
def ler_registros(caminho: Path) -> Iterator[tuple[tuple[str, ...], Iterator[RegistroLinhaTcesp]]]:
    linhas = _carregar_planilha(caminho)
    colunas = _cabecalho(linhas)
    registros = (
        converter(linha, numero) for numero, linha in enumerate(linhas, start=1) if _e_linha_de_dados(linha)
    )
    yield colunas, registros


@contextmanager
def ler_arquivo(caminho: Path) -> Iterator[Leitura]:
    with ler_registros(caminho) as (colunas, registros):
        yield Leitura(colunas, (registro.para_tabela() for registro in registros))


def _link_xlsx(pagina: str) -> str:
    encontrado = _PADRAO_LINK_XLSX.search(pagina)
    if encontrado is None:
        raise ErroObtencao("link do xlsx de Prest_Contas não encontrado na página do TCE-SP")
    return encontrado.group(1)


def _data_atualizacao(pagina: str) -> date | None:
    encontrada = _PADRAO_ULTIMA_ATUALIZACAO.search(pagina)
    if encontrada is None:
        return None
    dia, mes, ano = encontrada.groups()
    try:
        return date(int(ano), int(mes), int(dia))
    except ValueError:
        return None


def data_do_nome(nome: str) -> date | None:
    prefixo = _PADRAO_PREFIXO_ARQUIVO.match(nome)
    if prefixo is not None:
        valor = prefixo.group(1)
        try:
            return date(int(valor[:4]), int(valor[4:6]), int(valor[6:]))
        except ValueError:
            return None
    encontrado = _PADRAO_PERIODO_ARQUIVO.search(unquote(nome))
    if encontrado is None:
        return None
    dia, mes, ano = encontrado.groups()
    try:
        return date(int(ano), int(mes), int(dia))
    except ValueError:
        return None


def obtencao_remota(cliente: httpx.Client) -> Obtencao:
    def gravar(destino: BinaryIO) -> ArquivoObtido:
        def buscar_pagina() -> str:
            resposta = cliente.get(PAGINA)
            resposta.raise_for_status()
            return resposta.content.decode("utf-8")

        pagina = com_tentativas(buscar_pagina, "página de relação do TCE-SP", PAUSA_TENTATIVA_S)
        url = _link_xlsx(pagina)
        data_base = _data_atualizacao(pagina) or data_do_nome(url)

        def baixar() -> str:
            destino.seek(0)
            destino.truncate()
            with cliente.stream("GET", url) as resposta:
                resposta.raise_for_status()
                for bloco in resposta.iter_bytes():
                    destino.write(bloco)
                return str(resposta.url)

        url_final = com_tentativas(baixar, "download da relação do TCE-SP", PAUSA_TENTATIVA_S)
        return ArquivoObtido(url_final, data_base, EXTENSAO)

    return Obtencao(PAGINA, gravar)


def obtencao_local(caminho: Path) -> Obtencao:
    absoluto = caminho.resolve()

    def gravar(destino: BinaryIO) -> ArquivoObtido:
        if absoluto.suffix.lower() != f".{EXTENSAO}":
            raise ErroArquivo(f"extensão não suportada: {absoluto.name} (use .xlsx)")
        with absoluto.open("rb") as origem:
            shutil.copyfileobj(origem, destino)
        return ArquivoObtido(absoluto.as_uri(), data_do_nome(absoluto.name), EXTENSAO)

    return Obtencao(absoluto.as_uri(), gravar)
