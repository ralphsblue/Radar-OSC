from validador_osc.cnpj import cnpj_da_matriz
from validador_osc.cnpj import formatar as formatar_cnpj
from validador_osc.dominio.resultado import Achado, Contexto, Estado, ResultadoVerificacao
from validador_osc.dominio.tipos import SituacaoCadastral
from validador_osc.regras.catalogo import ESTABELECIMENTO, SITUACAO
from validador_osc.regras.entidade import Entidade, SituacaoMatriz
from validador_osc.regras.verificacoes.cadastro import avaliar_situacao, data_br


def verificar_situacao_entidade(entidade: Entidade, contexto: Contexto) -> ResultadoVerificacao:
    match entidade.situacao_matriz:
        case SituacaoMatriz.OBTIDA if entidade.matriz is not None:
            resultado = avaliar_situacao(entidade.matriz, contexto, "Matriz: ")
            return ResultadoVerificacao(
                resultado.definicao,
                resultado.estado,
                resultado.mensagem,
                resultado.achados,
                entidade.fontes,
                resultado.situacao,
            )
        case SituacaoMatriz.INDISPONIVEL:
            return ResultadoVerificacao(
                SITUACAO,
                Estado.INDISPONIVEL,
                "A consulta partiu de uma filial e os dados da matriz não puderam ser obtidos. "
                "A situação da entidade não foi confirmada; tente de novo em alguns minutos.",
                fontes=entidade.fontes,
                situacao="MATRIZ_INDISPONIVEL",
            )
        case _:
            return avaliar_situacao(entidade.consultado, contexto)


def verificar_estabelecimento(entidade: Entidade) -> ResultadoVerificacao:
    consultado = entidade.consultado.cadastro
    fontes = entidade.fontes
    if not entidade.eh_filial:
        return ResultadoVerificacao(
            ESTABELECIMENTO, Estado.OK, "Consulta feita pelo CNPJ da matriz.", fontes=fontes
        )

    filial = formatar_cnpj(consultado.cnpj)
    match entidade.situacao_matriz:
        case SituacaoMatriz.NAO_IDENTIFICADA:
            provavel = cnpj_da_matriz(consultado.cnpj)
            tentativa = (
                "tem a ordem 0001, mas não é a matriz"
                if provavel == consultado.cnpj
                else f"a matriz não foi identificada pelo CNPJ {formatar_cnpj(provavel)}"
            )
            return ResultadoVerificacao(
                ESTABELECIMENTO,
                Estado.ALERTA,
                f"O CNPJ {filial} é de uma filial e {tentativa}. Informe o CNPJ da matriz para avaliar "
                "a entidade; nesta consulta a avaliação usa os dados da filial.",
                (Achado("matriz_nao_identificada", {"cnpj_tentado": provavel}),),
                fontes,
                "MATRIZ_NAO_IDENTIFICADA",
            )
        case SituacaoMatriz.INDISPONIVEL:
            return ResultadoVerificacao(
                ESTABELECIMENTO,
                Estado.OK,
                f"A consulta partiu da filial {filial}; os dados da matriz não puderam ser obtidos.",
                fontes=fontes,
                situacao="FILIAL",
            )
        case _:
            matriz = entidade.avaliado.cadastro
            achado = (Achado("filial", {"cnpj_filial": consultado.cnpj, "cnpj_matriz": matriz.cnpj}),)
            situacao_filial = consultado.situacao.name
            desde = f" desde {data_br(consultado.situacao_data)}" if consultado.situacao_data else ""
            motivo = (
                f" (motivo: {consultado.motivo_descricao})"
                if consultado.motivo_codigo and consultado.motivo_descricao
                else ""
            )
            if (
                consultado.situacao is not SituacaoCadastral.ATIVA
                and matriz.situacao is SituacaoCadastral.ATIVA
            ):
                return ResultadoVerificacao(
                    ESTABELECIMENTO,
                    Estado.ALERTA,
                    f"O estabelecimento informado ({filial}, filial) está {situacao_filial}{desde}{motivo}; "
                    f"a entidade (matriz {formatar_cnpj(matriz.cnpj)}) está ATIVA. Confira se o CNPJ do "
                    "edital ou do contrato está correto.",
                    achado,
                    fontes,
                    "FILIAL_NAO_ATIVA",
                )
            return ResultadoVerificacao(
                ESTABELECIMENTO,
                Estado.OK,
                f"A consulta partiu da filial {filial} ({situacao_filial}); a entidade foi avaliada pela "
                f"matriz {formatar_cnpj(matriz.cnpj)}.",
                achado,
                fontes,
                "FILIAL",
            )
