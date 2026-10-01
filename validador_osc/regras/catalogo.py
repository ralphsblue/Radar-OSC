from validador_osc.dominio.resultado import DefinicaoVerificacao, TipoVerificacao

DV = DefinicaoVerificacao("dv", 1, "Dígito verificador", TipoVerificacao.ELIMINATORIA)
SITUACAO = DefinicaoVerificacao("situacao", 2, "Situação cadastral", TipoVerificacao.ELIMINATORIA)
NATUREZA = DefinicaoVerificacao("natureza", 3, "Natureza jurídica", TipoVerificacao.ELIMINATORIA)
CNAE = DefinicaoVerificacao("cnae", 4, "CNAE de relevância social", TipoVerificacao.ALERTA)
RELIGIOSA = DefinicaoVerificacao("religiosa", 4, "Organização religiosa", TipoVerificacao.ALERTA)
TEMPO = DefinicaoVerificacao("tempo", 5, "Tempo de existência", TipoVerificacao.ALERTA)
ESTABELECIMENTO = DefinicaoVerificacao(
    "estabelecimento", 2, "Estabelecimento consultado", TipoVerificacao.INFORMATIVA
)
CEPIM = DefinicaoVerificacao("cepim", 6, "CEPIM", TipoVerificacao.ELIMINATORIA)
CEIS = DefinicaoVerificacao("ceis", 7, "CEIS", TipoVerificacao.ELIMINATORIA)
CNEP = DefinicaoVerificacao("cnep", 8, "CNEP", TipoVerificacao.ELIMINATORIA)
TCU_INIDONEOS = DefinicaoVerificacao(
    "tcu_inidoneos", 9, "Licitantes inidôneos (TCU)", TipoVerificacao.ELIMINATORIA
)
CNJ_CNIA = DefinicaoVerificacao(
    "cnj_cnia", 9, "Improbidade administrativa (CNJ)", TipoVerificacao.ELIMINATORIA
)
TCU_CONTAS_IRREGULARES = DefinicaoVerificacao(
    "tcu_contas_irregulares", 9, "Contas julgadas irregulares (TCU)", TipoVerificacao.ALERTA
)
DIRIGENTES = DefinicaoVerificacao("dirigentes", 10, "Dirigentes", TipoVerificacao.ALERTA)
MAPA_OSC = DefinicaoVerificacao("mapa_osc", 11, "Mapa das OSCs", TipoVerificacao.INFORMATIVA)
CEBAS = DefinicaoVerificacao("cebas", 12, "CEBAS", TipoVerificacao.INFORMATIVA)

CATALOGO: tuple[DefinicaoVerificacao, ...] = (
    DV,
    SITUACAO,
    ESTABELECIMENTO,
    NATUREZA,
    CNAE,
    RELIGIOSA,
    TEMPO,
    CEPIM,
    CEIS,
    CNEP,
    TCU_INIDONEOS,
    CNJ_CNIA,
    TCU_CONTAS_IRREGULARES,
    DIRIGENTES,
    MAPA_OSC,
    CEBAS,
)
