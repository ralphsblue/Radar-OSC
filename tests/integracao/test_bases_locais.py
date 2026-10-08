import asyncio
import hashlib
import re
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine, insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.csv_cgu import (
    alterar,
    compactar,
    cpf_sintetico,
    fixture,
    formatar_cpf,
    gravar_csv,
    ler_fixture,
)
from validador_osc import cli
from validador_osc.bases_locais import sancoes_cgu
from validador_osc.bases_locais.carga import CicloCarga, ResultadoCarga, Sanidade, StatusCarga
from validador_osc.bases_locais.sancoes_cgu import FONTES_CGU, definicao, obtencao_local
from validador_osc.config import obter_configuracao
from validador_osc.dominio.pessoa_fisica import contem_cpf
from validador_osc.dominio.sancoes import CadastroSancao, ListaTcu, TipoPessoa
from validador_osc.persistencia.banco import criar_engine_async, criar_fabrica_sessoes
from validador_osc.persistencia.bases import RepositorioBasesLocais
from validador_osc.persistencia.modelos import Carga, ListaTcuRegistro, SancaoRegistro

pytestmark = pytest.mark.db

SANIDADE_TESTE = Sanidade(minimo_linhas=5)
DOWNLOADS_FASE0 = Path(__file__).parent.parent.parent / "fase0" / "portal" / "downloads"

type Sessoes = async_sessionmaker[AsyncSession]


def rodar[T](url: str, funcao: Callable[[RepositorioBasesLocais], Awaitable[T]]) -> T:
    async def principal() -> T:
        engine = criar_engine_async(url)
        try:
            return await funcao(RepositorioBasesLocais(criar_fabrica_sessoes(engine)))
        finally:
            await engine.dispose()

    return asyncio.run(principal(), loop_factory=asyncio.SelectorEventLoop)


@pytest.fixture
def engine(banco_limpo: str) -> Iterator[Engine]:
    motor = create_engine(banco_limpo)
    yield motor
    motor.dispose()


@pytest.fixture
def arquivos(tmp_path: Path) -> Path:
    return tmp_path / "arquivos"


def ingerir(
    engine: Engine, arquivos: Path, fonte: str, arquivo: Path, sanidade: Sanidade = SANIDADE_TESTE
) -> ResultadoCarga:
    ciclo = CicloCarga(engine, arquivos)
    return ciclo.executar(definicao(FONTES_CGU[fonte], sanidade), obtencao_local(arquivo))


def cargas(engine: Engine) -> list[Any]:
    with engine.connect() as conexao:
        return list(conexao.execute(select(Carga.__table__).order_by(Carga.id)).mappings())


def contar(engine: Engine, carga_id: int) -> int:
    with engine.connect() as conexao:
        total = conexao.scalar(
            select(text("count(*)")).select_from(SancaoRegistro).where(SancaoRegistro.carga_id == carga_id)
        )
    return int(total or 0)


def arquivos_em(arquivos: Path, fonte: str) -> list[str]:
    pasta = arquivos / fonte
    return sorted(p.name for p in pasta.iterdir()) if pasta.exists() else []


def variante(
    tmp_path: Path, nome: str, cadastro: str, linhas_extras: int = 0, manter: int | None = None
) -> Path:
    cabecalho, linhas = ler_fixture(cadastro)
    codigo = "CÓDIGO DA SANÇÃO" if cadastro != "CEPIM" else "NÚMERO CONVÊNIO"
    extras = [alterar(cabecalho, linhas[-1], {codigo: f"99{n:04d}"}) for n in range(linhas_extras)]
    selecionadas = (linhas if manter is None else linhas[:manter]) + extras
    return gravar_csv(tmp_path / "variantes" / nome, (cabecalho, selecionadas))


