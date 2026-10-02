import asyncio
import hashlib
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from validador_osc.dominio.coleta import MotivoFalha
from validador_osc.dominio.evidencias import RespostaBruta, ResultadoResposta
from validador_osc.persistencia.banco import criar_engine_async, criar_fabrica_sessoes
from validador_osc.persistencia.modelos import ConsultaEvidencia, RespostaFonte
from validador_osc.persistencia.repositorios import (
    NovaConsulta,
    RepositorioConsultas,
    RepositorioEvidencias,
    RepositorioSaudeFontes,
    ResumoFonte,
)

pytestmark = pytest.mark.db

AGORA = datetime(2026, 10, 1, 15, 0, tzinfo=UTC)
VALIDADE = timedelta(hours=24)
CNPJ = "19131243000197"

type Sessoes = async_sessionmaker[AsyncSession]


def rodar[T](url: str, funcao: Callable[[Sessoes], Awaitable[T]]) -> T:
    async def principal() -> T:
        engine = criar_engine_async(url)
        try:
            return await funcao(criar_fabrica_sessoes(engine))
        finally:
            await engine.dispose()

    return asyncio.run(principal(), loop_factory=asyncio.SelectorEventLoop)


def resposta(
    recebida_em: datetime,
    *,
    corpo: bytes | None = b'{"cnpj":"19131243000197"}',
    resultado: ResultadoResposta = ResultadoResposta.OBTIDO,
    fonte: str = "opencnpj",
    chave: str = CNPJ,
) -> RespostaBruta:
    falha = resultado is ResultadoResposta.FALHA
    return RespostaBruta(
        fonte=fonte,
        chave=chave,
        url=f"https://api.opencnpj.org/{chave}",
        resultado=resultado,
        recebida_em=recebida_em,
        duracao_ms=12,
        tentativas=3 if falha else 1,
        http_status=503 if falha else 200,
        content_type=None if falha else "application/json",
        corpo=None if falha else corpo,
        motivo_falha=MotivoFalha.HTTP_5XX if falha else None,
    )


def nova_consulta(iniciada_em: datetime = AGORA, **alteracoes: Any) -> NovaConsulta:
    consulta_id = uuid.uuid4()
    base = NovaConsulta(
        id=consulta_id,
        cnpj_informado="19.131.243/0001-97",
        cnpj=CNPJ,
        cnpj_matriz=None,
        esfera=None,
        data_referencia=date(2026, 10, 1),
        iniciada_em=iniciada_em,
        duracao_ms=150,
        status="APTA",
        resultado={"id": str(consulta_id), "cnpj": CNPJ, "status": "APTA"},
        versao_app="0.1.0",
        versao_regras="sha256:teste",
        forcou_atualizacao=False,
        chave_idempotencia=None,
        evidencias=(),
    )
    return replace(base, **alteracoes)


def test_gravar_evidencia_calcula_sha256(banco_limpo: str) -> None:
    corpo = b'{"razao_social":"OPEN KNOWLEDGE BRASIL"}'

    async def cenario(sessoes: Sessoes) -> tuple[Any, RespostaFonte | None]:
        repositorio = RepositorioEvidencias(sessoes)
        ref = await repositorio.gravar(resposta(AGORA, corpo=corpo))
        return ref, await repositorio.obter(ref.id)

    ref, linha = rodar(banco_limpo, cenario)

    esperado = hashlib.sha256(corpo).hexdigest()
    assert ref.sha256 == esperado
    assert ref.fonte == "opencnpj"
    assert ref.recebida_em == AGORA
    assert ref.de_cache is False
    assert linha is not None
    assert linha.sha256 == esperado
    assert linha.corpo == corpo
    assert linha.resultado == "OBTIDO"
    assert linha.http_status == 200


