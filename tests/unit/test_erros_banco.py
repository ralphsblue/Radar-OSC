import asyncio
from typing import NoReturn

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, OperationalError

from validador_osc.api.app import criar_app
from validador_osc.config import Configuracao
from validador_osc.servico.consulta import PedidoConsulta

OPCOES = {"loop_factory": asyncio.SelectorEventLoop}


@pytest.mark.parametrize(
    ("erro", "status", "titulo"),
    [
        (OperationalError("SELECT 1", {}, Exception("conexão recusada")), 503, "Serviço indisponível"),
        (IntegrityError("INSERT", {}, Exception("violação de chave")), 500, "Erro interno"),
    ],
)
def test_erros_de_banco_viram_problema_com_status_certo(
    erro: Exception, status: int, titulo: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def falhar(pedido: PedidoConsulta) -> NoReturn:
        del pedido
        raise erro

    app = criar_app(Configuracao())
    with TestClient(app, backend_options=OPCOES) as cliente:
        monkeypatch.setattr(app.state.contexto.consultas, "executar", falhar)
        resposta = cliente.post("/api/v1/consultas", json={"cnpj": "19131243000197"})

    assert resposta.status_code == status
    assert resposta.headers["content-type"] == "application/problem+json"
    assert resposta.json()["title"] == titulo
