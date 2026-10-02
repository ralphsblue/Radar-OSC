import io
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from tests.csv_cgu import (
    alterar,
    compactar,
    cpf_sintetico,
    fixture,
    formatar_cpf,
    gravar_csv,
    ler_fixture,
)
from validador_osc.bases_locais import sancoes_cgu
from validador_osc.bases_locais.carga import ErroArquivo
from validador_osc.bases_locais.obtencao import ErroObtencao
from validador_osc.bases_locais.sancoes_cgu import (
    COLUNAS_CEIS,
    COLUNAS_CEPIM,
    COLUNAS_CNEP,
    FONTES_CGU,
    RegistroSancao,
    data_do_nome,
    descobrir_data,
    ler_arquivo,
    ler_sancoes,
    obtencao_local,
    obtencao_remota,
)
from validador_osc.dominio.sancoes import CadastroSancao, TipoPessoa
from validador_osc.pessoa_fisica import FragmentoCpf, contem_cpf

PAGINA = (
    '<script>arquivos.push({"ano" : "2026", "mes" : "09", "dia" : "29", "origem" : "CEIS"});'
    'arquivos.push({"ano" : "2026", "mes" : "09", "dia" : "30", "origem" : "CEIS"});</script>'
)
URL_CDN = "https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/ceis/20260930_CEIS.zip"


def registros(caminho: Path, cadastro: CadastroSancao) -> list[RegistroSancao]:
    with ler_sancoes(caminho, cadastro) as (_, lidos):
        return list(lidos)


def por_codigo(lidos: list[RegistroSancao], codigo: str) -> list[RegistroSancao]:
    return [r for r in lidos if r.sancao.codigo_sancao == codigo]


def test_colunas_das_fixtures_sao_as_esperadas() -> None:
    for cadastro, colunas in (("CEPIM", COLUNAS_CEPIM), ("CEIS", COLUNAS_CEIS), ("CNEP", COLUNAS_CNEP)):
        with ler_arquivo(fixture(cadastro), CadastroSancao(cadastro)) as leitura:
            assert leitura.colunas == colunas
            assert all("linha" in registro for registro in leitura.registros)


def test_ceis_pessoa_juridica() -> None:
    lidos = registros(fixture("CEIS"), CadastroSancao.CEIS)
    assert len(lidos) == 14
    (prisma,) = por_codigo(lidos, "105078")
    s = prisma.sancao
    assert s.cadastro is CadastroSancao.CEIS
    assert s.tipo_pessoa is TipoPessoa.JURIDICA
    assert s.documento == "06278833000103"
    assert s.raiz == "06278833"
    assert s.nome == "PRISMASERV SOLUCOES EMPRESARIAIS EIRELI"
    assert s.data_inicio == date(2019, 7, 18)
    assert s.data_fim == date(2039, 7, 10)
    assert s.valor_multa is None
    assert prisma.cpf is None
    assert prisma.nome_normalizado == "PRISMASERV SOLUCOES EMPRESARIAIS EIRELI"
    (filial,) = por_codigo(lidos, "900001")
    assert filial.sancao.raiz == "06278833"
    assert filial.sancao.documento != s.documento


def test_ceis_pessoa_fisica_mascarada_na_origem() -> None:
    lidos = registros(fixture("CEIS"), CadastroSancao.CEIS)
    (mario,) = por_codigo(lidos, "316136")
    assert mario.sancao.tipo_pessoa is TipoPessoa.FISICA
    assert mario.sancao.documento is None
    assert mario.sancao.raiz is None
    assert mario.cpf == FragmentoCpf("921012", None)
    assert mario.linha["CPF OU CNPJ DO SANCIONADO"] == "***921012**"
    assert mario.nome_normalizado == "MARIO SERGIO LACERDA"
    (jose,) = por_codigo(lidos, "900004")
    assert jose.sancao.nome == "José  da   Conceição D'Ávila"
    assert jose.nome_normalizado == "JOSE DA CONCEICAO D AVILA"


