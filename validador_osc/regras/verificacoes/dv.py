from validador_osc.cnpj import Motivo, ResultadoDV
from validador_osc.dominio.resultado import Achado, Estado, ResultadoVerificacao
from validador_osc.regras.catalogo import DV


def _mensagem_falha(resultado: ResultadoDV) -> str:
    match resultado.motivo:
        case Motivo.FORMATO:
            return "CNPJ inválido: informe 14 caracteres (12 letras ou números seguidos de 2 dígitos)."
        case Motivo.REPETIDO:
            return "CNPJ inválido: sequência de caracteres repetidos."
        case _:
            return f"CNPJ inválido: dígito verificador não confere (esperado {resultado.dv_esperado})."


def verificar_dv(resultado: ResultadoDV) -> ResultadoVerificacao:
    if resultado.valido:
        return ResultadoVerificacao(DV, Estado.OK, "Dígito verificador confere.")
    achado = Achado(
        "cnpj_invalido",
        {"motivo": str(resultado.motivo), "dv_esperado": resultado.dv_esperado},
    )
    return ResultadoVerificacao(DV, Estado.RESTRICAO, _mensagem_falha(resultado), (achado,))
