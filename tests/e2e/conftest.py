from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from tests.e2e.replay import OPCOES_CLIENTE, OpenCnpjReplay, RelogioFixo
from validador_osc.api.app import criar_app
from validador_osc.config import Configuracao


@pytest.fixture
def replay() -> OpenCnpjReplay:
    return OpenCnpjReplay()


@pytest.fixture
def relogio() -> RelogioFixo:
    return RelogioFixo()


@pytest.fixture
def cliente(banco_limpo: str, replay: OpenCnpjReplay, relogio: RelogioFixo) -> Iterator[TestClient]:
    configuracao = Configuracao(database_url=banco_limpo)
    app = criar_app(configuracao, replay.transporte, relogio)
    with TestClient(app, backend_options=OPCOES_CLIENTE) as cliente_http:
        yield cliente_http
