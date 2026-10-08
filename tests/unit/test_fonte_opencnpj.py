import asyncio
import hashlib
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from tests.apoio.evidencias_em_memoria import EvidenciasEmMemoria
from validador_osc.dominio.coleta import Coleta, Falha, MotivoFalha, NaoEncontrado, Obtido
from validador_osc.dominio.evidencias import ResultadoResposta
from validador_osc.dominio.tipos import Cadastro, SituacaoCadastral
from validador_osc.fontes.http import ClienteHttp, PoliticaRetry
from validador_osc.fontes.opencnpj import FONTE, FONTE_INFO, URL_BASE, FonteOpenCnpj

FIXTURES = Path(__file__).parent.parent / "fixtures" / "fontes" / "opencnpj"
CNPJ_OKBR = "19131243000197"
CNPJ_INEXISTENTE = "94580730000152"
CNPJ_BAIXADA = "08942107000160"
SHA256_OKBR = "ebec160e4b4e1ff587505dc8c6575c22b58e35928734d00461aeacb232dbf3ba"
DATA_BASE_INFO = date(2026, 9, 14)


def ler(nome: str) -> bytes:
    return (FIXTURES / nome).read_bytes()


def semear(
    evidencias: EvidenciasEmMemoria,
    chave: str,
    resultado: ResultadoResposta,
    corpo: bytes | None,
    idade: timedelta,
    fonte: str = FONTE,
) -> None:
    evidencias.semear(fonte, f"{URL_BASE}/{chave}", chave, resultado, corpo, datetime.now(UTC) - idade)


type Rota = Callable[[httpx.Request], httpx.Response]


def corpo(status: int, nome: str | bytes) -> Rota:
    conteudo = ler(nome) if isinstance(nome, str) else nome
    return lambda _: httpx.Response(status, content=conteudo, headers={"content-type": "application/json"})


def lanca(erro: type[httpx.TransportError]) -> Rota:
    def rota(request: httpx.Request) -> httpx.Response:
        raise erro("falhou", request=request)

    return rota


ROTAS_PADRAO: dict[str, Rota] = {
    "/info": corpo(200, "info.json"),
    f"/{CNPJ_OKBR}": corpo(200, f"{CNPJ_OKBR}.json"),
    f"/{CNPJ_BAIXADA}": corpo(200, f"{CNPJ_BAIXADA}.json"),
    f"/{CNPJ_INEXISTENTE}": corpo(404, f"404_{CNPJ_INEXISTENTE}.json"),
}


@dataclass
class Cenario:
    rotas: dict[str, Rota] = field(default_factory=lambda: dict(ROTAS_PADRAO))
    evidencias: EvidenciasEmMemoria = field(default_factory=EvidenciasEmMemoria)
    chamadas: Counter[str] = field(default_factory=Counter)
    url_base: str = URL_BASE

    def responder(self, request: httpx.Request) -> httpx.Response:
        self.chamadas[request.url.path] += 1
        rota = self.rotas.get(request.url.path)
        if rota is None:
            return httpx.Response(418)
        return rota(request)

    def consultar(self, cnpj: str, *, ignorar_cache: bool = False) -> Coleta[Cadastro]:
        async def nao_dormir(_: float) -> None:
            return None

        async def rodar() -> Coleta[Cadastro]:
            async with httpx.AsyncClient(transport=httpx.MockTransport(self.responder)) as cliente:
                fonte = FonteOpenCnpj(
                    ClienteHttp(cliente, dormir=nao_dormir), self.evidencias, url_base=self.url_base
                )
                return await fonte.consultar(cnpj, ignorar_cache=ignorar_cache)

        return asyncio.run(rodar())


def obtido(coleta: Coleta[Cadastro]) -> Obtido[Cadastro]:
    assert isinstance(coleta, Obtido)
    return coleta


