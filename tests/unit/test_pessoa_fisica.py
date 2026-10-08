import pytest

from tests.apoio.csv_cgu import cpf_sintetico, formatar_cpf
from validador_osc.dominio.pessoa_fisica import (
    FragmentoCpf,
    calcular_dvs,
    contem_cpf,
    cpf_valido,
    fragmento_cpf,
    mascarar_cpfs,
    normalizar_nome,
)


@pytest.mark.parametrize(
    ("nome", "esperado"),
    [
        ("José  da   Conceição", "JOSE DA CONCEICAO"),
        ("  maria d'ávila-souza ", "MARIA D AVILA SOUZA"),
        ("JOÃO PAULO II", "JOAO PAULO II"),
        ("Ana 123 Lúcia", "ANA LUCIA"),
        ("", ""),
    ],
)
def test_normalizar_nome(nome: str, esperado: str) -> None:
    assert normalizar_nome(nome) == esperado


def test_dvs_do_cpf() -> None:
    assert calcular_dvs("123456789") == "09"
    assert calcular_dvs("000000001") == "91"
    with pytest.raises(ValueError, match="9 dígitos"):
        calcular_dvs("12345")


def test_cpf_valido() -> None:
    cpf = cpf_sintetico(1)
    assert cpf_valido(cpf)
    assert not cpf_valido(cpf[:9] + str((int(cpf[9]) + 1) % 10) + cpf[10])
    assert not cpf_valido("11111111111")
    assert not cpf_valido(cpf[:10])


def test_fragmento_de_cpf_completo_formatado_ou_mascarado() -> None:
    cpf = cpf_sintetico(2)
    assert fragmento_cpf(cpf) == FragmentoCpf(cpf[3:9], cpf[9:])
    assert fragmento_cpf(formatar_cpf(cpf)) == FragmentoCpf(cpf[3:9], cpf[9:])
    assert fragmento_cpf("***.921.012-**") == FragmentoCpf("921012", None)
    assert fragmento_cpf(" ***921012** ") == FragmentoCpf("921012", None)
    assert fragmento_cpf("06278833000103") is None
    assert fragmento_cpf("000123456") is None
    assert fragmento_cpf("") is None
    assert FragmentoCpf("921012", "34").mascarado == "***921012**"


def test_mascarar_cpfs_em_texto_livre() -> None:
    cpf = cpf_sintetico(3)
    formatado = formatar_cpf(cpf)
    texto = f"sócio {formatado} e procurador {cpf}; processo 00007370620074013100; CNPJ 06278833000103"
    mascarado = mascarar_cpfs(texto)
    assert cpf not in mascarado
    assert formatado not in mascarado
    assert f"***.{cpf[3:6]}.{cpf[6:9]}-**" in mascarado
    assert f"***{cpf[3:9]}**" in mascarado
    assert "00007370620074013100" in mascarado
    assert "06278833000103" in mascarado
    assert contem_cpf(texto)
    assert not contem_cpf(mascarado)


def test_onze_digitos_sem_dv_de_cpf_nao_sao_mascarados() -> None:
    cpf = cpf_sintetico(4)
    invalido = cpf[:10] + str((int(cpf[10]) + 1) % 10)
    assert mascarar_cpfs(f"processo {invalido}") == f"processo {invalido}"
    assert not contem_cpf(invalido)
