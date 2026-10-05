import time
from collections import defaultdict, deque
from collections.abc import Callable


class LimitePorCliente:
    def __init__(
        self, maximo: int, janela_s: float = 60.0, relogio: Callable[[], float] = time.monotonic
    ) -> None:
        self._maximo = maximo
        self._janela_s = janela_s
        self._relogio = relogio
        self._registros: defaultdict[str, deque[float]] = defaultdict(deque)

    def permitir(self, cliente: str) -> bool:
        if self._maximo <= 0:
            return True
        agora = self._relogio()
        fila = self._registros[cliente]
        while fila and agora - fila[0] >= self._janela_s:
            fila.popleft()
        if len(fila) >= self._maximo:
            return False
        fila.append(agora)
        return True
