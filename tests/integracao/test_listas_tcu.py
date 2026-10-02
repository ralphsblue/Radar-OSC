import asyncio
import re
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine, func, select, text

from tests.csv_cgu import cpf_sintetico, formatar_cpf, gravar_csv
from tests.csv_cgu import fixture as fixture_cgu
from tests.csv_cgu import ler_fixture as ler_fixture_cgu
from tests.json_tcu import alterar, fixture, gravar_json, ler_fixture
from validador_osc import __main__ as cli
from validador_osc.bases_locais import listas_tcu
from validador_osc.bases_locais.carga import CicloCarga, ResultadoCarga, Sanidade, StatusCarga
from validador_osc.bases_locais.listas_tcu import FONTES_TCU, definicao, obtencao_local
from validador_osc.bases_locais.sancoes_cgu import FONTES_CGU
from validador_osc.bases_locais.sancoes_cgu import definicao as definicao_cgu
from validador_osc.bases_locais.sancoes_cgu import obtencao_local as obtencao_local_cgu
from validador_osc.config import obter_configuracao
from validador_osc.dominio.sancoes import ListaTcu
from validador_osc.persistencia.banco import criar_engine_async, criar_fabrica_sessoes
from validador_osc.persistencia.bases import RepositorioBasesLocais
from validador_osc.persistencia.modelos import Carga, ListaTcuRegistro, SancaoRegistro
from validador_osc.pessoa_fisica import contem_cpf

pytestmark = pytest.mark.db

SANIDADE_TESTE = Sanidade(minimo_linhas=3)
DOWNLOADS_FASE0 = Path(__file__).parent.parent.parent / "fase0" / "dirigentes" / "downloads"


def rodar[T](engine: Engine, funcao: Callable[[RepositorioBasesLocais], Awaitable[T]]) -> T:
    async def principal() -> T:
        motor = criar_engine_async(engine.url.render_as_string(hide_password=False))
        try:
            return await funcao(RepositorioBasesLocais(criar_fabrica_sessoes(motor)))
        finally:
            await motor.dispose()

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
    return CicloCarga(engine, arquivos).executar(
        definicao(FONTES_TCU[fonte], sanidade), obtencao_local(arquivo)
    )


def ingerir_cgu(engine: Engine, arquivos: Path, arquivo: Path) -> ResultadoCarga:
    return CicloCarga(engine, arquivos).executar(
        definicao_cgu(FONTES_CGU["cgu_ceis"], Sanidade(minimo_linhas=5)), obtencao_local_cgu(arquivo)
    )


def cargas(engine: Engine, fonte: str) -> list[Any]:
    with engine.connect() as conexao:
        consulta = select(Carga.__table__).where(Carga.fonte == fonte).order_by(Carga.id)
        return list(conexao.execute(consulta).mappings())


def contar(engine: Engine, tabela: type[ListaTcuRegistro] | type[SancaoRegistro], carga_id: int) -> int:
    with engine.connect() as conexao:
        total = conexao.scalar(select(func.count()).select_from(tabela).where(tabela.carga_id == carga_id))
    return int(total or 0)


def versao(tmp_path: Path, fonte: str, data: str, extras: int = 0, manter: int | None = None) -> Path:
    itens = ler_fixture(fonte)
    base = itens[0]
    selecionados = (itens if manter is None else itens[:manter]) + [
        alterar(base, codigoProcesso=900_000 + n) for n in range(extras)
    ]
    return gravar_json(tmp_path / "versoes" / f"{data}_{fonte}.json", selecionados)


def despejo(engine: Engine) -> str:
    with engine.connect() as conexao:
        linhas = [
            *conexao.scalars(text("SELECT row_to_json(t)::text FROM lista_tcu_registro t")),
            *conexao.scalars(text("SELECT row_to_json(t)::text FROM carga t")),
        ]
    return "\n".join(linhas)


