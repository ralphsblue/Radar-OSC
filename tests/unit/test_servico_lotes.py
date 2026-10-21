import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from validador_osc.persistencia.repositorios import (
    ItemComLoteRegistro,
    ItemLoteRegistro,
    LoteRegistro,
    NovoLote,
    RepositorioConsultas,
    RepositorioLotes,
)
from validador_osc.servico.lotes import (
    CNPJS_MAXIMO_POR_LOTE,
    LimiteLoteExcedido,
    PedidoLote,
    ServicoLotes,
    dividir_cnpjs,
)


class RepositorioLotesEmMemoria(RepositorioLotes):
    def __init__(self) -> None:
        self._lotes: dict[uuid.UUID, LoteRegistro] = {}
        self._item_para_lote: dict[int, uuid.UUID] = {}
        self._proximo_item_id = 1

    async def criar(self, novo: NovoLote) -> list[int]:
        itens = []
        ids = []
        for posicao, cnpj in enumerate(novo.cnpjs):
            item_id = self._proximo_item_id
            self._proximo_item_id += 1
            ids.append(item_id)
            self._item_para_lote[item_id] = novo.id
            itens.append(
                ItemLoteRegistro(
                    id=item_id,
                    posicao=posicao,
                    cnpj_informado=cnpj,
                    status="PENDENTE",
                    consulta_id=None,
                    erro=None,
                )
            )
        self._lotes[novo.id] = LoteRegistro(
            id=novo.id,
            usuario_id=novo.usuario_id,
            esfera=novo.esfera,
            status="PENDENTE",
            total_itens=len(novo.cnpjs),
            criado_em=novo.criado_em,
            concluido_em=None,
            itens=tuple(itens),
        )
        return ids

    async def obter(self, lote_id: uuid.UUID) -> LoteRegistro | None:
        return self._lotes.get(lote_id)

    async def listar_por_usuario(self, usuario_id: uuid.UUID) -> list[LoteRegistro]:
        lotes = [lote for lote in self._lotes.values() if lote.usuario_id == usuario_id]
        return sorted(lotes, key=lambda lote: lote.criado_em, reverse=True)

    async def obter_item_com_lote(self, item_id: int) -> ItemComLoteRegistro | None:
        lote_id = self._item_para_lote.get(item_id)
        if lote_id is None:
            return None
        lote = self._lotes[lote_id]
        item = next(item for item in lote.itens if item.id == item_id)
        return ItemComLoteRegistro(
            id=item.id, lote_id=lote_id, cnpj_informado=item.cnpj_informado, esfera=lote.esfera
        )

    async def marcar_item(
        self,
        item_id: int,
        *,
        status: str,
        consulta_id: uuid.UUID | None,
        erro: str | None,
        atualizado_em: datetime,
    ) -> None:
        del atualizado_em
        lote_id = self._item_para_lote[item_id]
        lote = self._lotes[lote_id]
        itens = tuple(
            ItemLoteRegistro(
                id=item.id,
                posicao=item.posicao,
                cnpj_informado=item.cnpj_informado,
                status=status if item.id == item_id else item.status,
                consulta_id=consulta_id if item.id == item_id else item.consulta_id,
                erro=erro if item.id == item_id else item.erro,
            )
            for item in lote.itens
        )
        self._lotes[lote_id] = LoteRegistro(
            id=lote.id,
            usuario_id=lote.usuario_id,
            esfera=lote.esfera,
            status=lote.status,
            total_itens=lote.total_itens,
            criado_em=lote.criado_em,
            concluido_em=lote.concluido_em,
            itens=itens,
        )

    async def atualizar_status_lote(
        self, lote_id: uuid.UUID, *, status: str, concluido_em: datetime | None
    ) -> None:
        lote = self._lotes[lote_id]
        self._lotes[lote_id] = LoteRegistro(
            id=lote.id,
            usuario_id=lote.usuario_id,
            esfera=lote.esfera,
            status=status,
            total_itens=lote.total_itens,
            criado_em=lote.criado_em,
            concluido_em=concluido_em,
            itens=lote.itens,
        )


class RepositorioConsultasEmMemoria(RepositorioConsultas):
    def __init__(self) -> None:
        self._documentos: dict[uuid.UUID, dict[str, Any]] = {}

    def gravar_documento(self, consulta_id: uuid.UUID, documento: dict[str, Any]) -> None:
        self._documentos[consulta_id] = documento

    async def obter_resultado(self, consulta_id: uuid.UUID) -> dict[str, Any] | None:
        return self._documentos.get(consulta_id)


