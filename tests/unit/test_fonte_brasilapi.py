import asyncio
import hashlib
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from tests.unit.evidencias_em_memoria import EvidenciasEmMemoria
from validador_osc.dominio.coleta import Coleta, Falha, MotivoFalha, NaoEncontrado, Obtido
from validador_osc.dominio.evidencias import ResultadoResposta
from validador_osc.dominio.tipos import Cadastro, SituacaoCadastral
from validador_osc.fontes.brasilapi import FONTE, POLITICA_RETRY, URL_BASE, FonteBrasilApi
from validador_osc.fontes.http import ClienteHttp

FIXTURES = Path(__file__).parent.parent / "fixtures" / "fontes" / "brasilapi"
CAMINHO = "/api/cnpj/v1"
CNPJ_OKBR = "19131243000197"
CNPJ_BAIXADA = "08942107000160"
CNPJ_FILIAL = "62779145000270"
CNPJ_ALFANUMERICO = "00000000E08G12"
CNPJ_INEXISTENTE = "12ABC34501DE35"
CNPJ_DV_INVALIDO = "19131243000198"
SHA256_OKBR = "721473356287deb74079289cea9074a622362a7fd41791be71dd1199b584b00a"


def ler(nome: str) -> bytes:
    return (FIXTURES / nome).read_bytes()


type Rota = Callable[[httpx.Request], httpx.Response]


def corpo(status: int, nome: str | bytes, cabecalhos: dict[str, str] | None = None) -> Rota:
    conteudo = ler(nome) if isinstance(nome, str) else nome
    headers = {"content-type": "application/json; charset=utf-8", **(cabecalhos or {})}
    return lambda _: httpx.Response(status, content=conteudo, headers=headers)


def lanca(erro: type[httpx.TransportError]) -> Rota:
    def rota(request: httpx.Request) -> httpx.Response:
        raise erro("falhou", request=request)

    return rota


ROTAS_PADRAO: dict[str, Rota] = {
    f"{CAMINHO}/{CNPJ_OKBR}": corpo(200, f"{CNPJ_OKBR}.json"),
    f"{CAMINHO}/{CNPJ_BAIXADA}": corpo(200, f"{CNPJ_BAIXADA}.json"),
    f"{CAMINHO}/{CNPJ_FILIAL}": corpo(200, f"{CNPJ_FILIAL}.json"),
    f"{CAMINHO}/{CNPJ_ALFANUMERICO}": corpo(200, f"{CNPJ_ALFANUMERICO}.json"),
    f"{CAMINHO}/{CNPJ_INEXISTENTE}": corpo(404, f"404_{CNPJ_INEXISTENTE}.json"),
    f"{CAMINHO}/{CNPJ_DV_INVALIDO}": corpo(400, f"400_{CNPJ_DV_INVALIDO}.json"),
}


@dataclass
class Relogio:
    agora: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __call__(self) -> datetime:
        return self.agora

    def avancar(self, intervalo: timedelta) -> None:
        self.agora += intervalo


@dataclass
class Cenario:
    rotas: dict[str, Rota] = field(default_factory=lambda: dict(ROTAS_PADRAO))
    evidencias: EvidenciasEmMemoria = field(default_factory=EvidenciasEmMemoria)
    chamadas: Counter[str] = field(default_factory=Counter)
    relogio: Relogio = field(default_factory=Relogio)
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
                fonte = FonteBrasilApi(
                    ClienteHttp(cliente, POLITICA_RETRY, dormir=nao_dormir),
                    self.evidencias,
                    url_base=self.url_base,
                    relogio=self.relogio,
                )
                return await fonte.consultar(cnpj, ignorar_cache=ignorar_cache)

        return asyncio.run(rodar())

    def semear(self, chave: str, resultado: ResultadoResposta, conteudo: bytes, idade: timedelta) -> None:
        self.evidencias.semear(
            FONTE, f"{URL_BASE}/{chave}", chave, resultado, conteudo, self.relogio() - idade
        )

    def chamadas_de(self, cnpj: str) -> int:
        return self.chamadas[f"{CAMINHO}/{cnpj}"]