def test_gravar_falha_sem_corpo_nao_tem_sha256(banco_limpo: str) -> None:
    async def cenario(sessoes: Sessoes) -> RespostaFonte | None:
        repositorio = RepositorioEvidencias(sessoes)
        ref = await repositorio.gravar(resposta(AGORA, resultado=ResultadoResposta.FALHA))
        assert ref.sha256 is None
        return await repositorio.obter(ref.id)

    linha = rodar(banco_limpo, cenario)

    assert linha is not None
    assert linha.sha256 is None
    assert linha.corpo is None
    assert linha.resultado == "FALHA"
    assert linha.motivo_falha == "HTTP_5XX"


@pytest.mark.parametrize(
    ("idade", "encontrada"),
    [
        (timedelta(0), True),
        (timedelta(hours=23, minutes=59), True),
        (VALIDADE, True),
        (VALIDADE + timedelta(seconds=1), False),
    ],
)
def test_buscar_recente_respeita_validade(banco_limpo: str, idade: timedelta, encontrada: bool) -> None:
    async def cenario(sessoes: Sessoes) -> bool:
        repositorio = RepositorioEvidencias(sessoes)
        await repositorio.gravar(resposta(AGORA - idade))
        return await repositorio.buscar_recente("opencnpj", CNPJ, VALIDADE, AGORA) is not None

    assert rodar(banco_limpo, cenario) is encontrada


def test_buscar_recente_ignora_falha_e_pega_a_mais_recente(banco_limpo: str) -> None:
    async def cenario(sessoes: Sessoes) -> tuple[int, Any]:
        repositorio = RepositorioEvidencias(sessoes)
        await repositorio.gravar(resposta(AGORA - timedelta(hours=5), corpo=b"antiga"))
        recente = await repositorio.gravar(
            resposta(AGORA - timedelta(hours=2), resultado=ResultadoResposta.NAO_ENCONTRADO, corpo=b"404")
        )
        await repositorio.gravar(resposta(AGORA - timedelta(hours=1), resultado=ResultadoResposta.FALHA))
        await repositorio.gravar(resposta(AGORA - timedelta(minutes=1), fonte="brasilapi", corpo=b"outra"))
        await repositorio.gravar(resposta(AGORA - timedelta(minutes=1), chave="00000000000191"))
        return recente.id, await repositorio.buscar_recente("opencnpj", CNPJ, VALIDADE, AGORA)

    id_recente, guardada = rodar(banco_limpo, cenario)

    assert guardada is not None
    assert guardada.evidencia.id == id_recente
    assert guardada.resultado is ResultadoResposta.NAO_ENCONTRADO
    assert guardada.corpo == b"404"
    assert guardada.evidencia.de_cache is True
    assert guardada.evidencia.sha256 == hashlib.sha256(b"404").hexdigest()


def test_buscar_recente_so_com_falhas_devolve_nada(banco_limpo: str) -> None:
    async def cenario(sessoes: Sessoes) -> Any:
        repositorio = RepositorioEvidencias(sessoes)
        await repositorio.gravar(resposta(AGORA - timedelta(minutes=1), resultado=ResultadoResposta.FALHA))
        return await repositorio.buscar_recente("opencnpj", CNPJ, VALIDADE, AGORA)

    assert rodar(banco_limpo, cenario) is None


def test_salvar_consulta_liga_evidencias(banco_limpo: str) -> None:
    async def cenario(
        sessoes: Sessoes,
    ) -> tuple[NovaConsulta, Any, list[tuple[int | None, str, bool]], tuple[int, int]]:
        evidencias = RepositorioEvidencias(sessoes)
        primeira = await evidencias.gravar(resposta(AGORA))
        segunda = await evidencias.gravar(resposta(AGORA, fonte="opencnpj_info", chave="info"))
        nova = nova_consulta(
            evidencias=((primeira.id, "opencnpj", False), (segunda.id, "opencnpj_info", True))
        )
        consultas = RepositorioConsultas(sessoes)
        await consultas.salvar(nova)
        async with sessoes() as sessao:
            ligacoes = (
                await sessao.scalars(
                    select(ConsultaEvidencia)
                    .where(ConsultaEvidencia.consulta_id == nova.id)
                    .order_by(ConsultaEvidencia.resposta_fonte_id)
                )
            ).all()
        return (
            nova,
            await consultas.obter_resultado(nova.id),
            [(ligacao.resposta_fonte_id, ligacao.papel, ligacao.de_cache) for ligacao in ligacoes],
            (primeira.id, segunda.id),
        )

    nova, resultado, ligacoes, (primeira, segunda) = rodar(banco_limpo, cenario)

    assert resultado == nova.resultado
    assert ligacoes == [(primeira, "opencnpj", False), (segunda, "opencnpj_info", True)]


