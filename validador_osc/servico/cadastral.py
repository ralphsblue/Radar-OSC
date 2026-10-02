from typing import Protocol

import structlog

from validador_osc.dominio.coleta import Coleta, Falha, NaoEncontrado, Obtido
from validador_osc.dominio.tipos import Cadastro

log = structlog.get_logger()


class FonteCadastral(Protocol):
    nome: str

    async def consultar(self, cnpj: str, *, ignorar_cache: bool = False) -> Coleta[Cadastro]: ...


class CadastralComReserva:
    nome = "cadastral"

    def __init__(self, principal: FonteCadastral, reserva: FonteCadastral) -> None:
        self._principal = principal
        self._reserva = reserva

    async def consultar(self, cnpj: str, *, ignorar_cache: bool = False) -> Coleta[Cadastro]:
        principal = await self._principal.consultar(cnpj, ignorar_cache=ignorar_cache)
        if isinstance(principal, Obtido):
            return principal
        log.info(
            "fonte_reserva_acionada",
            principal=self._principal.nome,
            reserva=self._reserva.nome,
            motivo=type(principal).__name__,
        )
        reserva = await self._reserva.consultar(cnpj, ignorar_cache=ignorar_cache)
        match principal, reserva:
            case _, Obtido():
                return reserva
            case NaoEncontrado(), _:
                return principal
            case Falha(), NaoEncontrado():
                return reserva
            case _:
                return principal
