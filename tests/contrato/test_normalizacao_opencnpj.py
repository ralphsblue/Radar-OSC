import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from validador_osc.dominio.tipos import Cadastro, Dirigente, SituacaoCadastral
from validador_osc.fontes.normalizacao.opencnpj import ErroFormato, extrair_data_base, normalizar_cadastro

FIXTURES = Path(__file__).parent.parent / "fixtures" / "fontes" / "opencnpj"
DATA_BASE = date(2026, 9, 14)
_REMOVER = object()
MASCARA_CPF = re.compile(r"\*{3}\d{6}\*{2}")
CADASTROS = sorted(
    caminho.name for caminho in FIXTURES.glob("*.json") if caminho.stem.isalnum() and len(caminho.stem) == 14
)


def ler(nome: str) -> bytes:
    return (FIXTURES / nome).read_bytes()


def okbr_com(**alteracoes: Any) -> bytes:
    bruto: dict[str, Any] = json.loads(ler("19131243000197.json"))
    for campo, valor in alteracoes.items():
        if valor is _REMOVER:
            del bruto[campo]
        else:
            bruto[campo] = valor
    return json.dumps(bruto, ensure_ascii=False).encode()


def socio_okbr_com(**alteracoes: Any) -> bytes:
    socio: dict[str, Any] = json.loads(ler("19131243000197.json"))["QSA"][0]
    socio.update(alteracoes)
    return okbr_com(QSA=[socio])


def test_okbr_vira_cadastro_completo() -> None:
    assert normalizar_cadastro(ler("19131243000197.json"), DATA_BASE) == Cadastro(
        cnpj="19131243000197",
        razao_social="OPEN KNOWLEDGE BRASIL",
        nome_fantasia="REDE PELO CONHECIMENTO LIVRE",
        situacao=SituacaoCadastral.ATIVA,
        situacao_data=date(2013, 10, 3),
        motivo_codigo=0,
        motivo_descricao="SEM MOTIVO",
        matriz=True,
        natureza_codigo=None,
        natureza_descricao="Associação Privada",
        cnae_principal="9430800",
        cnaes_secundarios=("9493600", "9499500", "8599699", "8230001", "6204000"),
        data_inicio=date(2013, 10, 3),
        uf="SP",
        municipio="SAO PAULO",
        qsa=(
            Dirigente(
                nome="HAYDEE SVAB",
                qualificacao="Presidente",
                data_entrada=date(2024, 2, 27),
                documento_mascarado="***112108**",
                pessoa_fisica=True,
            ),
        ),
        fonte="opencnpj",
        data_base=DATA_BASE,
    )


@dataclass(frozen=True)
class Esperado:
    arquivo: str
    razao_social: str
    nome_fantasia: str | None
    situacao: SituacaoCadastral
    situacao_data: date | None
    motivo_codigo: int
    motivo_descricao: str
    matriz: bool
    natureza_descricao: str
    cnae_principal: str
    cnaes_secundarios: tuple[str, ...]
    data_inicio: date
    uf: str
    municipio: str
    tamanho_qsa: int


