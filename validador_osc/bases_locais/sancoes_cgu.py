import csv
import io
import re
import shutil
import zipfile
from collections.abc import Callable, Iterator, Mapping
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
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
from validador_osc.bases_locais.obtencao import ErroObtencao, com_tentativas
from validador_osc.dominio.sancoes import CadastroSancao, Sancao, TipoPessoa
from validador_osc.persistencia.bases import FONTES_SANCAO
from validador_osc.persistencia.modelos import SancaoRegistro
from validador_osc.pessoa_fisica import FragmentoCpf, fragmento_cpf, mascarar_cpfs, normalizar_nome

ENCODING = "iso-8859-1"
URL_DOWNLOAD = "https://portaldatransparencia.gov.br/download-de-dados"
TAMANHO_CNPJ = 14
TAMANHO_RAIZ = 8
PAUSA_TENTATIVA_S = 2.0
EXTENSOES = frozenset({"zip", "csv"})
SEM_INFORMACAO = frozenset({"", "sem informação", "sem informacao"})

_PADRAO_DATA_PAGINA = re.compile(
    r'arquivos\.push\(\{\s*"ano"\s*:\s*"(\d{4})"\s*,\s*"mes"\s*:\s*"(\d{2})"\s*,\s*"dia"\s*:\s*"(\d{2})"'
)
_PADRAO_DATA_ARQUIVO = re.compile(r"(?<!\d)(\d{8})_[A-Za-z]+\.(?:zip|csv)$", re.IGNORECASE)
_PADRAO_DATA_CSV = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
_PADRAO_VALOR = re.compile(r"\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?")

COLUNAS_CEPIM = (
    "CNPJ ENTIDADE",
    "NOME ENTIDADE",
    "NÚMERO CONVÊNIO",
    "ÓRGÃO CONCEDENTE",
    "MOTIVO DO IMPEDIMENTO",
)
_COLUNAS_SANCAO_INICIO = (
    "CADASTRO",
    "CÓDIGO DA SANÇÃO",
    "TIPO DE PESSOA",
    "CPF OU CNPJ DO SANCIONADO",
    "NOME DO SANCIONADO",
    "NOME INFORMADO PELO ÓRGÃO SANCIONADOR",
    "RAZÃO SOCIAL - CADASTRO RECEITA",
    "NOME FANTASIA - CADASTRO RECEITA",
    "NÚMERO DO PROCESSO",
    "CATEGORIA DA SANÇÃO",
)
_COLUNAS_SANCAO_FIM = (
    "DATA INÍCIO SANÇÃO",
    "DATA FINAL SANÇÃO",
    "DATA PUBLICAÇÃO",
    "PUBLICAÇÃO",
    "DETALHAMENTO DO MEIO DE PUBLICAÇÃO",
    "DATA DO TRÂNSITO EM JULGADO",
    "ABRAGÊNCIA DA SANÇÃO",
    "ÓRGÃO SANCIONADOR",
    "UF ÓRGÃO SANCIONADOR",
    "ESFERA ÓRGÃO SANCIONADOR",
    "FUNDAMENTAÇÃO LEGAL",
    "DATA ORIGEM INFORMAÇÃO",
    "ORIGEM INFORMAÇÕES",
    "OBSERVAÇÕES",
)
COLUNAS_CEIS = (*_COLUNAS_SANCAO_INICIO, *_COLUNAS_SANCAO_FIM)
COLUNAS_CNEP = (*_COLUNAS_SANCAO_INICIO, "VALOR DA MULTA", *_COLUNAS_SANCAO_FIM)
_COLUNA_DOCUMENTO = {
    CadastroSancao.CEPIM: "CNPJ ENTIDADE",
    CadastroSancao.CEIS: "CPF OU CNPJ DO SANCIONADO",
    CadastroSancao.CNEP: "CPF OU CNPJ DO SANCIONADO",
}


@dataclass(frozen=True, slots=True)
class FonteCgu:
    cadastro: CadastroSancao
    colunas: tuple[str, ...]
    sanidade: Sanidade

    @property
    def fonte(self) -> str:
        return FONTES_SANCAO[self.cadastro]

    @property
    def caminho(self) -> str:
        return self.cadastro.value.lower()


