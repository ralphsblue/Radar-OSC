from collections.abc import Mapping
from dataclasses import dataclass, field

from validador_osc.dominio.bases import ConsultaLocal
from validador_osc.dominio.coleta import Coleta
from validador_osc.dominio.sancoes import (
    CadastroSancao,
    ListaTcu,
    RegistroListaTcu,
    RegistroTcesp,
    RespostaTcu,
    Sancao,
)
from validador_osc.dominio.tipos import Cadastro, Dirigente, PerfilMapa


@dataclass(frozen=True, slots=True)
class ObservacoesSancoes:
    consultado: str
    matriz: str | None
    locais: Mapping[CadastroSancao, ConsultaLocal[Sancao] | None] = field(default_factory=dict)
    listas: Mapping[ListaTcu, ConsultaLocal[RegistroListaTcu] | None] = field(default_factory=dict)
    tcu: Mapping[str, Coleta[RespostaTcu]] = field(default_factory=dict)

    @property
    def cnpjs(self) -> tuple[str, ...]:
        if self.matriz and self.matriz != self.consultado:
            return (self.consultado, self.matriz)
        return (self.consultado,)


@dataclass(frozen=True, slots=True)
class ConsultaDirigente:
    dirigente: Dirigente
    ceis: ConsultaLocal[Sancao] | None = None
    cnep: ConsultaLocal[Sancao] | None = None
    contas_irregulares: ConsultaLocal[RegistroListaTcu] | None = None
    inabilitados: ConsultaLocal[RegistroListaTcu] | None = None
    tcesp: ConsultaLocal[RegistroTcesp] | None = None


@dataclass(frozen=True, slots=True)
class ObservacoesDirigentes:
    consultas: tuple[ConsultaDirigente, ...] = ()
    sem_fragmento: tuple[Dirigente, ...] = ()


@dataclass(frozen=True, slots=True)
class DadosConsulta:
    cnpj_informado: str
    cadastro: Coleta[Cadastro] | None = None
    matriz: Coleta[Cadastro] | None = None
    sancoes: ObservacoesSancoes | None = None
    mapa: Coleta[PerfilMapa] | None = None
    dirigentes: ObservacoesDirigentes | None = None