ESPERADOS = [
    Esperado(
        "00000000000191.json",
        "BANCO DO BRASIL SA",
        "DIRECAO GERAL",
        SituacaoCadastral.ATIVA,
        date(2005, 11, 3),
        0,
        "SEM MOTIVO",
        True,
        "Sociedade de Economia Mista",
        "6422100",
        ("6499999",),
        date(1966, 8, 1),
        "DF",
        "BRASILIA",
        41,
    ),
    Esperado(
        "08942107000160.json",
        "ASSOCIACAO DE INCLUSAO E DESENVOLVIMENTO SOCIAL POR UM RIO MELHOR",
        "CENTRO SOCIAL RENATO MOURA",
        SituacaoCadastral.BAIXADA,
        date(2012, 1, 4),
        1,
        "EXTINCAO POR ENCERRAMENTO LIQUIDACAO VOLUNTARIA",
        True,
        "Associação Privada",
        "9499500",
        (),
        date(2007, 6, 29),
        "RJ",
        "RIO DE JANEIRO",
        6,
    ),
    Esperado(
        "62779145000270.json",
        "IRMANDADE DA SANTA CASA DE MISERICORDIA DE SAO PAULO",
        "HOSPITAL SAO LUIZ GONZAGA",
        SituacaoCadastral.ATIVA,
        date(2005, 11, 3),
        0,
        "SEM MOTIVO",
        False,
        "Associação Privada",
        "8610101",
        ("8610102", "8630501", "8630502", "8630503", "8630599", "8690999", "8712300"),
        date(1970, 4, 27),
        "SP",
        "SAO PAULO",
        2,
    ),
    Esperado(
        "62779145000190.json",
        "IRMANDADE DA SANTA CASA DE MISERICORDIA DE SAO PAULO",
        None,
        SituacaoCadastral.ATIVA,
        date(2005, 11, 3),
        0,
        "SEM MOTIVO",
        True,
        "Associação Privada",
        "8610101",
        (
            "8610102",
            "8630501",
            "8630502",
            "8630503",
            "8630599",
            "8690999",
            "8712300",
            "9102301",
            "8511200",
            "8533300",
        ),
        date(1970, 4, 27),
        "SP",
        "SAO PAULO",
        2,
    ),
    Esperado(
        "00108217000110.json",
        "MITRA ARQUIDIOCESANA DE BRASILIA",
        "MITRA ARQUIDIOCESANA DE BRASILIA",
        SituacaoCadastral.ATIVA,
        date(2005, 11, 3),
        0,
        "SEM MOTIVO",
        True,
        "Organização Religiosa",
        "9491000",
        (),
        date(1970, 11, 13),
        "DF",
        "BRASILIA",
        1,
    ),
    Esperado(
        "04311762000160.json",
        "COOPERATIVA MISTA DOS TRABALHADORES AGRO-EXTRATIVISTAS DO ALTO CAJARI",
        "COOPERALCA",
        SituacaoCadastral.ATIVA,
        date(2019, 3, 11),
        0,
        "SEM MOTIVO",
        True,
        "Cooperativa",
        "0220903",
        ("0161099", "0220906", "0230600", "1629301", "3299099", "7990200"),
        date(2001, 1, 17),
        "AP",
        "MAZAGAO",
        4,
    ),
    Esperado(
        "65478551000100.json",
        "ASSOCIACAO MATURIDADE EM MOVIMENTO",
        None,
        SituacaoCadastral.ATIVA,
        date(2026, 2, 3),
        0,
        "SEM MOTIVO",
        True,
        "Associação Privada",
        "9499500",
        ("9001902", "9001903", "9001904", "9319101", "9329899", "9493600"),
        date(2026, 2, 3),
        "MG",
        "BELO HORIZONTE",
        4,
    ),
    Esperado(
        "03126200000183.json",
        "ASSOCIACAO PLURAL",
        "PLURAL",
        SituacaoCadastral.INAPTA,
        date(2026, 5, 12),
        63,
        "OMISSAO DE DECLARACOES",
        True,
        "Associação Privada",
        "8630502",
        ("8412400", "8660700", "8800600", "8211300"),
        date(1999, 4, 7),
        "SP",
        "SANTOS",
        1,
    ),
    Esperado(
        "03728829000101.json",
        "ASSOCIACAO DOS PRODUTORES RURAIS DO SERINGAL",
        "AGUA DOCE",
        SituacaoCadastral.SUSPENSA,
        date(2022, 4, 6),
        21,
        "PEDIDO DE BAIXA INDEFERIDA",
        True,
        "Associação Privada",
        "9430800",
        ("9493600", "9499500"),
        date(2000, 3, 3),
        "AC",
        "FEIJO",
        1,
    ),
    Esperado(
        "04955882000108.json",
        "INSTITUTO GRPCOM",
        "INSTITUTO RPC",
        SituacaoCadastral.ATIVA,
        None,
        0,
        "SEM MOTIVO",
        True,
        "Associação Privada",
        "9430800",
        ("9493600", "9499500"),
        date(2002, 3, 7),
        "PR",
        "CURITIBA",
        2,
    ),
    Esperado(
        "04955882000523.json",
        "INSTITUTO GRPCOM",
        "INSTITUTO GRPCOM CASCAVEL",
        SituacaoCadastral.BAIXADA,
        date(2017, 1, 5),
        1,
        "EXTINCAO POR ENCERRAMENTO LIQUIDACAO VOLUNTARIA",
        False,
        "Associação Privada",
        "9430800",
        ("9493600", "9499500"),
        date(2011, 11, 29),
        "PR",
        "CASCAVEL",
        2,
    ),
    Esperado(
        "24006302000488.json",
        "INSTITUTO DE DESENVOLVIMENTO, ENSINO E ASSISTENCIA A SAUDE - IDEAS",
        "INSTITUTO IDEAS",
        SituacaoCadastral.ATIVA,
        date(2018, 1, 19),
        0,
        "SEM MOTIVO",
        True,
        "Associação Privada",
        "8660700",
        (
            "7490199",
            "7810800",
            "7820500",
            "7830200",
            "8111700",
            "8121400",
            "8129000",
            "8211300",
            "8550302",
            "8599699",
            "8610101",
            "8610102",
            "8630501",
            "8630502",
            "8630503",
            "8630504",
            "8630599",
            "8640210",
            "8650001",
            "8690901",
            "8690999",
            "9499500",
        ),
        date(2018, 1, 19),
        "SC",
        "JAGUARUNA",
        2,
    ),
    Esperado(
        "24006302000135.json",
        "INSTITUTO DE DESENVOLVIMENTO, ENSINO E ASSISTENCIA A SAUDE - IDEAS",
        "INSTITUTO IDEAS",
        SituacaoCadastral.ATIVA,
        date(2016, 1, 18),
        0,
        "SEM MOTIVO",
        False,
        "Associação Privada",
        "8660700",
        (
            "7490199",
            "7810800",
            "7820500",
            "7830200",
            "8111700",
            "8121400",
            "8129000",
            "8211300",
            "8550302",
            "8599699",
            "8610101",
            "8610102",
            "8630501",
            "8630502",
            "8630503",
            "8630599",
            "8650001",
            "8690901",
            "8690999",
            "9499500",
        ),
        date(2016, 1, 18),
        "SC",
        "FLORIANOPOLIS",
        2,
    ),
    Esperado(
        "44551605000570.json",
        "INSTITUTO GLOBAL GESTAO EM MEDICINA E SAUDE",
        None,
        SituacaoCadastral.ATIVA,
        date(2023, 6, 6),
        0,
        "SEM MOTIVO",
        False,
        "Associação Privada",
        "8640202",
        (
            "3312103",
            "7739002",
            "8599604",
            "8610102",
            "8630501",
            "8630502",
            "8630503",
            "8640201",
            "8640205",
            "8640299",
            "8660700",
        ),
        date(2023, 6, 6),
        "SP",
        "SAO JOSE DOS CAMPOS",
        1,
    ),
    Esperado(
        "44551605000146.json",
        "INSTITUTO GLOBAL GESTAO EM MEDICINA E SAUDE",
        None,
        SituacaoCadastral.ATIVA,
        date(2021, 12, 10),
        0,
        "SEM MOTIVO",
        True,
        "Associação Privada",
        "8640202",
        (
            "3312103",
            "4930202",
            "4930203",
            "5229099",
            "7739002",
            "8599604",
            "8610102",
            "8630501",
            "8630502",
            "8630503",
            "8640201",
            "8640205",
            "8640299",
            "8660700",
        ),
        date(2021, 12, 10),
        "SP",
        "SAO PAULO",
        1,
    ),
]