def test_obter_resultado_inexistente(banco_limpo: str) -> None:
    async def cenario(sessoes: Sessoes) -> Any:
        return await RepositorioConsultas(sessoes).obter_resultado(uuid.uuid4())

    assert rodar(banco_limpo, cenario) is None


def test_por_chave_de_idempotencia(banco_limpo: str) -> None:
    async def cenario(sessoes: Sessoes) -> tuple[NovaConsulta, Any, Any]:
        consultas = RepositorioConsultas(sessoes)
        com_chave = nova_consulta(chave_idempotencia="pedido-123")
        await consultas.salvar(nova_consulta())
        await consultas.salvar(com_chave)
        return (
            com_chave,
            await consultas.por_chave_idempotencia("pedido-123"),
            await consultas.por_chave_idempotencia("outra-chave"),
        )

    com_chave, encontrada, ausente = rodar(banco_limpo, cenario)

    assert encontrada == com_chave.resultado
    assert ausente is None


def test_recente_equivalente_separa_esfera_nula_de_informada(banco_limpo: str) -> None:
    async def cenario(sessoes: Sessoes) -> tuple[NovaConsulta, NovaConsulta, Any, Any, Any]:
        consultas = RepositorioConsultas(sessoes)
        sem_esfera = nova_consulta()
        municipio = nova_consulta(esfera="municipio")
        await consultas.salvar(sem_esfera)
        await consultas.salvar(municipio)
        desde = AGORA - timedelta(seconds=10)
        return (
            sem_esfera,
            municipio,
            await consultas.recente_equivalente(CNPJ, None, desde),
            await consultas.recente_equivalente(CNPJ, "municipio", desde),
            await consultas.recente_equivalente(CNPJ, "uniao", desde),
        )

    sem_esfera, municipio, achada_nula, achada_municipio, achada_uniao = rodar(banco_limpo, cenario)

    assert achada_nula == sem_esfera.resultado
    assert achada_municipio == municipio.resultado
    assert achada_uniao is None


def test_recente_equivalente_ignora_forcadas_antigas_e_outro_cnpj(banco_limpo: str) -> None:
    async def cenario(sessoes: Sessoes) -> tuple[NovaConsulta, Any]:
        consultas = RepositorioConsultas(sessoes)
        mais_antiga = nova_consulta(AGORA - timedelta(seconds=8))
        mais_recente = nova_consulta(AGORA - timedelta(seconds=3))
        await consultas.salvar(mais_antiga)
        await consultas.salvar(mais_recente)
        await consultas.salvar(nova_consulta(AGORA - timedelta(seconds=1), forcou_atualizacao=True))
        await consultas.salvar(nova_consulta(AGORA - timedelta(seconds=1), cnpj="00000000000191"))
        await consultas.salvar(nova_consulta(AGORA - timedelta(seconds=11)))
        return mais_recente, await consultas.recente_equivalente(CNPJ, None, AGORA - timedelta(seconds=10))

    mais_recente, achada = rodar(banco_limpo, cenario)

    assert achada == mais_recente.resultado


def test_recente_equivalente_fora_da_janela(banco_limpo: str) -> None:
    async def cenario(sessoes: Sessoes) -> Any:
        consultas = RepositorioConsultas(sessoes)
        await consultas.salvar(nova_consulta(AGORA - timedelta(seconds=11)))
        await consultas.salvar(nova_consulta(AGORA, forcou_atualizacao=True))
        return await consultas.recente_equivalente(CNPJ, None, AGORA - timedelta(seconds=10))

    assert rodar(banco_limpo, cenario) is None


