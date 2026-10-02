import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.exc import OperationalError

from validador_osc.config import Configuracao

RAIZ = Path(__file__).parent.parent
TABELAS = (
    "consulta_evidencia",
    "consulta",
    "resposta_fonte",
    "sancao_registro",
    "lista_tcu_registro",
    "carga",
)


def _url_teste() -> str:
    explicita = os.environ.get("VOSC_TEST_DATABASE_URL")
    if explicita:
        return explicita
    url = make_url(Configuracao().url_banco)
    return url.set(database=f"{url.database}_teste").render_as_string(hide_password=False)


URL_TESTE = _url_teste()
os.environ["VOSC_DATABASE_URL"] = URL_TESTE


def _url_admin(url: str) -> str:
    return make_url(url).set(database="postgres").render_as_string(hide_password=False)


def _garantir_banco(url: str) -> None:
    alvo = make_url(url)
    admin = create_engine(_url_admin(url), isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 2})
    try:
        with admin.connect() as conexao:
            existe = conexao.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :nome"), {"nome": alvo.database}
            )
            if not existe:
                conexao.execute(text(f'CREATE DATABASE "{alvo.database}"'))
    finally:
        admin.dispose()


def _banco_acessivel(url: str) -> bool:
    engine = create_engine(url, connect_args={"connect_timeout": 2})
    try:
        with engine.connect() as conexao:
            conexao.execute(text("SELECT 1"))
    except OperationalError:
        return False
    finally:
        engine.dispose()
    return True


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    del config
    if os.environ.get("CI"):
        return
    if not any(item.get_closest_marker("db") for item in items):
        return
    if _banco_acessivel(_url_admin(URL_TESTE)):
        _garantir_banco(URL_TESTE)
        return
    pular = pytest.mark.skip(reason="PostgreSQL inacessível; suba com `docker compose up -d db`")
    for item in items:
        if item.get_closest_marker("db"):
            item.add_marker(pular)


@pytest.fixture(scope="session")
def url_banco() -> str:
    url = Configuracao().url_banco
    alembic = Config(str(RAIZ / "alembic.ini"))
    alembic.set_main_option("sqlalchemy.url", url)
    command.upgrade(alembic, "head")
    return url


@pytest.fixture
def banco_limpo(url_banco: str) -> str:
    engine = create_engine(url_banco)
    try:
        with engine.begin() as conexao:
            conexao.execute(text(f"TRUNCATE {', '.join(TABELAS)} RESTART IDENTITY CASCADE"))
    finally:
        engine.dispose()
    return url_banco
