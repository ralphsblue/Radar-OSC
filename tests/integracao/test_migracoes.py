import asyncio

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

from validador_osc.api.app import criar_app
from validador_osc.config import Configuracao
from validador_osc.persistencia.modelos import Base

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def banco_migrado() -> str:
    url = Configuracao().url_banco
    alembic = Config("alembic.ini")
    alembic.set_main_option("sqlalchemy.url", url)
    command.downgrade(alembic, "base")
    command.upgrade(alembic, "head")
    return url


def test_tabelas_criadas(banco_migrado: str) -> None:
    engine = create_engine(banco_migrado)
    try:
        tabelas = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert {"resposta_fonte", "carga", "consulta", "consulta_evidencia", "alembic_version"} <= tabelas


def test_modelos_e_migracoes_nao_divergem(banco_migrado: str) -> None:
    engine = create_engine(banco_migrado)
    try:
        with engine.connect() as conexao:
            diferencas = compare_metadata(MigrationContext.configure(conexao), Base.metadata)
    finally:
        engine.dispose()
    assert diferencas == []


def test_prontidao_com_banco_migrado(banco_migrado: str) -> None:
    del banco_migrado
    opcoes = {"loop_factory": asyncio.SelectorEventLoop}
    with TestClient(criar_app(Configuracao()), backend_options=opcoes) as cliente:
        resposta = cliente.get("/health/ready")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}