@pytest.mark.parametrize(
    ("fonte", "total", "data_base"),
    [
        ("tcu_inidoneos", 8, date(2026, 10, 2)),
        ("tcu_contas_irregulares", 12, date(2026, 10, 1)),
        ("tcu_inabilitados", 6, date(2026, 10, 1)),
    ],
)
def test_carga_das_tres_listas(
    engine: Engine, arquivos: Path, fonte: str, total: int, data_base: date
) -> None:
    resultado = ingerir(engine, arquivos, fonte, fixture(fonte))
    assert resultado.status is StatusCarga.CONCLUIDA
    assert resultado.linhas == total
    assert resultado.data_base == data_base
    (carga,) = cargas(engine, fonte)
    assert carga["ativa"] is True
    assert carga["arquivo_caminho"] == f"{fonte}/{resultado.sha256}.json"
    assert contar(engine, ListaTcuRegistro, carga["id"]) == total
    with engine.connect() as conexao:
        listas = set(conexao.scalars(select(ListaTcuRegistro.lista).distinct()))
    assert listas == {FONTES_TCU[fonte].lista.value}


def test_leitura_por_cnpj_e_por_raiz(engine: Engine, arquivos: Path) -> None:
    ingerir(engine, arquivos, "tcu_inidoneos", fixture("tcu_inidoneos"))
    matriz = rodar(engine, lambda r: r.listas_tcu_pj(ListaTcu.INIDONEOS, "30139983000102"))
    assert matriz is not None
    assert matriz.carga.fonte == "tcu_inidoneos"
    assert matriz.carga.data_base == date(2026, 10, 2)
    assert [r.documento for r in matriz.registros] == ["30139983000102", "30139983000293"]
    filial = rodar(engine, lambda r: r.listas_tcu_pj(ListaTcu.INIDONEOS, "30139983000293"))
    assert filial is not None
    assert len(filial.registros) == 2
    alfatec = rodar(engine, lambda r: r.listas_tcu_pj(ListaTcu.INIDONEOS, "28025673000115"))
    assert alfatec is not None
    (registro,) = alfatec.registros
    assert registro.processo == "024.778/2024-9"
    assert registro.acordao == "1610/2025-PL"
    assert registro.data_final == date(2029, 6, 2)
    limpa = rodar(engine, lambda r: r.listas_tcu_pj(ListaTcu.INIDONEOS, "19131243000197"))
    assert limpa is not None
    assert limpa.registros == ()
    assert rodar(engine, lambda r: r.listas_tcu_pj(ListaTcu.CONTAS_IRREGULARES, "28025673000115")) is None


def test_leitura_de_pessoa_fisica_por_nome_e_seis_digitos(engine: Engine, arquivos: Path) -> None:
    ingerir(engine, arquivos, "tcu_inabilitados", fixture("tcu_inabilitados"))
    achado = rodar(
        engine, lambda r: r.listas_tcu_pf(ListaTcu.INABILITADOS, "JOAO CARLOS DEMONSTRACAO", "456789")
    )
    assert achado is not None
    (registro,) = achado.registros
    assert registro.nome == "JOÃO  CARLOS   DEMONSTRAÇÃO"
    assert registro.documento is None
    assert registro.data_final == date(2028, 8, 25)
    outro_meio = rodar(
        engine, lambda r: r.listas_tcu_pf(ListaTcu.INABILITADOS, "JOAO CARLOS DEMONSTRACAO", "456780")
    )
    assert outro_meio is not None
    assert outro_meio.registros == ()


def test_banco_nunca_guarda_cpf_completo(engine: Engine, arquivos: Path, tmp_path: Path) -> None:
    cpfs = [cpf_sintetico(n) for n in range(40, 46)]
    titular, formatado, no_nome, no_municipio, no_link, outro = cpfs
    itens = ler_fixture("tcu_contas_irregulares")
    pf = next(item for item in itens if item["tipoRegistro"] == "CPF" and item["numeroRegistro"])
    itens += [
        alterar(
            pf,
            numeroRegistro=titular,
            nome=f"BELTRANO DE TAL {formatar_cpf(no_nome)}",
            municipio=f"CIDADE {no_municipio}",
            linkAcompanhamentoProcesso=f"https://exemplo/{no_link}",
        ),
        alterar(pf, numeroRegistro=formatar_cpf(formatado), nome="CICLANO DE TAL"),
        alterar(pf, numeroRegistro=f" {formatar_cpf(outro)} ", nome="FULANO DE TAL"),
    ]
    caminho = gravar_json(tmp_path / "20261001_tcu_contas_irregulares.json", itens)
    resultado = ingerir(engine, arquivos, "tcu_contas_irregulares", caminho)
    assert resultado.status is StatusCarga.CONCLUIDA
    conteudo = despejo(engine)
    for cpf in cpfs:
        assert cpf not in conteudo
        assert formatar_cpf(cpf) not in conteudo
    assert not contem_cpf(conteudo)
    with engine.connect() as conexao:
        documentos_pf = conexao.scalar(
            select(func.count())
            .select_from(ListaTcuRegistro)
            .where(ListaTcuRegistro.tipo_registro == "CPF", ListaTcuRegistro.documento.is_not(None))
        )
        dv = conexao.scalar(
            select(ListaTcuRegistro.cpf_dv_final).where(ListaTcuRegistro.nome_normalizado == "CICLANO DE TAL")
        )
    assert documentos_pf == 0
    assert dv == formatado[9:]
    achado = rodar(
        engine,
        lambda r: r.listas_tcu_pf(ListaTcu.CONTAS_IRREGULARES, "BELTRANO DE TAL", titular[3:9]),
    )
    assert achado is not None
    assert len(achado.registros) == 1


