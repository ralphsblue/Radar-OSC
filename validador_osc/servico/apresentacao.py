from collections import Counter
from datetime import date, datetime
from typing import Any

from validador_osc.dominio.resultado import Avaliacao, Esfera, Estado, RefFonte, ResultadoVerificacao
from validador_osc.dominio.tipos import Cadastro

AVISO = "Triagem automatizada de cadastros públicos. Não substitui certidões oficiais."


def _fonte(ref: RefFonte) -> dict[str, Any]:
    return {
        "fonte": ref.fonte,
        "data_base": ref.data_base.isoformat() if ref.data_base else None,
        "obtida_em": ref.obtida_em.isoformat() if ref.obtida_em else None,
        "de_cache": ref.de_cache,
        "evidencia": ref.evidencia_id,
        "carga": ref.carga_id,
        "sha256": ref.sha256,
    }


def _verificacao(resultado: ResultadoVerificacao) -> dict[str, Any]:
    definicao = resultado.definicao
    documento: dict[str, Any] = {
        "id": definicao.id,
        "spec": definicao.spec,
        "nome": definicao.nome,
        "tipo": definicao.tipo.value,
        "estado": resultado.estado.value,
        "mensagem": resultado.mensagem,
        "achados": [{"tipo": a.tipo, **a.dados} for a in resultado.achados],
        "fontes": [_fonte(f) for f in resultado.fontes],
    }
    if resultado.situacao is not None:
        documento["situacao"] = resultado.situacao
    return documento


def _resumo(avaliacao: Avaliacao) -> dict[str, int]:
    contagem = Counter(v.estado for v in avaliacao.verificacoes)
    return {estado.value.lower(): contagem.get(estado, 0) for estado in Estado}


def montar_documento(
    *,
    consulta_id: str,
    cnpj: str,
    cadastro: Cadastro | None,
    matriz: Cadastro | None,
    esfera: Esfera | None,
    data_referencia: date,
    consultado_em: datetime,
    avaliacao: Avaliacao,
    versao_app: str,
    versao_regras: str,
) -> dict[str, Any]:
    estabelecimento = None if cadastro is None else ("MATRIZ" if cadastro.matriz else "FILIAL")
    entidade = matriz or cadastro
    return {
        "id": consulta_id,
        "cnpj": cnpj,
        "cnpj_avaliado": entidade.cnpj if entidade else cnpj,
        "estabelecimento": estabelecimento,
        "razao_social": entidade.razao_social if entidade else None,
        "nome_fantasia": entidade.nome_fantasia if entidade else None,
        "esfera": esfera.value if esfera else None,
        "data_referencia": data_referencia.isoformat(),
        "consultado_em": consultado_em.isoformat(),
        "status": avaliacao.status.value,
        "motivos": list(avaliacao.motivos),
        "avisos": list(avaliacao.avisos),
        "resumo": _resumo(avaliacao),
        "verificacoes": [_verificacao(v) for v in avaliacao.verificacoes],
        "versao": {"app": versao_app, "regras": versao_regras},
        "aviso": AVISO,
    }
