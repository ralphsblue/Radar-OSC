import asyncio
from collections.abc import Awaitable, Callable, Iterator
from datetime import date
from pathlib import Path
from typing import Any

import openpyxl
import pytest
from sqlalchemy import Engine, create_engine, func, select

from validador_osc.bases_locais.carga import CicloCarga, ResultadoCarga, Sanidade, StatusCarga
from validador_osc.bases_locais.tcesp import COLUNAS_TCESP, FONTES_TCESP, definicao, obtencao_local
from validador_osc.persistencia.banco import criar_engine_async, criar_fabrica_sessoes
from validador_osc.persistencia.bases import RepositorioBasesLocais
from validador_osc.persistencia.modelos import Carga, TcespRegistro

pytestmark = pytest.mark.db

FONTE = "tcesp_terceiro_setor"
SANIDADE_TESTE = Sanidade(minimo_linhas=3)

LINHAS: list[tuple[object, ...]] = [
    (
        "GRUPO 1",
        1,
        "BELTRANO DA SILVA",
        "123.XXX.XXX-45",
        "111/010/20",
        "PREST.CONTAS-REPASSES TERC.SETOR-AUX/SUB/CONTR",
        "PREFEITURA MUNICIPAL X",
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
        "PREFEITURA MUNICIPAL Y",
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
        "PREFEITURA MUNICIPAL X",
        "01/01/2022",
        2021,
        None,
    ),
]


def rodar[T](engine: Engine, funcao: Callable[[RepositorioBasesLocais], Awaitable[T]]) -> T:
    async def principal() -> T:
        motor = criar_engine_async(engine.url.render_as_string(hide_password=False))
        try:
            return await funcao(RepositorioBasesLocais(criar_fabrica_sessoes(motor)))
        finally:
            await motor.dispose()

    return asyncio.run(principal(), loop_factory=asyncio.SelectorEventLoop)


@pytest.fixture
def engine(banco_limpo: str) -> Iterator[Engine]:
    motor = create_engine(banco_limpo)
    yield motor
    motor.dispose()


@pytest.fixture
def arquivos(tmp_path: Path) -> Path:
    return tmp_path / "arquivos"


def gravar_planilha(caminho: Path, linhas: list[tuple[object, ...]]) -> Path:
    livro = openpyxl.Workbook()
    planilha = livro.worksheets[0]
    planilha.append([None] * 10)
    planilha.append(list(COLUNAS_TCESP))
    for linha in linhas:
        planilha.append(list(linha))
    caminho.parent.mkdir(parents=True, exist_ok=True)
    livro.save(caminho)
    return caminho


def ingerir(
    engine: Engine, arquivos: Path, caminho: Path, sanidade: Sanidade = SANIDADE_TESTE
) -> ResultadoCarga:
    return CicloCarga(engine, arquivos).executar(
        definicao(FONTES_TCESP[FONTE], sanidade), obtencao_local(caminho)
    )


def cargas(engine: Engine) -> list[Any]:
    with engine.connect() as conexao:
        consulta = select(Carga.__table__).where(Carga.fonte == FONTE).order_by(Carga.id)
        return list(conexao.execute(consulta).mappings())


def contar(engine: Engine, carga_id: int) -> int:
    with engine.connect() as conexao:
        total = conexao.scalar(
            select(func.count()).select_from(TcespRegistro).where(TcespRegistro.carga_id == carga_id)
        )
    return int(total or 0)


def test_carga_da_relacao(engine: Engine, arquivos: Path, tmp_path: Path) -> None:
    caminho = gravar_planilha(tmp_path / "20261001_tcesp_terceiro_setor.xlsx", LINHAS)
    resultado = ingerir(engine, arquivos, caminho)
    assert resultado.status is StatusCarga.CONCLUIDA
    assert resultado.linhas == 3
    assert resultado.data_base == date(2026, 10, 1)
    (carga,) = cargas(engine)
    assert carga["ativa"] is True
    assert contar(engine, carga["id"]) == 3


def test_leitura_por_nome_normalizado(engine: Engine, arquivos: Path, tmp_path: Path) -> None:
    caminho = gravar_planilha(tmp_path / "20261001_tcesp_terceiro_setor.xlsx", LINHAS)
    ingerir(engine, arquivos, caminho)
    achado = rodar(engine, lambda r: r.tcesp_pf("BELTRANO DA SILVA"))
    assert achado is not None
    assert achado.carga.fonte == FONTE
    assert achado.carga.data_base == date(2026, 10, 1)
    assert len(achado.registros) == 2
    processos = sorted(r.processo for r in achado.registros if r.processo is not None)
    assert processos == ["111/010/20", "333/012/22"]
    (registro,) = [r for r in achado.registros if r.processo == "111/010/20"]
    assert registro.cpf_inicio == "123"
    assert registro.cpf_fim == "45"
    assert registro.data_transito == date(2020, 5, 10)
    assert registro.exercicio == "2019"
    ausente = rodar(engine, lambda r: r.tcesp_pf("NOME QUE NAO EXISTE"))
    assert ausente is not None
    assert ausente.registros == ()


def test_sem_carga_ativa_devolve_none(engine: Engine, arquivos: Path) -> None:
    del arquivos
    assert rodar(engine, lambda r: r.tcesp_pf("QUALQUER NOME")) is None


def test_minimo_real_de_linhas_falha(engine: Engine, arquivos: Path, tmp_path: Path) -> None:
    caminho = gravar_planilha(tmp_path / "20261001_tcesp_terceiro_setor.xlsx", LINHAS)
    resultado = ingerir(engine, arquivos, caminho, FONTES_TCESP[FONTE].sanidade)
    assert resultado.status is StatusCarga.FALHOU
    assert resultado.erro is not None
    assert "abaixo do mínimo de 8" in resultado.erro