FONTES_CGU: dict[str, FonteCgu] = {
    fonte.fonte: fonte
    for fonte in (
        FonteCgu(CadastroSancao.CEPIM, COLUNAS_CEPIM, Sanidade(minimo_linhas=3_000)),
        FonteCgu(CadastroSancao.CEIS, COLUNAS_CEIS, Sanidade(minimo_linhas=20_000)),
        FonteCgu(CadastroSancao.CNEP, COLUNAS_CNEP, Sanidade(minimo_linhas=1_500)),
    )
}


@dataclass(frozen=True, slots=True)
class RegistroSancao:
    sancao: Sancao
    nome_normalizado: str
    cpf: FragmentoCpf | None
    linha: dict[str, str]

    def para_tabela(self) -> dict[str, Any]:
        s = self.sancao
        return {
            "cadastro": s.cadastro.value,
            "tipo_pessoa": s.tipo_pessoa.value if s.tipo_pessoa is not None else None,
            "documento": s.documento,
            "raiz": s.raiz,
            "nome": s.nome,
            "nome_normalizado": self.nome_normalizado,
            "cpf_meio": self.cpf.meio if self.cpf is not None else None,
            "cpf_dv_final": self.cpf.dv_final if self.cpf is not None else None,
            "categoria": s.categoria,
            "data_inicio": s.data_inicio,
            "data_fim": s.data_fim,
            "orgao": s.orgao,
            "esfera": s.esfera,
            "uf": s.uf,
            "abrangencia": s.abrangencia,
            "fundamentacao": s.fundamentacao,
            "processo": s.processo,
            "valor_multa": s.valor_multa,
            "codigo_sancao": s.codigo_sancao,
            "origem_informacoes": s.origem_informacoes,
            "motivo": s.motivo,
            "convenio": s.convenio,
            "linha": self.linha,
        }


def definicao(fonte: FonteCgu, sanidade: Sanidade | None = None) -> DefinicaoBase:
    return DefinicaoBase(
        fonte=fonte.fonte,
        tabela=cast(Table, SancaoRegistro.__table__),
        colunas_esperadas=fonte.colunas,
        sanidade=sanidade or fonte.sanidade,
        ler=partial(ler_arquivo, cadastro=fonte.cadastro),
    )


def data_do_nome(nome: str) -> date | None:
    encontrado = _PADRAO_DATA_ARQUIVO.search(nome)
    if encontrado is None:
        return None
    valor = encontrado.group(1)
    try:
        return date(int(valor[:4]), int(valor[4:6]), int(valor[6:]))
    except ValueError:
        return None


def _texto(valor: str) -> str | None:
    limpo = valor.strip()
    return None if limpo.casefold() in SEM_INFORMACAO else limpo


def _data(valor: str, coluna: str, numero: int) -> date | None:
    limpo = valor.strip()
    if limpo.casefold() in SEM_INFORMACAO:
        return None
    encontrada = _PADRAO_DATA_CSV.fullmatch(limpo)
    try:
        if encontrada is None:
            raise ValueError(limpo)
        dia, mes, ano = encontrada.groups()
        return date(int(ano), int(mes), int(dia))
    except ValueError as erro:
        raise ErroArquivo(f"linha {numero}: {coluna} com data inválida {limpo!r}") from erro


def _valor(valor: str, coluna: str, numero: int) -> Decimal | None:
    limpo = valor.strip()
    if limpo.casefold() in SEM_INFORMACAO:
        return None
    if _PADRAO_VALOR.fullmatch(limpo) is None:
        raise ErroArquivo(f"linha {numero}: {coluna} com valor inválido {limpo!r}")
    try:
        return Decimal(limpo.replace(".", "").replace(",", "."))
    except InvalidOperation as erro:
        raise ErroArquivo(f"linha {numero}: {coluna} com valor inválido {limpo!r}") from erro


def _tipo_pessoa(valor: str, numero: int) -> TipoPessoa | None:
    limpo = valor.strip().upper()
    if not limpo:
        return None
    try:
        return TipoPessoa(limpo)
    except ValueError as erro:
        raise ErroArquivo(f"linha {numero}: TIPO DE PESSOA desconhecido {limpo!r}") from erro