def test_primeira_carga_concluida(engine: Engine, arquivos: Path) -> None:
    resultado = ingerir(engine, arquivos, "cgu_ceis", fixture("CEIS"))
    assert resultado.status is StatusCarga.CONCLUIDA
    assert resultado.linhas == 14
    assert resultado.data_base == date(2026, 9, 30)
    assert resultado.erro is None
    (carga,) = cargas(engine)
    sha = hashlib.sha256(fixture("CEIS").read_bytes()).hexdigest()
    assert carga["status"] == "CONCLUIDA"
    assert carga["ativa"] is True
    assert carga["linhas"] == 14
    assert carga["data_base"] == date(2026, 9, 30)
    assert carga["arquivo_sha256"] == sha
    assert carga["arquivo_caminho"] == f"cgu_ceis/{sha}.csv"
    assert carga["arquivo_bytes"] == fixture("CEIS").stat().st_size
    assert carga["url"] == fixture("CEIS").resolve().as_uri()
    assert carga["concluida_em"] is not None
    assert (arquivos / carga["arquivo_caminho"]).read_bytes() == fixture("CEIS").read_bytes()
    assert contar(engine, carga["id"]) == 14


def test_zip_oficial(engine: Engine, arquivos: Path, tmp_path: Path) -> None:
    arquivo_zip = compactar(fixture("CNEP"), tmp_path / "20260930_CNEP.zip")
    resultado = ingerir(engine, arquivos, "cgu_cnep", arquivo_zip)
    assert resultado.status is StatusCarga.CONCLUIDA
    assert resultado.linhas == 11
    assert arquivos_em(arquivos, "cgu_cnep") == [f"{resultado.sha256}.zip"]


def test_mesmo_arquivo_fica_sem_mudanca(engine: Engine, arquivos: Path) -> None:
    primeira = ingerir(engine, arquivos, "cgu_ceis", fixture("CEIS"))
    segunda = ingerir(engine, arquivos, "cgu_ceis", fixture("CEIS"))
    assert segunda.status is StatusCarga.SEM_MUDANCA
    assert segunda.linhas == 14
    anterior, nova = cargas(engine)
    assert anterior["ativa"] is True
    assert nova["ativa"] is False
    assert nova["status"] == "SEM_MUDANCA"
    assert nova["arquivo_sha256"] == anterior["arquivo_sha256"]
    assert contar(engine, nova["id"]) == 0
    assert arquivos_em(arquivos, "cgu_ceis") == [f"{primeira.sha256}.csv"]


def test_troca_atomica_e_arquivo_anterior_apagado(engine: Engine, arquivos: Path, tmp_path: Path) -> None:
    primeira = ingerir(engine, arquivos, "cgu_ceis", fixture("CEIS"))
    nova_versao = variante(tmp_path, "20261001_CEIS.csv", "CEIS", linhas_extras=2)
    segunda = ingerir(engine, arquivos, "cgu_ceis", nova_versao)
    assert segunda.status is StatusCarga.CONCLUIDA
    assert segunda.linhas == 16
    anterior, atual = cargas(engine)
    assert anterior["ativa"] is False
    assert anterior["arquivo_caminho"] is None
    assert anterior["arquivo_sha256"] == primeira.sha256
    assert atual["ativa"] is True
    assert atual["data_base"] == date(2026, 10, 1)
    assert arquivos_em(arquivos, "cgu_ceis") == [f"{segunda.sha256}.csv"]
    assert contar(engine, anterior["id"]) == 14
    consulta = rodar(engine.url.render_as_string(hide_password=False), lambda r: r.carga_ativa("cgu_ceis"))
    assert consulta is not None
    assert consulta.id == atual["id"]
    assert consulta.data_base == date(2026, 10, 1)
    assert consulta.arquivo_sha256 == segunda.sha256