def _documento(
    cnpj: str, status: str, motivos: list[str], verificacoes: list[dict[str, str]]
) -> dict[str, Any]:
    return {"cnpj": cnpj, "status": status, "motivos": motivos, "verificacoes": verificacoes}


class Enfileirador:
    def __init__(self) -> None:
        self.chamadas: list[tuple[uuid.UUID, int]] = []

    def __call__(self, lote_id: uuid.UUID, item_id: int) -> None:
        self.chamadas.append((lote_id, item_id))


def _relogio_fixo() -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC)


def test_dividir_cnpjs_ignora_vazios_e_espacos() -> None:
    assert dividir_cnpjs(" 11111111000111 ; 22222222000122 ;; ") == (
        "11111111000111",
        "22222222000122",
    )


def test_dividir_cnpjs_de_texto_vazio_resulta_em_tupla_vazia() -> None:
    assert dividir_cnpjs("") == ()
    assert dividir_cnpjs("   ") == ()
    assert dividir_cnpjs(";;;") == ()


def test_dividir_cnpjs_separa_so_por_ponto_e_virgula() -> None:
    assert dividir_cnpjs("11111111000111,22222222000122") == ("11111111000111,22222222000122",)


def test_criar_lote_acima_do_limite_leva_a_limite_lote_excedido() -> None:
    servico = ServicoLotes(RepositorioLotesEmMemoria(), Enfileirador(), _relogio_fixo)
    cnpjs = tuple(str(i).zfill(14) for i in range(CNPJS_MAXIMO_POR_LOTE + 1))
    with pytest.raises(LimiteLoteExcedido):
        asyncio.run(servico.criar(PedidoLote(usuario_id=uuid.uuid4(), esfera=None, cnpjs=cnpjs)))


def test_criar_lote_no_limite_e_aceito() -> None:
    servico = ServicoLotes(RepositorioLotesEmMemoria(), Enfileirador(), _relogio_fixo)
    cnpjs = tuple(str(i).zfill(14) for i in range(CNPJS_MAXIMO_POR_LOTE))
    lote_id = asyncio.run(servico.criar(PedidoLote(usuario_id=uuid.uuid4(), esfera=None, cnpjs=cnpjs)))
    assert isinstance(lote_id, uuid.UUID)


def test_criar_lote_enfileira_uma_vez_por_item() -> None:
    enfileirador = Enfileirador()
    servico = ServicoLotes(RepositorioLotesEmMemoria(), enfileirador, _relogio_fixo)
    usuario_id = uuid.uuid4()
    cnpjs = ("11111111000111", "22222222000122", "33333333000133")
    lote_id = asyncio.run(servico.criar(PedidoLote(usuario_id=usuario_id, esfera="municipio", cnpjs=cnpjs)))
    assert len(enfileirador.chamadas) == len(cnpjs)
    assert all(chamada[0] == lote_id for chamada in enfileirador.chamadas)
    assert len({chamada[1] for chamada in enfileirador.chamadas}) == len(cnpjs)


def test_obter_lote_so_retorna_pro_dono() -> None:
    enfileirador = Enfileirador()
    repositorio = RepositorioLotesEmMemoria()
    servico = ServicoLotes(repositorio, enfileirador, _relogio_fixo)
    usuario_id = uuid.uuid4()
    outro_usuario_id = uuid.uuid4()
    lote_id = asyncio.run(
        servico.criar(PedidoLote(usuario_id=usuario_id, esfera=None, cnpjs=("11111111000111",)))
    )

    detalhe = asyncio.run(servico.obter(lote_id, usuario_id))
    assert detalhe is not None
    assert detalhe.id == lote_id
    assert len(detalhe.itens) == 1
    assert detalhe.itens[0].status == "PENDENTE"

    assert asyncio.run(servico.obter(lote_id, outro_usuario_id)) is None


def test_obter_lote_inexistente_retorna_none() -> None:
    servico = ServicoLotes(RepositorioLotesEmMemoria(), Enfileirador(), _relogio_fixo)
    assert asyncio.run(servico.obter(uuid.uuid4(), uuid.uuid4())) is None


