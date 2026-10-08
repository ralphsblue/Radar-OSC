import re
import unicodedata
from dataclasses import dataclass

TAMANHO_CPF = 11
_RESTO_MINIMO = 2
_NAO_LETRAS = re.compile(r"[^A-Z]+")
_CPF_EM_TEXTO = re.compile(
    r"(?<![0-9])([0-9]{3})([.\s]?)([0-9]{3})([.\s]?)([0-9]{3})([-.\s]?)([0-9]{2})(?![0-9])"
)
_CPF_MASCARADO = re.compile(r"\*{3}\.?([0-9]{3})\.?([0-9]{3})-?\*{2}")
_SEPARADORES = re.compile(r"[.\-\s]")


@dataclass(frozen=True, slots=True)
class FragmentoCpf:
    meio: str
    dv_final: str | None

    @property
    def mascarado(self) -> str:
        return f"***{self.meio}**"


def normalizar_nome(nome: str) -> str:
    decomposto = unicodedata.normalize("NFKD", nome)
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return " ".join(_NAO_LETRAS.sub(" ", sem_acento.upper()).split())


def _digito(valores: list[int]) -> int:
    peso_inicial = len(valores) + 1
    resto = sum(v * p for v, p in zip(valores, range(peso_inicial, 1, -1), strict=True)) % 11
    return 0 if resto < _RESTO_MINIMO else 11 - resto


def calcular_dvs(base9: str) -> str:
    if len(base9) != TAMANHO_CPF - 2 or not base9.isdecimal():
        raise ValueError(f"base do CPF deve ter 9 dígitos: {base9!r}")
    valores = [int(c) for c in base9]
    dv1 = _digito(valores)
    dv2 = _digito([*valores, dv1])
    return f"{dv1}{dv2}"


def cpf_valido(digitos: str) -> bool:
    if len(digitos) != TAMANHO_CPF or not digitos.isdecimal() or len(set(digitos)) == 1:
        return False
    return calcular_dvs(digitos[:9]) == digitos[9:]


def fragmento_cpf(valor: str) -> FragmentoCpf | None:
    limpo = valor.strip()
    mascarado = _CPF_MASCARADO.fullmatch(limpo)
    if mascarado is not None:
        return FragmentoCpf(mascarado.group(1) + mascarado.group(2), None)
    digitos = _SEPARADORES.sub("", limpo)
    if len(digitos) == TAMANHO_CPF and digitos.isdecimal():
        return FragmentoCpf(digitos[3:9], digitos[9:])
    return None


def _mascarar(trecho: re.Match[str]) -> str:
    primeiro, sep1, segundo, sep2, terceiro, sep3, dv = trecho.groups()
    formatado = bool(sep1 and sep2 and sep3)
    if not formatado and not cpf_valido(primeiro + segundo + terceiro + dv):
        return trecho.group(0)
    return f"***{sep1}{segundo}{sep2}{terceiro}{sep3}**"


def mascarar_cpfs(texto: str) -> str:
    if len(texto) < TAMANHO_CPF:
        return texto
    return _CPF_EM_TEXTO.sub(_mascarar, texto)


def contem_cpf(texto: str) -> bool:
    return any(_mascarar(trecho) != trecho.group(0) for trecho in _CPF_EM_TEXTO.finditer(texto))
