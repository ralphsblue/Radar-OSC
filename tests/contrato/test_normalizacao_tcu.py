import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from validador_osc.dominio.sancoes import (
    CertidaoTcu,
    RespostaTcu,
    SituacaoCertidaoTcu,
    TipoCertidaoTcu,
)
from validador_osc.fontes.normalizacao.tcu import ErroFormato, normalizar_certidoes

FIXTURES = Path(__file__).parent.parent / "fixtures" / "fontes" / "tcu"
RESPOSTAS = sorted(caminho.name for caminho in FIXTURES.glob("*.json") if not caminho.name.startswith("412_"))
OKBR = "19131243000197.json"
LINK_INIDONEOS = "https://certidoes.apps.tcu.gov.br/lista-inidoneos"
LINK_CNIA = "http://www.cnj.jus.br/improbidade_adm/consultar_requerido.php"
LINK_CEIS = "http://www.portaltransparencia.gov.br/sancoes/ceis"
LINK_CNEP = "http://www.portaltransparencia.gov.br/sancoes/cnep"
SHA256 = {
    "19131243000197.json": "757622ba7b54f1950c20cde4c3af3a99338f0f9349b4fc3b7ec6f964e08b07fa",
    "28025673000115.json": "130f20384b61eb7cd50b2ec14a5e129d7932bbd82e0295cf6ffd46661e9d0987",
    "21145289000107.json": "31329cfefe010208ae1b85f52890d1bc0e6730a1cf458ab11138ff3f949ddbdd",
    "53524534000183.json": "5d8c02f7eea28409ec27601440b67ddaad37c91d09c774d70de134887ae7321e",
    "03126200000183.json": "6a58172447bb072ddeab9c12316d08d416b9f226b40cd8fa4f77e3863d9e971c",
    "05051898000140.json": "6804e54144783336446db0d9c42be1118810eb6c72f005b20e810c57150aaee8",
    "43337682000135.json": "d88d61d34eb4ca4bb070d26e0d5f0074961936933750d4beccd43044ebffc1d2",
    "25705450000100.json": "121966fb4e9fb269bce5fe551117c36397ed6cdfadfd19122ad8ad1ea0f87b77",
    "98765432000198.json": "41facde86d53d0e0dd3dbee1d8ac6d5cafc910cf59f05eef2523bbb133a7b0c4",
    "12ABC34501DE35.json": "7a517abbdac8a8188355765b7134c3c50d80803eb61fe6b87b5f1ddb82403b56",
    "24006302000488.json": "191bc7331f532ef092a6a5330296a23636e00544577f4467b15e65654061229a",
    "24006302000135.json": "15ff34ca0bdfdd74905ab8b10ef85cbd9b2b21c43849cc956148bf667ea4139e",
    "02203539000173.json": "973afb2e2f1c5089b3b476518b967190945edaebe64c5ebb05e6d1c51a532e5a",
    "00688001000170.json": "3b03d11faeb665aecb8f71cc1801b302cc3c2fe54e001cdf0153cb180f00a7b8",
    "30994499000160.json": "7c3468245970d24b650559cda3f35a855fbfd71e74e85ddd3a0749e09c15c4dc",
    "02393242000118.json": "09300d894759aba84d3296af86cf0cf43deda32890ae4ec8040d8231976e41b9",
    "07408449000132.json": "1cbc405c99aa459841354622f7cac22739bf2391b2345cc279654f17929aebef",
    "09058351000128.json": "be647a47de3e5c722305c4483a991a6d7d54b4642f14b263d7265017e6d1636b",
    "13144375000177.json": "1bcc7e33fe97f8774e6eed9c3e3e36bcf38c428f446311d6a207396d0de61ac8",
    "01081476000167.json": "69b33cf6b6f5ba9ac3c26affef979006f8cd8767fe4cf40655ee9eb6055ee12b",
    "44551605000570.json": "cb193c6df7394798e58af58f0171874c831d4e2003d55db22eea6a26e689a8ff",
    "44551605000146.json": "73de097c2e079d61a9097bfb0a0801d2203a9fcfa9c8be201b3032f9e8562234",
    "06287661000126.json": "afae308e9b6d5056431d6b2783b91eaf0ade756548f006d22811102599326825",
    "03463763000167.json": "fbf06f8f1e449bf02358c32e425b6ba9425d3d5681fb679d90321957c2efe7e2",
    "14112015000156.json": "098d11191978478760138793125290e3eddb880f06ede67e612956c927123b61",
    "08928169000118.json": "a6b56a460ab5fe49dca65b33fbadd7f1822cb4f8a90dd7292241f238d9440d04",
    "412_19131243000198.json": "cec1950ae167504773c8f9db4f88093d87173b587d7bddee811a1e5eae983f85",
}


