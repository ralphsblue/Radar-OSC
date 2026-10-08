"""Definição dos casos de referência (spec 25.1 ampliado).

Cada caso tem o CNPJ como o usuário digitaria e o que ele testa.
`variantes` são execuções extras do mesmo CNPJ com outra data de referência ou
outro parâmetro `esfera` (D6), para testar fronteiras.
"""

from __future__ import annotations

DATA_REFERENCIA = "2026-10-01"

CASOS: list[dict] = [
    # --- verificação 1 do spec (DV) e entrada
    {
        "id": "C01",
        "cnpj": "19131243000197",
        "titulo": "OSC regular",
        "testa": "Caminho feliz: associação ativa, CNAE ALTA, mais de 3 anos, sem sanções, presente no Mapa.",
    },
    {
        "id": "C02",
        "cnpj": "19131243000198",
        "titulo": "DV inválido",
        "testa": "`dv`: último dígito errado (esperado 97); nenhuma fonte é consultada; status CNPJ_INVALIDO (Q3).",
    },
    {
        "id": "C03",
        "cnpj": "11111111111180",
        "titulo": "Base repetida com DV que confere",
        "testa": "`dv`: base de 12 posições repetida (D11), mesmo com os DVs calculados batendo; status CNPJ_INVALIDO (Q3).",
    },
    {
        "id": "C04",
        "cnpj": "12ABC34501DE3",
        "titulo": "Formato inválido (13 caracteres)",
        "testa": "`dv`: formato; status CNPJ_INVALIDO (Q3).",
    },
    {
        "id": "C05",
        "cnpj": "12ABC34501DE35",
        "titulo": "Alfanumérico válido (exemplo oficial)",
        "testa": "D4 e Q2: DV aceita alfanumérico, consultas ficam fora do MVP (NAO_VERIFICADO), status INCONCLUSIVA.",
    },
    {
        "id": "C06",
        "cnpj": "00000000E08G12",
        "titulo": "Alfanumérico real (BB filial)",
        "testa": "D4 com um CNPJ alfanumérico que existe de fato (OpenCNPJ responde).",
    },
    {
        "id": "C07",
        "cnpj": "94580730000152",
        "titulo": "CNPJ inexistente com DV válido",
        "testa": "`situacao` INDISPONIVEL com motivo NAO_ENCONTRADO (Q26); TCU devolveria NADA_CONSTA com seCnpjEncontradoNaBaseTcu false (D13).",
    },
    # --- verificação 2 do spec (situação)
    {
        "id": "C08",
        "cnpj": "08942107000160",
        "titulo": "Associação BAIXADA",
        "testa": "`situacao`: situação 8, motivo extinção.",
    },
    {
        "id": "C09",
        "cnpj": "11468674000131",
        "titulo": "Associação INAPTA",
        "testa": "`situacao`: situação 4.",
    },
    {
        "id": "C10",
        "cnpj": "03728829000101",
        "titulo": "Associação SUSPENSA",
        "testa": "`situacao`: situação 3.",
    },
    # --- verificação 3 do spec (natureza)
    {
        "id": "C11",
        "cnpj": "00000000000191",
        "titulo": "Natureza não elegível (Banco do Brasil)",
        "testa": "`natureza`: 2038 Sociedade de Economia Mista.",
    },
    {
        "id": "C12",
        "cnpj": "00108217000110",
        "titulo": "Organização religiosa 3220 só com CNAE religioso",
        "testa": "`natureza` elegível + verificação `religiosa` (D7, Q25).",
    },
    {
        "id": "C13",
        "cnpj": "03128347000102",
        "titulo": "Igreja como associação (3999) com CNAE 9491",
        "testa": "`religiosa` pelo CNAE principal 94.91-0 (D7, ORIENTADOR Q15).",
    },
    {
        "id": "C14",
        "cnpj": "04311762000160",
        "titulo": "Cooperativa 2143",
        "testa": "`natureza`: REVISÃO MANUAL (ALERTA); CNAE com zero à esquerda.",
    },
    {
        "id": "C15",
        "cnpj": "08055129000109",
        "titulo": "Organização Social 3301",
        "testa": "`natureza`: REVISÃO MANUAL (ALERTA).",
    },
    {
        "id": "C16",
        "cnpj": "38894796000146",
        "titulo": "Fundação privada com perfil do Mapa preenchido (Fundação Abrinq)",
        "testa": "Natureza 3069 e `mapa_osc` com perfil preenchido pela OSC.",
    },
    # --- verificação 4 do spec (CNAE)
    {
        "id": "C17",
        "cnpj": "03308444000187",
        "titulo": "Associação com CNAE comercial (BAIXA)",
        "testa": "`cnae`: nenhum CNAE em ALTA ou MEDIA.",
    },
    # --- verificação 5 do spec (tempo)
    {
        "id": "C18",
        "cnpj": "65478551000100",
        "titulo": "Associação recente (menos de 1 ano)",
        "testa": "`tempo`: não atinge nenhuma esfera.",
        "variantes": [{"esfera": "municipio"}],
    },
    {
        "id": "C19",
        "cnpj": "58323085000129",
        "titulo": "Associação entre 1 e 2 anos",
        "testa": "`tempo`: atinge só municípios.",
        "variantes": [{"esfera": "municipio"}, {"esfera": "estado"}],
    },
    {
        "id": "C20",
        "cnpj": "53071884000131",
        "titulo": "Associação entre 2 e 3 anos",
        "testa": "`tempo`: atinge municípios e estados.",
        "variantes": [{"esfera": "estado"}, {"esfera": "uniao"}],
    },
    {
        "id": "C21",
        "cnpj": "62988692000185",
        "titulo": "Associação com exatamente 1 ano na data de referência",
        "testa": "Fronteira do art. 33, V, a: início 01/10/2025.",
        "variantes": [{"esfera": "municipio"}, {"esfera": "municipio", "data_referencia": "2026-09-30"}],
    },
    {
        "id": "C22",
        "cnpj": "57946201000101",
        "titulo": "Associação a 1 dia de completar 2 anos",
        "testa": "Fronteira: início 02/10/2024.",
        "variantes": [{"esfera": "estado"}, {"esfera": "estado", "data_referencia": "2026-10-02"}],
    },
    # --- filiais (D5)
    {
        "id": "C23",
        "cnpj": "62779145000270",
        "titulo": "Filial ativa com matriz ativa (Santa Casa de SP)",
        "testa": "D5: resolve para a matriz; situação das duas; tempo da matriz.",
    },
    {
        "id": "C24",
        "cnpj": "04955882000523",
        "titulo": "Filial baixada com matriz ativa (Instituto GRPCOM)",
        "testa": "D5: filial baixada, matriz ativa; data_situacao_cadastral '0' na matriz (OpenCNPJ).",
    },
    {
        "id": "C25",
        "cnpj": "62779145000190",
        "titulo": "Matriz da Santa Casa de SP (CEBAS em renovação tempestiva)",
        "testa": "`cebas` com renovação tempestiva pendente no SisCEBAS.",
    },
    {
        "id": "C26",
        "cnpj": "24006302000488",
        "titulo": "Matriz com ordem 0004 (IDEAS) e CEIS vigente",
        "testa": "D5: estabelecimento 0004 é a matriz; a 0001 é filial. Sanção própria vigente.",
    },
    {
        "id": "C27",
        "cnpj": "24006302000135",
        "titulo": "Filial com ordem 0001 (IDEAS)",
        "testa": "D5: ordem 0001 que não é matriz; cnpj_da_matriz devolve o próprio CNPJ.",
    },
    # --- sanções em entidades ATIVAS (o fluxo chega ao fan-out)
    {"id": "C28", "cnpj": "02203539000173", "titulo": "CEPIM (fundação ativa)", "testa": "`cepim` positiva."},
    {
        "id": "C29",
        "cnpj": "00688001000170",
        "titulo": "CEIS vigente sem data final",
        "testa": "`ceis`: vigência por ausência de data final.",
    },
    {
        "id": "C30",
        "cnpj": "30994499000160",
        "titulo": "CEIS vigente com fim futuro",
        "testa": "`ceis` com data final no futuro.",
    },
    {
        "id": "C31",
        "cnpj": "02393242000118",
        "titulo": "CEIS vencendo em 22/11/2026",
        "testa": "Fronteira de vigência do CEIS (data injetada).",
        "variantes": [{"data_referencia": "2026-11-22"}, {"data_referencia": "2026-11-23"}],
    },
    {
        "id": "C32",
        "cnpj": "07408449000132",
        "titulo": "CEIS expirado",
        "testa": "`ceis`: OK com histórico; TCU diz CONSTAM_REGISTROS (D18).",
    },
    {
        "id": "C33",
        "cnpj": "09058351000128",
        "titulo": "CEIS 'com prazo determinado' sem data final",
        "testa": "Dado inconsistente na fonte: vigente pela regra de data.",
    },
    {
        "id": "C34",
        "cnpj": "13144375000177",
        "titulo": "CNEP",
        "testa": "`cnep` com multa e publicação extraordinária (Q16 provisório: ALERTA).",
    },
    {
        "id": "C35",
        "cnpj": "05051898000140",
        "titulo": "Ocorrência no CNIA (CNJ)",
        "testa": "`cnj_cnia` positiva com a mesma decisão no CEIS de origem CNJ (Q19, Q42).",
    },
    {
        "id": "C36",
        "cnpj": "01081476000167",
        "titulo": "CNIA + dirigente com sanção (nome e CPF)",
        "testa": "`ceis`, `cnj_cnia` e `dirigentes` (D15) juntas.",
    },
    {
        "id": "C37",
        "cnpj": "44551605000570",
        "titulo": "Sanção só na filial, consulta pela filial",
        "testa": "D5: sanção da própria filial consultada.",
    },
    {
        "id": "C38",
        "cnpj": "44551605000146",
        "titulo": "Sanção só na filial, consulta pela matriz",
        "testa": "Q20: registro em outro estabelecimento da mesma raiz achado pela busca por raiz no CSV local.",
    },
    # --- sanções em entidades NÃO ATIVAS (sem parada antecipada, Q1)
    {
        "id": "C39",
        "cnpj": "06287661000126",
        "titulo": "INAPTA com CEIS vigente, CNIA e dirigente",
        "testa": "Q1: sem parada antecipada, o relatório mostra CEIS, CNIA e dirigente de entidade já INAPTA.",
    },
    {
        "id": "C40",
        "cnpj": "03463763000167",
        "titulo": "INAPTA com inidoneidade TCU",
        "testa": "Único tipo de OSC inidônea no TCU; Q1 mostra `tcu_inidoneos` mesmo com a entidade INAPTA.",
    },
    {
        "id": "C41",
        "cnpj": "53524534000183",
        "titulo": "INAPTA com CEPIM + CEIS + CNEP (Santa Casa de Pacaembu)",
        "testa": "Q1 com várias restrições; CNEP de multa (Q16).",
    },
    {
        "id": "C42",
        "cnpj": "21145289000107",
        "titulo": "INAPTA com CEPIM + CEIS + TCU (IMDC)",
        "testa": "Q1 com `cepim`, `ceis` e `tcu_inidoneos`.",
    },
    {
        "id": "C43",
        "cnpj": "14112015000156",
        "titulo": "BAIXADA com CEPIM",
        "testa": "Q1: CEPIM de entidade baixada.",
    },
    {
        "id": "C44",
        "cnpj": "03126200000183",
        "titulo": "INAPTA com CEIS expirado",
        "testa": "Q1: categoria 'sem prazo' com data final passada (OK com histórico).",
    },
    {
        "id": "C45",
        "cnpj": "08928169000118",
        "titulo": "INAPTA com CNEP",
        "testa": "Q1 com CNEP de multa (Q16).",
    },
    {
        "id": "C46",
        "cnpj": "43337682000135",
        "titulo": "INAPTA com CNIA + CEIS + CEPIM (AVAPE)",
        "testa": "Q1 com CNIA (Q19) e sanção em outro estabelecimento (Q20).",
    },
    # --- verificação 11 e 12 do spec
    {
        "id": "C47",
        "cnpj": "50798453000183",
        "titulo": "CEBAS Saúde ativo (Santa Casa de Cerquilho)",
        "testa": "`cebas` OK pelo SisCEBAS Saúde.",
    },
    {
        "id": "C48",
        "cnpj": "00001297000100",
        "titulo": "CEBAS não vigente (concessão indeferida)",
        "testa": "`cebas`: último ato é indeferimento.",
    },
    {
        "id": "C49",
        "cnpj": "26447003000161",
        "titulo": "Associação profissional (CNAE 94.12) com CEPIM",
        "testa": "CNAE BAIXA explícita e presença no Mapa de associação de categoria.",
    },
]

# Ausente do Mapa: escolhido depois da coleta (ver montar_casos.py, caso C42).
CANDIDATOS_AUSENTE_MAPA: list[str] = []
