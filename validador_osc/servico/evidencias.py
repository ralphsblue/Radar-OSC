from dataclasses import dataclass

from validador_osc.persistencia.repositorios import RepositorioEvidencias


@dataclass(frozen=True, slots=True)
class EvidenciaBruta:
    id: int
    fonte: str
    url: str
    content_type: str | None
    sha256: str | None
    corpo: bytes


class ServicoEvidencias:
    def __init__(self, repositorio: RepositorioEvidencias) -> None:
        self._repositorio = repositorio

    async def obter(self, evidencia_id: int) -> EvidenciaBruta | None:
        linha = await self._repositorio.obter(evidencia_id)
        if linha is None or linha.corpo is None:
            return None
        return EvidenciaBruta(linha.id, linha.fonte, linha.url, linha.content_type, linha.sha256, linha.corpo)
