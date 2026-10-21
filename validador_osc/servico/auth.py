import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError

from validador_osc.persistencia.repositorios import NovoUsuario, RepositorioUsuarios

ALGORITMO = "HS256"


def _agora() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class Credenciais:
    email: str
    senha: str


@dataclass(frozen=True, slots=True)
class TokenEmitido:
    token: str
    usuario_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class UsuarioAutenticado:
    id: uuid.UUID
    email: str


class ErroAutenticacao(Exception):
    pass


class EmailJaCadastrado(ErroAutenticacao):
    pass


class CredenciaisInvalidas(ErroAutenticacao):
    pass


class ServicoAuth:
    def __init__(
        self,
        usuarios: RepositorioUsuarios,
        segredo: SecretStr,
        expiracao_min: int,
        relogio: Callable[[], datetime] | None = None,
    ) -> None:
        self._usuarios = usuarios
        self._segredo = segredo.get_secret_value()
        self._expiracao = timedelta(minutes=expiracao_min)
        self._relogio = relogio or _agora

    async def registrar(self, credenciais: Credenciais) -> TokenEmitido:
        email = credenciais.email.strip().lower()
        senha_hash = bcrypt.hashpw(credenciais.senha.encode("utf-8"), bcrypt.gensalt()).decode("ascii")
        usuario_id = uuid.uuid4()
        try:
            await self._usuarios.criar(
                NovoUsuario(id=usuario_id, email=email, senha_hash=senha_hash, criado_em=self._relogio())
            )
        except IntegrityError as erro:
            raise EmailJaCadastrado(email) from erro
        return self._emitir(usuario_id)

    async def autenticar(self, credenciais: Credenciais) -> TokenEmitido:
        email = credenciais.email.strip().lower()
        usuario = await self._usuarios.por_email(email)
        if usuario is None or not bcrypt.checkpw(
            credenciais.senha.encode("utf-8"), usuario.senha_hash.encode("utf-8")
        ):
            raise CredenciaisInvalidas(email)
        return self._emitir(usuario.id)

    def verificar_token(self, token: str) -> uuid.UUID | None:
        try:
            payload = jwt.decode(token, self._segredo, algorithms=[ALGORITMO])
        except jwt.PyJWTError:
            return None
        try:
            return uuid.UUID(str(payload["sub"]))
        except KeyError, ValueError:
            return None

    async def obter_usuario(self, usuario_id: uuid.UUID) -> UsuarioAutenticado | None:
        usuario = await self._usuarios.por_id(usuario_id)
        if usuario is None or not usuario.ativo:
            return None
        return UsuarioAutenticado(usuario.id, usuario.email)

    def _emitir(self, usuario_id: uuid.UUID) -> TokenEmitido:
        agora = self._relogio()
        payload = {
            "sub": str(usuario_id),
            "iat": int(agora.timestamp()),
            "exp": int((agora + self._expiracao).timestamp()),
        }
        token = jwt.encode(payload, self._segredo, algorithm=ALGORITMO)
        return TokenEmitido(token, usuario_id)
