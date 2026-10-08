import asyncio
from collections.abc import Coroutine
from typing import Any, Protocol

import structlog

from validador_osc.dominio.bases import ConsultaLocal
from validador_osc.dominio.coleta import Coleta, Falha, MotivoFalha
from validador_osc.dominio.sancoes import CadastroSancao, ListaTcu, RegistroListaTcu, RespostaTcu, Sancao
from validador_osc.regras import ObservacoesSancoes

log = structlog.get_logger()

CADASTROS_LOCAIS = (CadastroSancao.CEPIM, CadastroSancao.CEIS, CadastroSancao.CNEP)
LISTAS_LOCAIS = (ListaTcu.INIDONEOS, ListaTcu.CONTAS_IRREGULARES)


class FonteCertidoesTcu(Protocol):
    async def consultar(self, cnpj: str, *, ignorar_cache: bool = False) -> Coleta[RespostaTcu]: ...


class BasesLocais(Protocol):
    async def sancoes_pj(self, cadastro: CadastroSancao, cnpj: str) -> ConsultaLocal[Sancao] | None: ...

    async def listas_tcu_pj(self, lista: ListaTcu, cnpj: str) -> ConsultaLocal[RegistroListaTcu] | None: ...


class ColetorSancoes:
    def __init__(self, tcu: FonteCertidoesTcu, bases: BasesLocais) -> None:
        self._tcu = tcu
        self._bases = bases

    async def coletar(
        self, consultado: str, matriz: str | None, *, ignorar_cache: bool, limite: float
    ) -> ObservacoesSancoes:
        cnpjs = (consultado, matriz) if matriz and matriz != consultado else (consultado,)
        tarefas: dict[tuple[str, object], asyncio.Task[Any]] = {}

        def agendar(chave: tuple[str, object], corrotina: Coroutine[Any, Any, Any]) -> None:
            tarefas[chave] = asyncio.create_task(corrotina)

        for cnpj in cnpjs:
            agendar(("tcu", cnpj), self._tcu.consultar(cnpj, ignorar_cache=ignorar_cache))
        for cadastro in CADASTROS_LOCAIS:
            agendar(("sancao", cadastro), self._bases.sancoes_pj(cadastro, consultado))
        for lista in LISTAS_LOCAIS:
            agendar(("lista", lista), self._bases.listas_tcu_pj(lista, consultado))

        espera = max(0.0, limite - asyncio.get_running_loop().time())
        prontas, pendentes = await asyncio.wait(tarefas.values(), timeout=espera)
        for tarefa in pendentes:
            tarefa.cancel()
        if pendentes:
            log.warning("prazo_consulta_esgotado", etapa="sancoes", pendentes=len(pendentes))

        def resultado(chave: tuple[str, object]) -> Any:
            tarefa = tarefas[chave]
            if tarefa not in prontas:
                return None
            erro = tarefa.exception()
            if erro is not None:
                log.error("coleta_sancoes_falhou", chave=str(chave), erro=repr(erro))
                return None
            return tarefa.result()

        tcu: dict[str, Coleta[RespostaTcu]] = {}
        for cnpj in cnpjs:
            obtido = resultado(("tcu", cnpj))
            tcu[cnpj] = obtido or Falha(MotivoFalha.PRAZO_ESGOTADO, "TCU não respondeu no prazo da consulta")
        return ObservacoesSancoes(
            consultado=consultado,
            matriz=matriz,
            locais={c: resultado(("sancao", c)) for c in CADASTROS_LOCAIS},
            listas={lista: resultado(("lista", lista)) for lista in LISTAS_LOCAIS},
            tcu=tcu,
        )