def obtido(coleta: Coleta[Cadastro]) -> Obtido[Cadastro]:
    assert isinstance(coleta, Obtido)
    return coleta


def test_identidade_da_fonte() -> None:
    assert FonteBrasilApi.nome == "brasilapi"
    assert FonteBrasilApi.aceita_alfanumerico
    assert URL_BASE == "https://brasilapi.com.br/api/cnpj/v1"
    assert POLITICA_RETRY.tentativas == 1


def test_obtido_a_partir_da_fixture_okbr() -> None:
    cenario = Cenario()
    coleta = obtido(cenario.consultar(CNPJ_OKBR))
    assert coleta.dados.cnpj == CNPJ_OKBR
    assert coleta.dados.razao_social == "OPEN KNOWLEDGE BRASIL"
    assert coleta.dados.situacao is SituacaoCadastral.ATIVA
    assert coleta.dados.natureza_codigo == 3999
    assert coleta.dados.fonte == FONTE
    assert coleta.dados.data_base is None
    assert coleta.evidencia.sha256 == SHA256_OKBR
    assert coleta.evidencia.fonte == FONTE
    assert not coleta.evidencia.de_cache
    [gravada] = cenario.evidencias.de(FONTE)
    assert gravada.chave == CNPJ_OKBR
    assert gravada.url == f"{URL_BASE}/{CNPJ_OKBR}"
    assert gravada.resultado is ResultadoResposta.OBTIDO
    assert gravada.http_status == 200
    assert gravada.content_type == "application/json; charset=utf-8"
    assert gravada.corpo == ler(f"{CNPJ_OKBR}.json")
    assert gravada.tentativas == 1
    assert gravada.motivo_falha is None
    assert cenario.chamadas == Counter({f"{CAMINHO}/{CNPJ_OKBR}": 1})


def test_cache_valido_nao_chama_a_rede() -> None:
    cenario = Cenario()
    primeira = obtido(cenario.consultar(CNPJ_OKBR))
    segunda = obtido(cenario.consultar(CNPJ_OKBR))
    assert segunda.dados == primeira.dados
    assert segunda.evidencia.de_cache
    assert segunda.evidencia.id == primeira.evidencia.id
    assert segunda.evidencia.sha256 == SHA256_OKBR
    assert cenario.chamadas_de(CNPJ_OKBR) == 1
    assert len(cenario.evidencias.gravadas) == 1


@pytest.mark.parametrize(
    ("idade", "chamadas"),
    [(timedelta(days=6, hours=23), 0), (timedelta(days=7, minutes=1), 1), (timedelta(days=30), 1)],
)
def test_cache_do_cadastro_vale_7_dias(idade: timedelta, chamadas: int) -> None:
    cenario = Cenario()
    cenario.semear(CNPJ_OKBR, ResultadoResposta.OBTIDO, ler(f"{CNPJ_OKBR}.json"), idade)
    obtido(cenario.consultar(CNPJ_OKBR))
    assert cenario.chamadas_de(CNPJ_OKBR) == chamadas


def test_relogio_injetado_decide_a_validade_do_cache() -> None:
    cenario = Cenario()
    obtido(cenario.consultar(CNPJ_OKBR))
    cenario.relogio.avancar(timedelta(days=6))
    assert obtido(cenario.consultar(CNPJ_OKBR)).evidencia.de_cache
    cenario.relogio.avancar(timedelta(days=1, minutes=1))
    assert not obtido(cenario.consultar(CNPJ_OKBR)).evidencia.de_cache
    assert cenario.chamadas_de(CNPJ_OKBR) == 2


def test_ignorar_cache_chama_a_rede() -> None:
    cenario = Cenario()
    cenario.consultar(CNPJ_OKBR)
    coleta = obtido(cenario.consultar(CNPJ_OKBR, ignorar_cache=True))
    assert not coleta.evidencia.de_cache
    assert cenario.chamadas_de(CNPJ_OKBR) == 2
    assert len(cenario.evidencias.de(FONTE)) == 2