def test_mesmo_conteudo_em_data_nova_vira_carga_nova(engine: Engine, arquivos: Path, tmp_path: Path) -> None:
    primeira = ingerir(engine, arquivos, "tcu_inidoneos", fixture("tcu_inidoneos"))
    mesma_data = ingerir(engine, arquivos, "tcu_inidoneos", fixture("tcu_inidoneos"))
    assert mesma_data.status is StatusCarga.SEM_MUDANCA
    copia = tmp_path / "20261003_tcu_inidoneos.json"
    copia.write_bytes(fixture("tcu_inidoneos").read_bytes())
    nova_data = ingerir(engine, arquivos, "tcu_inidoneos", copia)
    assert nova_data.status is StatusCarga.CONCLUIDA
    assert nova_data.sha256 == primeira.sha256
    ativa = rodar(engine, lambda r: r.carga_ativa("tcu_inidoneos"))
    assert ativa is not None
    assert ativa.id == nova_data.carga_id
    assert ativa.data_base == date(2026, 10, 3)
    assert (arquivos / "tcu_inidoneos" / f"{primeira.sha256}.json").exists()


def test_queda_brusca_falha_e_mantem_a_ativa(engine: Engine, arquivos: Path, tmp_path: Path) -> None:
    ingerir(engine, arquivos, "tcu_contas_irregulares", fixture("tcu_contas_irregulares"))
    menor = versao(tmp_path, "tcu_contas_irregulares", "20261002", manter=5)
    resultado = ingerir(engine, arquivos, "tcu_contas_irregulares", menor)
    assert resultado.status is StatusCarga.FALHOU
    assert resultado.erro is not None
    assert "queda maior que 50%" in resultado.erro
    anterior, falha = cargas(engine, "tcu_contas_irregulares")
    assert anterior["ativa"] is True
    assert contar(engine, ListaTcuRegistro, falha["id"]) == 0


def test_minimo_real_de_linhas(engine: Engine, arquivos: Path) -> None:
    fonte = "tcu_inabilitados"
    resultado = ingerir(engine, arquivos, fonte, fixture(fonte), FONTES_TCU[fonte].sanidade)
    assert resultado.status is StatusCarga.FALHOU
    assert resultado.erro is not None
    assert "abaixo do mínimo de 600" in resultado.erro


def test_colunas_diferentes_falham(engine: Engine, arquivos: Path, tmp_path: Path) -> None:
    itens = [
        {k: v for k, v in item.items() if k != "dataFinalSancao"} for item in ler_fixture("tcu_inidoneos")
    ]
    caminho = gravar_json(tmp_path / "20261002_tcu_inidoneos.json", itens)
    resultado = ingerir(engine, arquivos, "tcu_inidoneos", caminho)
    assert resultado.status is StatusCarga.FALHOU
    assert resultado.erro is not None
    assert "colunas diferentes" in resultado.erro