def converter(cadastro: CadastroSancao, valores: Mapping[str, str], numero: int) -> RegistroSancao:
    coluna_documento = _COLUNA_DOCUMENTO[cadastro]
    documento_bruto = valores[coluna_documento].strip()
    if cadastro is CadastroSancao.CEPIM:
        tipo: TipoPessoa | None = TipoPessoa.JURIDICA
        coluna_nome = "NOME ENTIDADE"
    else:
        cadastro_linha = valores["CADASTRO"].strip()
        if cadastro_linha != cadastro.value:
            raise ErroArquivo(f"linha {numero}: CADASTRO {cadastro_linha!r} em arquivo do {cadastro.value}")
        tipo = _tipo_pessoa(valores["TIPO DE PESSOA"], numero)
        coluna_nome = "NOME DO SANCIONADO"

    cpf = fragmento_cpf(documento_bruto)
    pessoa_fisica = cpf is not None or tipo is TipoPessoa.FISICA
    if cpf is not None and tipo is TipoPessoa.JURIDICA:
        tipo = None
    documento = None if pessoa_fisica or not documento_bruto else documento_bruto
    raiz = documento[:TAMANHO_RAIZ] if documento is not None and len(documento) == TAMANHO_CNPJ else None

    linha = {coluna: mascarar_cpfs(valor) for coluna, valor in valores.items()}
    if pessoa_fisica:
        linha[coluna_documento] = cpf.mascarado if cpf is not None else "***"
    valores = linha

    nome = valores[coluna_nome].strip()
    if cadastro is CadastroSancao.CEPIM:
        sancao = Sancao(
            cadastro=cadastro,
            tipo_pessoa=tipo,
            documento=documento,
            raiz=raiz,
            nome=nome,
            categoria=None,
            data_inicio=None,
            data_fim=None,
            orgao=_texto(valores["ÓRGÃO CONCEDENTE"]),
            esfera=None,
            uf=None,
            abrangencia=None,
            fundamentacao=None,
            processo=None,
            valor_multa=None,
            codigo_sancao=None,
            origem_informacoes=None,
            motivo=_texto(valores["MOTIVO DO IMPEDIMENTO"]),
            convenio=_texto(valores["NÚMERO CONVÊNIO"]),
        )
    else:
        multa = valores.get("VALOR DA MULTA")
        sancao = Sancao(
            cadastro=cadastro,
            tipo_pessoa=tipo,
            documento=documento,
            raiz=raiz,
            nome=nome,
            categoria=_texto(valores["CATEGORIA DA SANÇÃO"]),
            data_inicio=_data(valores["DATA INÍCIO SANÇÃO"], "DATA INÍCIO SANÇÃO", numero),
            data_fim=_data(valores["DATA FINAL SANÇÃO"], "DATA FINAL SANÇÃO", numero),
            orgao=_texto(valores["ÓRGÃO SANCIONADOR"]),
            esfera=_texto(valores["ESFERA ÓRGÃO SANCIONADOR"]),
            uf=_texto(valores["UF ÓRGÃO SANCIONADOR"]),
            abrangencia=_texto(valores["ABRAGÊNCIA DA SANÇÃO"]),
            fundamentacao=_texto(valores["FUNDAMENTAÇÃO LEGAL"]),
            processo=_texto(valores["NÚMERO DO PROCESSO"]),
            valor_multa=_valor(multa, "VALOR DA MULTA", numero) if multa is not None else None,
            codigo_sancao=_texto(valores["CÓDIGO DA SANÇÃO"]),
            origem_informacoes=_texto(valores["ORIGEM INFORMAÇÕES"]),
        )
    return RegistroSancao(sancao, normalizar_nome(nome), cpf, linha)


def _registros(
    leitor: Iterator[list[str]], colunas: tuple[str, ...], cadastro: CadastroSancao
) -> Iterator[RegistroSancao]:
    numero = 1
    try:
        for campos in leitor:
            numero += 1
            if not any(campo.strip() for campo in campos):
                continue
            if len(campos) != len(colunas):
                raise ErroArquivo(f"linha {numero}: {len(campos)} campos, esperados {len(colunas)}")
            yield converter(cadastro, dict(zip(colunas, campos, strict=True)), numero)
    except (csv.Error, zipfile.BadZipFile, EOFError) as erro:
        raise ErroArquivo(f"linha {numero}: arquivo corrompido ({erro})") from erro