def test_ceis_quirks_preservados() -> None:
    lidos = registros(fixture("CEIS"), CadastroSancao.CEIS)
    assert len(por_codigo(lidos, "79114")) == 2
    (sem_fim,) = por_codigo(lidos, "70548")
    assert sem_fim.sancao.categoria is not None
    assert "com prazo" in sem_fim.sancao.categoria
    assert sem_fim.sancao.data_fim is None
    (sem_prazo, _) = por_codigo(lidos, "79114")
    assert sem_prazo.sancao.categoria is not None
    assert "sem prazo" in sem_prazo.sancao.categoria
    assert sem_prazo.sancao.data_fim == date(2017, 10, 19)
    (mario,) = por_codigo(lidos, "316136")
    assert mario.sancao.abrangencia is None
    assert mario.linha["ABRAGÊNCIA DA SANÇÃO"] == "Sem Informação"


def test_ceis_sem_tipo_de_pessoa() -> None:
    lidos = registros(fixture("CEIS"), CadastroSancao.CEIS)
    (estrangeira,) = por_codigo(lidos, "900002")
    assert estrangeira.sancao.tipo_pessoa is None
    assert estrangeira.sancao.documento == "000123456"
    assert estrangeira.sancao.raiz is None
    assert estrangeira.cpf is None
    (sem_tipo,) = por_codigo(lidos, "900003")
    assert sem_tipo.sancao.tipo_pessoa is None
    assert sem_tipo.sancao.documento == "11222333000181"
    assert sem_tipo.sancao.raiz == "11222333"


def test_cnep_multa_e_sem_data_final() -> None:
    lidos = registros(fixture("CNEP"), CadastroSancao.CNEP)
    assert len(lidos) == 11
    (multa,) = por_codigo(lidos, "289393")
    assert multa.sancao.valor_multa == Decimal("517662.90")
    assert multa.sancao.data_fim is None
    assert multa.sancao.tipo_pessoa is TipoPessoa.FISICA
    assert multa.cpf == FragmentoCpf("146799", None)
    (publicacao,) = por_codigo(lidos, "289394")
    assert publicacao.sancao.valor_multa == Decimal("0.00")
    assert len(por_codigo(lidos, "84816")) == 2
    (curto,) = por_codigo(lidos, "900005")
    assert curto.sancao.documento == "1234567"
    assert curto.sancao.raiz is None


def test_cepim_sem_datas_com_convenio() -> None:
    lidos = registros(fixture("CEPIM"), CadastroSancao.CEPIM)
    assert len(lidos) == 10
    primeiro = lidos[0].sancao
    assert primeiro.cadastro is CadastroSancao.CEPIM
    assert primeiro.tipo_pessoa is TipoPessoa.JURIDICA
    assert primeiro.documento == "14112015000156"
    assert primeiro.raiz == "14112015"
    assert primeiro.convenio == "039516"
    assert primeiro.motivo == "DESCUMPRIMENTO DE CLAUSULA/CONDICAO DO INSTR."
    assert primeiro.orgao is not None
    assert primeiro.data_inicio is None
    assert primeiro.data_fim is None
    assert primeiro.codigo_sancao is None
    assert sum(1 for r in lidos if r.sancao.documento == "02307795000100") == 4


def test_zip_oficial_e_csv_dao_o_mesmo_resultado(tmp_path: Path) -> None:
    arquivo_zip = compactar(fixture("CNEP"), tmp_path / "20260930_CNEP.zip")
    assert registros(arquivo_zip, CadastroSancao.CNEP) == registros(fixture("CNEP"), CadastroSancao.CNEP)


def test_cpf_completo_nunca_sai_do_parser(tmp_path: Path) -> None:
    cabecalho, linhas = ler_fixture("CEIS")
    titular, sem_tipo, socio, procurador = (cpf_sintetico(n) for n in range(10, 14))
    modelo = linhas[0]
    novas = [
        alterar(
            cabecalho,
            modelo,
            {
                "CÓDIGO DA SANÇÃO": "1",
                "CPF OU CNPJ DO SANCIONADO": titular,
                "NOME INFORMADO PELO ÓRGÃO SANCIONADOR": f"MARIO {formatar_cpf(titular)}",
                "OBSERVAÇÕES": f"sócio {formatar_cpf(socio)}, procurador {procurador}",
            },
        ),
        alterar(
            cabecalho,
            modelo,
            {"CÓDIGO DA SANÇÃO": "2", "TIPO DE PESSOA": "", "CPF OU CNPJ DO SANCIONADO": sem_tipo},
        ),
    ]
    caminho = gravar_csv(tmp_path / "20260930_CEIS.csv", (cabecalho, novas))
    with ler_arquivo(caminho, CadastroSancao.CEIS) as leitura:
        tabela = list(leitura.registros)
    texto = repr(tabela)
    for cpf in (titular, sem_tipo, socio, procurador):
        assert cpf not in texto
        assert formatar_cpf(cpf) not in texto
    assert not contem_cpf(texto)
    primeiro, segundo = tabela
    assert primeiro["documento"] is None
    assert primeiro["cpf_meio"] == titular[3:9]
    assert primeiro["cpf_dv_final"] == titular[9:]
    assert primeiro["linha"]["CPF OU CNPJ DO SANCIONADO"] == f"***{titular[3:9]}**"
    assert segundo["tipo_pessoa"] is None
    assert segundo["documento"] is None
    assert segundo["cpf_meio"] == sem_tipo[3:9]


