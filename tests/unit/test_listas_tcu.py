import io
import json
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pytest

from tests.csv_cgu import cpf_sintetico, formatar_cpf
from tests.json_tcu import alterar, fixture, gravar_json, ler_fixture
from validador_osc.bases_locais import listas_tcu
from validador_osc.bases_locais.carga import ErroArquivo
from validador_osc.bases_locais.listas_tcu import (
    COLUNAS_COM_SANCAO,
    COLUNAS_CONTAS_IRREGULARES,
    FONTES_TCU,
    RegistroTcu,
    converter,
    data_do_nome,
    ler_arquivo,
    ler_registros,
    normalizar_acordao,
    normalizar_processo,
    obtencao_local,
    obtencao_remota,
)
from validador_osc.bases_locais.obtencao import ErroObtencao
from validador_osc.dominio.pessoa_fisica import FragmentoCpf, contem_cpf
from validador_osc.dominio.sancoes import ListaTcu

LISTAS = {
    "tcu_inidoneos": ListaTcu.INIDONEOS,
    "tcu_contas_irregulares": ListaTcu.CONTAS_IRREGULARES,
    "tcu_inabilitados": ListaTcu.INABILITADOS,
}


def registros(fonte: str, caminho: Path | None = None) -> tuple[tuple[str, ...], list[RegistroTcu]]:
    with ler_registros(caminho or fixture(fonte), LISTAS[fonte]) as (colunas, lidos):
        return colunas, list(lidos)


def por_nome(lidos: list[RegistroTcu], nome: str) -> RegistroTcu:
    return next(r for r in lidos if r.registro.nome == nome)


def test_fontes_e_urls() -> None:
    assert list(FONTES_TCU) == ["tcu_inidoneos", "tcu_contas_irregulares", "tcu_inabilitados"]
    assert FONTES_TCU["tcu_inidoneos"].url == (
        "https://certidoes.apps.tcu.gov.br/api/publico/responsaveis-inidoneos"
    )
    assert FONTES_TCU["tcu_contas_irregulares"].sanidade.minimo_linhas == 40_000
    assert FONTES_TCU["tcu_inabilitados"].sanidade.fracao_minima_anterior == 0.5


@pytest.mark.parametrize(
    ("fonte", "colunas", "total"),
    [
        ("tcu_inidoneos", COLUNAS_COM_SANCAO, 8),
        ("tcu_contas_irregulares", COLUNAS_CONTAS_IRREGULARES, 12),
        ("tcu_inabilitados", COLUNAS_COM_SANCAO, 6),
    ],
)
def test_colunas_e_quantidade_das_fixtures(fonte: str, colunas: tuple[str, ...], total: int) -> None:
    lidas, lidos = registros(fonte)
    assert lidas == colunas
    assert len(lidos) == total
    assert all(r.registro.lista is LISTAS[fonte] for r in lidos)


def test_inidoneo_normalizado() -> None:
    _, lidos = registros("tcu_inidoneos")
    alfatec = por_nome(lidos, "ALFATEC SERVICOS LTDA")
    r = alfatec.registro
    assert alfatec.tipo_registro == "CNPJ"
    assert r.documento == "28025673000115"
    assert r.raiz == "28025673"
    assert r.processo == "024.778/2024-9"
    assert r.acordao == "1610/2025-PL"
    assert r.data_acordao == date(2025, 7, 23)
    assert r.data_transito == date(2026, 6, 2)
    assert r.data_final == date(2029, 6, 2)
    assert alfatec.cpf is None
    assert alfatec.linha["numeroRegistro"] == "28.025.673/0001-15"
    assert alfatec.linha["codigoProcesso"] == 77024985
    tabela = alfatec.para_tabela()
    assert tabela["lista"] == "INIDONEOS"
    assert tabela["cpf_meio"] is None
    assert tabela["nome_normalizado"] == "ALFATEC SERVICOS LTDA"


def test_inidoneo_sem_documento_e_filial() -> None:
    _, lidos = registros("tcu_inidoneos")
    estrangeira = por_nome(lidos, "CTU SECURITY LLC")
    assert estrangeira.tipo_registro == "CNPJ"
    assert estrangeira.registro.documento is None
    assert estrangeira.registro.raiz is None
    filiais = [r.registro.documento for r in lidos if r.registro.raiz == "30139983"]
    assert filiais == ["30139983000102", "30139983000293"]


def test_contas_irregulares_sem_acordao_e_colegiados() -> None:
    _, lidos = registros("tcu_contas_irregulares")
    sem_acordao = por_nome(lidos, "A C CHAVES")
    assert sem_acordao.registro.acordao is None
    assert sem_acordao.registro.data_acordao is None
    assert sem_acordao.registro.data_final is None
    assert sem_acordao.registro.data_transito is not None
    assert por_nome(lidos, "A & S CONSTRUTORA ALBUQUERQUE & SOUZA LTDA").registro.acordao == "7586/2024-1C"
    sistal = por_nome(lidos, "' SISTAL - ALIMENTACAO DE COLETIVIDADE LTDA.'")
    assert sistal.nome_normalizado == "SISTAL ALIMENTACAO DE COLETIVIDADE LTDA"


