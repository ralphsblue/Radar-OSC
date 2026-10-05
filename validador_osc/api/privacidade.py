import copy
import secrets
from typing import Any

from pydantic import SecretStr

CAMPOS_PESSOAIS = ("nome", "qualificacao", "data_entrada")


def eh_operador(token_informado: str | None, token_configurado: SecretStr | None) -> bool:
    if not token_informado or token_configurado is None:
        return False
    esperado = token_configurado.get_secret_value()
    return bool(esperado) and secrets.compare_digest(token_informado.encode(), esperado.encode())


def ocultar_dirigentes(documento: dict[str, Any]) -> dict[str, Any]:
    publico = copy.deepcopy(documento)
    for verificacao in publico.get("verificacoes", []):
        if verificacao.get("id") != "dirigentes":
            continue
        rotulos: dict[str, str] = {}
        for achado in verificacao.get("achados", []):
            if achado.get("tipo") != "dirigente":
                continue
            nome = str(achado.get("nome"))
            rotulos.setdefault(nome, f"Dirigente {len(rotulos) + 1}")
            for campo in CAMPOS_PESSOAIS:
                achado.pop(campo, None)
            achado["dirigente"] = rotulos[nome]
    return publico
