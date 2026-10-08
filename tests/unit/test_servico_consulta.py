import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.apoio.fabricas import RECEBIDA_EM, coleta_obtida
from validador_osc.dominio.coleta import Coleta, NaoEncontrado, Obtido
from validador_osc.dominio.tipos import Cadastro, Dirigente, PerfilMapa
from validador_osc.persistencia.repositorios import NovaConsulta, RepositorioConsultas
from validador_osc.regras.entradas import ObservacoesDirigentes, ObservacoesSancoes
from validador_osc.regras.tabelas import carregar_tabelas
from validador_osc.servico.consulta import Coletores, PedidoConsulta, ServicoConsulta
from validador_osc.servico.dirigentes import ColetorDirigentes
from validador_osc.servico.sancoes import ColetorSancoes

FILIAL = "62779145000270"
MATRIZ = "62779145000190"
OKBR = "19131243000197"
TABELAS = carregar_tabelas()
PRAZO_CURTO = timedelta(milliseconds=50)


class ConsultasEmMemoria(RepositorioConsultas):
    def __init__(self) -> None:
        super().__init__(async_sessionmaker())
        self.salvas: list[NovaConsulta] = []

    async def salvar(self, nova: NovaConsulta) -> None:
        self.salvas.append(nova)

    async def obter_resultado(self, consulta_id: Any) -> dict[str, Any] | None:
        return None

    async def por_chave_idempotencia(self, chave: str) -> dict[str, Any] | None:
        return None

    async def recente_equivalente(self, cnpj: str, esfera: str | None, desde: Any) -> dict[str, Any] | None:
        return None


@dataclass
class FonteControlada:
    respostas: dict[str, Coleta[Cadastro]]
    esperas: dict[str, float] = field(default_factory=dict)
    travadas: frozenset[str] = frozenset()
    nome: str = "cadastral"
    chamadas: list[str] = field(default_factory=list)
    concluidas: list[str] = field(default_factory=list)

    async def consultar(self, cnpj: str, *, ignorar_cache: bool = False) -> Coleta[Cadastro]:
        del ignorar_cache
        self.chamadas.append(cnpj)
        if cnpj in self.travadas:
            await asyncio.Event().wait()
        await asyncio.sleep(self.esperas.get(cnpj, 0))
        self.concluidas.append(cnpj)
        return self.respostas[cnpj]


class SancoesVazias(ColetorSancoes):
    def __init__(self) -> None:
        self.chamadas: list[tuple[str, str | None]] = []

    async def coletar(
        self, consultado: str, matriz: str | None, *, ignorar_cache: bool, limite: float
    ) -> ObservacoesSancoes:
        del ignorar_cache, limite
        self.chamadas.append((consultado, matriz))
        return ObservacoesSancoes(consultado=consultado, matriz=matriz)


class MapaAusente:
    async def consultar(self, cnpj: str, *, ignorar_cache: bool = False) -> Coleta[PerfilMapa]:
        del cnpj, ignorar_cache
        return NaoEncontrado(None)


class DirigentesVazios(ColetorDirigentes):
    def __init__(self) -> None:
        pass

    async def coletar(self, qsa: tuple[Dirigente, ...]) -> ObservacoesDirigentes:
        del qsa
        return ObservacoesDirigentes()


class MapaQuebrado:
    async def consultar(self, cnpj: str, *, ignorar_cache: bool = False) -> Coleta[PerfilMapa]:
        del cnpj, ignorar_cache
        raise RuntimeError("falha inesperada")


def servico(
    fonte: FonteControlada, prazo: timedelta, mapa: MapaAusente | MapaQuebrado | None = None
) -> tuple[ServicoConsulta, ConsultasEmMemoria]:
    consultas = ConsultasEmMemoria()
    return (
        ServicoConsulta(
            coletores=Coletores(
                cadastral=fonte,
                sancoes=SancoesVazias(),
                mapa=mapa or MapaAusente(),
                dirigentes=DirigentesVazios(),
            ),
            consultas=consultas,
            tabelas=TABELAS,
            zona=ZoneInfo("America/Sao_Paulo"),
            versao_app="teste",
            versao_regras="sha256:teste",
            relogio=lambda: RECEBIDA_EM,
            prazo=prazo,
        ),
        consultas,
    )


def executar(fonte: FonteControlada, cnpj: str, prazo: timedelta = PRAZO_CURTO) -> dict[str, Any]:
    alvo, consultas = servico(fonte, prazo)
    feita = asyncio.run(alvo.executar(PedidoConsulta(cnpj)))
    assert feita.nova
    assert len(consultas.salvas) == 1
    return feita.documento


def verificacao(documento: dict[str, Any], id_: str) -> dict[str, Any]:
    encontrada: dict[str, Any] = next(v for v in documento["verificacoes"] if v["id"] == id_)
    return encontrada