def ler(nome: str) -> bytes:
    return (FIXTURES / nome).read_bytes()


def normalizar(nome: str) -> RespostaTcu:
    return normalizar_certidoes(ler(nome))


def certidao(resposta: RespostaTcu, tipo: TipoCertidaoTcu) -> CertidaoTcu:
    encontrada = resposta.certidao(tipo)
    assert encontrada is not None
    return encontrada


def okbr_com(**alteracoes: Any) -> bytes:
    bruto: dict[str, Any] = json.loads(ler(OKBR))
    bruto.update(alteracoes)
    return json.dumps(bruto, ensure_ascii=False).encode()


def item_okbr_com(indice: int, **alteracoes: Any) -> bytes:
    certidoes: list[dict[str, Any]] = json.loads(ler(OKBR))["certidoes"]
    certidoes[indice].update(alteracoes)
    return okbr_com(certidoes=certidoes)


def cnia_com(observacao: str) -> CertidaoTcu:
    resposta = normalizar_certidoes(item_okbr_com(1, situacao="CONSTAM_REGISTROS", observacao=observacao))
    return certidao(resposta, TipoCertidaoTcu.CNIA)


def ceis_com(observacao: str) -> CertidaoTcu:
    resposta = normalizar_certidoes(item_okbr_com(2, situacao="CONSTAM_REGISTROS", observacao=observacao))
    return certidao(resposta, TipoCertidaoTcu.CEIS)


def nada_consta(tipo: TipoCertidaoTcu, link: str) -> CertidaoTcu:
    return CertidaoTcu(tipo, SituacaoCertidaoTcu.NADA_CONSTA, None, (), (), link)


@pytest.mark.parametrize(("nome", "sha256"), sorted(SHA256.items()))
def test_fixtures_sao_os_bytes_da_coleta(nome: str, sha256: str) -> None:
    assert hashlib.sha256(ler(nome)).hexdigest() == sha256


def test_todas_as_fixtures_estao_conferidas() -> None:
    assert sorted(SHA256) == sorted(caminho.name for caminho in FIXTURES.glob("*.json"))


def test_okbr_nada_consta_completo() -> None:
    assert normalizar(OKBR) == RespostaTcu(
        cnpj="19131243000197",
        razao_social="OPEN KNOWLEDGE FOUNDATION BRASIL",
        cnpj_encontrado=True,
        certidoes=(
            nada_consta(TipoCertidaoTcu.INIDONEOS, LINK_INIDONEOS),
            nada_consta(TipoCertidaoTcu.CNIA, LINK_CNIA),
            nada_consta(TipoCertidaoTcu.CEIS, LINK_CEIS),
            nada_consta(TipoCertidaoTcu.CNEP, LINK_CNEP),
        ),
    )


def test_alfatec_inidonea_com_ceis() -> None:
    resposta = normalizar("28025673000115.json")
    assert resposta.cnpj == "28025673000115"
    assert resposta.razao_social == "ALFATEC SERVICOS LTDA"
    assert resposta.cnpj_encontrado
    assert certidao(resposta, TipoCertidaoTcu.INIDONEOS) == CertidaoTcu(
        tipo=TipoCertidaoTcu.INIDONEOS,
        situacao=SituacaoCertidaoTcu.CONSTAM_REGISTROS,
        observacao="Data da Decisão: 23/07/2025 - 024.778/2024-9 - 1610/2025-PL",
        datas_observacao=(),
        processos=(),
        link_manual=LINK_INIDONEOS,
    )
    assert certidao(resposta, TipoCertidaoTcu.CEIS) == CertidaoTcu(
        tipo=TipoCertidaoTcu.CEIS,
        situacao=SituacaoCertidaoTcu.CONSTAM_REGISTROS,
        observacao=(
            "Declaração de Inidoneidade com prazo determinado (02/06/2029) - TRIBUNAL DE CONTAS DA UNIÃO"
        ),
        datas_observacao=(date(2029, 6, 2),),
        processos=(),
        link_manual=LINK_CEIS,
    )
    assert certidao(resposta, TipoCertidaoTcu.CNIA) == nada_consta(TipoCertidaoTcu.CNIA, LINK_CNIA)
    assert certidao(resposta, TipoCertidaoTcu.CNEP) == nada_consta(TipoCertidaoTcu.CNEP, LINK_CNEP)


