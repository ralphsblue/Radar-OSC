import asyncio
import hashlib
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from tests.apoio.evidencias_em_memoria import EvidenciasEmMemoria
from validador_osc.dominio.coleta import Coleta, Falha, MotivoFalha, Obtido
from validador_osc.dominio.evidencias import ResultadoResposta
from validador_osc.dominio.sancoes import RespostaTcu, SituacaoCertidaoTcu, TipoCertidaoTcu
from validador_osc.fontes.http import ClienteHttp
from validador_osc.fontes.tcu import FONTE, POLITICA_RETRY, TIMEOUT, URL_BASE, VALIDADE, FonteTcu

FIXTURES = Path(__file__).parent.parent / "fixtures" / "fontes" / "tcu"
CAMINHO = "/api/rest/publico/certidoes"
CNPJ_OKBR = "19131243000197"
CNPJ_ALFATEC = "28025673000115"
CNPJ_FORA_DO_TCU = "98765432000198"
CNPJ_ALFANUMERICO = "12ABC34501DE35"
CNPJ_CNIA = "05051898000140"
CNPJ_DV_INVALIDO = "19131243000198"
SHA256_OKBR = "757622ba7b54f1950c20cde4c3af3a99338f0f9349b4fc3b7ec6f964e08b07fa"


def ler(nome: str) -> bytes:
    return (FIXTURES / nome).read_bytes()


type Rota = Callable[[httpx.Request], httpx.Response]


def corpo(status: int, nome: str | bytes) -> Rota:
    conteudo = ler(nome) if isinstance(nome, str) else nome
    return lambda _: httpx.Response(status, content=conteudo, headers={"content-type": "application/json"})


def lanca(erro: type[httpx.TransportError]) -> Rota:
    def rota(request: httpx.Request) -> httpx.Response:
        raise erro("falhou", request=request)

    return rota


def sequencia(*rotas: Rota) -> Rota:
    pendentes = list(rotas)

    def rota(request: httpx.Request) -> httpx.Response:
        return pendentes.pop(0)(request) if len(pendentes) > 1 else pendentes[0](request)

    return rota


