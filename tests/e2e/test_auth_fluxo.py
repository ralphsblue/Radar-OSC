import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.db


def test_registrar_seta_cookie_e_redireciona_ao_painel(cliente: TestClient) -> None:
    resposta = cliente.post(
        "/registrar",
        data={"email": "pessoa@exemplo.org", "senha": "senha-forte-123"},
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/painel"
    assert "vosc_token" in resposta.cookies


def test_registrar_com_email_repetido_e_rejeitado(cliente: TestClient) -> None:
    cliente.post("/registrar", data={"email": "pessoa@exemplo.org", "senha": "senha-forte-123"})

    resposta = cliente.post("/registrar", data={"email": "pessoa@exemplo.org", "senha": "outra-senha-123"})

    assert resposta.status_code == 409
    assert "Já existe uma conta" in resposta.text


def test_entrar_com_senha_errada_e_rejeitado(cliente: TestClient) -> None:
    cliente.post("/registrar", data={"email": "pessoa@exemplo.org", "senha": "senha-forte-123"})

    resposta = cliente.post(
        "/entrar", data={"email": "pessoa@exemplo.org", "senha": "senha-errada"}, follow_redirects=False
    )

    assert resposta.status_code == 401
    assert "incorretos" in resposta.text


def test_entrar_com_senha_correta_seta_cookie(cliente: TestClient) -> None:
    cliente.post("/registrar", data={"email": "pessoa@exemplo.org", "senha": "senha-forte-123"})
    cliente.cookies.clear()

    resposta = cliente.post(
        "/entrar",
        data={"email": "pessoa@exemplo.org", "senha": "senha-forte-123"},
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/painel"
    assert "vosc_token" in resposta.cookies


def test_painel_redireciona_para_entrar_sem_cookie(cliente: TestClient) -> None:
    resposta = cliente.get("/painel", follow_redirects=False)

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/entrar"


def test_painel_mostra_conteudo_com_cookie_valido(cliente: TestClient) -> None:
    cliente.post("/registrar", data={"email": "pessoa@exemplo.org", "senha": "senha-forte-123"})

    resposta = cliente.get("/painel")

    assert resposta.status_code == 200
    assert "Painel" in resposta.text


def test_sair_limpa_o_cookie(cliente: TestClient) -> None:
    cliente.post("/registrar", data={"email": "pessoa@exemplo.org", "senha": "senha-forte-123"})

    resposta = cliente.post("/sair", follow_redirects=False)

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/"
    assert cliente.cookies.get("vosc_token") is None

    pagina_painel = cliente.get("/painel", follow_redirects=False)
    assert pagina_painel.status_code == 303
    assert pagina_painel.headers["location"] == "/entrar"