def test_imdc_inidoneo_com_ceis_de_varios_registros() -> None:
    resposta = normalizar("21145289000107.json")
    assert resposta.razao_social == "INSTITUTO MUNDIAL DE DESENVOLVIMENTO E DA CIDADANIA - IMDC."
    inidoneos = certidao(resposta, TipoCertidaoTcu.INIDONEOS)
    assert inidoneos.situacao is SituacaoCertidaoTcu.CONSTAM_REGISTROS
    assert inidoneos.observacao == "Data da Decisão: 14/08/2019 - 010.925/2015-5 - 1897/2019-PL"
    assert inidoneos.datas_observacao == ()
    ceis = certidao(resposta, TipoCertidaoTcu.CEIS)
    assert ceis.situacao is SituacaoCertidaoTcu.CONSTAM_REGISTROS
    assert ceis.observacao is not None
    assert ceis.observacao.count("<br/>") == 2
    assert ceis.datas_observacao == (date(2029, 4, 16),)
    assert ceis.processos == ()


def test_pacaembu_ceis_e_cnep_sem_datas() -> None:
    resposta = normalizar("53524534000183.json")
    ceis = certidao(resposta, TipoCertidaoTcu.CEIS)
    cnep = certidao(resposta, TipoCertidaoTcu.CNEP)
    assert ceis.situacao is SituacaoCertidaoTcu.CONSTAM_REGISTROS
    assert cnep.situacao is SituacaoCertidaoTcu.CONSTAM_REGISTROS
    assert ceis.observacao == (
        "Declaração de Inidoneidade sem prazo determinado (Sem informação) - Controladoria-Geral da União"
    )
    assert ceis.datas_observacao == ()
    assert cnep.datas_observacao == ()
    assert cnep.observacao is not None
    assert cnep.observacao.startswith("Publicação extraordinária da decisão condenatória (Sem informação)")
    assert certidao(resposta, TipoCertidaoTcu.INIDONEOS).situacao is SituacaoCertidaoTcu.NADA_CONSTA
    assert certidao(resposta, TipoCertidaoTcu.CNIA).situacao is SituacaoCertidaoTcu.NADA_CONSTA


def test_plural_ceis_expirado_com_data_e_espaco_final_removido() -> None:
    ceis = certidao(normalizar("03126200000183.json"), TipoCertidaoTcu.CEIS)
    assert ceis == CertidaoTcu(
        tipo=TipoCertidaoTcu.CEIS,
        situacao=SituacaoCertidaoTcu.CONSTAM_REGISTROS,
        observacao=(
            "Declaração de Inidoneidade sem prazo determinado (18/11/2021)"
            " - Fundação Hospitalar Getúlio Vargas - RS"
        ),
        datas_observacao=(date(2021, 11, 18),),
        processos=(),
        link_manual=LINK_CEIS,
    )


@pytest.mark.parametrize(
    ("nome", "processos", "datas_ceis"),
    [
        ("05051898000140.json", ("09000212620168240040",), (date(2037, 4, 16),)),
        (
            "43337682000135.json",
            ("10021337720158260032", "00031114620128260624"),
            (date(2028, 3, 25), date(2028, 3, 27), date(2027, 5, 11), date(2027, 11, 17)),
        ),
        ("25705450000100.json", ("0625090977178",), (date(2026, 10, 13),)),
    ],
)
def test_cnia_com_ocorrencia_traz_os_processos(
    nome: str, processos: tuple[str, ...], datas_ceis: tuple[date, ...]
) -> None:
    resposta = normalizar(nome)
    cnia = certidao(resposta, TipoCertidaoTcu.CNIA)
    assert cnia.situacao is SituacaoCertidaoTcu.CONSTAM_REGISTROS
    assert cnia.processos == processos
    assert cnia.datas_observacao == ()
    assert cnia.link_manual == LINK_CNIA
    ceis = certidao(resposta, TipoCertidaoTcu.CEIS)
    assert ceis.datas_observacao == datas_ceis
    assert ceis.processos == ()


