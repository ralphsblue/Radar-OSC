import asyncio
from dataclasses import dataclass, field

import pytest

from tests.unit.fabricas import EVIDENCIA, coleta_obtida
from validador_osc.dominio.coleta import Coleta, Falha, MotivoFalha, NaoEncontrado
from validador_osc.dominio.tipos import Cadastro
from validador_osc.servico.cadastral import CadastralComReserva

CNPJ = "19131243000197"
OBTIDO_PRINCIPAL = coleta_obtida(fonte="opencnpj")
OBTIDO_RESERVA = coleta_obtida(fonte="brasilapi")
NAO_ENCONTRADO_PRINCIPAL = NaoEncontrado(EVIDENCIA)
NAO_ENCONTRADO_RESERVA = NaoEncontrado(None)
FALHA_PRINCIPAL = Falha(MotivoFalha.HTTP_5XX, "HTTP 503")
FALHA_RESERVA = Falha(MotivoFalha.TIMEOUT, "ReadTimeout")


@dataclass
class FonteFixa:
    nome: str
    resposta: Coleta[Cadastro]
    chamadas: list[tuple[str, bool]] = field(default_factory=list)

    async def consultar(self, cnpj: str, *, ignorar_cache: bool = False) -> Coleta[Cadastro]:
        self.chamadas.append((cnpj, ignorar_cache))
        return self.resposta


def consultar(
    principal: Coleta[Cadastro], reserva: Coleta[Cadastro], ignorar_cache: bool = False
) -> tuple[Coleta[Cadastro], FonteFixa, FonteFixa]:
    fonte_principal = FonteFixa("opencnpj", principal)
    fonte_reserva = FonteFixa("brasilapi", reserva)
    cadastral = CadastralComReserva(fonte_principal, fonte_reserva)
    resultado = asyncio.run(cadastral.consultar(CNPJ, ignorar_cache=ignorar_cache))
    return resultado, fonte_principal, fonte_reserva


@pytest.mark.parametrize("reserva", [OBTIDO_RESERVA, NAO_ENCONTRADO_RESERVA, FALHA_RESERVA])
def test_principal_obtido_nao_aciona_a_reserva(reserva: Coleta[Cadastro]) -> None:
    resultado, principal, fonte_reserva = consultar(OBTIDO_PRINCIPAL, reserva)

    assert resultado is OBTIDO_PRINCIPAL
    assert principal.chamadas == [(CNPJ, False)]
    assert fonte_reserva.chamadas == []


@pytest.mark.parametrize(
    ("principal", "reserva", "esperado"),
    [
        pytest.param(NAO_ENCONTRADO_PRINCIPAL, OBTIDO_RESERVA, OBTIDO_RESERVA, id="404-obtido"),
        pytest.param(
            NAO_ENCONTRADO_PRINCIPAL, NAO_ENCONTRADO_RESERVA, NAO_ENCONTRADO_PRINCIPAL, id="404-404"
        ),
        pytest.param(NAO_ENCONTRADO_PRINCIPAL, FALHA_RESERVA, NAO_ENCONTRADO_PRINCIPAL, id="404-falha"),
        pytest.param(FALHA_PRINCIPAL, OBTIDO_RESERVA, OBTIDO_RESERVA, id="falha-obtido"),
        pytest.param(FALHA_PRINCIPAL, NAO_ENCONTRADO_RESERVA, NAO_ENCONTRADO_RESERVA, id="falha-404"),
        pytest.param(FALHA_PRINCIPAL, FALHA_RESERVA, FALHA_PRINCIPAL, id="falha-falha"),
    ],
)
def test_principal_sem_cadastro_aciona_a_reserva(
    principal: Coleta[Cadastro], reserva: Coleta[Cadastro], esperado: Coleta[Cadastro]
) -> None:
    resultado, fonte_principal, fonte_reserva = consultar(principal, reserva)

    assert resultado is esperado
    assert fonte_principal.chamadas == [(CNPJ, False)]
    assert fonte_reserva.chamadas == [(CNPJ, False)]


def test_ignorar_cache_chega_as_duas_fontes() -> None:
    _, principal, reserva = consultar(FALHA_PRINCIPAL, OBTIDO_RESERVA, ignorar_cache=True)

    assert principal.chamadas == [(CNPJ, True)]
    assert reserva.chamadas == [(CNPJ, True)]