@pytest.mark.parametrize("esperado", ESPERADOS, ids=lambda esperado: esperado.arquivo)
def test_fixture_vira_cadastro_esperado(esperado: Esperado) -> None:
    cadastro = normalizar_cadastro(ler(esperado.arquivo), DATA_BASE)

    assert cadastro.cnpj == esperado.arquivo.removesuffix(".json")
    assert cadastro.razao_social == esperado.razao_social
    assert cadastro.nome_fantasia == esperado.nome_fantasia
    assert cadastro.situacao is esperado.situacao
    assert cadastro.situacao_data == esperado.situacao_data
    assert cadastro.motivo_codigo == esperado.motivo_codigo
    assert cadastro.motivo_descricao == esperado.motivo_descricao
    assert cadastro.matriz is esperado.matriz
    assert cadastro.natureza_codigo is None
    assert cadastro.natureza_descricao == esperado.natureza_descricao
    assert cadastro.cnae_principal == esperado.cnae_principal
    assert cadastro.cnaes_secundarios == esperado.cnaes_secundarios
    assert cadastro.data_inicio == esperado.data_inicio
    assert cadastro.uf == esperado.uf
    assert cadastro.municipio == esperado.municipio
    assert len(cadastro.qsa) == esperado.tamanho_qsa
    assert cadastro.fonte == "opencnpj"
    assert cadastro.data_base == DATA_BASE


