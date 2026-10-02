import hashlib
import os
import time
import uuid
from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, BinaryIO, cast

import psycopg
import structlog
from psycopg.types.json import Jsonb
from sqlalchemy import Connection, Engine, Table, delete, insert, select, text, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from validador_osc import cnpj
from validador_osc.persistencia.modelos import Carga

TAMANHO_CNPJ = 14
TAMANHO_BLOCO = 1024 * 1024
EXEMPLOS_INVALIDOS = 3

log = structlog.get_logger()

_CARGA = cast(Table, Carga.__table__)


class StatusCarga(StrEnum):
    EM_ANDAMENTO = "EM_ANDAMENTO"
    CONCLUIDA = "CONCLUIDA"
    SEM_MUDANCA = "SEM_MUDANCA"
    FALHOU = "FALHOU"


class ErroCarga(Exception):
    pass


class ErroArquivo(ErroCarga):
    pass


class ErroSanidade(ErroCarga):
    pass


_ERROS_ESPERADOS = (ErroCarga, OSError, DBAPIError, psycopg.Error)


@dataclass(frozen=True, slots=True)
class Sanidade:
    minimo_linhas: int
    fracao_minima_anterior: float = 0.5
    fracao_minima_dv_valido: float = 0.99


@dataclass(frozen=True, slots=True)
class Leitura:
    colunas: tuple[str, ...]
    registros: Iterator[Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class DefinicaoBase:
    fonte: str
    tabela: Table
    colunas_esperadas: tuple[str, ...]
    sanidade: Sanidade
    ler: Callable[[Path], AbstractContextManager[Leitura]]


@dataclass(frozen=True, slots=True)
class ArquivoObtido:
    url: str
    data_base: date | None
    extensao: str


@dataclass(frozen=True, slots=True)
class Obtencao:
    url_inicial: str
    gravar: Callable[[BinaryIO], ArquivoObtido]


@dataclass(frozen=True, slots=True)
class ResultadoCarga:
    carga_id: int
    fonte: str
    status: StatusCarga
    linhas: int | None
    data_base: date | None
    sha256: str | None
    duracao_s: float
    erro: str | None = None


@dataclass(slots=True)
class _Contagem:
    linhas: int = 0
    documentos_cnpj: int = 0
    cnpjs_validos: int = 0
    exemplos_invalidos: list[str] = field(default_factory=list)

    def registrar(self, registro: Mapping[str, Any]) -> None:
        self.linhas += 1
        documento = registro.get("documento")
        if isinstance(documento, str) and len(documento) == TAMANHO_CNPJ:
            self.documentos_cnpj += 1
            if cnpj.validar(documento).valido:
                self.cnpjs_validos += 1
            elif len(self.exemplos_invalidos) < EXEMPLOS_INVALIDOS:
                self.exemplos_invalidos.append(documento)


@dataclass(frozen=True, slots=True)
class _Anterior:
    id: int
    linhas: int | None
    data_base: date | None
    arquivo_sha256: str | None


@dataclass(frozen=True, slots=True)
class _Arquivo:
    caminho_relativo: str
    sha256: str
    tamanho: int
    obtido: ArquivoObtido


class CicloCarga:
    def __init__(
        self,
        engine: Engine,
        dir_arquivos: Path,
        relogio: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._engine = engine
        self._dir = dir_arquivos
        self._relogio = relogio

    def executar(self, definicao: DefinicaoBase, obtencao: Obtencao) -> ResultadoCarga:
        inicio = time.perf_counter()
        fonte = definicao.fonte
        carga_id = self._iniciar(fonte, obtencao.url_inicial)
        logger = log.bind(fonte=fonte, carga_id=carga_id)
        logger.info("carga_iniciada", url=obtencao.url_inicial)
        with self._engine.connect() as trava:
            obtida = trava.scalar(text("SELECT pg_try_advisory_lock(hashtextextended(:f, 0))"), {"f": fonte})
            trava.commit()
            if not obtida:
                mensagem = "ErroCarga: outra carga desta fonte está em andamento"
                self._falhar(carga_id, None, mensagem)
                logger.error("carga_falhou", erro=mensagem)
                return self._resultado(carga_id, fonte, StatusCarga.FALHOU, None, inicio, erro=mensagem)
            try:
                return self._executar(carga_id, definicao, obtencao, inicio, logger)
            finally:
                self._limpar_arquivos(fonte, logger)
                trava.execute(text("SELECT pg_advisory_unlock(hashtextextended(:f, 0))"), {"f": fonte})
                trava.commit()

    def _executar(
        self, carga_id: int, definicao: DefinicaoBase, obtencao: Obtencao, inicio: float, logger: Any
    ) -> ResultadoCarga:
        fonte = definicao.fonte
        arquivo: _Arquivo | None = None
        try:
            arquivo = self._obter(fonte, obtencao)
            logger.info(
                "carga_arquivo_obtido",
                url=arquivo.obtido.url,
                sha256=arquivo.sha256,
                bytes=arquivo.tamanho,
                data_base=_iso(arquivo.obtido.data_base),
            )
            anterior = self._ativa(fonte)
            if anterior is not None and _sem_mudanca(anterior, arquivo):
                self._encerrar(carga_id, StatusCarga.SEM_MUDANCA, arquivo)
                resultado = self._resultado(
                    carga_id, fonte, StatusCarga.SEM_MUDANCA, arquivo, inicio, anterior.linhas
                )
                logger.info("carga_sem_mudanca", ativa=anterior.id, duracao_s=resultado.duracao_s)
                return resultado
            linhas, apagadas = self._carregar(carga_id, definicao, arquivo)
            resultado = self._resultado(carga_id, fonte, StatusCarga.CONCLUIDA, arquivo, inicio, linhas)
            logger.info(
                "carga_concluida",
                linhas=linhas,
                data_base=_iso(arquivo.obtido.data_base),
                anterior=anterior.id if anterior is not None else None,
                linhas_antigas_apagadas=apagadas,
                duracao_s=resultado.duracao_s,
            )
            return resultado
        except Exception as erro:
            mensagem = f"{type(erro).__name__}: {erro}"
            self._falhar(carga_id, arquivo, mensagem)
            resultado = self._resultado(carga_id, fonte, StatusCarga.FALHOU, arquivo, inicio, erro=mensagem)
            logger.error("carga_falhou", erro=mensagem, duracao_s=resultado.duracao_s)
            if not isinstance(erro, _ERROS_ESPERADOS):
                raise
            return resultado

    def _resultado(
        self,
        carga_id: int,
        fonte: str,
        status: StatusCarga,
        arquivo: _Arquivo | None,
        inicio: float,
        linhas: int | None = None,
        erro: str | None = None,
    ) -> ResultadoCarga:
        return ResultadoCarga(
            carga_id=carga_id,
            fonte=fonte,
            status=status,
            linhas=linhas,
            data_base=arquivo.obtido.data_base if arquivo is not None else None,
            sha256=arquivo.sha256 if arquivo is not None else None,
            duracao_s=round(time.perf_counter() - inicio, 3),
            erro=erro,
        )

    def _iniciar(self, fonte: str, url: str) -> int:
        with self._engine.begin() as conexao:
            carga_id = conexao.scalar(
                insert(_CARGA)
                .values(
                    fonte=fonte,
                    status=StatusCarga.EM_ANDAMENTO.value,
                    iniciada_em=self._relogio(),
                    url=url,
                )
                .returning(_CARGA.c.id)
            )
        if carga_id is None:
            raise ErroCarga("insert da carga não devolveu id")
        return int(carga_id)

    def _obter(self, fonte: str, obtencao: Obtencao) -> _Arquivo:
        pasta = self._dir / fonte
        pasta.mkdir(parents=True, exist_ok=True)
        parcial = pasta / f".parcial-{uuid.uuid4().hex}"
        try:
            with parcial.open("wb") as destino:
                obtido = obtencao.gravar(destino)
            sha256, tamanho = _hash(parcial)
            nome = f"{sha256}.{obtido.extensao}"
            os.replace(parcial, pasta / nome)
        finally:
            parcial.unlink(missing_ok=True)
        return _Arquivo(f"{fonte}/{nome}", sha256, tamanho, obtido)

    def _ativa(self, fonte: str, conexao: Connection | None = None) -> _Anterior | None:
        consulta = select(_CARGA.c.id, _CARGA.c.linhas, _CARGA.c.data_base, _CARGA.c.arquivo_sha256).where(
            _CARGA.c.fonte == fonte, _CARGA.c.ativa.is_(True)
        )
        if conexao is None:
            with self._engine.connect() as propria:
                linha = propria.execute(consulta).first()
        else:
            linha = conexao.execute(consulta.with_for_update()).first()
        if linha is None:
            return None
        return _Anterior(linha.id, linha.linhas, linha.data_base, linha.arquivo_sha256)

    def _carregar(self, carga_id: int, definicao: DefinicaoBase, arquivo: _Arquivo) -> tuple[int, int]:
        caminho = self._dir / arquivo.caminho_relativo
        contagem = _Contagem()
        with self._engine.begin() as conexao:
            with definicao.ler(caminho) as leitura:
                if leitura.colunas != definicao.colunas_esperadas:
                    raise ErroSanidade(
                        f"colunas diferentes das esperadas: recebidas {list(leitura.colunas)}, "
                        f"esperadas {list(definicao.colunas_esperadas)}"
                    )
                _copiar(conexao, definicao.tabela, carga_id, _contando(leitura.registros, contagem))
            anterior = self._ativa(definicao.fonte, conexao)
            _verificar_sanidade(definicao.sanidade, contagem, arquivo.obtido.data_base, anterior)
            if anterior is not None:
                conexao.execute(update(_CARGA).where(_CARGA.c.id == anterior.id).values(ativa=False))
            conexao.execute(
                update(_CARGA)
                .where(_CARGA.c.id == carga_id)
                .values(
                    ativa=True,
                    linhas=contagem.linhas,
                    **self._campos_conclusao(StatusCarga.CONCLUIDA, arquivo),
                )
            )
            mantidas = [carga_id] if anterior is None else [carga_id, anterior.id]
            apagadas = _reter(conexao, definicao.tabela, definicao.fonte, mantidas)
        return contagem.linhas, apagadas

    def _campos_conclusao(self, status: StatusCarga, arquivo: _Arquivo | None) -> dict[str, Any]:
        campos: dict[str, Any] = {"status": status.value, "concluida_em": self._relogio()}
        if arquivo is not None:
            campos |= {
                "url": arquivo.obtido.url,
                "data_base": arquivo.obtido.data_base,
                "arquivo_caminho": arquivo.caminho_relativo,
                "arquivo_sha256": arquivo.sha256,
                "arquivo_bytes": arquivo.tamanho,
            }
        return campos

    def _encerrar(
        self,
        carga_id: int,
        status: StatusCarga,
        arquivo: _Arquivo | None,
        linhas: int | None = None,
        erro: str | None = None,
    ) -> None:
        with self._engine.begin() as conexao:
            conexao.execute(
                update(_CARGA)
                .where(_CARGA.c.id == carga_id)
                .values(linhas=linhas, erro=erro, **self._campos_conclusao(status, arquivo))
            )

    def _falhar(self, carga_id: int, arquivo: _Arquivo | None, erro: str) -> None:
        self._encerrar(carga_id, StatusCarga.FALHOU, arquivo, erro=erro)

    def _limpar_arquivos(self, fonte: str, logger: Any) -> None:
        ativa = self._caminho_ativo(fonte)
        with self._engine.begin() as conexao:
            condicao = _CARGA.c.arquivo_caminho.is_not(None) & (_CARGA.c.fonte == fonte)
            if ativa is not None:
                condicao &= _CARGA.c.arquivo_caminho != ativa
            conexao.execute(update(_CARGA).where(condicao).values(arquivo_caminho=None))
        pasta = self._dir / fonte
        if not pasta.is_dir():
            return
        for arquivo in pasta.iterdir():
            relativo = f"{fonte}/{arquivo.name}"
            if relativo == ativa or arquivo.name.startswith(".parcial-") or not arquivo.is_file():
                continue
            arquivo.unlink(missing_ok=True)
            logger.info("carga_arquivo_apagado", arquivo=relativo)

    def _caminho_ativo(self, fonte: str) -> str | None:
        with self._engine.connect() as conexao:
            caminho = conexao.scalar(
                select(_CARGA.c.arquivo_caminho).where(_CARGA.c.fonte == fonte, _CARGA.c.ativa.is_(True))
            )
        return str(caminho) if caminho is not None else None


def _sem_mudanca(anterior: _Anterior, arquivo: _Arquivo) -> bool:
    if anterior.arquivo_sha256 != arquivo.sha256:
        return False
    nova = arquivo.obtido.data_base
    return nova is None or (anterior.data_base is not None and nova <= anterior.data_base)


def _reter(conexao: Connection, tabela: Table, fonte: str, mantidas: list[int]) -> int:
    antigas = select(_CARGA.c.id).where(_CARGA.c.fonte == fonte, _CARGA.c.id.not_in(mantidas))
    resultado = conexao.execute(delete(tabela).where(tabela.c.carga_id.in_(antigas)))
    return max(resultado.rowcount, 0)


def _iso(data: date | None) -> str | None:
    return data.isoformat() if data is not None else None


def _hash(caminho: Path) -> tuple[str, int]:
    resumo = hashlib.sha256()
    tamanho = 0
    with caminho.open("rb") as origem:
        while bloco := origem.read(TAMANHO_BLOCO):
            resumo.update(bloco)
            tamanho += len(bloco)
    return resumo.hexdigest(), tamanho


def _contando(registros: Iterator[Mapping[str, Any]], contagem: _Contagem) -> Iterator[Mapping[str, Any]]:
    for registro in registros:
        contagem.registrar(registro)
        yield registro


def _copiar(
    conexao: Connection, tabela: Table, carga_id: int, registros: Iterator[Mapping[str, Any]]
) -> None:
    colunas = [coluna for coluna in tabela.columns if coluna.name not in {"id", "carga_id"}]
    json = {coluna.name for coluna in colunas if isinstance(coluna.type, JSONB)}
    nomes = ", ".join(["carga_id", *(coluna.name for coluna in colunas)])
    bruta = cast(psycopg.Connection[Any], conexao.connection.driver_connection)
    with bruta.cursor() as cursor, cursor.copy(f"COPY {tabela.name} ({nomes}) FROM STDIN") as copia:
        for registro in registros:
            copia.write_row(
                (
                    carga_id,
                    *(
                        Jsonb(registro[coluna.name]) if coluna.name in json else registro[coluna.name]
                        for coluna in colunas
                    ),
                )
            )


def _verificar_sanidade(
    sanidade: Sanidade, contagem: _Contagem, data_base: date | None, anterior: _Anterior | None
) -> None:
    if contagem.linhas < sanidade.minimo_linhas:
        raise ErroSanidade(f"{contagem.linhas} linhas, abaixo do mínimo de {sanidade.minimo_linhas}")
    if contagem.documentos_cnpj:
        fracao = contagem.cnpjs_validos / contagem.documentos_cnpj
        if fracao < sanidade.fracao_minima_dv_valido:
            raise ErroSanidade(
                f"só {fracao:.1%} dos CNPJs com DV válido (mínimo {sanidade.fracao_minima_dv_valido:.0%}); "
                f"exemplos inválidos: {contagem.exemplos_invalidos}"
            )
    if anterior is None:
        return
    if anterior.linhas:
        minimo = anterior.linhas * sanidade.fracao_minima_anterior
        if contagem.linhas < minimo:
            raise ErroSanidade(
                f"{contagem.linhas} linhas contra {anterior.linhas} da carga ativa {anterior.id} "
                f"(queda maior que {1 - sanidade.fracao_minima_anterior:.0%})"
            )
    if data_base is not None and anterior.data_base is not None and data_base < anterior.data_base:
        raise ErroSanidade(
            f"data da base {data_base.isoformat()} anterior à da carga ativa "
            f"{anterior.id} ({anterior.data_base.isoformat()})"
        )
