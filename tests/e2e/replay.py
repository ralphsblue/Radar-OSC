import asyncio
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

FIXTURES = Path(__file__).parent.parent / "fixtures" / "fontes"
FIXTURES_OPENCNPJ = FIXTURES / "opencnpj"
FIXTURES_BRASILAPI = FIXTURES / "brasilapi"
HOST_OPENCNPJ = "api.opencnpj.org"
HOST_BRASILAPI = "brasilapi.com.br"
PREFIXO_BRASILAPI = "/api/cnpj/v1/"
FUSO = ZoneInfo("America/Sao_Paulo")
DATA_REFERENCIA = date(2026, 10, 1)
HORA_REFERENCIA = time(12, 0)
_CNPJ = re.compile(r"[0-9A-Z]{14}")
_JSON = {"content-type": "application/json"}
_NAO_ENCONTRADO_OPENCNPJ = b'{"error":"not found"}'
_NAO_ENCONTRADO_BRASILAPI = (
    b'{"message":"CNPJ n\xc3\xa3o encontrado.","type":"not_found","name":"NotFoundError"}'
)
OPCOES_CLIENTE = {"loop_factory": asyncio.SelectorEventLoop}


def instante_referencia(data: date = DATA_REFERENCIA) -> datetime:
    return datetime.combine(data, HORA_REFERENCIA, tzinfo=FUSO)


class RelogioFixo:
    def __init__(self, instante: datetime | None = None) -> None:
        self.instante = instante or instante_referencia()

    def __call__(self) -> datetime:
        return self.instante

    def avancar(self, intervalo: timedelta) -> None:
        self.instante += intervalo


def _arquivos(diretorio: Path, cnpj: str) -> tuple[Path, Path]:
    return diretorio / f"{cnpj}.json", diretorio / f"404_{cnpj}.json"


def _cnpj(requisicao: httpx.Request, diretorio: Path, cnpj: str, nao_encontrado: bytes) -> httpx.Response:
    encontrado, ausente = _arquivos(diretorio, cnpj)
    if encontrado.is_file():
        return httpx.Response(200, content=encontrado.read_bytes(), headers=_JSON, request=requisicao)
    corpo = ausente.read_bytes() if ausente.is_file() else nao_encontrado
    return httpx.Response(404, content=corpo, headers=_JSON, request=requisicao)


class FontesReplay:
    def __init__(self, opencnpj: Path = FIXTURES_OPENCNPJ, brasilapi: Path = FIXTURES_BRASILAPI) -> None:
        self._opencnpj = opencnpj
        self._brasilapi = brasilapi
        self.chamadas: list[httpx.URL] = []
        self.status_forcado: dict[str, int] = {}
        self.transporte = httpx.MockTransport(self._responder)

    def tem_fixture(self, cnpj: str) -> bool:
        return any(arquivo.is_file() for arquivo in _arquivos(self._opencnpj, cnpj))

    def caminhos(self, host: str = HOST_OPENCNPJ) -> list[str]:
        return [url.path for url in self.chamadas if url.host == host]

    def derrubar(self, *hosts: str, status: int = 503) -> None:
        for host in hosts:
            self.status_forcado[host] = status

    def religar(self) -> None:
        self.status_forcado.clear()

    def _responder(self, requisicao: httpx.Request) -> httpx.Response:
        host = requisicao.url.host
        if host not in {HOST_OPENCNPJ, HOST_BRASILAPI}:
            raise AssertionError(f"chamada fora do modo replay: {requisicao.url}")
        self.chamadas.append(requisicao.url)
        status = self.status_forcado.get(host)
        if status is not None:
            return httpx.Response(status, content=b"", request=requisicao)
        if host == HOST_BRASILAPI:
            return self._brasilapi_responder(requisicao)
        return self._opencnpj_responder(requisicao)

    def _brasilapi_responder(self, requisicao: httpx.Request) -> httpx.Response:
        caminho = requisicao.url.path
        cnpj = caminho.removeprefix(PREFIXO_BRASILAPI)
        if not caminho.startswith(PREFIXO_BRASILAPI) or _CNPJ.fullmatch(cnpj) is None:
            return httpx.Response(404, content=_NAO_ENCONTRADO_BRASILAPI, headers=_JSON, request=requisicao)
        return _cnpj(requisicao, self._brasilapi, cnpj, _NAO_ENCONTRADO_BRASILAPI)

    def _opencnpj_responder(self, requisicao: httpx.Request) -> httpx.Response:
        caminho = requisicao.url.path.strip("/")
        if caminho == "info":
            corpo = (self._opencnpj / "info.json").read_bytes()
            return httpx.Response(200, content=corpo, headers=_JSON, request=requisicao)
        if _CNPJ.fullmatch(caminho) is None:
            return httpx.Response(404, content=_NAO_ENCONTRADO_OPENCNPJ, headers=_JSON, request=requisicao)
        if requisicao.url.params.get("datasets"):
            return self._datasets(requisicao, caminho)
        return _cnpj(requisicao, self._opencnpj, caminho, _NAO_ENCONTRADO_OPENCNPJ)

    def _datasets(self, requisicao: httpx.Request, cnpj: str) -> httpx.Response:
        arquivo = self._opencnpj / f"{cnpj}_datasets.json"
        if arquivo.is_file():
            return httpx.Response(200, content=arquivo.read_bytes(), headers=_JSON, request=requisicao)
        return httpx.Response(404, content=_NAO_ENCONTRADO_OPENCNPJ, headers=_JSON, request=requisicao)