def test_esperados_cobrem_todas_as_fixtures_de_cadastro() -> None:
    assert sorted([*(esperado.arquivo for esperado in ESPERADOS), "19131243000197.json"]) == CADASTROS


@pytest.mark.parametrize("arquivo", CADASTROS)
def test_qsa_das_fixtures_vem_mascarado_e_de_pessoa_fisica(arquivo: str) -> None:
    cadastro = normalizar_cadastro(ler(arquivo), None)

    assert cadastro.qsa
    for dirigente in cadastro.qsa:
        assert dirigente.documento_mascarado is not None
        assert MASCARA_CPF.fullmatch(dirigente.documento_mascarado)
        assert dirigente.pessoa_fisica
        assert dirigente.nome
        assert dirigente.data_entrada is not None


def test_qsa_da_cooperativa_preserva_ordem_e_qualificacao() -> None:
    cadastro = normalizar_cadastro(ler("04311762000160.json"), None)

    assert [(d.nome, d.qualificacao, d.data_entrada) for d in cadastro.qsa] == [
        ("OZANEI RIBEIRO PINTO", "Presidente", date(2019, 8, 23)),
        ("RAIMUNDO DA PENHA RIBEIRO", "Diretor", date(2019, 8, 23)),
        ("EDIVAN FARIAS GOES", "Diretor", date(2023, 9, 14)),
        ("RAIMUNDO RODRIGUES DE LIMA", "Diretor", date(2023, 9, 14)),
    ]


def test_data_base_ausente_fica_none() -> None:
    assert normalizar_cadastro(ler("19131243000197.json"), None).data_base is None


def test_resposta_404_nao_e_cadastro() -> None:
    with pytest.raises(ErroFormato, match="cnpj"):
        normalizar_cadastro(ler("404_94580730000152.json"), DATA_BASE)


def test_resposta_de_datasets_nao_traz_cadastro() -> None:
    with pytest.raises(ErroFormato, match="razao_social"):
        normalizar_cadastro(ler("19131243000197_datasets.json"), DATA_BASE)


@pytest.mark.parametrize("valor", ["0", "", _REMOVER])
def test_data_nula_vira_none(valor: object) -> None:
    corpo = okbr_com(data_situacao_cadastral=valor, data_inicio_atividade=valor)

    cadastro = normalizar_cadastro(corpo, None)

    assert cadastro.situacao_data is None
    assert cadastro.data_inicio is None


@pytest.mark.parametrize("valor", ["03/10/2013", "20131003", "2013-13-03", "Sem informação"])
def test_data_fora_do_iso_e_erro_de_formato(valor: str) -> None:
    with pytest.raises(ErroFormato, match="data_situacao_cadastral"):
        normalizar_cadastro(okbr_com(data_situacao_cadastral=valor), None)


def test_data_numerica_e_erro_de_formato() -> None:
    with pytest.raises(ErroFormato, match="data_inicio_atividade"):
        normalizar_cadastro(okbr_com(data_inicio_atividade=20131003), None)


@pytest.mark.parametrize(
    ("valor", "esperado"), [(220903, "0220903"), ("220903", "0220903"), (9430800, "9430800")]
)
def test_cnae_principal_ganha_zero_a_esquerda(valor: object, esperado: str) -> None:
    assert normalizar_cadastro(okbr_com(cnae_principal=valor), None).cnae_principal == esperado