def test_404_vira_nao_encontrado_com_evidencia() -> None:
    cenario = Cenario()
    coleta = cenario.consultar(CNPJ_INEXISTENTE)
    assert isinstance(coleta, NaoEncontrado)
    assert coleta.evidencia is not None
    assert not coleta.evidencia.de_cache
    assert coleta.data_base is None
    [gravada] = cenario.evidencias.de(FONTE)
    assert gravada.resultado is ResultadoResposta.NAO_ENCONTRADO
    assert gravada.http_status == 404
    assert gravada.tentativas == 1
    assert gravada.corpo == ler(f"404_{CNPJ_INEXISTENTE}.json")


def test_404_em_cache_e_reaproveitado() -> None:
    cenario = Cenario()
    cenario.consultar(CNPJ_INEXISTENTE)
    coleta = cenario.consultar(CNPJ_INEXISTENTE)
    assert isinstance(coleta, NaoEncontrado)
    assert coleta.evidencia is not None
    assert coleta.evidencia.de_cache
    assert cenario.chamadas_de(CNPJ_INEXISTENTE) == 1


@pytest.mark.parametrize(
    ("idade", "chamadas"),
    [(timedelta(hours=5, minutes=59), 0), (timedelta(hours=6, minutes=1), 1), (timedelta(days=3), 1)],
)
def test_cache_do_404_expira_em_6_horas(idade: timedelta, chamadas: int) -> None:
    cenario = Cenario()
    cenario.semear(CNPJ_INEXISTENTE, ResultadoResposta.NAO_ENCONTRADO, b"{}", idade)
    assert isinstance(cenario.consultar(CNPJ_INEXISTENTE), NaoEncontrado)
    assert cenario.chamadas_de(CNPJ_INEXISTENTE) == chamadas


def test_cnpj_que_passou_a_existir_depois_do_404_expirado() -> None:
    cenario = Cenario()
    cenario.semear(CNPJ_OKBR, ResultadoResposta.NAO_ENCONTRADO, b"{}", timedelta(hours=7))
    assert obtido(cenario.consultar(CNPJ_OKBR)).dados.cnpj == CNPJ_OKBR


def test_dv_invalido_vira_falha_4xx_sem_retry() -> None:
    cenario = Cenario()
    coleta = cenario.consultar(CNPJ_DV_INVALIDO)
    assert isinstance(coleta, Falha)
    assert coleta.motivo is MotivoFalha.HTTP_4XX
    assert coleta.evidencia is not None
    [gravada] = cenario.evidencias.de(FONTE)
    assert gravada.resultado is ResultadoResposta.FALHA
    assert gravada.motivo_falha is MotivoFalha.HTTP_4XX
    assert gravada.http_status == 400
    assert gravada.chave == CNPJ_DV_INVALIDO
    assert cenario.chamadas_de(CNPJ_DV_INVALIDO) == 1


@pytest.mark.parametrize(
    ("rota", "motivo", "status"),
    [
        (corpo(500, "500_65478551000100.json"), MotivoFalha.HTTP_5XX, 500),
        (corpo(504, b"{}", {"retry-after": "120"}), MotivoFalha.HTTP_5XX, 504),
        (corpo(503, b""), MotivoFalha.HTTP_5XX, 503),
        (corpo(429, b""), MotivoFalha.HTTP_429, 429),
        (corpo(403, b""), MotivoFalha.HTTP_4XX, 403),
        (lanca(httpx.ReadTimeout), MotivoFalha.TIMEOUT, None),
        (lanca(httpx.ConnectError), MotivoFalha.CONEXAO, None),
    ],
)
def test_falha_http_gravada_com_motivo(rota: Rota, motivo: MotivoFalha, status: int | None) -> None:
    cenario = Cenario()
    cenario.rotas[f"{CAMINHO}/{CNPJ_OKBR}"] = rota
    coleta = cenario.consultar(CNPJ_OKBR)
    assert isinstance(coleta, Falha)
    assert coleta.motivo is motivo
    assert coleta.evidencia is not None
    assert coleta.evidencia.sha256 is None
    [gravada] = cenario.evidencias.de(FONTE)
    assert gravada.resultado is ResultadoResposta.FALHA
    assert gravada.motivo_falha is motivo
    assert gravada.http_status == status
    assert gravada.tentativas == 1
    assert gravada.corpo is None
    assert gravada.chave == CNPJ_OKBR
    assert gravada.url == f"{URL_BASE}/{CNPJ_OKBR}"
    assert cenario.chamadas_de(CNPJ_OKBR) == 1