def test_pessoa_fisica_com_cpf_mascarado_na_fonte() -> None:
    _, lidos = registros("tcu_inabilitados")
    maria = por_nome(lidos, "MARIA DE TESTE SINTETICA")
    assert maria.tipo_registro == "CPF"
    assert maria.cpf == FragmentoCpf("123456", None)
    assert maria.registro.documento is None
    assert maria.registro.raiz is None
    assert maria.linha["numeroRegistro"] == "***123456**"
    joao = por_nome(lidos, "JOÃO  CARLOS   DEMONSTRAÇÃO")
    assert joao.nome_normalizado == "JOAO CARLOS DEMONSTRACAO"
    sem_cpf = por_nome(lidos, "PEDRO ESTRANGEIRO SEM CPF")
    assert sem_cpf.cpf is None
    assert sem_cpf.linha["numeroRegistro"] is None


def test_cpf_completo_vira_fragmento_e_some_do_texto() -> None:
    titular, no_nome, no_municipio = (cpf_sintetico(n) for n in (1, 2, 3))
    item = alterar(
        ler_fixture("tcu_inabilitados")[0],
        numeroRegistro=formatar_cpf(titular),
        nome=f"FULANO DE TAL {formatar_cpf(no_nome)}",
        municipio=f"CIDADE {no_municipio}",
    )
    registro = converter(ListaTcu.INABILITADOS, item, 1)
    assert registro.cpf == FragmentoCpf(titular[3:9], titular[9:])
    assert registro.registro.documento is None
    assert registro.nome_normalizado == "FULANO DE TAL"
    tabela = registro.para_tabela()
    assert tabela["cpf_meio"] == titular[3:9]
    assert tabela["cpf_dv_final"] == titular[9:]
    texto = json.dumps(tabela, ensure_ascii=False, default=str)
    for cpf in (titular, no_nome, no_municipio):
        assert cpf not in texto
        assert formatar_cpf(cpf) not in texto
    assert not contem_cpf(texto)
    assert registro.linha["numeroRegistro"] == f"***{titular[3:9]}**"


def test_caracteres_de_controle_saem_do_nome() -> None:
    item = alterar(ler_fixture("tcu_inidoneos")[0], nome="EMPRESA\x02 LTDA\x00 ")
    registro = converter(ListaTcu.INIDONEOS, item, 1)
    assert registro.registro.nome == "EMPRESA LTDA"
    assert registro.linha["nome"] == "EMPRESA LTDA "


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("024.778/2024-9", "024.778/2024-9"),
        ("TC 024.778/2024-9", "024.778/2024-9"),
        ("TC-24778/2024-9", "024.778/2024-9"),
        (" 024.778 / 2024 - 9 ", "024.778/2024-9"),
        ("024778/2024", None),
        ("processo 1", None),
    ],
)
def test_normalizar_processo(bruto: str, esperado: str | None) -> None:
    assert normalizar_processo(bruto) == esperado


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("1610/2025-PL", "1610/2025-PL"),
        ("01610/2025-pl", "1610/2025-PL"),
        ("AC-7586/2024-1C", "7586/2024-1C"),
        ("289/2007 - 2C", "289/2007-2C"),
        ("289/2007-3C", None),
        ("289/07-PL", None),
    ],
)
def test_normalizar_acordao(bruto: str, esperado: str | None) -> None:
    assert normalizar_acordao(bruto) == esperado


@pytest.mark.parametrize(
    ("campos", "mensagem"),
    [
        ({"dataTransitoEmJulgado": "31/02/2026"}, "registro 1: dataTransitoEmJulgado com data inválida"),
        ({"dataFinalSancao": "2026-02-01"}, "registro 1: dataFinalSancao com data inválida"),
        ({"tipoRegistro": "OUTRO"}, "tipoRegistro desconhecido"),
        ({"nome": "  "}, "nome vazio"),
        ({"numeroProcessoFormatado": "abc"}, "numeroProcessoFormatado em formato inesperado"),
        ({"numeroAcordaoFormatado": "1/2026-XX"}, "numeroAcordaoFormatado em formato inesperado"),
        ({"numeroRegistro": 28025673000115}, "numeroRegistro deveria ser texto"),
    ],
)
def test_registro_invalido(campos: dict[str, Any], mensagem: str) -> None:
    item = alterar(ler_fixture("tcu_inidoneos")[0], **campos)
    with pytest.raises(ErroArquivo, match=mensagem):
        converter(ListaTcu.INIDONEOS, item, 1)


def test_cnpj_que_e_cpf_falha_sem_vazar_o_cpf() -> None:
    cpf = cpf_sintetico(7)
    item = alterar(ler_fixture("tcu_inidoneos")[0], numeroRegistro=formatar_cpf(cpf))
    with pytest.raises(ErroArquivo, match="não é CNPJ") as erro:
        converter(ListaTcu.INIDONEOS, item, 1)
    assert cpf not in str(erro.value)
    assert formatar_cpf(cpf) not in str(erro.value)


