from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from validador_osc.dominio.bases import CargaAtiva, ConsultaLocal
from validador_osc.dominio.sancoes import (
    CadastroSancao,
    ListaTcu,
    RegistroListaTcu,
    RegistroTcesp,
    Sancao,
    TipoPessoa,
)
from validador_osc.persistencia.modelos import Carga, ListaTcuRegistro, SancaoRegistro, TcespRegistro

TAMANHO_RAIZ = 8

FONTES_SANCAO: dict[CadastroSancao, str] = {
    CadastroSancao.CEPIM: "cgu_cepim",
    CadastroSancao.CEIS: "cgu_ceis",
    CadastroSancao.CNEP: "cgu_cnep",
}

FONTES_LISTA_TCU: dict[ListaTcu, str] = {
    ListaTcu.INIDONEOS: "tcu_inidoneos",
    ListaTcu.CONTAS_IRREGULARES: "tcu_contas_irregulares",
    ListaTcu.INABILITADOS: "tcu_inabilitados",
}

FONTE_TCESP = "tcesp_terceiro_setor"


def _carga_ativa(linha: Carga) -> CargaAtiva:
    if linha.concluida_em is None:
        raise ValueError(f"carga ativa {linha.id} sem data de conclusão")
    return CargaAtiva(linha.id, linha.fonte, linha.data_base, linha.concluida_em, linha.arquivo_sha256)


def _sancao(linha: SancaoRegistro) -> Sancao:
    return Sancao(
        cadastro=CadastroSancao(linha.cadastro),
        tipo_pessoa=TipoPessoa(linha.tipo_pessoa) if linha.tipo_pessoa is not None else None,
        documento=linha.documento,
        raiz=linha.raiz,
        nome=linha.nome,
        categoria=linha.categoria,
        data_inicio=linha.data_inicio,
        data_fim=linha.data_fim,
        orgao=linha.orgao,
        esfera=linha.esfera,
        uf=linha.uf,
        abrangencia=linha.abrangencia,
        fundamentacao=linha.fundamentacao,
        processo=linha.processo,
        valor_multa=linha.valor_multa,
        codigo_sancao=linha.codigo_sancao,
        origem_informacoes=linha.origem_informacoes,
        motivo=linha.motivo,
        convenio=linha.convenio,
    )


def _registro_tcesp(linha: TcespRegistro) -> RegistroTcesp:
    return RegistroTcesp(
        nome=linha.nome,
        cpf_inicio=linha.cpf_inicio,
        cpf_fim=linha.cpf_fim,
        processo=linha.processo,
        materia=linha.materia,
        origem=linha.origem,
        data_transito=linha.data_transito,
        exercicio=linha.exercicio,
    )


def _registro_tcu(linha: ListaTcuRegistro) -> RegistroListaTcu:
    return RegistroListaTcu(
        lista=ListaTcu(linha.lista),
        documento=linha.documento,
        raiz=linha.raiz,
        nome=linha.nome,
        processo=linha.processo,
        acordao=linha.acordao,
        data_acordao=linha.data_acordao,
        data_transito=linha.data_transito,
        data_final=linha.data_final,
    )


class RepositorioBasesLocais:
    def __init__(self, sessoes: async_sessionmaker[AsyncSession]) -> None:
        self._sessoes = sessoes

    async def carga_ativa(self, fonte: str) -> CargaAtiva | None:
        async with self._sessoes() as sessao:
            return await self._ativa(sessao, fonte)

    async def sancoes_pj(self, cadastro: CadastroSancao, cnpj: str) -> ConsultaLocal[Sancao] | None:
        filtro = or_(SancaoRegistro.documento == cnpj, SancaoRegistro.raiz == cnpj[:TAMANHO_RAIZ])
        return await self._sancoes(cadastro, filtro)

    async def sancoes_pf(
        self, cadastro: CadastroSancao, nome_normalizado: str, cpf_meio: str
    ) -> ConsultaLocal[Sancao] | None:
        filtro = (SancaoRegistro.nome_normalizado == nome_normalizado) & (SancaoRegistro.cpf_meio == cpf_meio)
        return await self._sancoes(cadastro, filtro)

    async def listas_tcu_pj(self, lista: ListaTcu, cnpj: str) -> ConsultaLocal[RegistroListaTcu] | None:
        filtro = or_(ListaTcuRegistro.documento == cnpj, ListaTcuRegistro.raiz == cnpj[:TAMANHO_RAIZ])
        return await self._listas_tcu(lista, filtro)

    async def listas_tcu_pf(
        self, lista: ListaTcu, nome_normalizado: str, cpf_meio: str
    ) -> ConsultaLocal[RegistroListaTcu] | None:
        filtro = (ListaTcuRegistro.nome_normalizado == nome_normalizado) & (
            ListaTcuRegistro.cpf_meio == cpf_meio
        )
        return await self._listas_tcu(lista, filtro)

    async def tcesp_pf(self, nome_normalizado: str) -> ConsultaLocal[RegistroTcesp] | None:
        async with self._sessoes() as sessao:
            carga = await self._ativa(sessao, FONTE_TCESP)
            if carga is None:
                return None
            consulta = (
                select(TcespRegistro)
                .where(TcespRegistro.carga_id == carga.id, TcespRegistro.nome_normalizado == nome_normalizado)
                .order_by(TcespRegistro.id)
            )
            linhas = (await sessao.scalars(consulta)).all()
        return ConsultaLocal(carga, tuple(_registro_tcesp(linha) for linha in linhas))

    async def _ativa(self, sessao: AsyncSession, fonte: str) -> CargaAtiva | None:
        consulta = select(Carga).where(Carga.fonte == fonte, Carga.ativa.is_(True))
        linha = (await sessao.scalars(consulta)).first()
        return _carga_ativa(linha) if linha is not None else None

    async def _sancoes(
        self, cadastro: CadastroSancao, filtro: ColumnElement[bool]
    ) -> ConsultaLocal[Sancao] | None:
        async with self._sessoes() as sessao:
            carga = await self._ativa(sessao, FONTES_SANCAO[cadastro])
            if carga is None:
                return None
            consulta = (
                select(SancaoRegistro)
                .where(SancaoRegistro.carga_id == carga.id, filtro)
                .order_by(SancaoRegistro.id)
            )
            linhas = (await sessao.scalars(consulta)).all()
        return ConsultaLocal(carga, tuple(_sancao(linha) for linha in linhas))

    async def _listas_tcu(
        self, lista: ListaTcu, filtro: ColumnElement[bool]
    ) -> ConsultaLocal[RegistroListaTcu] | None:
        async with self._sessoes() as sessao:
            carga = await self._ativa(sessao, FONTES_LISTA_TCU[lista])
            if carga is None:
                return None
            consulta = (
                select(ListaTcuRegistro)
                .where(
                    ListaTcuRegistro.carga_id == carga.id,
                    ListaTcuRegistro.lista == lista.value,
                    filtro,
                )
                .order_by(ListaTcuRegistro.id)
            )
            linhas = (await sessao.scalars(consulta)).all()
        return ConsultaLocal(carga, tuple(_registro_tcu(linha) for linha in linhas))