def test_listar_lotes_retorna_so_do_usuario_ordenado_por_criacao() -> None:
    repositorio = RepositorioLotesEmMemoria()
    enfileirador = Enfileirador()
    relogios = iter(
        [
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 1, 2, tzinfo=UTC),
            datetime(2026, 1, 3, tzinfo=UTC),
        ]
    )
    servico = ServicoLotes(repositorio, enfileirador, lambda: next(relogios))
    usuario_id = uuid.uuid4()
    outro_usuario_id = uuid.uuid4()

    primeiro = asyncio.run(servico.criar(PedidoLote(usuario_id=usuario_id, esfera=None, cnpjs=("1",))))
    asyncio.run(servico.criar(PedidoLote(usuario_id=outro_usuario_id, esfera=None, cnpjs=("2",))))
    segundo = asyncio.run(servico.criar(PedidoLote(usuario_id=usuario_id, esfera=None, cnpjs=("3",))))

    resumos = asyncio.run(servico.listar(usuario_id))
    assert [resumo.id for resumo in resumos] == [segundo, primeiro]


def test_marcar_item_atualiza_status_consulta_e_erro() -> None:
    enfileirador = Enfileirador()
    servico = ServicoLotes(RepositorioLotesEmMemoria(), enfileirador, _relogio_fixo)
    usuario_id = uuid.uuid4()
    lote_id = asyncio.run(
        servico.criar(PedidoLote(usuario_id=usuario_id, esfera=None, cnpjs=("11111111000111",)))
    )
    item_id = enfileirador.chamadas[0][1]

    item = asyncio.run(servico.obter_item(item_id))
    assert item is not None
    assert item.lote_id == lote_id
    assert item.cnpj_informado == "11111111000111"

    consulta_id = uuid.uuid4()
    asyncio.run(servico.marcar_item(item_id, status="CONCLUIDO", consulta_id=consulta_id))

    detalhe = asyncio.run(servico.obter(lote_id, usuario_id))
    assert detalhe is not None
    assert detalhe.itens[0].status == "CONCLUIDO"
    assert detalhe.itens[0].consulta_id == consulta_id


def test_marcar_item_registra_erro() -> None:
    enfileirador = Enfileirador()
    servico = ServicoLotes(RepositorioLotesEmMemoria(), enfileirador, _relogio_fixo)
    usuario_id = uuid.uuid4()
    lote_id = asyncio.run(
        servico.criar(PedidoLote(usuario_id=usuario_id, esfera=None, cnpjs=("11111111000111",)))
    )
    item_id = enfileirador.chamadas[0][1]

    asyncio.run(servico.marcar_item(item_id, status="ERRO", erro="falha de rede"))

    detalhe = asyncio.run(servico.obter(lote_id, usuario_id))
    assert detalhe is not None
    assert detalhe.itens[0].status == "ERRO"
    assert detalhe.itens[0].erro == "falha de rede"


def test_recalcular_status_lote_vira_processando_quando_um_item_sai_de_pendente() -> None:
    enfileirador = Enfileirador()
    servico = ServicoLotes(RepositorioLotesEmMemoria(), enfileirador, _relogio_fixo)
    usuario_id = uuid.uuid4()
    cnpjs = ("11111111000111", "22222222000122")
    lote_id = asyncio.run(servico.criar(PedidoLote(usuario_id=usuario_id, esfera=None, cnpjs=cnpjs)))
    primeiro_item_id = enfileirador.chamadas[0][1]

    asyncio.run(servico.marcar_item(primeiro_item_id, status="PROCESSANDO"))
    asyncio.run(servico.recalcular_status_lote(lote_id))

    detalhe = asyncio.run(servico.obter(lote_id, usuario_id))
    assert detalhe is not None
    assert detalhe.status == "PROCESSANDO"
    assert detalhe.concluido_em is None