def test_queda_brusca_de_linhas_falha_e_mantem_a_ativa(
    engine: Engine, arquivos: Path, tmp_path: Path
) -> None:
    primeira = ingerir(engine, arquivos, "cgu_ceis", fixture("CEIS"))
    menor = variante(tmp_path, "20261001_CEIS.csv", "CEIS", manter=6)
    resultado = ingerir(engine, arquivos, "cgu_ceis", menor)
    assert resultado.status is StatusCarga.FALHOU
    assert resultado.erro is not None
    assert "queda maior que 50%" in resultado.erro
    anterior, falha = cargas(engine)
    assert anterior["ativa"] is True
    assert falha["ativa"] is False
    assert falha["status"] == "FALHOU"
    assert falha["erro"] == resultado.erro
    assert falha["arquivo_caminho"] is None
    assert contar(engine, falha["id"]) == 0
    assert arquivos_em(arquivos, "cgu_ceis") == [f"{primeira.sha256}.csv"]


def test_minimo_de_linhas_na_primeira_carga(engine: Engine, arquivos: Path) -> None:
    resultado = ingerir(engine, arquivos, "cgu_cepim", fixture("CEPIM"), FONTES_CGU["cgu_cepim"].sanidade)
    assert resultado.status is StatusCarga.FALHOU
    assert resultado.erro is not None
    assert "abaixo do mínimo de 3000" in resultado.erro
    assert all(not c["ativa"] for c in cargas(engine))
    assert arquivos_em(arquivos, "cgu_cepim") == []


def test_colunas_diferentes_falham(engine: Engine, arquivos: Path, tmp_path: Path) -> None:
    cabecalho, linhas = ler_fixture("CEPIM")
    cabecalho[-1] = "MOTIVO"
    caminho = gravar_csv(tmp_path / "20260928_CEPIM.csv", (cabecalho, linhas))
    resultado = ingerir(engine, arquivos, "cgu_cepim", caminho)
    assert resultado.status is StatusCarga.FALHOU
    assert resultado.erro is not None
    assert "colunas diferentes" in resultado.erro


def test_data_mais_antiga_que_a_ativa_falha(engine: Engine, arquivos: Path, tmp_path: Path) -> None:
    ingerir(engine, arquivos, "cgu_ceis", fixture("CEIS"))
    antiga = variante(tmp_path, "20260901_CEIS.csv", "CEIS", linhas_extras=1)
    resultado = ingerir(engine, arquivos, "cgu_ceis", antiga)
    assert resultado.status is StatusCarga.FALHOU
    assert resultado.erro is not None
    assert "anterior à da carga ativa" in resultado.erro


def test_cnpjs_com_dv_invalido_falham(engine: Engine, arquivos: Path, tmp_path: Path) -> None:
    cabecalho, linhas = ler_fixture("CEPIM")
    invalidas = [alterar(cabecalho, linha, {"CNPJ ENTIDADE": linha[0][:12] + "00"}) for linha in linhas]
    caminho = gravar_csv(tmp_path / "20260928_CEPIM.csv", (cabecalho, invalidas))
    resultado = ingerir(engine, arquivos, "cgu_cepim", caminho)
    assert resultado.status is StatusCarga.FALHOU
    assert resultado.erro is not None
    assert "DV válido" in resultado.erro


def test_erro_de_parse_falha_sem_gravar_linhas(engine: Engine, arquivos: Path, tmp_path: Path) -> None:
    cabecalho, linhas = ler_fixture("CNEP")
    linhas[-1] = alterar(cabecalho, linhas[-1], {"DATA INÍCIO SANÇÃO": "99/99/2026"})
    caminho = gravar_csv(tmp_path / "20260930_CNEP.csv", (cabecalho, linhas))
    resultado = ingerir(engine, arquivos, "cgu_cnep", caminho)
    assert resultado.status is StatusCarga.FALHOU
    assert resultado.erro is not None
    assert resultado.erro.startswith("ErroArquivo: linha 12")
    (carga,) = cargas(engine)
    assert contar(engine, carga["id"]) == 0