def test_cnpj_fora_da_base_do_tcu() -> None:
    resposta = normalizar("98765432000198.json")
    assert resposta.cnpj == "98765432000198"
    assert resposta.razao_social is None
    assert not resposta.cnpj_encontrado
    assert {c.situacao for c in resposta.certidoes} == {SituacaoCertidaoTcu.NADA_CONSTA}


def test_alfanumerico_cnia_nao_suportado() -> None:
    resposta = normalizar("12ABC34501DE35.json")
    assert resposta.cnpj == "12ABC34501DE35"
    assert not resposta.cnpj_encontrado
    assert certidao(resposta, TipoCertidaoTcu.CNIA).situacao is SituacaoCertidaoTcu.NAO_SUPORTADO
    for tipo in (TipoCertidaoTcu.INIDONEOS, TipoCertidaoTcu.CEIS, TipoCertidaoTcu.CNEP):
        assert certidao(resposta, tipo).situacao is SituacaoCertidaoTcu.NADA_CONSTA


@pytest.mark.parametrize("nome", RESPOSTAS)
def test_toda_resposta_real_traz_as_quatro_certidoes(nome: str) -> None:
    resposta = normalizar(nome)
    assert resposta.cnpj == nome.removesuffix(".json")
    assert [c.tipo for c in resposta.certidoes] == list(TipoCertidaoTcu)
    for item in resposta.certidoes:
        assert item.link_manual is not None
        assert (item.observacao is None) is (item.situacao is not SituacaoCertidaoTcu.CONSTAM_REGISTROS)


@pytest.mark.parametrize(
    ("situacao", "esperada"),
    [
        ("NADA_CONSTA", SituacaoCertidaoTcu.NADA_CONSTA),
        ("CONSTAM_REGISTROS", SituacaoCertidaoTcu.CONSTAM_REGISTROS),
        ("ERRO", SituacaoCertidaoTcu.INDISPONIVEL),
        ("SISTEMA_INDISPONIVEL", SituacaoCertidaoTcu.INDISPONIVEL),
        ("ALFANUMERICO_NAO_SUPORTADO", SituacaoCertidaoTcu.NAO_SUPORTADO),
        ("CNPJ_NAO_ENCONTRADO_NO_TCU", SituacaoCertidaoTcu.NADA_CONSTA),
    ],
)
def test_mapa_de_situacoes(situacao: str, esperada: SituacaoCertidaoTcu) -> None:
    resposta = normalizar_certidoes(item_okbr_com(0, situacao=situacao))
    assert certidao(resposta, TipoCertidaoTcu.INIDONEOS).situacao is esperada


def test_situacao_cnpj_nao_encontrado_desliga_cnpj_encontrado() -> None:
    resposta = normalizar_certidoes(item_okbr_com(0, situacao="CNPJ_NAO_ENCONTRADO_NO_TCU"))
    assert not resposta.cnpj_encontrado
    assert resposta.razao_social == "OPEN KNOWLEDGE FOUNDATION BRASIL"


def test_indisponivel_mantem_o_link_manual() -> None:
    resposta = normalizar_certidoes(item_okbr_com(3, situacao="SISTEMA_INDISPONIVEL"))
    assert certidao(resposta, TipoCertidaoTcu.CNEP) == CertidaoTcu(
        TipoCertidaoTcu.CNEP, SituacaoCertidaoTcu.INDISPONIVEL, None, (), (), LINK_CNEP
    )


