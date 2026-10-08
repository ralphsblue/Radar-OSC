import asyncio
from typing import Protocol

from validador_osc.dominio.bases import ConsultaLocal
from validador_osc.dominio.pessoa_fisica import fragmento_cpf, normalizar_nome
from validador_osc.dominio.sancoes import CadastroSancao, ListaTcu, RegistroListaTcu, RegistroTcesp, Sancao
from validador_osc.dominio.tipos import Dirigente
from validador_osc.regras import ConsultaDirigente, ObservacoesDirigentes


class BasesPessoasFisicas(Protocol):
    async def sancoes_pf(
        self, cadastro: CadastroSancao, nome_normalizado: str, cpf_meio: str
    ) -> ConsultaLocal[Sancao] | None: ...

    async def listas_tcu_pf(
        self, lista: ListaTcu, nome_normalizado: str, cpf_meio: str
    ) -> ConsultaLocal[RegistroListaTcu] | None: ...

    async def tcesp_pf(self, nome_normalizado: str) -> ConsultaLocal[RegistroTcesp] | None: ...


class ColetorDirigentes:
    def __init__(self, bases: BasesPessoasFisicas) -> None:
        self._bases = bases

    async def coletar(self, qsa: tuple[Dirigente, ...]) -> ObservacoesDirigentes:
        consultas: list[ConsultaDirigente] = []
        sem_fragmento: list[Dirigente] = []
        for dirigente in qsa:
            fragmento = (
                fragmento_cpf(dirigente.documento_mascarado or "") if dirigente.pessoa_fisica else None
            )
            if fragmento is None:
                sem_fragmento.append(dirigente)
                continue
            nome = normalizar_nome(dirigente.nome)
            ceis, cnep, contas, inabilitados, tcesp = await asyncio.gather(
                self._bases.sancoes_pf(CadastroSancao.CEIS, nome, fragmento.meio),
                self._bases.sancoes_pf(CadastroSancao.CNEP, nome, fragmento.meio),
                self._bases.listas_tcu_pf(ListaTcu.CONTAS_IRREGULARES, nome, fragmento.meio),
                self._bases.listas_tcu_pf(ListaTcu.INABILITADOS, nome, fragmento.meio),
                self._bases.tcesp_pf(nome),
            )
            consultas.append(ConsultaDirigente(dirigente, ceis, cnep, contas, inabilitados, tcesp))
        return ObservacoesDirigentes(tuple(consultas), tuple(sem_fragmento))
