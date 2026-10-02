import json
import re
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from validador_osc.dominio.tipos import Cadastro, Dirigente, SituacaoCadastral
from validador_osc.fontes.normalizacao import opencnpj
from validador_osc.fontes.normalizacao.brasilapi import ErroFormato, normalizar_cadastro

FIXTURES = Path(__file__).parent.parent / "fixtures" / "fontes"
BRASILAPI = FIXTURES / "brasilapi"
OPENCNPJ = FIXTURES / "opencnpj"
OKBR = "19131243000197.json"
_REMOVER = object()
MASCARA_CPF = re.compile(r"\*{3}\d{6}\*{2}")
CADASTROS = sorted(
    caminho.name for caminho in BRASILAPI.glob("*.json") if caminho.stem.isalnum() and len(caminho.stem) == 14
)
EM_COMUM_COM_OPENCNPJ = sorted(nome for nome in CADASTROS if (OPENCNPJ / nome).exists())


def ler(nome: str) -> bytes:
    return (BRASILAPI / nome).read_bytes()


def okbr_com(**alteracoes: Any) -> bytes:
    bruto: dict[str, Any] = json.loads(ler(OKBR))
    for campo, valor in alteracoes.items():
        if valor is _REMOVER:
            del bruto[campo]
        else:
            bruto[campo] = valor
    return json.dumps(bruto, ensure_ascii=False).encode()


def socio_okbr_com(**alteracoes: Any) -> bytes:
    socio: dict[str, Any] = json.loads(ler(OKBR))["qsa"][0]
    for campo, valor in alteracoes.items():
        if valor is _REMOVER:
            del socio[campo]
        else:
            socio[campo] = valor
    return okbr_com(qsa=[socio])


def test_okbr_vira_cadastro_completo() -> None:
    assert normalizar_cadastro(ler(OKBR)) == Cadastro(
        cnpj="19131243000197",
        razao_social="OPEN KNOWLEDGE BRASIL",
        nome_fantasia="REDE PELO CONHECIMENTO LIVRE",
        situacao=SituacaoCadastral.ATIVA,
        situacao_data=date(2013, 10, 3),
        motivo_codigo=0,
        motivo_descricao="SEM MOTIVO",
        matriz=True,
        natureza_codigo=3999,
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
        fonte="brasilapi",
        data_base=None,
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
    natureza_codigo: int
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
        2038,
        "Sociedade de Economia Mista",
        "6422100",
        ("6499999",),
        date(1966, 8, 1),
        "DF",
        "BRASILIA",
        41,
    ),
    Esperado(
        "00000000E08G12.json",
        "BANCO DO BRASIL SA",
        None,
        SituacaoCadastral.ATIVA,
        date(2026, 7, 31),
        0,
        "SEM MOTIVO",
        False,
        2038,
        "Sociedade de Economia Mista",
        "6422100",
        ("6499999",),
        date(2026, 7, 31),
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
        3999,
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
        3999,
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
        3999,
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
        "04955882000523.json",
        "INSTITUTO GRPCOM",
        "INSTITUTO GRPCOM CASCAVEL",
        SituacaoCadastral.BAIXADA,
        date(2017, 1, 5),
        1,
        "EXTINCAO POR ENCERRAMENTO LIQUIDACAO VOLUNTARIA",
        False,
        3999,
        "Associação Privada",
        "9430800",
        ("9493600", "9499500"),
        date(2011, 11, 29),
        "PR",
        "CASCAVEL",
        2,
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
        3999,
        "Associação Privada",
        "9430800",
        ("9493600", "9499500"),
        date(2002, 3, 7),
        "PR",
        "CURITIBA",
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
        3220,
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
        2143,
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
        3999,
        "Associação Privada",
        "9499500",
        ("9001902", "9001903", "9001904", "9319101", "9329899", "9493600"),
        date(2026, 2, 3),
        "MG",
        "BELO HORIZONTE",
        4,
    ),
]