@pytest.mark.parametrize(
    ("observacao", "datas"),
    [
        ("Suspensão (22/11/2026) - Governo do Estado da Bahia (BA)", (date(2026, 11, 22),)),
        ("Multa (Sem informação) - CGU<br/>Suspensão ( 01/02/2027 ) - CGU", (date(2027, 2, 1),)),
        ("Impedimento (06/08/2031) - X<br/>Impedimento (06/08/2031) - X", (date(2031, 8, 6),) * 2),
        ("Data da Decisão: 23/07/2025 - 024.778/2024-9", ()),
        ("Período 01/01/2020 a (31/12/2020)", (date(2020, 12, 31),)),
    ],
)
def test_datas_entre_parenteses(observacao: str, datas: tuple[date, ...]) -> None:
    assert ceis_com(observacao).datas_observacao == datas


@pytest.mark.parametrize("data", ["31/02/2027", "00/01/2027", "15/13/2027"])
def test_data_impossivel_na_observacao_e_erro(data: str) -> None:
    with pytest.raises(ErroFormato, match="data inválida"):
        ceis_com(f"Suspensão ({data}) - CGU")


@pytest.mark.parametrize(
    ("observacao", "processos"),
    [
        (
            "Existe(m) o(s) processo(s) a seguir para a empresa consultada: 0001105-96.2013.4.05.8304",
            ("00011059620134058304",),
        ),
        (
            "processos: 10021337720158260032,00031114620128260624, 10021337720158260032",
            ("10021337720158260032", "00031114620128260624"),
        ),
        ("Existe(m) o(s) processo(s) a seguir para a empresa consultada:", ()),
        ("Condenação de 2019 no processo 123", ()),
    ],
)
def test_processos_do_cnia(observacao: str, processos: tuple[str, ...]) -> None:
    assert cnia_com(observacao).processos == processos


def test_processos_so_sao_extraidos_do_cnia() -> None:
    assert ceis_com("Processo 10021337720158260032 (01/01/2030)").processos == ()


def test_tipo_e_emissor_comparados_sem_caixa_e_espacos() -> None:
    resposta = normalizar_certidoes(item_okbr_com(0, emissor=" tcu ", tipo="INIDÔNEOS"))
    assert certidao(resposta, TipoCertidaoTcu.INIDONEOS).situacao is SituacaoCertidaoTcu.NADA_CONSTA


def test_observacao_e_link_vazios_viram_none() -> None:
    resposta = normalizar_certidoes(item_okbr_com(2, observacao="  ", linkConsultaManual=""))
    assert certidao(resposta, TipoCertidaoTcu.CEIS) == CertidaoTcu(
        TipoCertidaoTcu.CEIS, SituacaoCertidaoTcu.NADA_CONSTA, None, (), (), None
    )


def test_certidao_ausente_fica_sem_item() -> None:
    certidoes: list[dict[str, Any]] = json.loads(ler(OKBR))["certidoes"]
    resposta = normalizar_certidoes(okbr_com(certidoes=certidoes[:3]))
    assert resposta.certidao(TipoCertidaoTcu.CNEP) is None


@pytest.mark.parametrize(
    ("corpo", "mensagem"),
    [
        (item_okbr_com(0, tipo="Contas Irregulares"), "certidão desconhecida"),
        (item_okbr_com(1, emissor="TCU"), "certidão desconhecida"),
        (item_okbr_com(2, situacao="EM_ANALISE"), "situacao desconhecida"),
        (item_okbr_com(2, situacao=None), "situacao"),
        (item_okbr_com(3, tipo="CEIS"), "certidões repetidas CEIS"),
        (okbr_com(certidoes=[]), "certidoes"),
        (okbr_com(certidoes=None), "certidoes"),
        (okbr_com(seCnpjEncontradoNaBaseTcu="true"), "seCnpjEncontradoNaBaseTcu"),
        (okbr_com(seCnpjEncontradoNaBaseTcu=None), "seCnpjEncontradoNaBaseTcu"),
        (okbr_com(cnpj="19.131.243/0001"), "cnpj inválido"),
        (okbr_com(cnpj=None), "cnpj"),
        (ler("412_19131243000198.json"), "cnpj"),
        (b"<html>manutencao</html>", "fora do formato"),
        (b"", "fora do formato"),
        (b"[]", "fora do formato"),
    ],
)
def test_formato_inesperado(corpo: bytes, mensagem: str) -> None:
    with pytest.raises(ErroFormato, match=mensagem) as erro:
        normalizar_certidoes(corpo)
    assert str(erro.value).startswith("TCU")
