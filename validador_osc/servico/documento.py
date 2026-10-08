from collections import Counter
from datetime import date, datetime
from typing import Any

from validador_osc.dominio.consulta import Esfera
from validador_osc.dominio.resultado import Avaliacao, Estado, RefFonte, ResultadoVerificacao
from validador_osc.dominio.tipos import Cadastro

AVISO = "Triagem automatizada de cadastros públicos. Não substitui certidões oficiais."

RECEITA = "https://solucoes.receita.fazenda.gov.br/servicos/cnpjreva/cnpjreva_solicitacao.asp"
TCU_CONSOLIDADA = "https://certidoes-apf.apps.tcu.gov.br/"
TCU_CERTIDOES = "https://certidoes.apps.tcu.gov.br/"
CONSULTA_MANUAL = {
    "situacao": RECEITA,
    "estabelecimento": RECEITA,
    "natureza": RECEITA,
    "cnae": RECEITA,
    "religiosa": RECEITA,
    "tempo": RECEITA,
    "cepim": "https://portaldatransparencia.gov.br/sancoes/cepim",
    "ceis": "https://portaldatransparencia.gov.br/sancoes/ceis",
    "cnep": "https://portaldatransparencia.gov.br/sancoes/cnep",
    "tcu_inidoneos": TCU_CONSOLIDADA,
    "cnj_cnia": TCU_CONSOLIDADA,
    "tcu_contas_irregulares": TCU_CERTIDOES,
    "dirigentes": TCU_CERTIDOES,
    "mapa_osc": "https://mapaosc.ipea.gov.br/",
}
LINKS_FONTES = {
    "opencnpj": "https://opencnpj.org/",
    "brasilapi": "https://brasilapi.com.br/",
    "tcu_consolidada": TCU_CONSOLIDADA,
    "cgu_cepim": "https://portaldatransparencia.gov.br/download-de-dados/cepim",
    "cgu_ceis": "https://portaldatransparencia.gov.br/download-de-dados/ceis",
    "cgu_cnep": "https://portaldatransparencia.gov.br/download-de-dados/cnep",
    "tcu_inidoneos": TCU_CERTIDOES,
    "tcu_contas_irregulares": TCU_CERTIDOES,
    "tcu_inabilitados": TCU_CERTIDOES,
    "tcesp_terceiro_setor": "https://www.tce.sp.gov.br/relacao-de-responsaveis-por-contas-julgadas-irregulares",
    "mapa_osc_busca": "https://mapaosc.ipea.gov.br/",
}


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
    if definicao.id in CONSULTA_MANUAL:
        documento["consulta_manual"] = CONSULTA_MANUAL[definicao.id]
    return documento


def _fontes_consultadas(avaliacao: Avaliacao) -> list[dict[str, Any]]:
    vistas: dict[str, RefFonte] = {}
    for verificacao in avaliacao.verificacoes:
        for ref in verificacao.fontes:
            atual = vistas.get(ref.fonte)
            if atual is None or (
                ref.data_base and (atual.data_base is None or ref.data_base > atual.data_base)
            ):
                vistas[ref.fonte] = ref
    return [
        {
            "fonte": nome,
            "data_base": ref.data_base.isoformat() if ref.data_base else None,
            "link": LINKS_FONTES.get(nome),
        }
        for nome, ref in sorted(vistas.items())
        if nome in LINKS_FONTES
    ]


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
        "fontes_consultadas": _fontes_consultadas(avaliacao),
        "versao": {"app": versao_app, "regras": versao_regras},
        "aviso": AVISO,
    }
