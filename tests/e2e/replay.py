import asyncio
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

FIXTURES_OPENCNPJ = Path(__file__).parent.parent / "fixtures" / "fontes" / "opencnpj"
HOST_OPENCNPJ = "api.opencnpj.org"
FUSO = ZoneInfo("America/Sao_Paulo")
DATA_REFERENCIA = date(2026, 10, 1)
HORA_REFERENCIA = time(12, 0)
_CNPJ = re.compile(r"[0-9A-Z]{14}")
_JSON = {"content-type": "application/json"}
_NAO_ENCONTRADO = b'{"error":"not found"}'
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


class OpenCnpjReplay:
    def __init__(self, diretorio: Path = FIXTURES_OPENCNPJ) -> None:
        self._diretorio = diretorio
        self.chamadas: list[httpx.URL] = []
        self.status_forcado: int | None = None
        self.transporte = httpx.MockTransport(self._responder)

    def tem_fixture(self, cnpj: str) -> bool:
        return any(arquivo.is_file() for arquivo in self._arquivos(cnpj))

    def caminhos(self) -> list[str]:
        return [url.path for url in self.chamadas]

    def _arquivos(self, cnpj: str) -> tuple[Path, Path]:
        return self._diretorio / f"{cnpj}.json", self._diretorio / f"404_{cnpj}.json"

    def _responder(self, requisicao: httpx.Request) -> httpx.Response:
        if requisicao.url.host != HOST_OPENCNPJ:
            raise AssertionError(f"chamada fora do modo replay: {requisicao.url}")
        self.chamadas.append(requisicao.url)
        if self.status_forcado is not None:
            return httpx.Response(self.status_forcado, content=b"", request=requisicao)
        caminho = requisicao.url.path.strip("/")
        if caminho == "info":
            corpo = (self._diretorio / "info.json").read_bytes()
            return httpx.Response(200, content=corpo, headers=_JSON, request=requisicao)
        if _CNPJ.fullmatch(caminho) is None:
            return httpx.Response(404, content=_NAO_ENCONTRADO, headers=_JSON, request=requisicao)
        if requisicao.url.params.get("datasets"):
            return self._datasets(requisicao, caminho)
        encontrado, nao_encontrado = self._arquivos(caminho)
        if encontrado.is_file():
            return httpx.Response(200, content=encontrado.read_bytes(), headers=_JSON, request=requisicao)
        corpo = nao_encontrado.read_bytes() if nao_encontrado.is_file() else _NAO_ENCONTRADO
        return httpx.Response(404, content=corpo, headers=_JSON, request=requisicao)

    def _datasets(self, requisicao: httpx.Request, cnpj: str) -> httpx.Response:
        arquivo = self._diretorio / f"{cnpj}_datasets.json"
        if arquivo.is_file():
            return httpx.Response(200, content=arquivo.read_bytes(), headers=_JSON, request=requisicao)
        return httpx.Response(404, content=_NAO_ENCONTRADO, headers=_JSON, request=requisicao)