def test_obtido_a_partir_da_fixture_okbr() -> None:
    cenario = Cenario()
    coleta = obtido(cenario.consultar(CNPJ_OKBR))
    assert coleta.dados.cnpj == CNPJ_OKBR
    assert coleta.dados.razao_social == "OPEN KNOWLEDGE BRASIL"
    assert coleta.dados.situacao is SituacaoCadastral.ATIVA
    assert coleta.dados.data_base == DATA_BASE_INFO
    assert coleta.evidencia.sha256 == SHA256_OKBR
    assert coleta.evidencia.fonte == FONTE
    assert not coleta.evidencia.de_cache
    [gravada] = cenario.evidencias.de(FONTE)
    assert gravada.chave == CNPJ_OKBR
    assert gravada.url == f"{URL_BASE}/{CNPJ_OKBR}"
    assert gravada.resultado is ResultadoResposta.OBTIDO
    assert gravada.http_status == 200
    assert gravada.content_type == "application/json"
    assert gravada.corpo == ler(f"{CNPJ_OKBR}.json")
    assert gravada.tentativas == 1
    assert gravada.motivo_falha is None
    assert cenario.chamadas == Counter({"/info": 1, f"/{CNPJ_OKBR}": 1})


def test_cache_valido_nao_chama_a_rede() -> None:
    cenario = Cenario()
    primeira = obtido(cenario.consultar(CNPJ_OKBR))
    segunda = obtido(cenario.consultar(CNPJ_OKBR))
    assert segunda.dados == primeira.dados
    assert segunda.evidencia.de_cache
    assert segunda.evidencia.id == primeira.evidencia.id
    assert segunda.evidencia.sha256 == SHA256_OKBR
    assert cenario.chamadas == Counter({"/info": 1, f"/{CNPJ_OKBR}": 1})
    assert len(cenario.evidencias.gravadas) == 2


@pytest.mark.parametrize(("idade", "chamadas"), [(timedelta(hours=23), 0), (timedelta(hours=25), 1)])
def test_cache_do_cadastro_vale_24_horas(idade: timedelta, chamadas: int) -> None:
    cenario = Cenario()
    semear(cenario.evidencias, CNPJ_OKBR, ResultadoResposta.OBTIDO, ler(f"{CNPJ_OKBR}.json"), idade)
    obtido(cenario.consultar(CNPJ_OKBR))
    assert cenario.chamadas[f"/{CNPJ_OKBR}"] == chamadas


def test_ignorar_cache_chama_a_rede() -> None:
    cenario = Cenario()
    cenario.consultar(CNPJ_OKBR)
    coleta = obtido(cenario.consultar(CNPJ_OKBR, ignorar_cache=True))
    assert not coleta.evidencia.de_cache
    assert cenario.chamadas == Counter({"/info": 1, f"/{CNPJ_OKBR}": 2})
    assert len(cenario.evidencias.de(FONTE)) == 2


def test_404_vira_nao_encontrado_com_evidencia() -> None:
    cenario = Cenario()
    coleta = cenario.consultar(CNPJ_INEXISTENTE)
    assert isinstance(coleta, NaoEncontrado)
    assert coleta.evidencia is not None
    assert not coleta.evidencia.de_cache
    [gravada] = cenario.evidencias.de(FONTE)
    assert gravada.resultado is ResultadoResposta.NAO_ENCONTRADO
    assert gravada.http_status == 404
    assert gravada.tentativas == 1
    assert gravada.corpo == b'{"error":"not found"}'


def test_404_em_cache_e_reaproveitado() -> None:
    cenario = Cenario()
    cenario.consultar(CNPJ_INEXISTENTE)
    coleta = cenario.consultar(CNPJ_INEXISTENTE)
    assert isinstance(coleta, NaoEncontrado)
    assert coleta.evidencia is not None
    assert coleta.evidencia.de_cache
    assert cenario.chamadas[f"/{CNPJ_INEXISTENTE}"] == 1


@pytest.mark.parametrize(
    ("idade", "chamadas"),
    [(timedelta(hours=5, minutes=59), 0), (timedelta(hours=6, minutes=1), 1), (timedelta(hours=12), 1)],
)
def test_cache_do_404_expira_em_6_horas(idade: timedelta, chamadas: int) -> None:
    cenario = Cenario()
    semear(cenario.evidencias, CNPJ_INEXISTENTE, ResultadoResposta.NAO_ENCONTRADO, b"{}", idade)
    assert isinstance(cenario.consultar(CNPJ_INEXISTENTE), NaoEncontrado)
    assert cenario.chamadas[f"/{CNPJ_INEXISTENTE}"] == chamadas