def _resumir(url: str, respostas: list[RespostaBruta], desde: datetime) -> list[ResumoFonte]:
    async def cenario(sessoes: Sessoes) -> list[ResumoFonte]:
        evidencias = RepositorioEvidencias(sessoes)
        for item in respostas:
            await evidencias.gravar(item)
        return await RepositorioSaudeFontes(sessoes).resumir(desde)

    return rodar(url, cenario)


def test_resumo_de_fontes_sem_respostas_e_vazio(banco_limpo: str) -> None:
    assert _resumir(banco_limpo, [], AGORA - VALIDADE) == []


def test_resumo_conta_respostas_falhas_mediana_e_ultima(banco_limpo: str) -> None:
    respostas = [
        replace(resposta(AGORA - timedelta(hours=3)), duracao_ms=40),
        replace(resposta(AGORA - timedelta(hours=2), resultado=ResultadoResposta.FALHA), duracao_ms=10),
        replace(resposta(AGORA - timedelta(hours=1)), duracao_ms=20),
        replace(resposta(AGORA - timedelta(minutes=30), fonte="brasilapi"), duracao_ms=100),
        replace(
            resposta(
                AGORA - timedelta(minutes=10), fonte="brasilapi", resultado=ResultadoResposta.NAO_ENCONTRADO
            ),
            duracao_ms=300,
        ),
    ]

    resumos = _resumir(banco_limpo, respostas, AGORA - VALIDADE)

    assert resumos == [
        ResumoFonte(
            fonte="brasilapi",
            ultima_resposta_em=AGORA - timedelta(minutes=10),
            ultimo_resultado="NAO_ENCONTRADO",
            ultima_falha_em=None,
            respostas=2,
            falhas=0,
            latencia_mediana_ms=200.0,
        ),
        ResumoFonte(
            fonte="opencnpj",
            ultima_resposta_em=AGORA - timedelta(hours=1),
            ultimo_resultado="OBTIDO",
            ultima_falha_em=AGORA - timedelta(hours=2),
            respostas=3,
            falhas=1,
            latencia_mediana_ms=20.0,
        ),
    ]


def test_resumo_so_conta_dentro_da_janela_mas_guarda_a_ultima_resposta(banco_limpo: str) -> None:
    antiga = AGORA - VALIDADE - timedelta(hours=1)
    respostas = [
        resposta(antiga, fonte="brasilapi", resultado=ResultadoResposta.FALHA),
        resposta(antiga, resultado=ResultadoResposta.FALHA),
        replace(resposta(AGORA - timedelta(hours=1)), duracao_ms=30),
    ]

    resumos = {r.fonte: r for r in _resumir(banco_limpo, respostas, AGORA - VALIDADE)}

    assert resumos["brasilapi"] == ResumoFonte(
        fonte="brasilapi",
        ultima_resposta_em=antiga,
        ultimo_resultado="FALHA",
        ultima_falha_em=None,
        respostas=0,
        falhas=0,
        latencia_mediana_ms=None,
    )
    assert resumos["opencnpj"].respostas == 1
    assert resumos["opencnpj"].falhas == 0
    assert resumos["opencnpj"].ultima_falha_em is None
    assert resumos["opencnpj"].latencia_mediana_ms == 30.0
    assert resumos["opencnpj"].ultimo_resultado == "OBTIDO"


def test_resumo_com_falha_como_ultima_resposta(banco_limpo: str) -> None:
    respostas = [
        resposta(AGORA - timedelta(hours=2)),
        resposta(AGORA - timedelta(minutes=5), resultado=ResultadoResposta.FALHA),
    ]

    [resumo] = _resumir(banco_limpo, respostas, AGORA - VALIDADE)

    assert resumo.ultimo_resultado == "FALHA"
    assert resumo.ultima_resposta_em == AGORA - timedelta(minutes=5)
    assert resumo.ultima_falha_em == AGORA - timedelta(minutes=5)
    assert (resumo.respostas, resumo.falhas) == (2, 1)