@pytest.mark.parametrize("esperado", ESPERADOS, ids=lambda esperado: esperado.arquivo)
def test_fixture_vira_cadastro_esperado(esperado: Esperado) -> None:
    cadastro = normalizar_cadastro(ler(esperado.arquivo))

    assert cadastro.cnpj == esperado.arquivo.removesuffix(".json")
    assert cadastro.razao_social == esperado.razao_social
    assert cadastro.nome_fantasia == esperado.nome_fantasia
    assert cadastro.situacao is esperado.situacao
    assert cadastro.situacao_data == esperado.situacao_data
    assert cadastro.motivo_codigo == esperado.motivo_codigo
    assert cadastro.motivo_descricao == esperado.motivo_descricao
    assert cadastro.matriz is esperado.matriz
    assert cadastro.natureza_codigo == esperado.natureza_codigo
    assert cadastro.natureza_descricao == esperado.natureza_descricao
    assert cadastro.cnae_principal == esperado.cnae_principal
    assert cadastro.cnaes_secundarios == esperado.cnaes_secundarios
    assert cadastro.data_inicio == esperado.data_inicio
    assert cadastro.uf == esperado.uf
    assert cadastro.municipio == esperado.municipio
    assert len(cadastro.qsa) == esperado.tamanho_qsa
    assert cadastro.fonte == "brasilapi"
    assert cadastro.data_base is None


def test_esperados_cobrem_todas_as_fixtures_de_cadastro() -> None:
    assert sorted([*(esperado.arquivo for esperado in ESPERADOS), OKBR]) == CADASTROS


@pytest.mark.parametrize("arquivo", CADASTROS)
def test_qsa_das_fixtures_vem_mascarado_e_de_pessoa_fisica(arquivo: str) -> None:
    cadastro = normalizar_cadastro(ler(arquivo))

    assert cadastro.qsa
    for dirigente in cadastro.qsa:
        assert dirigente.documento_mascarado is not None
        assert MASCARA_CPF.fullmatch(dirigente.documento_mascarado)
        assert dirigente.pessoa_fisica
        assert dirigente.nome
        assert dirigente.data_entrada is not None


def test_okbr_igual_ao_opencnpj_exceto_fonte_data_base_e_natureza() -> None:
    da_brasilapi = normalizar_cadastro(ler(OKBR))
    do_opencnpj = opencnpj.normalizar_cadastro((OPENCNPJ / OKBR).read_bytes(), date(2026, 9, 14))

    assert do_opencnpj.natureza_codigo is None
    assert da_brasilapi.natureza_codigo == 3999
    assert replace(da_brasilapi, fonte="opencnpj", data_base=date(2026, 9, 14), natureza_codigo=None) == (
        do_opencnpj
    )


@pytest.mark.parametrize("arquivo", EM_COMUM_COM_OPENCNPJ)
def test_mesmo_cnpj_nas_duas_fontes_so_difere_na_ordem_do_qsa(arquivo: str) -> None:
    da_brasilapi = normalizar_cadastro(ler(arquivo))
    do_opencnpj = opencnpj.normalizar_cadastro((OPENCNPJ / arquivo).read_bytes(), None)

    assert sorted(da_brasilapi.qsa, key=repr) == sorted(do_opencnpj.qsa, key=repr)
    assert replace(da_brasilapi, fonte="opencnpj", natureza_codigo=None, qsa=do_opencnpj.qsa) == do_opencnpj


def test_ha_cnpjs_em_comum_com_o_opencnpj() -> None:
    assert len(EM_COMUM_COM_OPENCNPJ) == 10