@contextmanager
def ler_sancoes(
    caminho: Path, cadastro: CadastroSancao
) -> Iterator[tuple[tuple[str, ...], Iterator[RegistroSancao]]]:
    with ExitStack() as pilha:
        binario = _abrir_csv(caminho, pilha)
        texto = pilha.enter_context(io.TextIOWrapper(binario, encoding=ENCODING, newline=""))
        leitor = csv.reader(texto, delimiter=";")
        try:
            cabecalho = next(leitor, None)
        except (csv.Error, zipfile.BadZipFile, EOFError) as erro:
            raise ErroArquivo(f"cabeçalho ilegível ({erro})") from erro
        if cabecalho is None:
            raise ErroArquivo("arquivo vazio")
        colunas = tuple(coluna.strip() for coluna in cabecalho)
        yield colunas, _registros(leitor, colunas, cadastro)


@contextmanager
def ler_arquivo(caminho: Path, cadastro: CadastroSancao) -> Iterator[Leitura]:
    with ler_sancoes(caminho, cadastro) as (colunas, registros):
        yield Leitura(colunas, (registro.para_tabela() for registro in registros))


def _abrir_csv(caminho: Path, pilha: ExitStack) -> BinaryIO:
    if caminho.suffix.lower() != ".zip":
        return pilha.enter_context(caminho.open("rb"))
    try:
        arquivo_zip = pilha.enter_context(zipfile.ZipFile(caminho))
    except zipfile.BadZipFile as erro:
        raise ErroArquivo(f"zip inválido ({erro})") from erro
    membros = [membro for membro in arquivo_zip.infolist() if membro.filename.lower().endswith(".csv")]
    if len(membros) != 1:
        nomes = [membro.filename for membro in arquivo_zip.infolist()]
        raise ErroArquivo(f"zip deveria ter exatamente um CSV, tem {nomes}")
    return cast(BinaryIO, pilha.enter_context(arquivo_zip.open(membros[0])))


def _com_tentativas[T](acao: Callable[[], T], descricao: str) -> T:
    return com_tentativas(acao, descricao, PAUSA_TENTATIVA_S)


def descobrir_data(cliente: httpx.Client, fonte: FonteCgu) -> date:
    url = f"{URL_DOWNLOAD}/{fonte.caminho}"

    def buscar() -> str:
        resposta = cliente.get(url)
        resposta.raise_for_status()
        return resposta.text

    pagina = _com_tentativas(buscar, f"página de download do {fonte.cadastro.value}")
    datas = [date(int(ano), int(mes), int(dia)) for ano, mes, dia in _PADRAO_DATA_PAGINA.findall(pagina)]
    if not datas:
        raise ErroObtencao(f"data do arquivo não encontrada na página {url}")
    return max(datas)


def obtencao_remota(cliente: httpx.Client, fonte: FonteCgu) -> Obtencao:
    url_pagina = f"{URL_DOWNLOAD}/{fonte.caminho}"

    def gravar(destino: BinaryIO) -> ArquivoObtido:
        data_base = descobrir_data(cliente, fonte)
        url = f"{url_pagina}/{data_base:%Y%m%d}"

        def baixar() -> str:
            destino.seek(0)
            destino.truncate()
            with cliente.stream("GET", url) as resposta:
                resposta.raise_for_status()
                for bloco in resposta.iter_bytes():
                    destino.write(bloco)
                return str(resposta.url)

        url_final = _com_tentativas(baixar, f"download do {fonte.cadastro.value} de {data_base:%d/%m/%Y}")
        return ArquivoObtido(url_final, data_base, "zip")

    return Obtencao(url_pagina, gravar)


def obtencao_local(caminho: Path) -> Obtencao:
    absoluto = caminho.resolve()
    extensao = absoluto.suffix.lower().lstrip(".")

    def gravar(destino: BinaryIO) -> ArquivoObtido:
        if extensao not in EXTENSOES:
            raise ErroArquivo(f"extensão não suportada: {absoluto.name} (use .zip ou .csv)")
        with absoluto.open("rb") as origem:
            shutil.copyfileobj(origem, destino)
        return ArquivoObtido(absoluto.as_uri(), _data_local(absoluto, extensao), extensao)

    return Obtencao(absoluto.as_uri(), gravar)


def _data_local(caminho: Path, extensao: str) -> date | None:
    data = data_do_nome(caminho.name)
    if data is not None or extensao != "zip":
        return data
    try:
        with zipfile.ZipFile(caminho) as arquivo_zip:
            nomes = arquivo_zip.namelist()
    except zipfile.BadZipFile as erro:
        raise ErroArquivo(f"zip inválido ({erro})") from erro
    return next((d for d in map(data_do_nome, nomes) if d is not None), None)