@pytest.mark.parametrize(
    ("campos", "mensagem"),
    [
        ({"DATA FINAL SANÇÃO": "31/02/2030"}, "data inválida"),
        ({"DATA INÍCIO SANÇÃO": "2030-01-01"}, "data inválida"),
        ({"CADASTRO": "CNEP"}, "CADASTRO"),
        ({"TIPO DE PESSOA": "X"}, "TIPO DE PESSOA"),
    ],
)
def test_linha_invalida_vira_erro_de_arquivo(tmp_path: Path, campos: dict[str, str], mensagem: str) -> None:
    cabecalho, linhas = ler_fixture("CEIS")
    linhas[3] = alterar(cabecalho, linhas[3], campos)
    caminho = gravar_csv(tmp_path / "x_CEIS.csv", (cabecalho, linhas))
    with pytest.raises(ErroArquivo, match=f"linha 5: .*{mensagem}"):
        registros(caminho, CadastroSancao.CEIS)


def test_sem_informacao_em_data_vira_none(tmp_path: Path) -> None:
    cabecalho, linhas = ler_fixture("CEIS")
    linhas[0] = alterar(cabecalho, linhas[0], {"DATA FINAL SANÇÃO": "Sem informação"})
    caminho = gravar_csv(tmp_path / "x_CEIS.csv", (cabecalho, linhas[:1]))
    (lido,) = registros(caminho, CadastroSancao.CEIS)
    assert lido.sancao.data_fim is None


def test_multa_invalida(tmp_path: Path) -> None:
    cabecalho, linhas = ler_fixture("CNEP")
    linhas[0] = alterar(cabecalho, linhas[0], {"VALOR DA MULTA": "R$ 10"})
    caminho = gravar_csv(tmp_path / "x_CNEP.csv", (cabecalho, linhas))
    with pytest.raises(ErroArquivo, match="VALOR DA MULTA"):
        registros(caminho, CadastroSancao.CNEP)


def test_linha_com_campos_a_menos(tmp_path: Path) -> None:
    cabecalho, linhas = ler_fixture("CEPIM")
    linhas[1] = linhas[1][:3]
    caminho = gravar_csv(tmp_path / "x_CEPIM.csv", (cabecalho, linhas))
    with pytest.raises(ErroArquivo, match="linha 3: 3 campos, esperados 5"):
        registros(caminho, CadastroSancao.CEPIM)


def test_zip_invalido_ou_com_mais_de_um_csv(tmp_path: Path) -> None:
    quebrado = tmp_path / "quebrado.zip"
    quebrado.write_bytes(b"nao e zip")
    with pytest.raises(ErroArquivo, match="zip inválido"):
        registros(quebrado, CadastroSancao.CEPIM)
    duplo = tmp_path / "duplo.zip"
    with zipfile.ZipFile(duplo, "w") as arquivo:
        arquivo.write(fixture("CEPIM"), "a.csv")
        arquivo.write(fixture("CEPIM"), "b.csv")
    with pytest.raises(ErroArquivo, match="exatamente um CSV"):
        registros(duplo, CadastroSancao.CEPIM)


def test_arquivo_vazio(tmp_path: Path) -> None:
    vazio = tmp_path / "vazio.csv"
    vazio.write_bytes(b"")
    with pytest.raises(ErroArquivo, match="vazio"):
        registros(vazio, CadastroSancao.CEPIM)


def test_data_do_nome() -> None:
    assert data_do_nome("20260930_CEIS.zip") == date(2026, 9, 30)
    assert data_do_nome("downloads/x/20260928_CEPIM.csv") == date(2026, 9, 28)
    assert data_do_nome("ceis.zip") is None
    assert data_do_nome("20261341_CEIS.zip") is None


