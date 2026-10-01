from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol

from validador_osc.dominio.coleta import MotivoFalha, RefEvidencia


class ResultadoResposta(StrEnum):
    OBTIDO = "OBTIDO"
    NAO_ENCONTRADO = "NAO_ENCONTRADO"
    FALHA = "FALHA"


@dataclass(frozen=True, slots=True)
class RespostaBruta:
    fonte: str
    chave: str
    url: str
    resultado: ResultadoResposta
    recebida_em: datetime
    duracao_ms: int
    tentativas: int
    http_status: int | None = None
    content_type: str | None = None
    corpo: bytes | None = None
    motivo_falha: MotivoFalha | None = None


@dataclass(frozen=True, slots=True)
class RespostaGuardada:
    resultado: ResultadoResposta
    corpo: bytes | None
    evidencia: RefEvidencia


class Evidencias(Protocol):
    async def gravar(self, resposta: RespostaBruta) -> RefEvidencia: ...

    async def buscar_recente(
        self, fonte: str, chave: str, validade: timedelta, agora: datetime
    ) -> RespostaGuardada | None: ...