def test_cnpj_que_passou_a_existir_depois_do_404_expirado() -> None:
    cenario = Cenario()
    semear(cenario.evidencias, CNPJ_OKBR, ResultadoResposta.NAO_ENCONTRADO, b"{}", timedelta(hours=7))
    assert obtido(cenario.consultar(CNPJ_OKBR)).dados.cnpj == CNPJ_OKBR


@pytest.mark.parametrize(
    ("rota", "motivo", "status", "tentativas"),
    [
        (corpo(503, b""), MotivoFalha.HTTP_5XX, 503, 3),
        (corpo(429, b""), MotivoFalha.HTTP_429, 429, 3),
        (corpo(403, b""), MotivoFalha.HTTP_4XX, 403, 1),
        (lanca(httpx.ReadTimeout), MotivoFalha.TIMEOUT, None, 3),
        (lanca(httpx.ConnectError), MotivoFalha.CONEXAO, None, 3),
    ],
)
def test_falha_http_gravada_com_motivo(
    rota: Rota, motivo: MotivoFalha, status: int | None, tentativas: int
) -> None:
    cenario = Cenario()
    cenario.rotas[f"/{CNPJ_OKBR}"] = rota
    coleta = cenario.consultar(CNPJ_OKBR)
    assert isinstance(coleta, Falha)
    assert coleta.motivo is motivo
    assert coleta.evidencia is not None
    assert coleta.evidencia.sha256 is None
    [gravada] = cenario.evidencias.de(FONTE)
    assert gravada.resultado is ResultadoResposta.FALHA
    assert gravada.motivo_falha is motivo
    assert gravada.http_status == status
    assert gravada.tentativas == tentativas
    assert gravada.corpo is None
    assert gravada.chave == CNPJ_OKBR
    assert cenario.chamadas[f"/{CNPJ_OKBR}"] == tentativas


def test_falha_nao_vira_cache() -> None:
    cenario = Cenario()
    cenario.rotas[f"/{CNPJ_OKBR}"] = corpo(500, b"")
    assert isinstance(cenario.consultar(CNPJ_OKBR), Falha)
    cenario.rotas[f"/{CNPJ_OKBR}"] = ROTAS_PADRAO[f"/{CNPJ_OKBR}"]
    assert not obtido(cenario.consultar(CNPJ_OKBR)).evidencia.de_cache
    assert cenario.chamadas[f"/{CNPJ_OKBR}"] == 4


@pytest.mark.parametrize(
    "conteudo",
    [
        b'{"foo":1}',
        b"<html>manutencao</html>",
        b"",
        ler(f"{CNPJ_OKBR}_datasets.json"),
        ler(f"{CNPJ_OKBR}.json").replace(b'"situacao_cadastral":"Ativa"', b'"situacao_cadastral":"Rara"'),
    ],
)
def test_formato_inesperado_vira_falha(conteudo: bytes) -> None:
    cenario = Cenario()
    cenario.rotas[f"/{CNPJ_OKBR}"] = corpo(200, conteudo)
    coleta = cenario.consultar(CNPJ_OKBR)
    assert isinstance(coleta, Falha)
    assert coleta.motivo is MotivoFalha.FORMATO_INESPERADO
    assert "OpenCNPJ" in coleta.detalhe
    assert coleta.evidencia is not None
    assert coleta.evidencia.sha256 == hashlib.sha256(conteudo).hexdigest()
    [gravada] = cenario.evidencias.de(FONTE)
    assert gravada.resultado is ResultadoResposta.OBTIDO
    assert gravada.corpo == conteudo


def test_cadastro_baixado_e_obtido() -> None:
    coleta = obtido(Cenario().consultar(CNPJ_BAIXADA))
    assert coleta.dados.situacao is SituacaoCadastral.BAIXADA


def test_info_gravado_e_reaproveitado_entre_cnpjs() -> None:
    cenario = Cenario()
    cenario.consultar(CNPJ_OKBR)
    cenario.consultar(CNPJ_BAIXADA)
    cenario.consultar(CNPJ_INEXISTENTE)
    assert cenario.chamadas["/info"] == 1
    [info] = cenario.evidencias.de(FONTE_INFO)
    assert info.chave == "info"
    assert info.url == f"{URL_BASE}/info"
    assert info.resultado is ResultadoResposta.OBTIDO
    assert info.corpo == ler("info.json")