def test_falha_nao_vira_cache() -> None:
    cenario = Cenario()
    cenario.rotas[f"{CAMINHO}/{CNPJ_OKBR}"] = corpo(500, "500_65478551000100.json")
    assert isinstance(cenario.consultar(CNPJ_OKBR), Falha)
    cenario.rotas[f"{CAMINHO}/{CNPJ_OKBR}"] = ROTAS_PADRAO[f"{CAMINHO}/{CNPJ_OKBR}"]
    assert not obtido(cenario.consultar(CNPJ_OKBR)).evidencia.de_cache
    assert cenario.chamadas_de(CNPJ_OKBR) == 2


@pytest.mark.parametrize(
    "conteudo",
    [
        b'{"foo":1}',
        b"<html>manutencao</html>",
        b"",
        ler("500_65478551000100.json"),
        ler(f"{CNPJ_OKBR}.json").replace(b'"situacao_cadastral":2', b'"situacao_cadastral":5'),
    ],
)
def test_formato_inesperado_vira_falha(conteudo: bytes) -> None:
    cenario = Cenario()
    cenario.rotas[f"{CAMINHO}/{CNPJ_OKBR}"] = corpo(200, conteudo)
    coleta = cenario.consultar(CNPJ_OKBR)
    assert isinstance(coleta, Falha)
    assert coleta.motivo is MotivoFalha.FORMATO_INESPERADO
    assert "BrasilAPI" in coleta.detalhe
    assert coleta.evidencia is not None
    assert coleta.evidencia.sha256 == hashlib.sha256(conteudo).hexdigest()
    [gravada] = cenario.evidencias.de(FONTE)
    assert gravada.resultado is ResultadoResposta.OBTIDO
    assert gravada.corpo == conteudo


def test_formato_inesperado_em_cache_tambem_vira_falha() -> None:
    cenario = Cenario()
    cenario.semear(CNPJ_OKBR, ResultadoResposta.OBTIDO, b'{"foo":1}', timedelta(hours=1))
    coleta = cenario.consultar(CNPJ_OKBR)
    assert isinstance(coleta, Falha)
    assert coleta.motivo is MotivoFalha.FORMATO_INESPERADO
    assert coleta.evidencia is not None
    assert coleta.evidencia.de_cache
    assert cenario.chamadas_de(CNPJ_OKBR) == 0


@pytest.mark.parametrize(
    ("cnpj", "situacao", "matriz"),
    [
        (CNPJ_BAIXADA, SituacaoCadastral.BAIXADA, True),
        (CNPJ_FILIAL, SituacaoCadastral.ATIVA, False),
        (CNPJ_ALFANUMERICO, SituacaoCadastral.ATIVA, False),
    ],
)
def test_casos_reais_sao_obtidos(cnpj: str, situacao: SituacaoCadastral, matriz: bool) -> None:
    coleta = obtido(Cenario().consultar(cnpj))
    assert coleta.dados.cnpj == cnpj
    assert coleta.dados.situacao is situacao
    assert coleta.dados.matriz is matriz


def test_url_base_com_barra_final() -> None:
    cenario = Cenario(url_base=f"{URL_BASE}/")
    obtido(cenario.consultar(CNPJ_OKBR))
    assert cenario.evidencias.de(FONTE)[0].url == f"{URL_BASE}/{CNPJ_OKBR}"