def test_arquivo_inexistente_falha(engine: Engine, arquivos: Path, tmp_path: Path) -> None:
    resultado = ingerir(engine, arquivos, "cgu_cnep", tmp_path / "20260930_CNEP.zip")
    assert resultado.status is StatusCarga.FALHOU
    assert resultado.erro is not None
    assert "FileNotFoundError" in resultado.erro
    assert arquivos_em(arquivos, "cgu_cnep") == []


def test_carga_concorrente_da_mesma_fonte_falha(engine: Engine, arquivos: Path) -> None:
    with engine.connect() as outra:
        outra.execute(text("SELECT pg_advisory_lock(hashtextextended('cgu_ceis', 0))"))
        resultado = ingerir(engine, arquivos, "cgu_ceis", fixture("CEIS"))
        outra.execute(text("SELECT pg_advisory_unlock(hashtextextended('cgu_ceis', 0))"))
    assert resultado.status is StatusCarga.FALHOU
    assert resultado.erro is not None
    assert "em andamento" in resultado.erro
    assert ingerir(engine, arquivos, "cgu_ceis", fixture("CEIS")).status is StatusCarga.CONCLUIDA


def test_leitura_por_cnpj_e_por_raiz(engine: Engine, arquivos: Path) -> None:
    ingerir(engine, arquivos, "cgu_ceis", fixture("CEIS"))
    url = engine.url.render_as_string(hide_password=False)
    matriz = rodar(url, lambda r: r.sancoes_pj(CadastroSancao.CEIS, "06278833000103"))
    assert matriz is not None
    assert matriz.carga.fonte == "cgu_ceis"
    assert {(s.codigo_sancao, s.documento) for s in matriz.registros} == {
        ("105078", "06278833000103"),
        ("900001", "06278833000286"),
    }
    filial = rodar(url, lambda r: r.sancoes_pj(CadastroSancao.CEIS, "06278833000286"))
    assert filial is not None
    assert {s.codigo_sancao for s in filial.registros} == {"105078", "900001"}
    limpa = rodar(url, lambda r: r.sancoes_pj(CadastroSancao.CEIS, "19131243000197"))
    assert limpa is not None
    assert limpa.registros == ()
    sem_base = rodar(url, lambda r: r.sancoes_pj(CadastroSancao.CNEP, "06278833000103"))
    assert sem_base is None


def test_leitura_da_sancao_completa(engine: Engine, arquivos: Path) -> None:
    ingerir(engine, arquivos, "cgu_cnep", fixture("CNEP"))
    url = engine.url.render_as_string(hide_password=False)
    consulta = rodar(url, lambda r: r.sancoes_pj(CadastroSancao.CNEP, "27869148000113"))
    assert consulta is not None
    multa = next(s for s in consulta.registros if s.codigo_sancao == "297586")
    assert multa.cadastro is CadastroSancao.CNEP
    assert multa.tipo_pessoa is TipoPessoa.JURIDICA
    assert str(multa.valor_multa) == "51436.42"
    assert multa.data_inicio == date(2024, 3, 1)
    assert multa.data_fim is None
    assert multa.esfera is not None


def test_leitura_de_pessoa_fisica_por_nome_e_seis_digitos(engine: Engine, arquivos: Path) -> None:
    ingerir(engine, arquivos, "cgu_cnep", fixture("CNEP"))
    url = engine.url.render_as_string(hide_password=False)
    achado = rodar(url, lambda r: r.sancoes_pf(CadastroSancao.CNEP, "WALDIR DE OLIVEIRA JUNIOR", "146799"))
    assert achado is not None
    assert {s.codigo_sancao for s in achado.registros} == {"289393", "289394"}
    assert all(s.documento is None and s.tipo_pessoa is TipoPessoa.FISICA for s in achado.registros)
    outro_meio = rodar(
        url, lambda r: r.sancoes_pf(CadastroSancao.CNEP, "WALDIR DE OLIVEIRA JUNIOR", "146790")
    )
    assert outro_meio is not None
    assert outro_meio.registros == ()