def test_qsa_vem_na_ordem_da_fonte() -> None:
    cadastro = normalizar_cadastro(ler("04311762000160.json"))

    assert [(d.nome, d.qualificacao, d.data_entrada) for d in cadastro.qsa] == [
        ("EDIVAN FARIAS GOES", "Diretor", date(2023, 9, 14)),
        ("OZANEI RIBEIRO PINTO", "Presidente", date(2019, 8, 23)),
        ("RAIMUNDO DA PENHA RIBEIRO", "Diretor", date(2019, 8, 23)),
        ("RAIMUNDO RODRIGUES DE LIMA", "Diretor", date(2023, 9, 14)),
    ]


@pytest.mark.parametrize(
    "arquivo", ["404_12ABC34501DE35.json", "400_19131243000198.json", "500_65478551000100.json"]
)
def test_corpo_de_erro_nao_e_cadastro(arquivo: str) -> None:
    with pytest.raises(ErroFormato, match="cnpj"):
        normalizar_cadastro(ler(arquivo))


@pytest.mark.parametrize("valor", [None, "", "  ", _REMOVER])
def test_data_nula_vira_none(valor: object) -> None:
    corpo = okbr_com(data_situacao_cadastral=valor, data_inicio_atividade=valor)

    cadastro = normalizar_cadastro(corpo)

    assert cadastro.situacao_data is None
    assert cadastro.data_inicio is None


@pytest.mark.parametrize("valor", ["03/10/2013", "20131003", "2013-13-03", "0"])
def test_data_fora_do_iso_e_erro_de_formato(valor: str) -> None:
    with pytest.raises(ErroFormato, match="data_situacao_cadastral"):
        normalizar_cadastro(okbr_com(data_situacao_cadastral=valor))


def test_data_numerica_e_erro_de_formato() -> None:
    with pytest.raises(ErroFormato, match="data_inicio_atividade"):
        normalizar_cadastro(okbr_com(data_inicio_atividade=20131003))


@pytest.mark.parametrize(
    ("valor", "esperado"), [(220903, "0220903"), ("220903", "0220903"), (9430800, "9430800")]
)
def test_cnae_fiscal_ganha_zero_a_esquerda(valor: object, esperado: str) -> None:
    assert normalizar_cadastro(okbr_com(cnae_fiscal=valor)).cnae_principal == esperado


@pytest.mark.parametrize("valor", [None, 0, "", _REMOVER])
def test_cnae_fiscal_ausente_vira_none(valor: object) -> None:
    assert normalizar_cadastro(okbr_com(cnae_fiscal=valor)).cnae_principal is None


@pytest.mark.parametrize("valor", [94308001, -9430800, "94.30-8-00"])
def test_cnae_fiscal_invalido_e_erro_de_formato(valor: object) -> None:
    with pytest.raises(ErroFormato, match="cnae_fiscal"):
        normalizar_cadastro(okbr_com(cnae_fiscal=valor))


def test_cnaes_secundarios_ignoram_zero_e_vazio() -> None:
    corpo = okbr_com(
        cnaes_secundarios=[
            {"codigo": 0, "descricao": ""},
            {"codigo": 9493600, "descricao": "x"},
            {"codigo": "", "descricao": ""},
            {"codigo": 220903, "descricao": "y"},
            {"codigo": "8599699"},
        ]
    )

    assert normalizar_cadastro(corpo).cnaes_secundarios == ("9493600", "0220903", "8599699")


@pytest.mark.parametrize("valor", [None, [], _REMOVER])
def test_cnaes_secundarios_ausentes_viram_tupla_vazia(valor: object) -> None:
    assert normalizar_cadastro(okbr_com(cnaes_secundarios=valor)).cnaes_secundarios == ()


def test_cnae_secundario_invalido_e_erro_de_formato() -> None:
    with pytest.raises(ErroFormato, match="cnaes_secundarios"):
        normalizar_cadastro(okbr_com(cnaes_secundarios=[{"codigo": 12345678}]))