def test_recalcular_status_lote_conclui_mesmo_com_item_em_erro() -> None:
    enfileirador = Enfileirador()
    servico = ServicoLotes(RepositorioLotesEmMemoria(), enfileirador, _relogio_fixo)
    usuario_id = uuid.uuid4()
    cnpjs = ("11111111000111", "22222222000122")
    lote_id = asyncio.run(servico.criar(PedidoLote(usuario_id=usuario_id, esfera=None, cnpjs=cnpjs)))
    primeiro_item_id, segundo_item_id = (chamada[1] for chamada in enfileirador.chamadas)

    asyncio.run(servico.marcar_item(primeiro_item_id, status="CONCLUIDO", consulta_id=uuid.uuid4()))
    asyncio.run(servico.marcar_item(segundo_item_id, status="ERRO", erro="falha de rede"))
    asyncio.run(servico.recalcular_status_lote(lote_id))

    detalhe = asyncio.run(servico.obter(lote_id, usuario_id))
    assert detalhe is not None
    assert detalhe.status == "CONCLUIDO"
    assert detalhe.concluido_em is not None


def test_recalcular_status_lote_mantem_pendente_se_nenhum_item_mudou() -> None:
    enfileirador = Enfileirador()
    servico = ServicoLotes(RepositorioLotesEmMemoria(), enfileirador, _relogio_fixo)
    usuario_id = uuid.uuid4()
    lote_id = asyncio.run(
        servico.criar(PedidoLote(usuario_id=usuario_id, esfera=None, cnpjs=("11111111000111",)))
    )

    asyncio.run(servico.recalcular_status_lote(lote_id))

    detalhe = asyncio.run(servico.obter(lote_id, usuario_id))
    assert detalhe is not None
    assert detalhe.status == "PENDENTE"


def test_metricas_agrega_lotes_cnpjs_status_e_impedimentos() -> None:
    enfileirador = Enfileirador()
    repositorio = RepositorioLotesEmMemoria()
    consultas = RepositorioConsultasEmMemoria()
    servico = ServicoLotes(repositorio, enfileirador, _relogio_fixo, consultas)
    usuario_id = uuid.uuid4()

    verificacoes_cepim = [
        {"id": "cepim", "nome": "CEPIM"},
        {"id": "ceis", "nome": "CEIS"},
    ]

    lote_um = asyncio.run(
        servico.criar(
            PedidoLote(
                usuario_id=usuario_id,
                esfera=None,
                cnpjs=("11111111000111", "22222222000122"),
            )
        )
    )
    item_a, item_b = (chamada[1] for chamada in enfileirador.chamadas if chamada[0] == lote_um)

    consulta_a = uuid.uuid4()
    consultas.gravar_documento(
        consulta_a,
        _documento("11111111000111", "INAPTA", ["cepim"], verificacoes_cepim),
    )
    asyncio.run(servico.marcar_item(item_a, status="CONCLUIDO", consulta_id=consulta_a))

    consulta_b = uuid.uuid4()
    consultas.gravar_documento(consulta_b, _documento("22222222000122", "APTA", [], verificacoes_cepim))
    asyncio.run(servico.marcar_item(item_b, status="CONCLUIDO", consulta_id=consulta_b))

    lote_dois = asyncio.run(
        servico.criar(PedidoLote(usuario_id=usuario_id, esfera=None, cnpjs=("11111111000111",)))
    )
    (item_c,) = (chamada[1] for chamada in enfileirador.chamadas if chamada[0] == lote_dois)
    consulta_c = uuid.uuid4()
    consultas.gravar_documento(
        consulta_c,
        _documento("11111111000111", "INAPTA", ["cepim", "ceis"], verificacoes_cepim),
    )
    asyncio.run(servico.marcar_item(item_c, status="CONCLUIDO", consulta_id=consulta_c))

    metricas = asyncio.run(servico.metricas(usuario_id))

    assert metricas.total_lotes == 2
    assert metricas.total_cnpjs_avaliados == 2
    assert metricas.distribuicao_status["INAPTA"] == 2
    assert metricas.distribuicao_status["APTA"] == 1
    assert metricas.distribuicao_status["APTA_COM_RESSALVAS"] == 0
    assert metricas.impedimentos_por_tipo == {"CEPIM": 2, "CEIS": 1}


def test_metricas_sem_lotes_retorna_tudo_zerado() -> None:
    servico = ServicoLotes(
        RepositorioLotesEmMemoria(), Enfileirador(), _relogio_fixo, RepositorioConsultasEmMemoria()
    )
    metricas = asyncio.run(servico.metricas(uuid.uuid4()))

    assert metricas.total_lotes == 0
    assert metricas.total_cnpjs_avaliados == 0
    assert metricas.impedimentos_por_tipo == {}
    assert all(quantidade == 0 for quantidade in metricas.distribuicao_status.values())
