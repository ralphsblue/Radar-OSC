from datetime import UTC, date, datetime
from typing import Any

from validador_osc.dominio.resultado import Avaliacao, Estado, RefFonte, ResultadoVerificacao, StatusFinal
from validador_osc.regras.catalogo import CEIS, DV, SITUACAO
from validador_osc.servico.documento import CONSULTA_MANUAL, montar_documento


def _documento(*verificacoes: ResultadoVerificacao) -> dict[str, Any]:
    return montar_documento(
        consulta_id="id",
        cnpj="19131243000197",
        cadastro=None,
        matriz=None,
        esfera=None,
        data_referencia=date(2026, 10, 5),
        consultado_em=datetime(2026, 10, 5, tzinfo=UTC),
        avaliacao=Avaliacao(StatusFinal.APTA, (), (), verificacoes),
        versao_app="0",
        versao_regras="sha256:0",
    )


def test_cada_verificacao_com_fonte_tem_link_de_consulta_manual() -> None:
    documento = _documento(
        ResultadoVerificacao(CEIS, Estado.OK, "ok"), ResultadoVerificacao(DV, Estado.OK, "ok")
    )
    verificacoes = {v["id"]: v for v in documento["verificacoes"]}
    assert verificacoes["ceis"]["consulta_manual"] == CONSULTA_MANUAL["ceis"]
    assert "consulta_manual" not in verificacoes["dv"]


def test_fontes_consultadas_resumem_a_base_mais_recente_com_link() -> None:
    antiga = RefFonte("cgu_ceis", data_base=date(2026, 10, 1))
    nova = RefFonte("cgu_ceis", data_base=date(2026, 10, 4))
    cadastro = RefFonte("opencnpj", data_base=date(2026, 9, 14))
    documento = _documento(
        ResultadoVerificacao(CEIS, Estado.OK, "ok", fontes=(antiga, nova)),
        ResultadoVerificacao(SITUACAO, Estado.OK, "ok", fontes=(cadastro, RefFonte("desconhecida"))),
    )
    assert documento["fontes_consultadas"] == [
        {
            "fonte": "cgu_ceis",
            "data_base": "2026-10-04",
            "link": "https://portaldatransparencia.gov.br/download-de-dados/ceis",
        },
        {"fonte": "opencnpj", "data_base": "2026-09-14", "link": "https://opencnpj.org/"},
    ]