def test_cnaes_secundarios_no_formato_do_opencnpj_sao_erro_de_formato() -> None:
    with pytest.raises(ErroFormato, match=r"cnaes_secundarios\.0"):
        normalizar_cadastro(okbr_com(cnaes_secundarios=["9493600"]))


def test_campo_extra_e_ignorado() -> None:
    corpo = okbr_com(campo_novo={"qualquer": [1, 2]}, regime_tributario=None)

    assert normalizar_cadastro(corpo) == normalizar_cadastro(ler(OKBR))


@pytest.mark.parametrize("corpo", [b"", b"{", b"<html>502 Bad Gateway</html>", b"[]", b"null"])
def test_json_invalido_ou_nao_objeto_e_erro_de_formato(corpo: bytes) -> None:
    with pytest.raises(ErroFormato, match="BrasilAPI"):
        normalizar_cadastro(corpo)


@pytest.mark.parametrize(
    ("codigo", "esperada"),
    [
        (1, SituacaoCadastral.NULA),
        (2, SituacaoCadastral.ATIVA),
        (3, SituacaoCadastral.SUSPENSA),
        (4, SituacaoCadastral.INAPTA),
        (8, SituacaoCadastral.BAIXADA),
    ],
)
def test_situacao_numerica_vira_enum(codigo: int, esperada: SituacaoCadastral) -> None:
    assert normalizar_cadastro(okbr_com(situacao_cadastral=codigo)).situacao is esperada


@pytest.mark.parametrize("codigo", [0, 5, 9, -2])
def test_situacao_desconhecida_e_erro_de_formato(codigo: int) -> None:
    with pytest.raises(ErroFormato, match="situacao_cadastral desconhecida"):
        normalizar_cadastro(okbr_com(situacao_cadastral=codigo))


@pytest.mark.parametrize("valor", ["2", "ATIVA", True, None])
def test_situacao_fora_do_tipo_e_erro_de_formato(valor: object) -> None:
    with pytest.raises(ErroFormato, match="situacao_cadastral"):
        normalizar_cadastro(okbr_com(situacao_cadastral=valor))


@pytest.mark.parametrize(("identificador", "matriz"), [(1, True), (2, False)])
def test_identificador_matriz_filial_vira_bool(identificador: int, matriz: bool) -> None:
    assert normalizar_cadastro(okbr_com(identificador_matriz_filial=identificador)).matriz is matriz


@pytest.mark.parametrize("valor", [0, 3, "1", "MATRIZ"])
def test_identificador_matriz_filial_desconhecido_e_erro_de_formato(valor: object) -> None:
    with pytest.raises(ErroFormato, match="identificador_matriz_filial"):
        normalizar_cadastro(okbr_com(identificador_matriz_filial=valor))


@pytest.mark.parametrize("valor", [None, _REMOVER])
def test_natureza_ausente_vira_none(valor: object) -> None:
    assert normalizar_cadastro(okbr_com(codigo_natureza_juridica=valor)).natureza_codigo is None


@pytest.mark.parametrize("valor", [0, 999, 10000, -3999])
def test_natureza_fora_de_4_digitos_e_erro_de_formato(valor: int) -> None:
    with pytest.raises(ErroFormato, match="codigo_natureza_juridica"):
        normalizar_cadastro(okbr_com(codigo_natureza_juridica=valor))


def test_natureza_com_hifen_e_erro_de_formato() -> None:
    with pytest.raises(ErroFormato, match="codigo_natureza_juridica"):
        normalizar_cadastro(okbr_com(codigo_natureza_juridica="399-9"))


@pytest.mark.parametrize("valor", ["", "  ", None, _REMOVER])
def test_campos_de_texto_vazios_viram_none(valor: object) -> None:
    corpo = okbr_com(
        nome_fantasia=valor,
        natureza_juridica=valor,
        uf=valor,
        municipio=valor,
        descricao_motivo_situacao_cadastral=valor,
    )

    cadastro = normalizar_cadastro(corpo)

    assert cadastro.nome_fantasia is None
    assert cadastro.natureza_descricao is None
    assert cadastro.uf is None
    assert cadastro.municipio is None
    assert cadastro.motivo_descricao is None


