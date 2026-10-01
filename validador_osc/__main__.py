import argparse
from collections.abc import Callable, Sequence

import uvicorn

from validador_osc.config import obter_configuracao


def _servir(argumentos: argparse.Namespace) -> int:
    uvicorn.run(
        "validador_osc.api.app:criar_app",
        factory=True,
        host=argumentos.host,
        port=argumentos.porta,
        reload=argumentos.recarregar,
        loop="asyncio:SelectorEventLoop",
        log_config=None,
    )
    return 0


def _configuracao(argumentos: argparse.Namespace) -> int:
    del argumentos
    config = obter_configuracao()
    for nome, valor in config.model_dump(mode="json").items():
        print(f"{nome}={valor}")
    return 0


def _analisador() -> argparse.ArgumentParser:
    analisador = argparse.ArgumentParser(prog="validador-osc")
    sub = analisador.add_subparsers(dest="comando", required=True)

    servir = sub.add_parser("servir", help="sobe a API e as páginas")
    servir.add_argument("--host", default="127.0.0.1")
    servir.add_argument("--porta", type=int, default=8000)
    servir.add_argument("--recarregar", action="store_true")
    servir.set_defaults(executar=_servir)

    configuracao = sub.add_parser("configuracao", help="mostra a configuração efetiva sem segredos")
    configuracao.set_defaults(executar=_configuracao)
    return analisador


def main(argv: Sequence[str] | None = None) -> int:
    argumentos = _analisador().parse_args(argv)
    executar: Callable[[argparse.Namespace], int] = argumentos.executar
    return executar(argumentos)


if __name__ == "__main__":
    raise SystemExit(main())
