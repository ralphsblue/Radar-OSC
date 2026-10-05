import io
from datetime import date
from pathlib import Path

import httpx
import openpyxl
import pytest

from validador_osc.bases_locais.carga import ErroArquivo
from validador_osc.bases_locais.obtencao import ErroObtencao
from validador_osc.bases_locais.tcesp import (
    COLUNAS_TCESP,
    FONTES_TCESP,
    converter,
    data_do_nome,
    ler_arquivo,
    ler_registros,
    obtencao_local,
    obtencao_remota,
)

LINHAS_BASE: list[tuple[object, ...]] = [
    (
        "FULANO AGRUPADOR",
        1,
        "BELTRANO DA SILVA",
        "123.XXX.XXX-45",
        "111/010/20",
        "PREST.CONTAS",
        "PREFEITURA X",
        "10/05/2020",
        2019,
        None,
    ),
    (
        None,
        2,
        "CICLANA DE TAL",
        "456.XXX.XXX-78",
        "222/011/21",
        "TERMO DE PARCERIA",
        "PREFEITURA Y",
        "15/08/2021",
        2020,
        None,
    ),
    (
        None,
        3,
        "BELTRANO DA SILVA",
        "123.XXX.XXX-45",
        "333/012/22",
        "CONTRATO DE GESTAO",
        "PREFEITURA X",
        "01/01/2022",
        2021,
        None,
    ),
]

VAZIA: tuple[object, ...] = (None,) * 10


def gravar_planilha(caminho: Path, linhas: list[tuple[object, ...]]) -> Path:
    livro = openpyxl.Workbook()
    planilha = livro.worksheets[0]
    planilha.append(list(VAZIA))
    planilha.append(list(VAZIA))
    planilha.append(
        [None, None, None, None, None, "Trânsito em julgado até 01/10/2026", None, None, None, None]
    )
    planilha.append(list(VAZIA))
    planilha.append(list(COLUNAS_TCESP))
    for linha in linhas:
        planilha.append(list(linha))
    caminho.parent.mkdir(parents=True, exist_ok=True)
    livro.save(caminho)
    return caminho


def fixture(tmp_path: Path, linhas: list[tuple[object, ...]] | None = None) -> Path:
    return gravar_planilha(tmp_path / "20261001_tcesp_terceiro_setor.xlsx", linhas or LINHAS_BASE)


def test_fonte_registrada() -> None:
    assert list(FONTES_TCESP) == ["tcesp_terceiro_setor"]
    assert FONTES_TCESP["tcesp_terceiro_setor"].sanidade.minimo_linhas == 8_000


def test_colunas_e_registros_da_fixture(tmp_path: Path) -> None:
    with ler_registros(fixture(tmp_path)) as (colunas, registros):
        lidos = list(registros)
    assert colunas == COLUNAS_TCESP
    assert len(lidos) == 3
    beltrano = next(
        r for r in lidos if r.registro.nome == "BELTRANO DA SILVA" and r.registro.processo == "111/010/20"
    )
    assert beltrano.registro.cpf_inicio == "123"
    assert beltrano.registro.cpf_fim == "45"
    assert beltrano.registro.materia == "PREST.CONTAS"
    assert beltrano.registro.origem == "PREFEITURA X"
    assert beltrano.registro.data_transito == date(2020, 5, 10)
    assert beltrano.registro.exercicio == "2019"
    assert beltrano.nome_normalizado == "BELTRANO DA SILVA"
    assert beltrano.linha["cpf"] == "123.XXX.XXX-45"


def test_rodape_e_linhas_vazias_nao_sao_dados(tmp_path: Path) -> None:
    linhas: list[tuple[object, ...]] = [
        *LINHAS_BASE,
        VAZIA,
        (None, None, None, "Fonte: http://exemplo Total de Registros: 3", None, None, None, None, None, None),
    ]
    with ler_registros(fixture(tmp_path, linhas)) as (_, registros):
        assert len(list(registros)) == 3


def test_cpf_sem_digitos_e_ignorado(tmp_path: Path) -> None:
    linhas: list[tuple[object, ...]] = [
        *LINHAS_BASE,
        (
            None,
            4,
            "SEM CPF VALIDO",
            "XXX.XXX",
            "444/013/22",
            "AUX/SUB",
            "PREFEITURA Z",
            "01/02/2022",
            2021,
            None,
        ),
    ]
    with ler_registros(fixture(tmp_path, linhas)) as (_, registros):
        assert len(list(registros)) == 3


