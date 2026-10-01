from dataclasses import replace
from datetime import UTC, date, datetime
from typing import Any

from validador_osc.dominio.coleta import Obtido, RefEvidencia
from validador_osc.dominio.resultado import RefFonte
from validador_osc.dominio.tipos import Cadastro, SituacaoCadastral
from validador_osc.regras.verificacoes.cadastro import CadastroObtido, referencia_fonte

DATA_REFERENCIA = date(2026, 10, 1)
RECEBIDA_EM = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
SHA256 = "ab" * 32

CADASTRO_BASE = Cadastro(
    cnpj="19131243000197",
    razao_social="OPEN KNOWLEDGE BRASIL",
    nome_fantasia=None,
    situacao=SituacaoCadastral.ATIVA,
    situacao_data=date(2013, 10, 3),
    motivo_codigo=None,
    motivo_descricao=None,
    matriz=True,
    natureza_codigo=None,
    natureza_descricao="Associação Privada",
    cnae_principal="9430800",
    cnaes_secundarios=(),
    data_inicio=date(2013, 10, 3),
    uf="SP",
    municipio="SAO PAULO",
    qsa=(),
    fonte="opencnpj",
    data_base=date(2026, 9, 15),
)

EVIDENCIA = RefEvidencia(id=7, fonte="opencnpj", sha256=SHA256, recebida_em=RECEBIDA_EM)


def cadastro(**alteracoes: Any) -> Cadastro:
    return replace(CADASTRO_BASE, **alteracoes)


def coleta_obtida(**alteracoes: Any) -> Obtido[Cadastro]:
    return Obtido(cadastro(**alteracoes), EVIDENCIA)


def obtido(**alteracoes: Any) -> CadastroObtido:
    coleta = coleta_obtida(**alteracoes)
    return CadastroObtido(coleta.dados, referencia_fonte(coleta))


def fonte_esperada(data_base: date | None = CADASTRO_BASE.data_base) -> RefFonte:
    return RefFonte(
        fonte="opencnpj",
        obtida_em=RECEBIDA_EM,
        data_base=data_base,
        de_cache=False,
        evidencia_id=7,
        sha256=SHA256,
    )