ROTAS_PADRAO: dict[str, Rota] = {
    f"{CAMINHO}/{CNPJ_OKBR}": corpo(200, f"{CNPJ_OKBR}.json"),
    f"{CAMINHO}/{CNPJ_ALFATEC}": corpo(200, f"{CNPJ_ALFATEC}.json"),
    f"{CAMINHO}/{CNPJ_FORA_DO_TCU}": corpo(200, f"{CNPJ_FORA_DO_TCU}.json"),
    f"{CAMINHO}/{CNPJ_ALFANUMERICO}": corpo(200, f"{CNPJ_ALFANUMERICO}.json"),
    f"{CAMINHO}/{CNPJ_CNIA}": corpo(200, f"{CNPJ_CNIA}.json"),
    f"{CAMINHO}/{CNPJ_DV_INVALIDO}": corpo(412, f"412_{CNPJ_DV_INVALIDO}.json"),
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
    pedidos: list[httpx.Request] = field(default_factory=list)
    esperas: list[float] = field(default_factory=list)
    relogio: Relogio = field(default_factory=Relogio)
    url_base: str = URL_BASE

    def responder(self, request: httpx.Request) -> httpx.Response:
        self.chamadas[request.url.path] += 1
        self.pedidos.append(request)
        rota = self.rotas.get(request.url.path)
        if rota is None:
            return httpx.Response(418)
        return rota(request)

    def consultar(self, cnpj: str, *, ignorar_cache: bool = False) -> Coleta[RespostaTcu]:
        async def dormir(segundos: float) -> None:
            self.esperas.append(segundos)

        async def rodar() -> Coleta[RespostaTcu]:
            async with httpx.AsyncClient(transport=httpx.MockTransport(self.responder)) as cliente:
                fonte = FonteTcu(
                    ClienteHttp(cliente, POLITICA_RETRY, dormir=dormir, timeout=TIMEOUT),
                    self.evidencias,
                    url_base=self.url_base,
                    relogio=self.relogio,
                )
                return await fonte.consultar(cnpj, ignorar_cache=ignorar_cache)

        return asyncio.run(rodar())

    def semear(self, chave: str, conteudo: bytes, idade: timedelta) -> None:
        self.evidencias.semear(
            FONTE, url(chave), chave, ResultadoResposta.OBTIDO, conteudo, self.relogio() - idade
        )

    def chamadas_de(self, cnpj: str) -> int:
        return self.chamadas[f"{CAMINHO}/{cnpj}"]


def url(cnpj: str) -> str:
    return f"{URL_BASE}/{cnpj}?seEmitirPDF=false"


def obtido(coleta: Coleta[RespostaTcu]) -> Obtido[RespostaTcu]:
    assert isinstance(coleta, Obtido)
    return coleta


def falha(coleta: Coleta[RespostaTcu]) -> Falha:
    assert isinstance(coleta, Falha)
    return coleta


def test_identidade_da_fonte() -> None:
    assert FonteTcu.nome == "tcu_consolidada"
    assert FonteTcu.aceita_alfanumerico
    assert URL_BASE == "https://certidoes-apf.apps.tcu.gov.br/api/rest/publico/certidoes"
    assert POLITICA_RETRY.tentativas == 2
    assert timedelta(hours=24) == VALIDADE
    assert httpx.Timeout(15.0, connect=5.0) == TIMEOUT


def test_obtido_a_partir_da_fixture_okbr() -> None:
    cenario = Cenario()
    coleta = obtido(cenario.consultar(CNPJ_OKBR))
    assert coleta.dados.cnpj == CNPJ_OKBR
    assert coleta.dados.razao_social == "OPEN KNOWLEDGE FOUNDATION BRASIL"
    assert coleta.dados.cnpj_encontrado
    assert {c.situacao for c in coleta.dados.certidoes} == {SituacaoCertidaoTcu.NADA_CONSTA}
    assert coleta.evidencia.sha256 == SHA256_OKBR
    assert coleta.evidencia.fonte == FONTE
    assert not coleta.evidencia.de_cache
    [gravada] = cenario.evidencias.de(FONTE)
    assert gravada.chave == CNPJ_OKBR
    assert gravada.url == url(CNPJ_OKBR)
    assert gravada.resultado is ResultadoResposta.OBTIDO
    assert gravada.http_status == 200
    assert gravada.content_type == "application/json"
    assert gravada.corpo == ler(f"{CNPJ_OKBR}.json")
    assert gravada.tentativas == 1
    assert gravada.motivo_falha is None
    assert cenario.chamadas == Counter({f"{CAMINHO}/{CNPJ_OKBR}": 1})


def test_pede_sem_pdf_e_com_timeout_proprio() -> None:
    cenario = Cenario()
    obtido(cenario.consultar(CNPJ_OKBR))
    [pedido] = cenario.pedidos
    assert pedido.method == "GET"
    assert str(pedido.url) == url(CNPJ_OKBR)
    assert pedido.extensions["timeout"] == {"connect": 5.0, "read": 15.0, "write": 15.0, "pool": 15.0}


def test_restricao_da_alfatec() -> None:
    dados = obtido(Cenario().consultar(CNPJ_ALFATEC)).dados
    inidoneos = dados.certidao(TipoCertidaoTcu.INIDONEOS)
    assert inidoneos is not None
    assert inidoneos.situacao is SituacaoCertidaoTcu.CONSTAM_REGISTROS


def test_cnpj_fora_da_base_do_tcu_e_obtido_com_marcacao() -> None:
    dados = obtido(Cenario().consultar(CNPJ_FORA_DO_TCU)).dados
    assert not dados.cnpj_encontrado
    assert dados.razao_social is None


def test_alfanumerico_e_obtido_com_cnia_nao_suportado() -> None:
    dados = obtido(Cenario().consultar(CNPJ_ALFANUMERICO)).dados
    cnia = dados.certidao(TipoCertidaoTcu.CNIA)
    assert cnia is not None
    assert cnia.situacao is SituacaoCertidaoTcu.NAO_SUPORTADO


def test_cnia_com_processo() -> None:
    cnia = obtido(Cenario().consultar(CNPJ_CNIA)).dados.certidao(TipoCertidaoTcu.CNIA)
    assert cnia is not None
    assert cnia.processos == ("09000212620168240040",)


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
    [(timedelta(hours=23, minutes=59), 0), (timedelta(hours=24, minutes=1), 1), (timedelta(days=7), 1)],
)
def test_cache_vale_24_horas(idade: timedelta, chamadas: int) -> None:
    cenario = Cenario()
    cenario.semear(CNPJ_OKBR, ler(f"{CNPJ_OKBR}.json"), idade)
    obtido(cenario.consultar(CNPJ_OKBR))
    assert cenario.chamadas_de(CNPJ_OKBR) == chamadas


