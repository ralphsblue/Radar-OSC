# CNPJs de referência - sanções (CEPIM, CEIS, CNEP, TCU)

Fonte: arquivos de dados abertos do Portal da Transparência (CEPIM de 28/09/2026, CEIS e CNEP de 30/09/2026) e API ORDS de inidôneos do TCU (consultada em 30/09/2026).
Data de referência para vigência: 30/09/2026.
Vigente = sem data final ou data final >= data de referência (regra do 19.3).
Todos os casos foram conferidos com `consultar_local.py` (busca exata pelos 14 dígitos e busca pela raiz de 8 dígitos).
Antes de virar teste de regressão, cada caso precisa ser repetido na API com chave, porque o dado muda diariamente.

## Tabela

| Caso | CNPJ | Razão social | Cadastro | Datas | O que testa |
|---|---|---|---|---|---|
| CEPIM 1 | 14.112.015/0001-56 | ASSOCIACAO DOS PAIS DE BOM JESUS DO TOCANTINS | só CEPIM | sem datas no CEPIM; convênio 039516, MGI, "DESCUMPRIMENTO DE CLAUSULA/CONDICAO DO INSTR." | Verificação 6 positiva, 1 convênio, associação. Esperado: RESTRICAO / INAPTA. |
| CEPIM 2 | 05.315.570/0001-94 | ASSOCIACAO CULTURAL DEPOSITO DO TEATRO | só CEPIM | convênio 558107, Ministério da Cultura, "NAO EXECUTOU TOTALMENTE O OBJETO PACTUADO" | Verificação 6 positiva, associação cultural. |
| CEPIM 3 | 02.203.539/0001-73 | FUNDACAO ASSIS GURGACZ | só CEPIM | convênio 522242, Ministério das Comunicações, "INSTAURACAO DE TOMADA DE CONTAS ESPECIAL" | Verificação 6 positiva, fundação. |
| CEIS vigente sem fim | 00.688.001/0001-70 | ASSOCIAÇÃO DE MULHERES DE TAIPAS | só CEIS | Declaração de Inidoneidade sem prazo determinado, início 21/02/2019, sem data final; Secretaria Municipal de Gestão de São Paulo | Vigência por ausência de data final. Esperado: RESTRICAO. |
| CEIS vigente com fim futuro | 06.287.661/0001-26 | ASSOCIAÇÃO MOVIMENTO EM DEFESA DE PARIPUEIRA | só CEIS | Impedimento de contratar, 11/10/2022 a 11/10/2027; 26ª Vara Federal Palmares/PE | Vigência por data final futura. Esperado: RESTRICAO. |
| CEIS vigente que vence em breve | 02.393.242/0001-18 | ASSOCIACAO REGIONAL DA ESCOLA FAMILIA AGRICOLA DO SERTAO | só CEIS | Suspensão, 25/02/2026 a 22/11/2026; Governo da Bahia; abrangência "Na Esfera e no Poder do órgão sancionador" | Fronteira de data: RESTRICAO até 22/11/2026, OK com histórico a partir de 23/11/2026. Teste deve injetar a data de hoje. Também testa exibição de abrangência limitada. |
| CEIS expirada 1 | 03.126.200/0001-83 | ASSOCIAÇÃO PLURAL | só CEIS | Declaração de Inidoneidade "sem prazo determinado", 18/11/2019 a 18/11/2021 | Sanção expirada. Esperado: OK + histórico. A categoria diz "sem prazo" mas há data final: a regra deve usar a data, não o texto da categoria. |
| CEIS expirada 2 | 07.408.449/0001-32 | INSTITUTO CAMINHADA | só CEIS | Declaração de Inidoneidade, 07/04/2020 a 07/04/2022; Prefeitura de Senhor do Bonfim/BA | Segundo caso de sanção expirada. Esperado: OK + histórico. |
| CEIS dado inconsistente | 09.058.351/0001-28 | ASSOCIACAO RECREATIVA CULTURAL E CARNAVALESCA DE SAMBA MILLENAR | só CEIS | Declaração de Inidoneidade "com prazo determinado", início 07/03/2020, sem data final | Categoria "com prazo" sem data final. Pela regra 19.3 é vigente (RESTRICAO); o texto deve sinalizar para revisão humana. |
| CNEP | 08.928.169/0001-18 | INSTITUTO ILUMINA TERRA AÇÃO PARA DESENVOLVIMENTO SOCIAL | só CNEP | Multa de R$ 6.000,00, início 10/01/2023, sem data final; Controladoria-Geral do Município de São Paulo | Verificação 8 positiva com valor de multa. Esperado: RESTRICAO. |
| CNEP + CEIS (OSC) | 43.190.337/0001-11 | Associação Beneficente Nossa Senhora da Saúde | CEIS + CNEP | CEIS: inidoneidade 21/07/2025 a 21/07/2027. CNEP: multa R$ 44.973.168,40 e publicação extraordinária, desde 21/07/2025 | Mesmo processo gerando registros em dois cadastros; várias linhas no CNEP para o mesmo CNPJ. |
| Multi-cadastro (3 do Portal) | 53.524.534/0001-83 | ASSOCIACAO DA IRMANDADE DA SANTA CASA DE MISERICORDIA DE PACAEMBU | CEPIM + CEIS + CNEP | CEPIM: 2 convênios (Ministério da Saúde). CEIS: inidoneidade desde 11/02/2025 sem fim (CGU). CNEP: 4 registros (CGU e CGE-SP), multas de R$ 47,4 mi e R$ 35,5 mi | Único CNPJ presente nos três cadastros. Agregação de várias restrições no relatório. |
| Multi-cadastro (Portal + TCU) | 21.145.289/0001-07 | INSTITUTO MUNDIAL DE DESENVOLVIMENTO E DA CIDADANIA - IMDC | CEPIM + CEIS + TCU | CEPIM: 10 convênios (MTur e MinC). CEIS: 3 registros (2 de 2015 sem fim, 1 do TCU de 16/04/2024 a 16/04/2029). TCU: AC-001897/2019-PL, trânsito 16/04/2024, fim 16/04/2029 | Verificações 6, 7 e 9 juntas; cruzamento TCU x CEIS; CNPJ com muitas linhas no CEPIM (testa paginação T7). |
| CEIS + CNEP pela CGU | 10.564.428/0001-10 | ASSOCIACAO DOS PRODUTORES RURAIS DE POCINHOS DE BAIXO | CEIS + CNEP | CEIS: inidoneidade desde 15/06/2026 sem fim. CNEP: multa R$ 188.114,07 e publicação, desde 16/07/2026 | Caso recente (2026), abrangência "Todas as Esferas em todos os Poderes". |
| Filial sancionada, matriz limpa (T4) | 44.551.605/0005-70 | INSTITUTO GLOBAL GESTAO EM MEDICINA E SAÚDE | CEIS (só a filial) | Suspensão 25/03/2026 a 24/03/2028; Grupo Hospitalar Conceição; abrangência "No órgão sancionador" | Consultar a matriz 44.551.605/0001-46 (DV calculado; existência na Receita a confirmar na BrasilAPI) na API: se a API devolver a sanção da filial, o filtro é por raiz. No arquivo, a matriz não tem registro próprio. |
| Matriz e filiais sancionadas (T4) | 24.006.302/0001-35 | INSTITUTO DE DESENVOLVIMENTO, ENSINO E ASSISTENCIA A SAUDE - IDEAS | CEIS (matriz e filiais 0003-05, 0004-88, 0005-69, 0008-01) | Impedimento sem prazo desde 10/03/2026 (TRF4, mesmo processo, um registro por estabelecimento); a filial 0004-88 tem mais 2 registros da Prefeitura de Caxias do Sul até 06/08/2031 | Mostra que o órgão registra cada estabelecimento separadamente. Consultar a matriz na API e contar quantos registros voltam (5 se for por raiz, 1 se for exato). |
| TCU inidôneo 1 | 03.463.763/0001-67 | I T S - INSTITUTO TERRA SOCIAL | TCU + CEIS | TCU: processo 016.537/2007-6, AC-000478/2019-PL, trânsito 01/03/2023, fim 01/03/2028. CEIS: mesma sanção com origem TCU | Verificação 9 positiva, OSC. Esperado: RESTRICAO. |
| TCU inidôneo 2 | 21.145.289/0001-07 | INSTITUTO MUNDIAL DE DESENVOLVIMENTO E DA CIDADANIA - IMDC | TCU + CEIS + CEPIM | ver linha "Multi-cadastro (Portal + TCU)" | Verificação 9 positiva, OSC. |
| TCU inidôneo fora do CEIS | 08.028.648/0001-88 | ATHENA CONSTRUÇÕES E SERVIÇOS LTDA. | só TCU | processo 012.901/2013-0, trânsito 30/03/2023, fim 30/03/2028 | Não é OSC, mas prova que o CEIS não substitui a consulta ao TCU (13 dos 91 inidôneos do TCU não aparecem no CEIS). |
| Nada consta | 19.131.243/0001-97 | (OSC regular do 25.1) | nenhum | - | Sem registro em CEPIM, CEIS, CNEP nem TCU (conferido nos arquivos e no filtro ORDS do TCU). |

## Observações para a regra de comparação (T4)

- Nos arquivos, todo documento de PJ tem 14 dígitos; não existe sanção registrada só com a raiz.
- O CEIS tem 172 linhas de filial (ordem diferente de 0001), o CNEP tem 25 e o CEPIM tem 23.
- Há casos em que só a filial está sancionada (Instituto Global) e casos em que cada estabelecimento tem seu próprio registro (IDEAS).
- Recomendação provisória: RESTRICAO só para correspondência exata dos 14 dígitos; registro em outro estabelecimento da mesma raiz vira ALERTA com o detalhe da sanção, para revisão humana.
- A recomendação final depende do resultado do T4 na API com chave.

## Pessoas físicas (insumo para a verificação 10)

- CEIS tem 9.148 linhas de pessoa física e CNEP tem 28.
- Nos arquivos de download, o CPF vem completo (11 dígitos, sem máscara, 100% com dígito verificador válido) e o nome vem sempre preenchido.
- Isso permite casar dirigente por nome e pelos 6 dígitos centrais do CPF, que é o que o QSA público costuma expor (`***.123.456-**`).
- Por ser dado pessoal, as amostras versionadas em `amostras/` mascaram o CPF; o arquivo bruto completo fica só em `downloads/`.