def test_retencao_mantem_so_a_ativa_e_a_anterior(engine: Engine, arquivos: Path, tmp_path: Path) -> None:
    fonte = "tcu_inabilitados"
    ingerir(engine, arquivos, "tcu_contas_irregulares", fixture("tcu_contas_irregulares"))
    resultados = [
        ingerir(engine, arquivos, fonte, versao(tmp_path, fonte, f"2026100{dia}", extras=dia))
        for dia in range(1, 5)
    ]
    assert all(r.status is StatusCarga.CONCLUIDA for r in resultados)
    falha = ingerir(engine, arquivos, fonte, versao(tmp_path, fonte, "20261005", manter=1))
    assert falha.status is StatusCarga.FALHOU
    linhas = {c["id"]: contar(engine, ListaTcuRegistro, c["id"]) for c in cargas(engine, fonte)}
    primeira, segunda, terceira, quarta = (r.carga_id for r in resultados)
    assert linhas == {primeira: 0, segunda: 0, terceira: 6 + 3, quarta: 6 + 4, falha.carga_id: 0}
    metadados = cargas(engine, fonte)
    assert len(metadados) == 5
    assert all(c["arquivo_sha256"] is not None for c in metadados)
    assert [c["linhas"] for c in metadados[:4]] == [7, 8, 9, 10]
    assert [c["id"] for c in metadados if c["ativa"]] == [quarta]
    (irregulares,) = cargas(engine, "tcu_contas_irregulares")
    assert contar(engine, ListaTcuRegistro, irregulares["id"]) == 12


def test_retencao_nas_sancoes_da_cgu(engine: Engine, arquivos: Path, tmp_path: Path) -> None:
    cabecalho, linhas = ler_fixture_cgu("CEIS")
    ingerir_cgu(engine, arquivos, fixture_cgu("CEIS"))
    for dia, extras in ((1, 1), (2, 2)):
        caminho = tmp_path / f"2026100{dia}_CEIS.csv"
        gravar_csv(caminho, (cabecalho, linhas + linhas[:extras]))
        assert ingerir_cgu(engine, arquivos, caminho).status is StatusCarga.CONCLUIDA
    contagens = [contar(engine, SancaoRegistro, c["id"]) for c in cargas(engine, "cgu_ceis")]
    assert contagens == [0, 15, 16]


@pytest.mark.skipif(not DOWNLOADS_FASE0.exists(), reason="downloads reais da fase 0 ausentes")
@pytest.mark.parametrize(
    ("fonte", "nome"),
    [
        ("tcu_contas_irregulares", "tcu_responsaveis-contas-irregulares.json"),
        ("tcu_inabilitados", "tcu_responsaveis-inabilitados.json"),
    ],
)
def test_arquivo_real_nao_deixa_cpf_no_banco(engine: Engine, arquivos: Path, fonte: str, nome: str) -> None:
    arquivo = DOWNLOADS_FASE0 / nome
    if not arquivo.exists():
        pytest.skip(f"{nome} ausente")
    resultado = ingerir(engine, arquivos, fonte, arquivo, FONTES_TCU[fonte].sanidade)
    assert resultado.status is StatusCarga.CONCLUIDA
    assert not contem_cpf(despejo(engine))


def test_cli_ingerir_lista_do_tcu(
    banco_limpo: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del banco_limpo
    monkeypatch.setenv("VOSC_DIR_ARQUIVOS", str(tmp_path / "arquivos"))
    for fonte in FONTES_TCU:
        monkeypatch.setitem(listas_tcu.FONTES_TCU, fonte, replace(FONTES_TCU[fonte], sanidade=SANIDADE_TESTE))
    obter_configuracao.cache_clear()
    try:
        codigo = cli.main(["ingerir", "tcu_inabilitados", "--arquivo", str(fixture("tcu_inabilitados"))])
        saida = capsys.readouterr().out
        assert codigo == 0
        assert re.search(r"tcu_inabilitados\s+CONCLUIDA\s+linhas\s+6\s+base 01/10/2026", saida)
        codigo = cli.main(["atualizar-bases", "--diretorio", str(fixture("tcu_inabilitados").parent)])
        saida = capsys.readouterr().out
        assert codigo == 1
        assert re.search(r"cgu_ceis\s+FALHOU", saida)
        assert re.search(r"tcu_inidoneos\s+CONCLUIDA\s+linhas\s+8", saida)
        assert re.search(r"tcu_contas_irregulares\s+CONCLUIDA\s+linhas\s+12", saida)
        assert re.search(r"tcu_inabilitados\s+SEM_MUDANCA", saida)
    finally:
        obter_configuracao.cache_clear()
