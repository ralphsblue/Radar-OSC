import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from validador_osc.persistencia.repositorios import NovoUsuario, RepositorioUsuarios, UsuarioRegistro
from validador_osc.servico.auth import (
    ALGORITMO,
    Credenciais,
    CredenciaisInvalidas,
    EmailJaCadastrado,
    ServicoAuth,
)


class RepositorioUsuariosEmMemoria(RepositorioUsuarios):
    def __init__(self) -> None:
        super().__init__(async_sessionmaker())
        self._por_email: dict[str, UsuarioRegistro] = {}
        self._por_id: dict[uuid.UUID, UsuarioRegistro] = {}

    async def criar(self, novo: NovoUsuario) -> None:
        if novo.email in self._por_email:
            raise IntegrityError("INSERT", {}, Exception("violação de chave"))
        registro = UsuarioRegistro(novo.id, novo.email, novo.senha_hash, ativo=True)
        self._por_email[novo.email] = registro
        self._por_id[novo.id] = registro

    async def por_email(self, email: str) -> UsuarioRegistro | None:
        return self._por_email.get(email)

    async def por_id(self, usuario_id: uuid.UUID) -> UsuarioRegistro | None:
        return self._por_id.get(usuario_id)


class Relogio:
    def __init__(self, agora: datetime) -> None:
        self.agora = agora

    def __call__(self) -> datetime:
        return self.agora


SEGREDO = SecretStr("segredo-de-teste")


def _servico(expiracao_min: int = 720, relogio: Relogio | None = None) -> ServicoAuth:
    return ServicoAuth(RepositorioUsuariosEmMemoria(), SEGREDO, expiracao_min, relogio)


def test_registrar_nunca_guarda_a_senha_em_texto_puro() -> None:
    servico = _servico()
    senha = "senha-forte-123"
    emitido = asyncio.run(servico.registrar(Credenciais("Pessoa@Exemplo.org", senha)))
    guardado = asyncio.run(servico._usuarios.por_email("pessoa@exemplo.org"))
    assert guardado is not None
    assert guardado.senha_hash != senha
    assert guardado.id == emitido.usuario_id


def test_registrar_com_email_repetido_leva_a_email_ja_cadastrado() -> None:
    servico = _servico()
    asyncio.run(servico.registrar(Credenciais("pessoa@exemplo.org", "senha-forte-123")))
    with pytest.raises(EmailJaCadastrado):
        asyncio.run(servico.registrar(Credenciais("PESSOA@exemplo.org", "outra-senha-123")))


def test_autenticar_com_senha_correta_emite_token_do_usuario() -> None:
    servico = _servico()
    emitido = asyncio.run(servico.registrar(Credenciais("pessoa@exemplo.org", "senha-forte-123")))
    autenticado = asyncio.run(servico.autenticar(Credenciais("pessoa@exemplo.org", "senha-forte-123")))
    assert autenticado.usuario_id == emitido.usuario_id
    assert servico.verificar_token(autenticado.token) == emitido.usuario_id


def test_autenticar_com_senha_errada_leva_a_credenciais_invalidas() -> None:
    servico = _servico()
    asyncio.run(servico.registrar(Credenciais("pessoa@exemplo.org", "senha-forte-123")))
    with pytest.raises(CredenciaisInvalidas):
        asyncio.run(servico.autenticar(Credenciais("pessoa@exemplo.org", "senha-errada")))


def test_autenticar_com_email_inexistente_leva_a_credenciais_invalidas() -> None:
    servico = _servico()
    with pytest.raises(CredenciaisInvalidas):
        asyncio.run(servico.autenticar(Credenciais("ninguem@exemplo.org", "senha-forte-123")))


def test_verificar_token_expirado_e_rejeitado() -> None:
    relogio = Relogio(datetime(2026, 1, 1, tzinfo=UTC))
    servico = _servico(expiracao_min=1, relogio=relogio)
    emitido = asyncio.run(servico.registrar(Credenciais("pessoa@exemplo.org", "senha-forte-123")))
    relogio.agora = relogio.agora + timedelta(minutes=2)
    assert servico.verificar_token(emitido.token) is None


def test_verificar_token_adulterado_e_rejeitado() -> None:
    servico = _servico()
    emitido = asyncio.run(servico.registrar(Credenciais("pessoa@exemplo.org", "senha-forte-123")))
    adulterado = emitido.token[:-1] + ("a" if emitido.token[-1] != "a" else "b")
    assert servico.verificar_token(adulterado) is None


def test_verificar_token_assinado_com_outro_segredo_e_rejeitado() -> None:
    servico = _servico()
    usuario_id = uuid.uuid4()
    token_estranho = jwt.encode({"sub": str(usuario_id)}, "outro-segredo", algorithm=ALGORITMO)
    assert servico.verificar_token(token_estranho) is None
