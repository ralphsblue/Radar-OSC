import time
from collections.abc import Callable

import httpx

from validador_osc.bases_locais.carga import ErroCarga

TENTATIVAS = 3


class ErroObtencao(ErroCarga):
    pass


def com_tentativas[T](acao: Callable[[], T], descricao: str, pausa_s: float) -> T:
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            return acao()
        except httpx.HTTPStatusError as erro:
            if erro.response.status_code < httpx.codes.INTERNAL_SERVER_ERROR or tentativa == TENTATIVAS:
                raise ErroObtencao(f"{descricao}: HTTP {erro.response.status_code}") from erro
        except httpx.HTTPError as erro:
            if tentativa == TENTATIVAS:
                raise ErroObtencao(f"{descricao}: {type(erro).__name__} {erro}") from erro
        time.sleep(pausa_s * tentativa)
    raise ErroObtencao(descricao)