def test_listas_do_tcu(engine: Engine) -> None:
    url = engine.url.render_as_string(hide_password=False)
    assert rodar(url, lambda r: r.listas_tcu_pj(ListaTcu.INIDONEOS, "03463763000167")) is None
    agora = datetime(2026, 10, 2, 12, tzinfo=UTC)
    with engine.begin() as conexao:
        carga_id = conexao.scalar(
            insert(Carga)
            .values(
                fonte="tcu_inidoneos",
                status="CONCLUIDA",
                ativa=True,
                data_base=date(2026, 10, 2),
                iniciada_em=agora,
                concluida_em=agora,
                url="https://certidoes.apps.tcu.gov.br/lista-inidoneos",
            )
            .returning(Carga.id)
        )
        conexao.execute(
            insert(ListaTcuRegistro),
            [
                {
                    "carga_id": carga_id,
                    "lista": "INIDONEOS",
                    "tipo_registro": "CNPJ",
                    "documento": documento,
                    "raiz": documento[:8],
                    "nome": "INSTITUTO TERRA SOCIAL",
                    "nome_normalizado": "INSTITUTO TERRA SOCIAL",
                    "processo": "000.000/2020-0",
                    "acordao": "AC-000001/2023-PL",
                    "data_acordao": date(2023, 1, 1),
                    "data_transito": date(2023, 2, 1),
                    "data_final": date(2028, 2, 1),
                    "linha": {"cpf_cnpj": documento},
                }
                for documento in ("03463763000167", "03463763000248")
            ],
        )
    consulta = rodar(url, lambda r: r.listas_tcu_pj(ListaTcu.INIDONEOS, "03463763000167"))
    assert consulta is not None
    assert consulta.carga.id == carga_id
    assert [r.documento for r in consulta.registros] == ["03463763000167", "03463763000248"]
    assert consulta.registros[0].lista is ListaTcu.INIDONEOS
    assert consulta.registros[0].data_final == date(2028, 2, 1)
    assert rodar(url, lambda r: r.listas_tcu_pf(ListaTcu.INABILITADOS, "FULANO", "123456")) is None


def despejo(engine: Engine) -> str:
    with engine.connect() as conexao:
        linhas = [
            *conexao.scalars(text("SELECT row_to_json(t)::text FROM sancao_registro t")),
            *conexao.scalars(text("SELECT row_to_json(t)::text FROM lista_tcu_registro t")),
            *conexao.scalars(text("SELECT row_to_json(t)::text FROM carga t")),
        ]
    return "\n".join(linhas)


def test_banco_nunca_guarda_cpf_completo(engine: Engine, arquivos: Path, tmp_path: Path) -> None:
    cabecalho, linhas = ler_fixture("CEIS")
    cpfs = [cpf_sintetico(n) for n in range(20, 26)]
    titular, sem_tipo, socio, procurador, nome, processo = cpfs
    pessoa = linhas[0]
    novas = [
        *linhas,
        alterar(
            cabecalho,
            pessoa,
            {
                "CÓDIGO DA SANÇÃO": "800001",
                "CPF OU CNPJ DO SANCIONADO": titular,
                "NOME DO SANCIONADO": f"FULANO DE TAL {formatar_cpf(nome)}",
                "NOME INFORMADO PELO ÓRGÃO SANCIONADOR": f"FULANO {titular}",
                "NÚMERO DO PROCESSO": processo,
                "OBSERVAÇÕES": f"sócio {formatar_cpf(socio)}, procurador {procurador}",
            },
        ),
        alterar(
            cabecalho,
            pessoa,
            {"CÓDIGO DA SANÇÃO": "800002", "TIPO DE PESSOA": "", "CPF OU CNPJ DO SANCIONADO": sem_tipo},
        ),
    ]
    caminho = gravar_csv(tmp_path / "20260930_CEIS.csv", (cabecalho, novas))
    resultado = ingerir(engine, arquivos, "cgu_ceis", caminho)
    assert resultado.status is StatusCarga.CONCLUIDA
    conteudo = despejo(engine)
    for cpf in cpfs:
        assert cpf not in conteudo
        assert formatar_cpf(cpf) not in conteudo
    assert not contem_cpf(conteudo)
    url = engine.url.render_as_string(hide_password=False)
    achado = rodar(url, lambda r: r.sancoes_pf(CadastroSancao.CEIS, "FULANO DE TAL", titular[3:9]))
    assert achado is not None
    assert [s.codigo_sancao for s in achado.registros] == ["800001"]
    with engine.connect() as conexao:
        dv = conexao.scalar(
            select(SancaoRegistro.cpf_dv_final).where(SancaoRegistro.codigo_sancao == "800001")
        )
    assert dv == titular[9:]