def test_obtencao_local_copia_e_le_data_de_dentro_do_zip(tmp_path: Path) -> None:
    arquivo_zip = compactar(fixture("CEIS"), tmp_path / "baixado.zip")
    destino = io.BytesIO()
    obtido = obtencao_local(arquivo_zip).gravar(destino)
    assert destino.getvalue() == arquivo_zip.read_bytes()
    assert obtido.data_base == date(2026, 9, 30)
    assert obtido.extensao == "zip"
    assert obtido.url == arquivo_zip.resolve().as_uri()


def test_obtencao_local_recusa_extensao_desconhecida(tmp_path: Path) -> None:
    arquivo = tmp_path / "20260930_CEIS.txt"
    arquivo.write_text("x")
    with pytest.raises(ErroArquivo, match="extensão"):
        obtencao_local(arquivo).gravar(io.BytesIO())


class Portal:
    def __init__(self, corpo_zip: bytes, falhas_download: int = 0, status_pagina: int = 200) -> None:
        self.corpo_zip = corpo_zip
        self.falhas_download = falhas_download
        self.status_pagina = status_pagina
        self.requisicoes: list[httpx.Request] = []

    def responder(self, requisicao: httpx.Request) -> httpx.Response:
        self.requisicoes.append(requisicao)
        url = str(requisicao.url)
        if url == f"{sancoes_cgu.URL_DOWNLOAD}/ceis":
            return httpx.Response(self.status_pagina, text=PAGINA)
        if url == f"{sancoes_cgu.URL_DOWNLOAD}/ceis/20260930":
            return httpx.Response(302, headers={"location": URL_CDN})
        if url == URL_CDN:
            if self.falhas_download:
                self.falhas_download -= 1
                return httpx.Response(503)
            return httpx.Response(200, content=self.corpo_zip)
        return httpx.Response(404)


def cliente(portal: Portal) -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(portal.responder),
        follow_redirects=True,
        headers={"User-Agent": "teste"},
    )


@pytest.fixture
def sem_pausa(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sancoes_cgu, "PAUSA_TENTATIVA_S", 0.0)


def test_descobre_a_data_mais_recente_na_pagina() -> None:
    with cliente(Portal(b"")) as http:
        assert descobrir_data(http, FONTES_CGU["cgu_ceis"]) == date(2026, 9, 30)


@pytest.mark.usefixtures("sem_pausa")
def test_obtencao_remota_segue_o_redirecionamento_e_repete_503(tmp_path: Path) -> None:
    corpo = compactar(fixture("CEIS"), tmp_path / "20260930_CEIS.zip").read_bytes()
    portal = Portal(corpo, falhas_download=1)
    destino = io.BytesIO()
    with cliente(portal) as http:
        obtencao = obtencao_remota(http, FONTES_CGU["cgu_ceis"])
        obtido = obtencao.gravar(destino)
    assert obtencao.url_inicial == f"{sancoes_cgu.URL_DOWNLOAD}/ceis"
    assert destino.getvalue() == corpo
    assert obtido.url == URL_CDN
    assert obtido.data_base == date(2026, 9, 30)
    assert obtido.extensao == "zip"
    assert all(r.headers["user-agent"] == "teste" for r in portal.requisicoes)
    assert [str(r.url) for r in portal.requisicoes].count(URL_CDN) == 2


@pytest.mark.usefixtures("sem_pausa")
def test_obtencao_remota_falha_sem_data_ou_com_erro_http() -> None:
    with cliente(Portal(b"", status_pagina=404)) as http, pytest.raises(ErroObtencao, match="HTTP 404"):
        obtencao_remota(http, FONTES_CGU["cgu_ceis"]).gravar(io.BytesIO())
    with cliente(Portal(b"", falhas_download=5)) as http, pytest.raises(ErroObtencao, match="HTTP 503"):
        obtencao_remota(http, FONTES_CGU["cgu_ceis"]).gravar(io.BytesIO())


def test_pagina_sem_data() -> None:
    def responder(requisicao: httpx.Request) -> httpx.Response:
        del requisicao
        return httpx.Response(200, text="<html></html>")

    with httpx.Client(transport=httpx.MockTransport(responder)) as http, pytest.raises(ErroObtencao):
        descobrir_data(http, FONTES_CGU["cgu_cnep"])
