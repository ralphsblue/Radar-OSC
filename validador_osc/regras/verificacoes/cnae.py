from validador_osc.dominio.resultado import Achado, Estado, ResultadoVerificacao
from validador_osc.regras.catalogo import CNAE, RELIGIOSA
from validador_osc.regras.comum import CadastroObtido
from validador_osc.regras.tabelas.cnae import (
    AvaliacaoCnae,
    ClassificacaoCnae,
    Faixa,
    TabelaCnae,
    descrever_subclasse,
    formatar_cnae,
)

_ROTULO_FAIXA = {Faixa.ALTA: "alta", Faixa.MEDIA: "média", Faixa.BAIXA: "baixa"}


def _achado(tabela: TabelaCnae, classificacao: ClassificacaoCnae, papel: str) -> Achado:
    return Achado(
        "cnae",
        {
            "papel": papel,
            "codigo": formatar_cnae(classificacao.subclasse),
            "descricao": descrever_subclasse(tabela, classificacao.subclasse),
            "faixa": classificacao.faixa.value,
            "regra": classificacao.regra_aplicada,
        },
    )


def verificar_cnae(
    obtido: CadastroObtido, tabela: TabelaCnae, avaliacao: AvaliacaoCnae | None
) -> ResultadoVerificacao:
    fontes = (obtido.fonte,)
    if avaliacao is None:
        return ResultadoVerificacao(
            CNAE, Estado.INDISPONIVEL, "CNAE principal não informado na base.", fontes=fontes
        )
    achados = (
        _achado(tabela, avaliacao.principal, "principal"),
        *(_achado(tabela, c, "secundario") for c in avaliacao.secundarios),
    )
    principal = formatar_cnae(avaliacao.principal.subclasse)
    if avaliacao.alerta_cnae:
        return ResultadoVerificacao(
            CNAE,
            Estado.ALERTA,
            f"Nenhuma atividade cadastrada (principal {principal}) tem relação direta com relevância "
            "pública e social. Confira o estatuto.",
            achados,
            fontes,
            situacao=avaliacao.melhor_faixa.value,
        )
    return ResultadoVerificacao(
        CNAE,
        Estado.OK,
        f"Aderência {_ROTULO_FAIXA[avaliacao.melhor_faixa]} a atividades de relevância social "
        f"(principal {principal}).",
        achados,
        fontes,
        situacao=avaliacao.melhor_faixa.value,
    )


def verificar_religiosa(obtido: CadastroObtido, avaliacao: AvaliacaoCnae | None) -> ResultadoVerificacao:
    fontes = (obtido.fonte,)
    if avaliacao is None or not avaliacao.gatilho_religioso:
        return ResultadoVerificacao(
            RELIGIOSA, Estado.OK, "Não se aplica: não é organização religiosa.", fontes=fontes
        )
    if avaliacao.alerta_religiosa:
        return ResultadoVerificacao(
            RELIGIOSA,
            Estado.ALERTA,
            "Organização religiosa sem atividade social cadastrada além da religiosa. A Lei 13.019/2014 "
            "(art. 2º, I, c) só admite as que atuam em interesse público e social distinto do religioso.",
            fontes=fontes,
        )
    return ResultadoVerificacao(
        RELIGIOSA,
        Estado.OK,
        "Organização religiosa com atividade social cadastrada (art. 2º, I, c).",
        fontes=fontes,
    )