def test_validade_configuravel() -> None:
    cenario = Cenario()
    cenario.semear(CNPJ_OKBR, ler(f"{CNPJ_OKBR}.json"), timedelta(hours=2))

    async def rodar() -> Coleta[RespostaTcu]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(cenario.responder)) as cliente:
            fonte = FonteTcu(
                ClienteHttp(cliente, POLITICA_RETRY),
                cenario.evidencias,
                validade=timedelta(hours=1),
                relogio=cenario.relogio,
            )
            return await fonte.consultar(CNPJ_OKBR)

    assert not obtido(asyncio.run(rodar())).evidencia.de_cache
    assert cenario.chamadas_de(CNPJ_OKBR) == 1


def test_relogio_injetado_decide_a_validade_do_cache() -> None:
    cenario = Cenario()
    obtido(cenario.consultar(CNPJ_OKBR))
    cenario.relogio.avancar(timedelta(hours=23))
    assert obtido(cenario.consultar(CNPJ_OKBR)).evidencia.de_cache
    cenario.relogio.avancar(timedelta(hours=1, minutes=1))
    assert not obtido(cenario.consultar(CNPJ_OKBR)).evidencia.de_cache
    assert cenario.chamadas_de(CNPJ_OKBR) == 2


def test_ignorar_cache_chama_a_rede() -> None:
    cenario = Cenario()
    cenario.consultar(CNPJ_OKBR)
    coleta = obtido(cenario.consultar(CNPJ_OKBR, ignorar_cache=True))
    assert not coleta.evidencia.de_cache
    assert cenario.chamadas_de(CNPJ_OKBR) == 2
    assert len(cenario.evidencias.de(FONTE)) == 2


def test_cache_e_por_cnpj() -> None:
    cenario = Cenario()
    obtido(cenario.consultar(CNPJ_OKBR))
    assert not obtido(cenario.consultar(CNPJ_ALFATEC)).evidencia.de_cache
    assert cenario.chamadas_de(CNPJ_ALFATEC) == 1


def test_412_de_dv_invalido_vira_falha_4xx_sem_retry() -> None:
    cenario = Cenario()
    coleta = falha(cenario.consultar(CNPJ_DV_INVALIDO))
    assert coleta.motivo is MotivoFalha.HTTP_4XX
    assert coleta.detalhe == "HTTP 412"
    assert coleta.evidencia is not None
    [gravada] = cenario.evidencias.de(FONTE)
    assert gravada.resultado is ResultadoResposta.FALHA
    assert gravada.motivo_falha is MotivoFalha.HTTP_4XX
    assert gravada.http_status == 412
    assert gravada.chave == CNPJ_DV_INVALIDO
    assert gravada.url == url(CNPJ_DV_INVALIDO)
    assert gravada.tentativas == 1
    assert cenario.chamadas_de(CNPJ_DV_INVALIDO) == 1
    assert cenario.esperas == []


@pytest.mark.parametrize(
    ("rota", "motivo", "status"),
    [
        (corpo(500, b""), MotivoFalha.HTTP_5XX, 500),
        (corpo(503, b"<html>indisponivel</html>"), MotivoFalha.HTTP_5XX, 503),
        (corpo(429, b""), MotivoFalha.HTTP_429, 429),
        (lanca(httpx.ReadTimeout), MotivoFalha.TIMEOUT, None),
        (lanca(httpx.ConnectError), MotivoFalha.CONEXAO, None),
    ],
)
def test_falha_retentavel_tenta_duas_vezes(rota: Rota, motivo: MotivoFalha, status: int | None) -> None:
    cenario = Cenario()
    cenario.rotas[f"{CAMINHO}/{CNPJ_OKBR}"] = rota
    coleta = falha(cenario.consultar(CNPJ_OKBR))
    assert coleta.motivo is motivo
    assert coleta.evidencia is not None
    assert coleta.evidencia.sha256 is None
    [gravada] = cenario.evidencias.de(FONTE)
    assert gravada.resultado is ResultadoResposta.FALHA
    assert gravada.motivo_falha is motivo
    assert gravada.http_status == status
    assert gravada.tentativas == 2
    assert gravada.corpo is None
    assert gravada.url == url(CNPJ_OKBR)
    assert cenario.chamadas_de(CNPJ_OKBR) == 2
    assert cenario.esperas == [POLITICA_RETRY.espera_inicial_s]


