from validador_osc.dominio.coleta import Coleta, Falha, NaoEncontrado, Obtido
from validador_osc.dominio.resultado import Achado, Estado, RefFonte, ResultadoVerificacao
from validador_osc.dominio.tipos import PerfilMapa, SituacaoCadastral
from validador_osc.regras.catalogo import MAPA_OSC

URL_PERFIL = "https://mapaosc.ipea.gov.br/detalhar"


def _fonte(coleta: Obtido[PerfilMapa] | NaoEncontrado | Falha) -> tuple[RefFonte, ...]:
    evidencia = coleta.evidencia
    if evidencia is None:
        return ()
    return (
        RefFonte(
            fonte=evidencia.fonte,
            obtida_em=evidencia.recebida_em,
            de_cache=evidencia.de_cache,
            evidencia_id=evidencia.id,
            sha256=evidencia.sha256,
        ),
    )


def _indice(perfil: PerfilMapa) -> str:
    if perfil.indice_preenchimento is None:
        return ""
    return f" Índice de preenchimento: {perfil.indice_preenchimento:.0f} de 100."


def _situacao_no_mapa(perfil: PerfilMapa) -> str:
    codigo = perfil.situacao_cadastral
    if codigo is None or codigo == SituacaoCadastral.ATIVA:
        return ""
    return f" O Mapa registra a situação cadastral código {codigo}, diferente de ativa."


def verificar_mapa_osc(coleta: Coleta[PerfilMapa]) -> ResultadoVerificacao:
    fontes = _fonte(coleta)
    match coleta:
        case Falha(motivo=motivo):
            return ResultadoVerificacao(
                MAPA_OSC,
                Estado.INDISPONIVEL,
                f"O Mapa das OSCs (Ipea) não respondeu ({motivo}).",
                fontes=fontes,
            )
        case NaoEncontrado():
            return ResultadoVerificacao(
                MAPA_OSC,
                Estado.ALERTA,
                "CNPJ não encontrado no Mapa das OSCs (Ipea), que cadastra automaticamente as OSCs ativas. "
                "Pode indicar que a entidade não é reconhecida como OSC; "
                "confira a natureza jurídica e o estatuto.",
                fontes=fontes,
                situacao="AUSENTE",
            )
        case Obtido(dados=perfil):
            achado = (
                Achado(
                    "perfil_mapa",
                    {
                        "id_osc": perfil.id_osc,
                        "url": f"{URL_PERFIL}/{perfil.id_osc}",
                        "indice_preenchimento": perfil.indice_preenchimento,
                        "campos_autodeclarados": list(perfil.campos_autodeclarados),
                    },
                ),
            )
            extras = _indice(perfil) + _situacao_no_mapa(perfil)
            if perfil.preenchido_pela_osc:
                return ResultadoVerificacao(
                    MAPA_OSC,
                    Estado.OK,
                    "Presente no Mapa das OSCs, com perfil completado pela própria organização." + extras,
                    achado,
                    fontes,
                    "PREENCHIDO",
                )
            return ResultadoVerificacao(
                MAPA_OSC,
                Estado.OK,
                "Presente no Mapa das OSCs só com dados automáticos; a organização pode completar o perfil "
                "(projetos, parcerias, governança) para dar mais transparência." + extras,
                achado,
                fontes,
                "AUTOMATICO",
            )