@pytest.mark.parametrize("valor", [None, _REMOVER])
def test_motivo_ausente_vira_none(valor: object) -> None:
    assert normalizar_cadastro(okbr_com(motivo_situacao_cadastral=valor)).motivo_codigo is None


@pytest.mark.parametrize("valor", [-1, "01"])
def test_motivo_invalido_e_erro_de_formato(valor: object) -> None:
    with pytest.raises(ErroFormato, match="motivo_situacao_cadastral"):
        normalizar_cadastro(okbr_com(motivo_situacao_cadastral=valor))


@pytest.mark.parametrize("valor", [None, [], _REMOVER])
def test_qsa_ausente_ou_vazio_vira_tupla_vazia(valor: object) -> None:
    assert normalizar_cadastro(okbr_com(qsa=valor)).qsa == ()


def test_qsa_maiusculo_nao_e_lido() -> None:
    corpo = okbr_com(QSA=json.loads(ler(OKBR))["qsa"], qsa=_REMOVER)

    assert normalizar_cadastro(corpo).qsa == ()


@pytest.mark.parametrize(
    ("identificador", "pessoa_fisica"), [(2, True), (1, False), (3, False), (None, False)]
)
def test_pessoa_fisica_pelo_identificador(identificador: int | None, pessoa_fisica: bool) -> None:
    corpo = socio_okbr_com(identificador_de_socio=identificador)

    assert normalizar_cadastro(corpo).qsa[0].pessoa_fisica is pessoa_fisica


def test_documento_do_socio_vem_como_veio() -> None:
    corpo = socio_okbr_com(cnpj_cpf_do_socio="12345678000199", identificador_de_socio=1)

    assert normalizar_cadastro(corpo).qsa[0].documento_mascarado == "12345678000199"


def test_cpf_do_representante_legal_nao_e_lido() -> None:
    dirigente = normalizar_cadastro(socio_okbr_com(cpf_representante_legal="***999999**")).qsa[0]

    assert dirigente.documento_mascarado == "***112108**"


@pytest.mark.parametrize("valor", ["", None, _REMOVER])
def test_socio_com_campos_vazios(valor: object) -> None:
    corpo = socio_okbr_com(cnpj_cpf_do_socio=valor, qualificacao_socio=valor, data_entrada_sociedade=valor)

    dirigente = normalizar_cadastro(corpo).qsa[0]

    assert dirigente.documento_mascarado is None
    assert dirigente.qualificacao is None
    assert dirigente.data_entrada is None


def test_data_de_entrada_do_socio_invalida_e_erro_de_formato() -> None:
    with pytest.raises(ErroFormato, match=r"qsa\.data_entrada_sociedade"):
        normalizar_cadastro(socio_okbr_com(data_entrada_sociedade="27/02/2024"))


def test_erro_de_esquema_aponta_o_campo_sem_expor_o_valor() -> None:
    corpo = socio_okbr_com(nome_socio=["FULANO DE TAL"])

    with pytest.raises(ErroFormato, match=r"qsa\.0\.nome_socio") as erro:
        normalizar_cadastro(corpo)

    assert "FULANO" not in str(erro.value)


@pytest.mark.parametrize(
    "campo", ["cnpj", "razao_social", "situacao_cadastral", "identificador_matriz_filial"]
)
def test_campo_obrigatorio_ausente_e_erro_de_formato(campo: str) -> None:
    with pytest.raises(ErroFormato, match=campo):
        normalizar_cadastro(okbr_com(**{campo: _REMOVER}))


def test_cnpj_e_normalizado_para_maiusculas() -> None:
    assert normalizar_cadastro(okbr_com(cnpj=" 00000000e08g12 ")).cnpj == "00000000E08G12"
