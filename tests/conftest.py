import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from validador_osc.config import Configuracao


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
    if _banco_acessivel(Configuracao().url_banco):
        return
    pular = pytest.mark.skip(reason="PostgreSQL inacessível; suba com `docker compose up -d db`")
    for item in items:
        if item.get_closest_marker("db"):
            item.add_marker(pular)
