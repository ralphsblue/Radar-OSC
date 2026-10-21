import asyncio
import uuid
from dataclasses import dataclass, field

from tests.unit.test_servico_lotes import Enfileirador, RepositorioLotesEmMemoria, _relogio_fixo
from validador_osc.servico.consulta import ConsultaFeita, PedidoConsulta
from validador_osc.servico.lotes import PedidoLote, ServicoLotes
from validador_osc.trabalhador import _processar_item_async


@dataclass
class ServicoConsultaFalso:
    pedidos: list[PedidoConsulta] = field(default_factory=list)
    resultado: ConsultaFeita | None = None
    erro: Exception | None = None

    async def executar(self, pedido: PedidoConsulta) -> ConsultaFeita:
        self.pedidos.append(pedido)
        if self.erro is not None:
            raise self.erro
        assert self.resultado is not None
        return self.resultado


@dataclass
class ContextoFalso:
    consultas: ServicoConsultaFalso
    lotes: ServicoLotes


def _contexto_com_lote(cnpjs: tuple[str, ...]) -> tuple[ContextoFalso, uuid.UUID, list[int]]:
    enfileirador = Enfileirador()
    lotes = ServicoLotes(RepositorioLotesEmMemoria(), enfileirador, _relogio_fixo)
    usuario_id = uuid.uuid4()
    lote_id = asyncio.run(lotes.criar(PedidoLote(usuario_id=usuario_id, esfera=None, cnpjs=cnpjs)))
    itens_ids = [chamada[1] for chamada in enfileirador.chamadas]
    contexto = ContextoFalso(consultas=ServicoConsultaFalso(), lotes=lotes)
    return contexto, lote_id, itens_ids


def test_item_com_sucesso_fica_concluido_com_consulta_id() -> None:
    contexto, lote_id, (item_id,) = _contexto_com_lote(("11111111000111",))
    consulta_id = uuid.uuid4()
    contexto.consultas.resultado = ConsultaFeita(documento={"id": str(consulta_id)}, nova=True)

    asyncio.run(_processar_item_async(contexto, lote_id, item_id))

    detalhe = asyncio.run(contexto.lotes.obter(lote_id, _usuario_do_lote(contexto, lote_id)))
    assert detalhe is not None
    assert detalhe.itens[0].status == "CONCLUIDO"
    assert detalhe.itens[0].consulta_id == consulta_id
    assert detalhe.status == "CONCLUIDO"
    assert detalhe.concluido_em is not None
    assert contexto.consultas.pedidos == [PedidoConsulta(cnpj="11111111000111", esfera=None)]


def test_item_com_falha_fica_erro_mas_lote_ainda_fecha_concluido() -> None:
    contexto, lote_id, (item_id,) = _contexto_com_lote(("11111111000111",))
    contexto.consultas.erro = RuntimeError("fonte externa fora do ar")

    asyncio.run(_processar_item_async(contexto, lote_id, item_id))

    detalhe = asyncio.run(contexto.lotes.obter(lote_id, _usuario_do_lote(contexto, lote_id)))
    assert detalhe is not None
    assert detalhe.itens[0].status == "ERRO"
    assert detalhe.itens[0].erro == "fonte externa fora do ar"
    assert detalhe.status == "CONCLUIDO"
    assert detalhe.concluido_em is not None


def test_item_inexistente_nao_quebra() -> None:
    contexto, lote_id, _ = _contexto_com_lote(("11111111000111",))
    del lote_id

    asyncio.run(_processar_item_async(contexto, uuid.uuid4(), 999))


def test_lote_com_um_item_sucesso_e_outro_erro_fecha_concluido() -> None:
    contexto, lote_id, (primeiro_id, segundo_id) = _contexto_com_lote(("11111111000111", "22222222000122"))
    contexto.consultas.resultado = ConsultaFeita(documento={"id": str(uuid.uuid4())}, nova=True)
    asyncio.run(_processar_item_async(contexto, lote_id, primeiro_id))

    contexto.consultas.resultado = None
    contexto.consultas.erro = RuntimeError("falha de rede")
    asyncio.run(_processar_item_async(contexto, lote_id, segundo_id))

    detalhe = asyncio.run(contexto.lotes.obter(lote_id, _usuario_do_lote(contexto, lote_id)))
    assert detalhe is not None
    assert {item.status for item in detalhe.itens} == {"CONCLUIDO", "ERRO"}
    assert detalhe.status == "CONCLUIDO"


def _usuario_do_lote(contexto: ContextoFalso, lote_id: uuid.UUID) -> uuid.UUID:
    repositorio = contexto.lotes._lotes
    assert isinstance(repositorio, RepositorioLotesEmMemoria)
    return repositorio._lotes[lote_id].usuario_id