@pytest.mark.parametrize("valor", ["", "0", 0, _REMOVER])
def test_cnae_principal_ausente_vira_none(valor: object) -> None:
    assert normalizar_cadastro(okbr_com(cnae_principal=valor), None).cnae_principal is None


@pytest.mark.parametrize("valor", ["94308001", "94.30-8-00", "abc"])
def test_cnae_principal_invalido_e_erro_de_formato(valor: str) -> None:
    with pytest.raises(ErroFormato, match="cnae_principal"):
        normalizar_cadastro(okbr_com(cnae_principal=valor), None)


def test_cnaes_secundarios_ignoram_vazios_e_zero() -> None:
    corpo = okbr_com(cnaes_secundarios=["", "9493600", "0", 0, 220903, " 8599699 "])

    assert normalizar_cadastro(corpo, None).cnaes_secundarios == ("9493600", "0220903", "8599699")


def test_cnaes_secundarios_ausentes_viram_tupla_vazia() -> None:
    assert normalizar_cadastro(okbr_com(cnaes_secundarios=_REMOVER), None).cnaes_secundarios == ()


def test_campo_extra_e_ignorado() -> None:
    corpo = okbr_com(campo_novo={"qualquer": [1, 2]}, ceis=None, cepim=None, cnep=None)

    assert normalizar_cadastro(corpo, DATA_BASE) == normalizar_cadastro(ler("19131243000197.json"), DATA_BASE)


@pytest.mark.parametrize("corpo", [b"", b"{", b"<html>502 Bad Gateway</html>", b"[]", b"null"])
def test_json_invalido_ou_nao_objeto_e_erro_de_formato(corpo: bytes) -> None:
    with pytest.raises(ErroFormato, match="OpenCNPJ"):
        normalizar_cadastro(corpo, None)


@pytest.mark.parametrize(
    ("texto", "esperada"),
    [
        ("Ativa", SituacaoCadastral.ATIVA),
        ("ATIVA", SituacaoCadastral.ATIVA),
        (" Baixada ", SituacaoCadastral.BAIXADA),
        ("Inapta", SituacaoCadastral.INAPTA),
        ("Suspensa", SituacaoCadastral.SUSPENSA),
        ("Nula", SituacaoCadastral.NULA),
    ],
)
def test_situacao_em_texto_vira_enum(texto: str, esperada: SituacaoCadastral) -> None:
    assert normalizar_cadastro(okbr_com(situacao_cadastral=texto), None).situacao is esperada


@pytest.mark.parametrize("texto", ["Cancelada", "", "2"])
def test_situacao_desconhecida_e_erro_de_formato(texto: str) -> None:
    with pytest.raises(ErroFormato, match="situacao_cadastral desconhecida"):
        normalizar_cadastro(okbr_com(situacao_cadastral=texto), None)


def test_situacao_numerica_e_erro_de_formato() -> None:
    with pytest.raises(ErroFormato, match="situacao_cadastral"):
        normalizar_cadastro(okbr_com(situacao_cadastral=2), None)


@pytest.mark.parametrize(("texto", "matriz"), [("Matriz", True), ("FILIAL", False), ("Filial", False)])
def test_matriz_filial_em_texto_vira_bool(texto: str, matriz: bool) -> None:
    assert normalizar_cadastro(okbr_com(matriz_filial=texto), None).matriz is matriz


def test_matriz_filial_desconhecido_e_erro_de_formato() -> None:
    with pytest.raises(ErroFormato, match="matriz_filial"):
        normalizar_cadastro(okbr_com(matriz_filial="Sucursal"), None)


def test_campos_de_texto_vazios_viram_none() -> None:
    corpo = okbr_com(nome_fantasia="", natureza_juridica="", uf="", municipio="  ")

    cadastro = normalizar_cadastro(corpo, None)

    assert cadastro.nome_fantasia is None
    assert cadastro.natureza_descricao is None
    assert cadastro.uf is None
    assert cadastro.municipio is None


def test_motivo_ausente_vira_none() -> None:
    cadastro = normalizar_cadastro(okbr_com(motivo_situacao_cadastral=_REMOVER), None)

    assert cadastro.motivo_codigo is None
    assert cadastro.motivo_descricao is None


