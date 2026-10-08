import argparse
from collections.abc import Callable, Sequence
from pathlib import Path

import uvicorn

from validador_osc.bases_locais.atualizacao import FONTES_IMPLEMENTADAS, Atualizador, criar_cliente
from validador_osc.bases_locais.carga import ResultadoCarga, StatusCarga
from validador_osc.config import obter_configuracao
from validador_osc.logs import configurar_logs
from validador_osc.persistencia.banco import criar_engine

LARGURA_FONTE = max(map(len, FONTES_IMPLEMENTADAS))


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


def _milhar(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def _linha_resumo(resultado: ResultadoCarga) -> str:
    linhas = _milhar(resultado.linhas) if resultado.linhas is not None else "-"
    data = resultado.data_base.strftime("%d/%m/%Y") if resultado.data_base is not None else "-"
    texto = (
        f"{resultado.fonte:<{LARGURA_FONTE}} {resultado.status.value:<12} linhas {linhas:>7}  "
        f"base {data}  {resultado.duracao_s:.1f} s  carga {resultado.carga_id}"
    )
    return f"{texto}\n  erro: {resultado.erro}" if resultado.erro else texto


def _executar_ingestao(executar: Callable[[Atualizador], list[ResultadoCarga]]) -> int:
    config = obter_configuracao()
    configurar_logs(config)
    engine = criar_engine(config.url_banco)
    try:
        with criar_cliente(config) as cliente:
            resultados = executar(Atualizador(engine, config, cliente))
    finally:
        engine.dispose()
    for resultado in resultados:
        print(_linha_resumo(resultado))
    return 1 if any(r.status is StatusCarga.FALHOU for r in resultados) else 0


def _ingerir(argumentos: argparse.Namespace) -> int:
    arquivo: Path | None = argumentos.arquivo
    return _executar_ingestao(lambda atualizador: [atualizador.ingerir(argumentos.fonte, arquivo)])


def _atualizar_bases(argumentos: argparse.Namespace) -> int:
    diretorio: Path | None = argumentos.diretorio
    return _executar_ingestao(lambda atualizador: atualizador.atualizar(diretorio))


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

    ingerir = sub.add_parser("ingerir", help="carrega uma base local")
    ingerir.add_argument("fonte", choices=FONTES_IMPLEMENTADAS)
    ingerir.add_argument(
        "--arquivo", type=Path, help="arquivo já baixado (.zip ou .csv da CGU, .json do TCU), em vez da rede"
    )
    ingerir.set_defaults(executar=_ingerir)

    atualizar = sub.add_parser("atualizar-bases", help="carrega todas as bases locais implementadas")
    atualizar.add_argument(
        "--diretorio",
        type=Path,
        help="pasta com AAAAMMDD_<CADASTRO>.zip da CGU e AAAAMMDD_<fonte>.json do TCU já baixados",
    )
    atualizar.set_defaults(executar=_atualizar_bases)
    return analisador


def main(argv: Sequence[str] | None = None) -> int:
    argumentos = _analisador().parse_args(argv)
    executar: Callable[[argparse.Namespace], int] = argumentos.executar
    return executar(argumentos)