def test_banco_recusa_cpf_completo_no_documento(engine: Engine) -> None:
    agora = datetime(2026, 10, 2, 12, tzinfo=UTC)
    with engine.begin() as conexao:
        carga_id = conexao.scalar(
            insert(Carga)
            .values(fonte="cgu_ceis", status="EM_ANDAMENTO", iniciada_em=agora, url="x")
            .returning(Carga.id)
        )
    for tipo in ("F", None):
        with pytest.raises(Exception, match="documento_sem_cpf"), engine.begin() as conexao:
            conexao.execute(
                insert(SancaoRegistro).values(
                    carga_id=carga_id,
                    cadastro="CEIS",
                    tipo_pessoa=tipo,
                    documento=cpf_sintetico(30),
                    nome="X",
                    nome_normalizado="X",
                    linha={},
                )
            )


@pytest.mark.skipif(not DOWNLOADS_FASE0.exists(), reason="downloads reais da fase 0 ausentes")
@pytest.mark.parametrize(
    ("fonte", "nome"), [("cgu_ceis", "20260930_CEIS.zip"), ("cgu_cnep", "20260930_CNEP.zip")]
)
def test_arquivo_real_nao_deixa_cpf_no_banco(engine: Engine, arquivos: Path, fonte: str, nome: str) -> None:
    arquivo = DOWNLOADS_FASE0 / nome
    if not arquivo.exists():
        pytest.skip(f"{nome} ausente")
    resultado = ingerir(engine, arquivos, fonte, arquivo, FONTES_CGU[fonte].sanidade)
    assert resultado.status is StatusCarga.CONCLUIDA
    assert not contem_cpf(despejo(engine))


def test_cli_ingerir(
    banco_limpo: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del banco_limpo
    monkeypatch.setenv("VOSC_DIR_ARQUIVOS", str(tmp_path / "arquivos"))
    monkeypatch.setitem(
        sancoes_cgu.FONTES_CGU, "cgu_cnep", replace(FONTES_CGU["cgu_cnep"], sanidade=SANIDADE_TESTE)
    )
    obter_configuracao.cache_clear()
    try:
        codigo = cli.main(["ingerir", "cgu_cnep", "--arquivo", str(fixture("CNEP"))])
        saida = capsys.readouterr().out
        assert codigo == 0
        assert "cgu_cnep" in saida
        assert "CONCLUIDA" in saida
        assert re.search(r"cgu_cnep\s+CONCLUIDA\s+linhas\s+11\s", saida)
        assert "base 30/09/2026" in saida
        codigo = cli.main(["atualizar-bases", "--diretorio", str(fixture("CNEP").parent)])
        saida = capsys.readouterr().out
        assert codigo == 1
        assert re.search(r"cgu_cepim\s+FALHOU", saida)
        assert "abaixo do mínimo de 3000" in saida
        assert re.search(r"cgu_cnep\s+SEM_MUDANCA", saida)
    finally:
        obter_configuracao.cache_clear()