def filial() -> Obtido[Cadastro]:
    return coleta_obtida(cnpj=FILIAL, matriz=False)


def matriz() -> Obtido[Cadastro]:
    return coleta_obtida(cnpj=MATRIZ, matriz=True, razao_social="MATRIZ")


def test_fonte_travada_esgota_o_prazo() -> None:
    fonte = FonteControlada({OKBR: coleta_obtida()}, travadas=frozenset({OKBR}))

    documento = executar(fonte, OKBR)

    situacao = verificacao(documento, "situacao")
    assert situacao["estado"] == "INDISPONIVEL"
    assert situacao["situacao"] == "FONTE_INDISPONIVEL"
    assert "PRAZO_ESGOTADO" in situacao["mensagem"]
    assert documento["status"] == "INCONCLUSIVA"
    assert documento["razao_social"] is None
    assert fonte.concluidas == []


def test_matriz_travada_esgota_o_prazo_depois_do_consultado() -> None:
    fonte = FonteControlada({FILIAL: filial(), MATRIZ: matriz()}, travadas=frozenset({MATRIZ}))

    documento = executar(fonte, FILIAL)

    assert fonte.chamadas == [FILIAL, MATRIZ]
    assert fonte.concluidas == [FILIAL]
    situacao = verificacao(documento, "situacao")
    assert situacao["estado"] == "INDISPONIVEL"
    assert situacao["situacao"] == "MATRIZ_INDISPONIVEL"
    assert verificacao(documento, "estabelecimento")["situacao"] == "FILIAL"
    assert documento["estabelecimento"] == "FILIAL"
    assert documento["cnpj_avaliado"] == FILIAL
    assert documento["status"] == "INCONCLUSIVA"


def test_prazo_e_global_para_consultado_e_matriz() -> None:
    fonte = FonteControlada({FILIAL: filial(), MATRIZ: matriz()}, esperas={FILIAL: 0.3, MATRIZ: 0.3})

    documento = executar(fonte, FILIAL, prazo=timedelta(seconds=0.45))

    assert fonte.concluidas == [FILIAL]
    assert verificacao(documento, "situacao")["situacao"] == "MATRIZ_INDISPONIVEL"


def test_filial_e_matriz_dentro_do_prazo() -> None:
    fonte = FonteControlada({FILIAL: filial(), MATRIZ: matriz()})

    documento = executar(fonte, FILIAL, prazo=timedelta(seconds=5))

    assert fonte.chamadas == [FILIAL, MATRIZ]
    assert documento["cnpj"] == FILIAL
    assert documento["cnpj_avaliado"] == MATRIZ
    assert documento["razao_social"] == "MATRIZ"
    assert documento["estabelecimento"] == "FILIAL"
    assert verificacao(documento, "situacao")["mensagem"].startswith("Matriz: ")


def test_matriz_consultada_nao_busca_outra_matriz() -> None:
    fonte = FonteControlada({OKBR: coleta_obtida()})

    documento = executar(fonte, OKBR, prazo=timedelta(seconds=5))

    assert fonte.chamadas == [OKBR]
    assert documento["estabelecimento"] == "MATRIZ"


def test_filial_com_ordem_0001_nao_consulta_de_novo() -> None:
    cnpj = "24006302000135"
    fonte = FonteControlada({cnpj: coleta_obtida(cnpj=cnpj, matriz=False)})

    documento = executar(fonte, cnpj, prazo=timedelta(seconds=5))

    assert fonte.chamadas == [cnpj]
    assert verificacao(documento, "estabelecimento")["situacao"] == "MATRIZ_NAO_IDENTIFICADA"


def test_matriz_que_volta_como_filial_nao_vira_entidade() -> None:
    fonte = FonteControlada({FILIAL: filial(), MATRIZ: coleta_obtida(cnpj=MATRIZ, matriz=False)})

    alvo, consultas = servico(fonte, timedelta(seconds=5))
    documento = asyncio.run(alvo.executar(PedidoConsulta(FILIAL))).documento

    assert documento["cnpj_avaliado"] == FILIAL
    assert consultas.salvas[0].cnpj_matriz is None
    assert verificacao(documento, "estabelecimento")["situacao"] == "MATRIZ_NAO_IDENTIFICADA"


def test_erro_inesperado_no_mapa_nao_derruba_a_consulta() -> None:
    alvo, consultas = servico(FonteControlada({OKBR: coleta_obtida()}), PRAZO_CURTO, MapaQuebrado())
    feita = asyncio.run(alvo.executar(PedidoConsulta(OKBR)))
    assert verificacao(feita.documento, "mapa_osc")["estado"] == "INDISPONIVEL"
    assert "mapa_osc" in feita.documento["avisos"]
    assert len(consultas.salvas) == 1
