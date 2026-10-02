import logging
import sys
from typing import TextIO, cast

import structlog

from validador_osc.config import Configuracao, FormatoLog


class _SaidaDeErroAtual:
    def write(self, texto: str) -> int:
        return sys.stderr.write(texto)

    def flush(self) -> None:
        sys.stderr.flush()


def configurar_logs(config: Configuracao) -> None:
    nivel = logging.getLevelNamesMapping()[config.log_nivel.upper()]
    renderizador: structlog.typing.Processor = (
        structlog.processors.JSONRenderer()
        if config.log_formato is FormatoLog.JSON
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderizador,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(nivel),
        logger_factory=structlog.PrintLoggerFactory(cast(TextIO, _SaidaDeErroAtual())),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=nivel, stream=sys.stderr, format="%(message)s")