def test_motivo_com_campos_vazios_vira_none() -> None:
    cadastro = normalizar_cadastro(okbr_com(motivo_situacao_cadastral={"codigo": "", "descricao": ""}), None)

    assert cadastro.motivo_codigo is None
    assert cadastro.motivo_descricao is None


def test_motivo_com_codigo_nao_numerico_e_erro_de_formato() -> None:
    with pytest.raises(ErroFormato, match="motivo_situacao_cadastral"):
        normalizar_cadastro(okbr_com(motivo_situacao_cadastral={"codigo": "X1", "descricao": "?"}), None)


@pytest.mark.parametrize("valor", [None, [], _REMOVER])
def test_qsa_ausente_ou_vazio_vira_tupla_vazia(valor: object) -> None:
    assert normalizar_cadastro(okbr_com(QSA=valor), None).qsa == ()


def test_qsa_minusculo_nao_e_lido() -> None:
    corpo = okbr_com(qsa=json.loads(ler("19131243000197.json"))["QSA"], QSA=_REMOVER)

    assert normalizar_cadastro(corpo, None).qsa == ()


@pytest.mark.parametrize(
    ("identificador", "pessoa_fisica"),
    [("Pessoa Física", True), ("PESSOA FÍSICA", True), ("Pessoa Jurídica", False), ("Estrangeiro", False)],
)
def test_pessoa_fisica_pelo_identificador(identificador: str, pessoa_fisica: bool) -> None:
    corpo = socio_okbr_com(identificador_socio=identificador)

    assert normalizar_cadastro(corpo, None).qsa[0].pessoa_fisica is pessoa_fisica


def test_documento_do_socio_vem_como_veio() -> None:
    corpo = socio_okbr_com(cnpj_cpf_socio="12345678000199", identificador_socio="Pessoa Jurídica")

    assert normalizar_cadastro(corpo, None).qsa[0].documento_mascarado == "12345678000199"


def test_socio_com_campos_vazios() -> None:
    corpo = socio_okbr_com(cnpj_cpf_socio="", qualificacao_socio="", data_entrada_sociedade="0")

    dirigente = normalizar_cadastro(corpo, None).qsa[0]

    assert dirigente.documento_mascarado is None
    assert dirigente.qualificacao is None
    assert dirigente.data_entrada is None


def test_erro_de_esquema_aponta_o_campo_sem_expor_o_valor() -> None:
    corpo = socio_okbr_com(nome_socio=["FULANO DE TAL"])

    with pytest.raises(ErroFormato, match=r"QSA\.0\.nome_socio") as erro:
        normalizar_cadastro(corpo, None)

    assert "FULANO" not in str(erro.value)


def test_campo_obrigatorio_ausente_e_erro_de_formato() -> None:
    with pytest.raises(ErroFormato, match="situacao_cadastral"):
        normalizar_cadastro(okbr_com(situacao_cadastral=_REMOVER), None)


def test_info_real_da_a_data_do_espelho_em_brasilia() -> None:
    assert extrair_data_base(ler("info.json")) == date(2026, 9, 14)


@pytest.mark.parametrize(
    ("last_updated", "esperada"),
    [
        ("2026-09-15T03:00:00Z", date(2026, 9, 15)),
        ("2026-09-15T02:59:59.9999999Z", date(2026, 9, 14)),
        ("2026-09-15T10:00:00", date(2026, 9, 15)),
        ("2026-09-15T00:30:00-03:00", date(2026, 9, 15)),
    ],
)
def test_info_converte_para_brasilia_antes_de_truncar(last_updated: str, esperada: date) -> None:
    assert extrair_data_base(json.dumps({"last_updated": last_updated}).encode()) == esperada


@pytest.mark.parametrize("corpo", [b"{}", b'{"last_updated":""}'])
def test_info_sem_data_devolve_none(corpo: bytes) -> None:
    assert extrair_data_base(corpo) is None


@pytest.mark.parametrize(
    "corpo", [b"", b"{", b"[]", b'{"last_updated":"ontem"}', b'{"last_updated":1757897681}']
)
def test_info_invalido_e_erro_de_formato(corpo: bytes) -> None:
    with pytest.raises(ErroFormato, match="OpenCNPJ"):
        extrair_data_base(corpo)