def test_leitura_para_tabela(tmp_path: Path) -> None:
    with ler_arquivo(fixture(tmp_path)) as leitura:
        linhas = list(leitura.registros)
    assert leitura.colunas == COLUNAS_TCESP
    assert len(linhas) == 3
    assert all(linha["cpf_inicio"] and linha["cpf_fim"] for linha in linhas)


@pytest.mark.parametrize(
    ("campos", "mensagem"),
    [
        ((None, 1, "", "123.XXX.XXX-45", "1/1/20", "M", "O", "10/05/2020", 2019, None), "nome vazio"),
        (
            (None, 1, "FULANO", "123.XXX.XXX-45", "1/1/20", "M", "O", "31/02/2020", 2019, None),
            "Trânsito em Julgado com data inválida",
        ),
    ],
)
def test_registro_invalido(campos: tuple[object, ...], mensagem: str) -> None:
    with pytest.raises(ErroArquivo, match=mensagem):
        converter(campos, 1)


def test_cabecalho_ausente_falha(tmp_path: Path) -> None:
    caminho = tmp_path / "sem_cabecalho.xlsx"
    livro = openpyxl.Workbook()
    livro.worksheets[0].append(["a", "b", "c"])
    livro.save(caminho)
    with pytest.raises(ErroArquivo, match="cabeçalho"), ler_registros(caminho) as (_, registros):
        list(registros)


def test_xlsx_invalido_falha(tmp_path: Path) -> None:
    caminho = tmp_path / "invalido.xlsx"
    caminho.write_bytes(b"nao e um xlsx")
    with pytest.raises(ErroArquivo, match="xlsx inválido"), ler_registros(caminho) as (_, registros):
        list(registros)


def test_data_do_nome() -> None:
    assert data_do_nome("20261001_tcesp_terceiro_setor.xlsx") == date(2026, 10, 1)
    nome_real = "contas%20irregulares%20de%2001-01-1900%20a%2001-10-2026_Prest_Contas_CPF_anonimizado.xlsx"
    assert data_do_nome(nome_real) == date(2026, 10, 1)
    assert data_do_nome("arquivo_sem_data.xlsx") is None


def test_obtencao_local(tmp_path: Path) -> None:
    caminho = fixture(tmp_path)
    destino = io.BytesIO()
    obtido = obtencao_local(caminho).gravar(destino)
    assert destino.getvalue() == caminho.read_bytes()
    assert obtido.data_base == date(2026, 10, 1)
    assert obtido.extensao == "xlsx"
    naoxlsx = tmp_path / "20261001_tcesp_terceiro_setor.csv"
    naoxlsx.write_text("x")
    with pytest.raises(ErroArquivo, match="extensão não suportada"):
        obtencao_local(naoxlsx).gravar(io.BytesIO())


PAGINA_HTML = (
    '<div><a href="https://www.tce.sp.gov.br/sites/default/files/portal/'
    "contas%20irregulares%20de%2001-01-1900%20a%2001-10-2026_"
    'Prest_Contas_CPF_anonimizado.xlsx" type="application/vnd">link</a>'
    "<strong>Última atualização em 01/10/2026.</strong></div>"
)


class Plataforma:
    def __init__(self, pagina: bytes, arquivo: bytes) -> None:
        self.pagina = pagina
        self.arquivo = arquivo
        self.requisicoes: list[httpx.Request] = []

    def responder(self, requisicao: httpx.Request) -> httpx.Response:
        self.requisicoes.append(requisicao)
        if str(requisicao.url).endswith(".xlsx"):
            return httpx.Response(200, content=self.arquivo)
        return httpx.Response(200, content=self.pagina)


def test_obtencao_remota_acha_link_e_data(tmp_path: Path) -> None:
    conteudo = fixture(tmp_path).read_bytes()
    plataforma = Plataforma(PAGINA_HTML.encode("utf-8"), conteudo)
    destino = io.BytesIO()
    with httpx.Client(transport=httpx.MockTransport(plataforma.responder)) as cliente:
        obtido = obtencao_remota(cliente).gravar(destino)
    assert destino.getvalue() == conteudo
    assert obtido.data_base == date(2026, 10, 1)
    assert obtido.extensao == "xlsx"
    assert obtido.url.endswith("Prest_Contas_CPF_anonimizado.xlsx")


def test_obtencao_remota_sem_link_falha() -> None:
    plataforma = Plataforma(b"<html>sem link</html>", b"")
    with (
        httpx.Client(transport=httpx.MockTransport(plataforma.responder)) as cliente,
        pytest.raises(ErroObtencao, match="link do xlsx"),
    ):
        obtencao_remota(cliente).gravar(io.BytesIO())