def test_cpf_ilegivel_falha() -> None:
    item = alterar(ler_fixture("tcu_inabilitados")[0], numeroRegistro="12345")
    with pytest.raises(ErroArquivo, match="não é CPF"):
        converter(ListaTcu.INABILITADOS, item, 1)


@pytest.mark.parametrize(
    ("conteudo", "mensagem"),
    [
        (b"{}", "deveria ser uma lista"),
        (b"[]", "lista vazia"),
        (b"[1]", "registro 1: deveria ser um objeto"),
        (b"[{", "JSON inválido"),
        (b"\xff\xfe[", "JSON inválido"),
    ],
)
def test_arquivo_invalido(tmp_path: Path, conteudo: bytes, mensagem: str) -> None:
    caminho = tmp_path / "lista.json"
    caminho.write_bytes(conteudo)
    with pytest.raises(ErroArquivo, match=mensagem), ler_arquivo(caminho, ListaTcu.INIDONEOS) as leitura:
        list(leitura.registros)


def test_colunas_sao_a_uniao_das_chaves(tmp_path: Path) -> None:
    itens = ler_fixture("tcu_inidoneos")
    itens[-1] = alterar(itens[-1], campoNovo="x")
    colunas, _ = registros("tcu_inidoneos", gravar_json(tmp_path / "l.json", itens))
    assert "campoNovo" in colunas
    assert colunas != COLUNAS_COM_SANCAO


def test_leitura_para_tabela() -> None:
    with ler_arquivo(fixture("tcu_inabilitados"), ListaTcu.INABILITADOS) as leitura:
        linhas = list(leitura.registros)
    assert leitura.colunas == COLUNAS_COM_SANCAO
    assert {linha["tipo_registro"] for linha in linhas} == {"CPF"}
    assert all(linha["documento"] is None for linha in linhas)


def test_data_do_nome() -> None:
    assert data_do_nome("20261002_tcu_inidoneos.json") == date(2026, 10, 2)
    assert data_do_nome("tcu_responsaveis-inabilitados.json") is None
    assert data_do_nome("20261399_tcu_inidoneos.json") is None


def test_obtencao_local(tmp_path: Path) -> None:
    destino = io.BytesIO()
    obtido = obtencao_local(fixture("tcu_inidoneos")).gravar(destino)
    assert destino.getvalue() == fixture("tcu_inidoneos").read_bytes()
    assert obtido.data_base == date(2026, 10, 2)
    assert obtido.extensao == "json"
    assert obtido.url == fixture("tcu_inidoneos").resolve().as_uri()
    csv = tmp_path / "20261002_tcu_inidoneos.csv"
    csv.write_text("x")
    with pytest.raises(ErroArquivo, match="extensão não suportada"):
        obtencao_local(csv).gravar(io.BytesIO())


class Plataforma:
    def __init__(self, corpo: bytes, falhas: int = 0, status: int = 200) -> None:
        self.corpo = corpo
        self.falhas = falhas
        self.status = status
        self.requisicoes: list[httpx.Request] = []

    def responder(self, requisicao: httpx.Request) -> httpx.Response:
        self.requisicoes.append(requisicao)
        if self.falhas:
            self.falhas -= 1
            return httpx.Response(503)
        return httpx.Response(self.status, content=self.corpo)


def cliente(plataforma: Plataforma) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(plataforma.responder), headers={"User-Agent": "teste"})


@pytest.fixture
def sem_pausa(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(listas_tcu, "PAUSA_TENTATIVA_S", 0.0)


@pytest.mark.usefixtures("sem_pausa")
def test_obtencao_remota_faz_post_com_corpo_vazio_e_repete_503() -> None:
    corpo = fixture("tcu_inabilitados").read_bytes()
    plataforma = Plataforma(corpo, falhas=1)
    fonte = FONTES_TCU["tcu_inabilitados"]
    destino = io.BytesIO()
    with cliente(plataforma) as http:
        obtencao = obtencao_remota(http, fonte, lambda: date(2026, 10, 2))
        obtido = obtencao.gravar(destino)
    assert obtencao.url_inicial == fonte.url
    assert destino.getvalue() == corpo
    assert obtido.url == fonte.url
    assert obtido.data_base == date(2026, 10, 2)
    assert obtido.extensao == "json"
    assert len(plataforma.requisicoes) == 2
    assert all(r.method == "POST" and r.content == b"{}" for r in plataforma.requisicoes)
    assert all(r.headers["user-agent"] == "teste" for r in plataforma.requisicoes)


@pytest.mark.usefixtures("sem_pausa")
def test_obtencao_remota_falha_com_erro_http() -> None:
    fonte = FONTES_TCU["tcu_inidoneos"]
    with cliente(Plataforma(b"", status=404)) as http, pytest.raises(ErroObtencao, match="HTTP 404"):
        obtencao_remota(http, fonte, date.today).gravar(io.BytesIO())
    with cliente(Plataforma(b"", falhas=5)) as http, pytest.raises(ErroObtencao, match="HTTP 503"):
        obtencao_remota(http, fonte, date.today).gravar(io.BytesIO())