def test_info_em_cache_da_a_data_base_sem_rede() -> None:
    cenario = Cenario()
    info = b'{"last_updated":"2026-07-01T12:00:00Z"}'
    semear(cenario.evidencias, "info", ResultadoResposta.OBTIDO, info, timedelta(hours=2), FONTE_INFO)
    coleta = obtido(cenario.consultar(CNPJ_OKBR))
    assert coleta.dados.data_base == date(2026, 7, 1)
    assert cenario.chamadas["/info"] == 0


def test_info_vencido_e_buscado_de_novo() -> None:
    cenario = Cenario()
    info = b'{"last_updated":"2026-07-01T12:00:00Z"}'
    semear(cenario.evidencias, "info", ResultadoResposta.OBTIDO, info, timedelta(hours=25), FONTE_INFO)
    coleta = obtido(cenario.consultar(CNPJ_OKBR))
    assert coleta.dados.data_base == DATA_BASE_INFO
    assert cenario.chamadas["/info"] == 1


def test_cadastro_em_cache_usa_a_data_base_atual() -> None:
    cenario = Cenario()
    semear(
        cenario.evidencias, CNPJ_OKBR, ResultadoResposta.OBTIDO, ler(f"{CNPJ_OKBR}.json"), timedelta(hours=1)
    )
    coleta = obtido(cenario.consultar(CNPJ_OKBR))
    assert coleta.evidencia.de_cache
    assert coleta.dados.data_base == DATA_BASE_INFO
    assert cenario.chamadas == Counter({"/info": 1})


def test_falha_no_info_nao_impede_o_cadastro() -> None:
    cenario = Cenario()
    cenario.rotas["/info"] = corpo(500, b"")
    coleta = obtido(cenario.consultar(CNPJ_OKBR))
    assert coleta.dados.data_base is None
    [info] = cenario.evidencias.de(FONTE_INFO)
    assert info.resultado is ResultadoResposta.FALHA
    assert info.motivo_falha is MotivoFalha.HTTP_5XX
    assert info.chave == "info"
    cenario.rotas["/info"] = ROTAS_PADRAO["/info"]
    assert obtido(cenario.consultar(CNPJ_OKBR)).dados.data_base == DATA_BASE_INFO
    assert cenario.chamadas["/info"] == 4


@pytest.mark.parametrize(
    "info",
    [b'{"last_updated":"ontem"}', b"[]", b'{"last_updated":""}', b'{"total":1}'],
)
def test_info_ilegivel_deixa_data_base_vazia(info: bytes) -> None:
    cenario = Cenario()
    cenario.rotas["/info"] = corpo(200, info)
    assert obtido(cenario.consultar(CNPJ_OKBR)).dados.data_base is None


def test_url_base_com_barra_final() -> None:
    cenario = Cenario(url_base="https://api.opencnpj.org/")
    obtido(cenario.consultar(CNPJ_OKBR))
    assert cenario.evidencias.de(FONTE)[0].url == f"{URL_BASE}/{CNPJ_OKBR}"


def test_falha_no_info_usa_a_ultima_data_conhecida() -> None:
    cenario = Cenario()
    info = b'{"last_updated":"2026-07-01T12:00:00Z"}'
    semear(cenario.evidencias, "info", ResultadoResposta.OBTIDO, info, timedelta(days=10), FONTE_INFO)
    cenario.rotas["/info"] = corpo(500, b"")
    assert obtido(cenario.consultar(CNPJ_OKBR)).dados.data_base == date(2026, 7, 1)


def test_falha_no_info_nao_e_repetida_a_cada_consulta() -> None:
    cenario = Cenario()
    cenario.rotas["/info"] = corpo(500, b"")

    async def nao_dormir(_: float) -> None:
        return None

    async def rodar() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(cenario.responder)) as cliente:
            fonte = FonteOpenCnpj(ClienteHttp(cliente, dormir=nao_dormir), cenario.evidencias)
            await fonte.consultar(CNPJ_OKBR, ignorar_cache=True)
            await fonte.consultar(CNPJ_OKBR, ignorar_cache=True)

    asyncio.run(rodar())
    assert cenario.chamadas["/info"] == PoliticaRetry().tentativas