def test_403_nao_retenta() -> None:
    cenario = Cenario()
    cenario.rotas[f"{CAMINHO}/{CNPJ_OKBR}"] = corpo(403, b"Requisicao rejeitada")
    assert falha(cenario.consultar(CNPJ_OKBR)).motivo is MotivoFalha.HTTP_4XX
    assert cenario.chamadas_de(CNPJ_OKBR) == 1


def test_timeout_seguido_de_sucesso_na_segunda_tentativa() -> None:
    cenario = Cenario()
    cenario.rotas[f"{CAMINHO}/{CNPJ_OKBR}"] = sequencia(
        lanca(httpx.ReadTimeout), corpo(200, f"{CNPJ_OKBR}.json")
    )
    coleta = obtido(cenario.consultar(CNPJ_OKBR))
    assert coleta.evidencia.sha256 == SHA256_OKBR
    [gravada] = cenario.evidencias.de(FONTE)
    assert gravada.tentativas == 2
    assert cenario.chamadas_de(CNPJ_OKBR) == 2


def test_falha_nao_vira_cache() -> None:
    cenario = Cenario()
    cenario.rotas[f"{CAMINHO}/{CNPJ_OKBR}"] = corpo(500, b"")
    falha(cenario.consultar(CNPJ_OKBR))
    cenario.rotas[f"{CAMINHO}/{CNPJ_OKBR}"] = ROTAS_PADRAO[f"{CAMINHO}/{CNPJ_OKBR}"]
    assert not obtido(cenario.consultar(CNPJ_OKBR)).evidencia.de_cache
    assert cenario.chamadas_de(CNPJ_OKBR) == 3
    assert [g.resultado for g in cenario.evidencias.de(FONTE)] == [
        ResultadoResposta.FALHA,
        ResultadoResposta.OBTIDO,
    ]


@pytest.mark.parametrize(
    "conteudo",
    [
        b'{"foo":1}',
        b"<html>manutencao</html>",
        b"",
        ler(f"412_{CNPJ_DV_INVALIDO}.json"),
        ler(f"{CNPJ_OKBR}.json").replace(b'"situacao":"NADA_CONSTA"', b'"situacao":"EM_ANALISE"', 1),
        ler(f"{CNPJ_OKBR}.json").replace(b'"tipo":"CNIA"', b'"tipo":"CNIB"'),
    ],
)
def test_formato_inesperado_vira_falha_com_evidencia(conteudo: bytes) -> None:
    cenario = Cenario()
    cenario.rotas[f"{CAMINHO}/{CNPJ_OKBR}"] = corpo(200, conteudo)
    coleta = falha(cenario.consultar(CNPJ_OKBR))
    assert coleta.motivo is MotivoFalha.FORMATO_INESPERADO
    assert coleta.detalhe.startswith("TCU")
    assert coleta.evidencia is not None
    assert coleta.evidencia.sha256 == hashlib.sha256(conteudo).hexdigest()
    [gravada] = cenario.evidencias.de(FONTE)
    assert gravada.resultado is ResultadoResposta.OBTIDO
    assert gravada.corpo == conteudo


def test_resposta_de_outro_cnpj_vira_falha() -> None:
    cenario = Cenario()
    cenario.rotas[f"{CAMINHO}/{CNPJ_OKBR}"] = corpo(200, f"{CNPJ_ALFATEC}.json")
    coleta = falha(cenario.consultar(CNPJ_OKBR))
    assert coleta.motivo is MotivoFalha.FORMATO_INESPERADO
    assert CNPJ_ALFATEC in coleta.detalhe


def test_formato_inesperado_em_cache_tambem_vira_falha() -> None:
    cenario = Cenario()
    cenario.semear(CNPJ_OKBR, b'{"foo":1}', timedelta(hours=1))
    coleta = falha(cenario.consultar(CNPJ_OKBR))
    assert coleta.motivo is MotivoFalha.FORMATO_INESPERADO
    assert coleta.evidencia is not None
    assert coleta.evidencia.de_cache
    assert cenario.chamadas_de(CNPJ_OKBR) == 0


def test_url_base_com_barra_final() -> None:
    cenario = Cenario(url_base=f"{URL_BASE}/")
    obtido(cenario.consultar(CNPJ_OKBR))
    assert cenario.evidencias.de(FONTE)[0].url == url(CNPJ_OKBR)
