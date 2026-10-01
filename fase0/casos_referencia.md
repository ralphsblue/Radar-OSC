# Casos de referência do validador de OSC

Conjunto de CNPJs do spec 25.1, ampliado com os casos das fichas da Fase 0 e das decisões D1 a D20.
Cada caso traz o resultado esperado de cada uma das 16 verificações do catálogo (Q25) e o status final.
Ele é a fonte do teste de regressão e E2E do motor; a versão para máquina é `casos_referencia.json`.

- Versão 1.2 do conjunto, alinhada ao spec 1.2. Data de referência das regras: 01/10/2026.
- Coleta das fontes: 2026-10-01 03:06 a 2026-10-01 03:24 (UTC).
- Gerado por `fase0/casos/montar_casos.py` a partir das respostas reais salvas em `fase0/casos/respostas/` e das bases locais da Fase 0.
- Não editar à mão: alterar a regra no script e gerar de novo.

## Catálogo de verificações (Q25)

| Coluna | id | Spec | Nome | Tipo |
|---|---|---|---|---|
| dv | `dv` | 1 | Dígito verificador | ELIMINATORIA |
| sit | `situacao` | 2 | Situação cadastral | ELIMINATORIA |
| nat | `natureza` | 3 | Natureza jurídica | ELIMINATORIA |
| cnae | `cnae` | 4 | CNAE de relevância social | ALERTA |
| rel | `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | ALERTA |
| tempo | `tempo` | 5 | Tempo de existência | ALERTA |
| estab | `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | INFORMATIVA |
| cepim | `cepim` | 6 | CEPIM | ELIMINATORIA |
| ceis | `ceis` | 7 | CEIS | ELIMINATORIA |
| cnep | `cnep` | 8 | CNEP | ELIMINATORIA |
| inid | `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | ELIMINATORIA |
| cnia | `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | ELIMINATORIA |
| ctas | `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | ALERTA |
| dir | `dirigentes` | 10 | Dirigentes (QSA) | ALERTA |
| mapa | `mapa_osc` | 11 | Mapa das OSCs | INFORMATIVA |
| cebas | `cebas` | 12 | CEBAS | INFORMATIVA |

## Fontes consultadas

| Uso | Fonte |
|---|---|
| cadastral | OpenCNPJ https://api.opencnpj.org/{cnpj} (espelho de 15/09/2026) |
| cepim_ceis_cnep | CSV diário oficial da CGU (CEIS e CNEP de 30/09/2026, CEPIM de 28/09/2026), observação principal com busca por raiz (D14); OpenCNPJ ?datasets=ceis,cepim,cnep como observação adicional |
| tcu | Consulta Consolidada https://certidoes-apf.apps.tcu.gov.br/api/rest/publico/certidoes/{cnpj}?seEmitirPDF=false |
| tcu_inidoneos_lista | Plataforma de Certidões do TCU, CSV de inidôneos de 30/09/2026 (Q34) |
| tcu_contas_irregulares | Plataforma de Certidões do TCU, CSV de responsáveis com contas irregulares de 01/10/2026 (Q21, provisório) |
| mapa_osc | https://mapaosc.ipea.gov.br/api/api/busca/cnpj/{cnpj sem zeros} |
| cebas | SisCEBAS Saúde (lista de 30/09/2026), planilhas MDS 24/10/2024 e MEC 2023 do Mapa das OSCs, DOU jun a ago/2026 (falta 12/2023 a 05/2026, X17) |
| dirigentes | QSA do OpenCNPJ x pessoas físicas do CSV CEIS e CNEP de 30/09/2026, das listas do TCU de contas irregulares e inabilitados de 01/10/2026 (Plataforma de Certidões) e da relação do TCE-SP de contas do Terceiro Setor julgadas irregulares (planilha com dados até 01/09/2026); D15, opção C do Q8 |

## Regras adotadas na geração

- **status_final**: CNPJ_INVALIDO se `dv` falhar (Q3); senão INAPTA se eliminatória em RESTRICAO; senão INCONCLUSIVA se eliminatória INDISPONIVEL ou NAO_VERIFICADO (Q2); senão APTA_COM_RESSALVAS se qualquer verificação em ALERTA (inclui `mapa_osc`, D2); senão APTA. `motivos` lista os ids que decidiram; `avisos` lista as não eliminatórias INDISPONIVEL, mostradas em destaque (Q5).
- **sem_parada_antecipada**: Com DV válido e cadastro encontrado, todas as verificações são avaliadas, inclusive de entidade já INAPTA (Q1). CNPJ não encontrado: fan-out não roda (Q26).
- **vigencia_sancao**: Vigente se sem data final ou data final >= data de referência (Q30); datas do CSV local e do OpenCNPJ ?datasets=; TCU CONSTAM_REGISTROS com tudo expirado não é divergência (D18); registro só no TCU segue Q35.
- **idade_das_bases**: Medida na data da coleta (01/10/2026), com os limites do Q6; as variantes mudam só a data de referência das vigências.
- `natureza` em REVISÃO MANUAL e natureza sem mapeamento viram ALERTA; o fluxo continua.
- Filial (D5, Q4, Q27, Q28): `situacao` avalia a entidade (matriz); `estabelecimento` avisa da filial não ativa ou da matriz não identificada; natureza, tempo e QSA da matriz; CNAEs dos dois; sanções da filial, da matriz e da raiz (Q20); Mapa pela matriz; CEBAS pela matriz e pelo consultado.
- CEBAS (D16, Q31, Q40): SisCEBAS Saúde primeiro; depois aba de situação da planilha MDS; aba de processos não é decisão. O campo `situacao_cebas` traz o rótulo próprio.

## Regras provisórias e pendentes

Os esperados marcados com estes códigos (coluna 'Depende de' e campo `depende_de` do JSON) podem mudar se a regra mudar.
Toda `tcu_contas_irregulares` existe por [ORIENTADOR Q21] e toda `dirigentes` com achado ou homônimo depende de [ORIENTADOR Q22]; no resumo esses dois marcadores só aparecem quando há achado.
As regras do orientador ficam em `REGRAS_ORIENTADOR` no início de `montar_casos.py`; trocar a regra é mudar um valor e gerar de novo.

| Marcador | Regra adotada agora | Parâmetro |
|---|---|---|
| [ORIENTADOR Q14] | Tabela de natureza jurídica (revisão manual de 214-3, 330-1, 320-4; 307-7 não elegível). | - |
| [ORIENTADOR Q15] | Faixas CNAE dos 8 pontos de fase0/cnae/proposta.md e gatilho religioso pelo CNAE 94.91-0. | - |
| [ORIENTADOR Q16] | CNEP: multa e publicação extraordinária vigentes = ALERTA; demais categorias = RESTRICAO. | `Q16_cnep_multa` = `alerta` |
| [ORIENTADOR Q17] | Abrangência limitada continua RESTRICAO, com a abrangência em destaque. | `Q17_abrangencia_limitada` = `restricao` |
| [ORIENTADOR Q18] | CEPIM = RESTRICAO em qualquer esfera. | `Q18_cepim` = `qualquer_esfera` |
| [ORIENTADOR Q19] | CNIA = RESTRICAO só com proibição vigente achada no CEIS pelo processo; senão ALERTA. | `Q19_cnia` = `vigencia` |
| [ORIENTADOR Q20] | Sanção em outro estabelecimento da raiz = RESTRICAO, indicando o estabelecimento. | `Q20_raiz` = `restricao` |
| [ORIENTADOR Q21] | Verificação `tcu_contas_irregulares` (OSC na lista do TCU com trânsito em julgado nos últimos 8 anos) = ALERTA. | `Q21_contas_irregulares_osc` = `alerta` |
| [ORIENTADOR Q22] | Dirigentes: só sanção vigente (CEIS, CNEP, TCU inabilitados) ou trânsito em julgado nos últimos 8 anos (TCU contas irregulares, TCE-SP) e categoria que é hipótese do art. 39. | `Q22_dirigentes` = `ficha` |
| [ORIENTADOR Q23] | Tempo desde data_inicio_atividade, citando a data da situação. | `Q23_tempo` = `inicio_atividade` |
| [ORIENTADOR Q24] | CEBAS vencido sem ato novo = possível renovação, sem limite, com a idade no texto. | `Q24_cebas_limite_anos` = `None` |
| [PENDENTE X17] | Esperado de CEBAS MDS/MEC sem os atos do DOU de 12/2023 a 05/2026 (Q39); gerar de novo depois da carga. | - |

## Resumo

Legenda: `OK` ok, `R` restrição, `A` alerta, `I` indisponível, `-` não verificado.

| Caso | CNPJ | O que testa | dv | sit | nat | cnae | rel | tempo | estab | cepim | ceis | cnep | inid | cnia | ctas | dir | mapa | cebas | Status final esperado | Depende de |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C01 | 19.131.243/0001-97 | OSC regular | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | - | **APTA** | - |
| C02 | 19.131.243/0001-98 | DV inválido | R | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | **CNPJ INVÁLIDO** | - |
| C03 | 11.111.111/1111-80 | Base repetida com DV que confere | R | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | **CNPJ INVÁLIDO** | - |
| C04 | 12ABC34501DE3 | Formato inválido (13 caracteres) | R | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | **CNPJ INVÁLIDO** | - |
| C05 | 12.ABC.345/01DE-35 | Alfanumérico válido (exemplo oficial) | OK | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | **INCONCLUSIVA** | - |
| C06 | 00.000.000/E08G-12 | Alfanumérico real (BB filial) | OK | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | **INCONCLUSIVA** | - |
| C07 | 94.580.730/0001-52 | CNPJ inexistente com DV válido | OK | I | - | - | - | - | - | - | - | - | - | - | - | - | - | - | **INCONCLUSIVA** | - |
| C08 | 08.942.107/0001-60 | Associação BAIXADA | OK | R | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | A | - | **INAPTA** | - |
| C09 | 11.468.674/0001-31 | Associação INAPTA | OK | R | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | - | **INAPTA** | - |
| C10 | 03.728.829/0001-01 | Associação SUSPENSA | OK | R | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | - | **INAPTA** | - |
| C11 | 00.000.000/0001-91 | Natureza não elegível (Banco do Brasil) | OK | OK | R | A | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | A | - | **INAPTA** | - |
| C12 | 00.108.217/0001-10 | Organização religiosa 3220 só com CNAE religioso | OK | OK | OK | OK | A | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | - | **APTA COM RESSALVAS** | - |
| C13 | 03.128.347/0001-02 | Igreja como associação (3999) com CNAE 9491 | OK | OK | OK | OK | A | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | - | **APTA COM RESSALVAS** | O-Q15 |
| C14 | 04.311.762/0001-60 | Cooperativa 2143 | OK | OK | A | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | A | - | **APTA COM RESSALVAS** | O-Q14, O-Q15 |
| C15 | 08.055.129/0001-09 | Organização Social 3301 | OK | OK | A | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | - | **APTA COM RESSALVAS** | O-Q14 |
| C16 | 38.894.796/0001-46 | Fundação privada com perfil do Mapa preenchido (Fundação Abrinq) | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | **APTA** | O-Q24, P-X17 |
| C17 | 03.308.444/0001-87 | Associação com CNAE comercial (BAIXA) | OK | OK | OK | A | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | - | **APTA COM RESSALVAS** | O-Q23 |
| C18 | 65.478.551/0001-00 | Associação recente (menos de 1 ano) | OK | OK | OK | OK | OK | A | OK | OK | OK | OK | OK | OK | OK | OK | OK | - | **APTA COM RESSALVAS** | - |
| C19 | 58.323.085/0001-29 | Associação entre 1 e 2 anos | OK | OK | OK | OK | OK | A | OK | OK | OK | OK | OK | OK | OK | OK | OK | - | **APTA COM RESSALVAS** | - |
| C20 | 53.071.884/0001-31 | Associação entre 2 e 3 anos | OK | OK | OK | OK | OK | A | OK | OK | OK | OK | OK | OK | OK | OK | OK | - | **APTA COM RESSALVAS** | - |
| C21 | 62.988.692/0001-85 | Associação com exatamente 1 ano na data de referência | OK | OK | OK | OK | OK | A | OK | OK | OK | OK | OK | OK | OK | OK | OK | - | **APTA COM RESSALVAS** | - |
| C22 | 57.946.201/0001-01 | Associação a 1 dia de completar 2 anos | OK | OK | OK | OK | OK | A | OK | OK | OK | OK | OK | OK | OK | OK | OK | - | **APTA COM RESSALVAS** | O-Q23 |
| C23 | 62.779.145/0002-70 | Filial ativa com matriz ativa (Santa Casa de SP) | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | **APTA** | O-Q24, P-X17 |
| C24 | 04.955.882/0005-23 | Filial baixada com matriz ativa (Instituto GRPCOM) | OK | OK | OK | OK | OK | OK | A | OK | OK | OK | OK | OK | OK | OK | OK | - | **APTA COM RESSALVAS** | - |
| C25 | 62.779.145/0001-90 | Matriz da Santa Casa de SP (CEBAS em renovação tempestiva) | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | **APTA** | O-Q24, P-X17 |
| C26 | 24.006.302/0004-88 | Matriz com ordem 0004 (IDEAS) e CEIS vigente | OK | OK | OK | OK | OK | OK | OK | OK | R | OK | OK | OK | OK | OK | OK | OK | **INAPTA** | O-Q20 |
| C27 | 24.006.302/0001-35 | Filial com ordem 0001 (IDEAS) | OK | OK | OK | OK | OK | OK | A | OK | R | OK | OK | OK | OK | OK | OK | OK | **INAPTA** | O-Q20 |
| C28 | 02.203.539/0001-73 | CEPIM (fundação ativa) | OK | OK | OK | OK | OK | OK | OK | R | OK | OK | OK | OK | OK | OK | OK | - | **INAPTA** | O-Q18, O-Q22 |
| C29 | 00.688.001/0001-70 | CEIS vigente sem data final | OK | OK | OK | OK | OK | OK | OK | OK | R | OK | OK | OK | OK | OK | OK | - | **INAPTA** | O-Q17, O-Q22, O-Q23 |
| C30 | 30.994.499/0001-60 | CEIS vigente com fim futuro | OK | OK | OK | OK | OK | OK | OK | OK | R | OK | OK | OK | OK | OK | OK | OK | **INAPTA** | O-Q15, O-Q17 |
| C31 | 02.393.242/0001-18 | CEIS vencendo em 22/11/2026 | OK | OK | OK | OK | OK | OK | OK | OK | R | OK | OK | OK | OK | OK | OK | - | **INAPTA** | O-Q17, P-X17 |
| C32 | 07.408.449/0001-32 | CEIS expirado | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | **APTA** | - |
| C33 | 09.058.351/0001-28 | CEIS 'com prazo determinado' sem data final | OK | OK | OK | OK | OK | OK | OK | OK | R | OK | OK | OK | OK | OK | OK | - | **INAPTA** | O-Q15 |
| C34 | 13.144.375/0001-77 | CNEP | OK | OK | OK | OK | OK | OK | OK | OK | OK | A | OK | OK | OK | OK | OK | - | **APTA COM RESSALVAS** | O-Q16 |
| C35 | 05.051.898/0001-40 | Ocorrência no CNIA (CNJ) | OK | OK | OK | OK | OK | OK | OK | OK | R | OK | OK | R | OK | OK | OK | - | **INAPTA** | O-Q19, O-Q23 |
| C36 | 01.081.476/0001-67 | CNIA + dirigente com sanção (nome e CPF) | OK | OK | OK | OK | OK | OK | OK | R | R | OK | OK | R | OK | A | OK | - | **INAPTA** | O-Q18, O-Q19, O-Q22, O-Q23 |
| C37 | 44.551.605/0005-70 | Sanção só na filial, consulta pela filial | OK | OK | OK | OK | OK | OK | OK | OK | R | OK | OK | OK | OK | OK | OK | - | **INAPTA** | O-Q15, O-Q17 |
| C38 | 44.551.605/0001-46 | Sanção só na filial, consulta pela matriz | OK | OK | OK | OK | OK | OK | OK | OK | R | OK | OK | OK | OK | OK | OK | - | **INAPTA** | O-Q15, O-Q17, O-Q20 |
| C39 | 06.287.661/0001-26 | INAPTA com CEIS vigente, CNIA e dirigente | OK | R | OK | OK | OK | OK | OK | OK | R | OK | OK | R | OK | A | OK | - | **INAPTA** | O-Q19, O-Q22 |
| C40 | 03.463.763/0001-67 | INAPTA com inidoneidade TCU | OK | R | OK | OK | OK | OK | OK | OK | R | OK | R | OK | A | A | OK | - | **INAPTA** | O-Q17, O-Q21, O-Q22 |
| C41 | 53.524.534/0001-83 | INAPTA com CEPIM + CEIS + CNEP (Santa Casa de Pacaembu) | OK | R | OK | OK | OK | OK | OK | R | R | A | OK | OK | OK | A | OK | OK | **INAPTA** | O-Q15, O-Q16, O-Q18, O-Q22 |
| C42 | 21.145.289/0001-07 | INAPTA com CEPIM + CEIS + TCU (IMDC) | OK | R | OK | OK | OK | OK | OK | R | R | OK | R | OK | A | A | OK | - | **INAPTA** | O-Q17, O-Q18, O-Q21, O-Q22 |
| C43 | 14.112.015/0001-56 | BAIXADA com CEPIM | OK | R | OK | OK | OK | OK | OK | R | OK | OK | OK | OK | OK | OK | A | - | **INAPTA** | O-Q18 |
| C44 | 03.126.200/0001-83 | INAPTA com CEIS expirado | OK | R | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | A | OK | - | **INAPTA** | O-Q22, P-X17 |
| C45 | 08.928.169/0001-18 | INAPTA com CNEP | OK | R | OK | OK | OK | OK | OK | OK | OK | A | OK | OK | OK | OK | OK | - | **INAPTA** | O-Q16, O-Q17 |
| C46 | 43.337.682/0001-35 | INAPTA com CNIA + CEIS + CEPIM (AVAPE) | OK | R | OK | OK | OK | OK | OK | R | R | OK | OK | R | A | A | OK | - | **INAPTA** | O-Q17, O-Q18, O-Q19, O-Q20, O-Q21, O-Q22, P-X17 |
| C47 | 50.798.453/0001-83 | CEBAS Saúde ativo (Santa Casa de Cerquilho) | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | **APTA** | O-Q15 |
| C48 | 00.001.297/0001-00 | CEBAS não vigente (concessão indeferida) | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | OK | **APTA** | O-Q23 |
| C49 | 26.447.003/0001-61 | Associação profissional (CNAE 94.12) com CEPIM | OK | OK | OK | A | OK | OK | OK | R | OK | OK | OK | OK | OK | OK | OK | - | **INAPTA** | O-Q18 |

Na coluna 'Depende de', `O-Qxx` é [ORIENTADOR Qxx] e `P-xx` é [PENDENTE xx].
Total: 49 casos e 11 variantes (mesmo CNPJ com outra data de referência ou esfera).
Distribuição do status final: APTA 7, APTA COM RESSALVAS 12, CNPJ INVÁLIDO 3, INAPTA 24, INCONCLUSIVA 3.

## Casos

### C01 - OSC regular

- CNPJ: `19.131.243/0001-97`.
- Entidade: OPEN KNOWLEDGE BRASIL.
- O que testa: Caminho feliz: associação ativa, CNAE ALTA, mais de 3 anos, sem sanções, presente no Mapa.
- Status final esperado: **APTA**.

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 9430800 (ALTA, regra 94.30-8 (classe)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 03/10/2013 (12 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 621480), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C02 - DV inválido

- CNPJ: `19.131.243/0001-98`.
- O que testa: `dv`: último dígito errado (esperado 97); nenhuma fonte é consultada; status CNPJ_INVALIDO (Q3).
- Status final esperado: **CNPJ INVÁLIDO**, motivos: `dv`.

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | RESTRICAO | CNPJ inválido: dígito verificador não confere (esperado 97). Erro de digitação, sem relatório de entidade (Q3). |
| `situacao` | 2 | Situação cadastral | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `natureza` | 3 | Natureza jurídica | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `cnae` | 4 | CNAE de relevância social | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `tempo` | 5 | Tempo de existência | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `cepim` | 6 | CEPIM | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `ceis` | 7 | CEIS | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `cnep` | 8 | CNEP | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `dirigentes` | 10 | Dirigentes (QSA) | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `mapa_osc` | 11 | Mapa das OSCs | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |

### C03 - Base repetida com DV que confere

- CNPJ: `11.111.111/1111-80`.
- O que testa: `dv`: base de 12 posições repetida (D11), mesmo com os DVs calculados batendo; status CNPJ_INVALIDO (Q3).
- Status final esperado: **CNPJ INVÁLIDO**, motivos: `dv`.

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | RESTRICAO | CNPJ inválido: base de 12 posições repetida. Erro de digitação, sem relatório de entidade (Q3). |
| `situacao` | 2 | Situação cadastral | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `natureza` | 3 | Natureza jurídica | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `cnae` | 4 | CNAE de relevância social | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `tempo` | 5 | Tempo de existência | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `cepim` | 6 | CEPIM | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `ceis` | 7 | CEIS | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `cnep` | 8 | CNEP | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `dirigentes` | 10 | Dirigentes (QSA) | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `mapa_osc` | 11 | Mapa das OSCs | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |

### C04 - Formato inválido (13 caracteres)

- CNPJ: `12ABC34501DE3`.
- O que testa: `dv`: formato; status CNPJ_INVALIDO (Q3).
- Status final esperado: **CNPJ INVÁLIDO**, motivos: `dv`.

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | RESTRICAO | CNPJ inválido: formato inválido (esperado 12 caracteres [0-9A-Z] + 2 dígitos). Erro de digitação, sem relatório de entidade (Q3). |
| `situacao` | 2 | Situação cadastral | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `natureza` | 3 | Natureza jurídica | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `cnae` | 4 | CNAE de relevância social | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `tempo` | 5 | Tempo de existência | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `cepim` | 6 | CEPIM | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `ceis` | 7 | CEIS | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `cnep` | 8 | CNEP | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `dirigentes` | 10 | Dirigentes (QSA) | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `mapa_osc` | 11 | Mapa das OSCs | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | CNPJ inválido: nenhuma fonte é consultada. |

### C05 - Alfanumérico válido (exemplo oficial)

- CNPJ: `12.ABC.345/01DE-35`.
- O que testa: D4 e Q2: DV aceita alfanumérico, consultas ficam fora do MVP (NAO_VERIFICADO), status INCONCLUSIVA.
- Status final esperado: **INCONCLUSIVA**, motivos: `situacao`, `natureza`, `cepim`, `ceis`, `cnep`, `tcu_inidoneos`, `cnj_cnia`.
- Ambiguidades envolvidas: A02.

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `natureza` | 3 | Natureza jurídica | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `cnae` | 4 | CNAE de relevância social | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `tempo` | 5 | Tempo de existência | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `cepim` | 6 | CEPIM | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `ceis` | 7 | CEIS | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `cnep` | 8 | CNEP | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `dirigentes` | 10 | Dirigentes (QSA) | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `mapa_osc` | 11 | Mapa das OSCs | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |

### C06 - Alfanumérico real (BB filial)

- CNPJ: `00.000.000/E08G-12`.
- O que testa: D4 com um CNPJ alfanumérico que existe de fato (OpenCNPJ responde).
- Status final esperado: **INCONCLUSIVA**, motivos: `situacao`, `natureza`, `cepim`, `ceis`, `cnep`, `tcu_inidoneos`, `cnj_cnia`.
- Ambiguidades envolvidas: A02.

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `natureza` | 3 | Natureza jurídica | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `cnae` | 4 | CNAE de relevância social | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `tempo` | 5 | Tempo de existência | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `cepim` | 6 | CEPIM | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `ceis` | 7 | CEIS | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `cnep` | 8 | CNEP | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `dirigentes` | 10 | Dirigentes (QSA) | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `mapa_osc` | 11 | Mapa das OSCs | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | CNPJ alfanumérico: as consultas ainda não são feitas pelo MVP (D4); status INCONCLUSIVA com mensagem própria (Q2). |

### C07 - CNPJ inexistente com DV válido

- CNPJ: `94.580.730/0001-52`.
- O que testa: `situacao` INDISPONIVEL com motivo NAO_ENCONTRADO (Q26); TCU devolveria NADA_CONSTA com seCnpjEncontradoNaBaseTcu false (D13).
- Status final esperado: **INCONCLUSIVA**, motivos: `situacao`, `natureza`, `cepim`, `ceis`, `cnep`, `tcu_inidoneos`, `cnj_cnia`.
- Ambiguidades envolvidas: A03.

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | INDISPONIVEL | CNPJ não encontrado no espelho do OpenCNPJ de 15/09/2026 (HTTP 404); pode ser CNPJ inexistente ou recém-criado. No motor a BrasilAPI também é consultada antes de concluir (Q26). |
| `natureza` | 3 | Natureza jurídica | NAO_VERIFICADO | Sem cadastro não há QSA nem raiz; fan-out não executado (o TCU daria um 'nada consta' enganoso, D13). |
| `cnae` | 4 | CNAE de relevância social | NAO_VERIFICADO | Sem cadastro não há QSA nem raiz; fan-out não executado (o TCU daria um 'nada consta' enganoso, D13). |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | NAO_VERIFICADO | Sem cadastro não há QSA nem raiz; fan-out não executado (o TCU daria um 'nada consta' enganoso, D13). |
| `tempo` | 5 | Tempo de existência | NAO_VERIFICADO | Sem cadastro não há QSA nem raiz; fan-out não executado (o TCU daria um 'nada consta' enganoso, D13). |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | NAO_VERIFICADO | Sem cadastro não há QSA nem raiz; fan-out não executado (o TCU daria um 'nada consta' enganoso, D13). |
| `cepim` | 6 | CEPIM | NAO_VERIFICADO | Sem cadastro não há QSA nem raiz; fan-out não executado (o TCU daria um 'nada consta' enganoso, D13). |
| `ceis` | 7 | CEIS | NAO_VERIFICADO | Sem cadastro não há QSA nem raiz; fan-out não executado (o TCU daria um 'nada consta' enganoso, D13). |
| `cnep` | 8 | CNEP | NAO_VERIFICADO | Sem cadastro não há QSA nem raiz; fan-out não executado (o TCU daria um 'nada consta' enganoso, D13). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | NAO_VERIFICADO | Sem cadastro não há QSA nem raiz; fan-out não executado (o TCU daria um 'nada consta' enganoso, D13). |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | NAO_VERIFICADO | Sem cadastro não há QSA nem raiz; fan-out não executado (o TCU daria um 'nada consta' enganoso, D13). |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | NAO_VERIFICADO | Sem cadastro não há QSA nem raiz; fan-out não executado (o TCU daria um 'nada consta' enganoso, D13). |
| `dirigentes` | 10 | Dirigentes (QSA) | NAO_VERIFICADO | Sem cadastro não há QSA nem raiz; fan-out não executado (o TCU daria um 'nada consta' enganoso, D13). |
| `mapa_osc` | 11 | Mapa das OSCs | NAO_VERIFICADO | Sem cadastro não há QSA nem raiz; fan-out não executado (o TCU daria um 'nada consta' enganoso, D13). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Sem cadastro não há QSA nem raiz; fan-out não executado (o TCU daria um 'nada consta' enganoso, D13). |

### C08 - Associação BAIXADA

- CNPJ: `08.942.107/0001-60`.
- Entidade: ASSOCIACAO DE INCLUSAO E DESENVOLVIMENTO SOCIAL POR UM RIO MELHOR.
- O que testa: `situacao`: situação 8, motivo extinção.
- Status final esperado: **INAPTA**, motivos: `situacao`.

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | RESTRICAO | Situação BAIXADA desde 04/01/2012 (motivo: EXTINCAO POR ENCERRAMENTO LIQUIDACAO VOLUNTARIA). |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 9499500 (MEDIA, regra 94.99-5 (classe)); melhor faixa MEDIA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 29/06/2007 (19 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 6 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | ALERTA | CNPJ ausente do Mapa das OSCs: possível divergência de classificação; conferir natureza (D2). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C09 - Associação INAPTA

- CNPJ: `11.468.674/0001-31`.
- Entidade: CENTRO DE APOIO AOS PORTADORES DE HIV - CAPH.
- O que testa: `situacao`: situação 4.
- Status final esperado: **INAPTA**, motivos: `situacao`.

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | RESTRICAO | Situação INAPTA desde 18/09/2018 (motivo: OMISSAO DE DECLARACOES). |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 9430800 (ALTA, regra 94.30-8 (classe)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 07/01/2010 (16 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 1211375), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C10 - Associação SUSPENSA

- CNPJ: `03.728.829/0001-01`.
- Entidade: ASSOCIACAO DOS PRODUTORES RURAIS DO SERINGAL.
- O que testa: `situacao`: situação 3.
- Status final esperado: **INAPTA**, motivos: `situacao`.

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | RESTRICAO | Situação SUSPENSA desde 06/04/2022 (motivo: PEDIDO DE BAIXA INDEFERIDA). |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 9430800 (ALTA, regra 94.30-8 (classe)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 03/03/2000 (26 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 1192102), perfil preenchido pela OSC (tx_email). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C11 - Natureza não elegível (Banco do Brasil)

- CNPJ: `00.000.000/0001-91`.
- Entidade: BANCO DO BRASIL SA.
- O que testa: `natureza`: 2038 Sociedade de Economia Mista.
- Status final esperado: **INAPTA**, motivos: `natureza`.

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | RESTRICAO | Natureza jurídica 2038 (Sociedade de Economia Mista) não é compatível com OSC (Lei 13.019/2014, art. 2º, I). |
| `cnae` | 4 | CNAE de relevância social | ALERTA | CNAE principal 6422100 (BAIXA); melhor faixa BAIXA. Nenhuma atividade cadastrada tem relação direta com relevância social; confira o estatuto. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 01/08/1966 (60 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 41 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | ALERTA | CNPJ ausente do Mapa das OSCs: possível divergência de classificação; conferir natureza (D2). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C12 - Organização religiosa 3220 só com CNAE religioso

- CNPJ: `00.108.217/0001-10`.
- Entidade: MITRA ARQUIDIOCESANA DE BRASILIA.
- O que testa: `natureza` elegível + verificação `religiosa` (D7, Q25).
- Status final esperado: **APTA COM RESSALVAS**, motivos: `religiosa`.
- Ambiguidades envolvidas: A07.

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3220 (Organização Religiosa) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 9491000 (MEDIA, regra 94.91-0 (classe)); melhor faixa MEDIA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | ALERTA | Gatilho: natureza 3220; nenhum CNAE em ALTA. Organização religiosa sem atividade social de alta aderência no CNAE: a Lei 13.019/2014, art. 2º, I, c, exige atividades de interesse público e de cunho social distintas das exclusivamente religiosas; confira estatuto e plano de trabalho. |
| `tempo` | 5 | Tempo de existência | OK | Início 13/11/1970 (55 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 781757), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C13 - Igreja como associação (3999) com CNAE 9491

- CNPJ: `03.128.347/0001-02`.
- Entidade: IGREJA BATISTA JERUSALEM.
- O que testa: `religiosa` pelo CNAE principal 94.91-0 (D7, ORIENTADOR Q15).
- Status final esperado: **APTA COM RESSALVAS**, motivos: `religiosa`.
- Ambiguidades envolvidas: A07.
- Depende de: [ORIENTADOR Q15].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 9491000 (MEDIA, regra 94.91-0 (classe)); melhor faixa MEDIA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | ALERTA | Gatilho: CNAE principal 94.91-0; nenhum CNAE em ALTA. Organização religiosa sem atividade social de alta aderência no CNAE: a Lei 13.019/2014, art. 2º, I, c, exige atividades de interesse público e de cunho social distintas das exclusivamente religiosas; confira estatuto e plano de trabalho. [ORIENTADOR Q15] |
| `tempo` | 5 | Tempo de existência | OK | Início 05/05/1999 (27 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 1191914), perfil preenchido pela OSC (tx_email). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C14 - Cooperativa 2143

- CNPJ: `04.311.762/0001-60`.
- Entidade: COOPERATIVA MISTA DOS TRABALHADORES AGRO-EXTRATIVISTAS DO ALTO CAJARI.
- O que testa: `natureza`: REVISÃO MANUAL (ALERTA); CNAE com zero à esquerda.
- Status final esperado: **APTA COM RESSALVAS**, motivos: `natureza`, `mapa_osc`.
- Depende de: [ORIENTADOR Q14], [ORIENTADOR Q15].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | ALERTA | Natureza 2143 (Cooperativa) exige revisão manual (spec 6.3). [ORIENTADOR Q14] |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 0220903 (BAIXA, regra padrao); melhor faixa ALTA. [ORIENTADOR Q15] |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 17/01/2001 (25 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 4 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | ALERTA | CNPJ ausente do Mapa das OSCs: possível divergência de classificação; conferir natureza (D2). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C15 - Organização Social 3301

- CNPJ: `08.055.129/0001-09`.
- Entidade: INSTITUTO FENIX.
- O que testa: `natureza`: REVISÃO MANUAL (ALERTA).
- Status final esperado: **APTA COM RESSALVAS**, motivos: `natureza`.
- Depende de: [ORIENTADOR Q14].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | ALERTA | Natureza 3301 (Organização Social (OS)) exige revisão manual (spec 6.3). [ORIENTADOR Q14] |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8660700 (ALTA, regra 86 (divisao)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 04/11/2005 (20 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 1203083), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C16 - Fundação privada com perfil do Mapa preenchido (Fundação Abrinq)

- CNPJ: `38.894.796/0001-46`.
- Entidade: FUNDACAO ABRINQ PELOS DIREITOS DA CRIANCA E DO ADOLESCENTE.
- O que testa: Natureza 3069 e `mapa_osc` com perfil preenchido pela OSC.
- Status final esperado: **APTA**.
- Ambiguidades envolvidas: A13.
- Depende de: [ORIENTADOR Q24], [PENDENTE X17].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3069 (Fundação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 9430800 (ALTA, regra 94.30-8 (classe)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 20/07/1990 (36 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 2 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 594130), perfil preenchido pela OSC (tx_missao_osc, tx_site, tx_visao_osc). |
| `cebas` | 12 | CEBAS | OK | Planilha MDS de 24/10/2024: CEBAS VÁLIDA com vigência até 31/12/2023, vencida há 2 ano(s) e 9 mês(es), sem ato posterior encontrado no DOU carregado (só jun a ago/2026): possível renovação em análise; o requerimento tempestivo mantém a validade até a decisão; confirme com o ministério (D16). [PENDENTE X17]: faltam os atos do DOU de 12/2023 a 05/2026. [ORIENTADOR Q24] [PENDENTE X17] |

### C17 - Associação com CNAE comercial (BAIXA)

- CNPJ: `03.308.444/0001-87`.
- Entidade: ASSOCIACAO DE PEQUENOS PRODUTORES RURAIS ASSOCIACAO SAO FRNCISCO.
- O que testa: `cnae`: nenhum CNAE em ALTA ou MEDIA.
- Status final esperado: **APTA COM RESSALVAS**, motivos: `cnae`.
- Ambiguidades envolvidas: A09.
- Depende de: [ORIENTADOR Q23].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | ALERTA | CNAE principal 4724500 (BAIXA); melhor faixa BAIXA. Nenhuma atividade cadastrada tem relação direta com relevância social; confira o estatuto. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 28/06/1999 (27 ano(s) completo(s) em 01/10/2026); situação ATIVA desde 12/11/2024, possível reativação (contado desde o início, Q23): atinge o prazo para União, estados e municípios. [ORIENTADOR Q23] |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 415974), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C18 - Associação recente (menos de 1 ano)

- CNPJ: `65.478.551/0001-00`.
- Entidade: ASSOCIACAO MATURIDADE EM MOVIMENTO.
- O que testa: `tempo`: não atinge nenhuma esfera.
- Status final esperado: **APTA COM RESSALVAS**, motivos: `tempo`.

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 9499500 (MEDIA, regra 94.99-5 (classe)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | ALERTA | Início 03/02/2026 (0 ano(s) completo(s) em 01/10/2026): ainda não atinge o prazo mínimo para nenhuma esfera. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 4 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 1499597), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

Variante (data_referencia = 2026-10-01, esfera = municipio): status **APTA COM RESSALVAS**.
`tempo`: ALERTA - Início 03/02/2026 (0 ano(s) completo(s) em 01/10/2026): não atinge o prazo de 1 ano(s) exigido para municípios; o gestor pode reduzir o prazo (art. 33, V, a).

### C19 - Associação entre 1 e 2 anos

- CNPJ: `58.323.085/0001-29`.
- Entidade: CASA DE ACOLHIMENTO VILA AVIVA.
- O que testa: `tempo`: atinge só municípios.
- Status final esperado: **APTA COM RESSALVAS**, motivos: `tempo`.

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8720499 (ALTA, regra 87 (divisao)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | ALERTA | Início 01/11/2024 (1 ano(s) completo(s) em 01/10/2026): atinge municípios; estados/DF exige 2 anos; União exige 3 anos. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 1441050), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

Variante (data_referencia = 2026-10-01, esfera = municipio): status **APTA**.
`tempo`: OK - Início 01/11/2024 (1 ano(s) completo(s) em 01/10/2026): atinge o prazo para municípios (1 ano(s)).

Variante (data_referencia = 2026-10-01, esfera = estado): status **APTA COM RESSALVAS**.
`tempo`: ALERTA - Início 01/11/2024 (1 ano(s) completo(s) em 01/10/2026): não atinge o prazo de 2 ano(s) exigido para estados/DF; o gestor pode reduzir o prazo (art. 33, V, a).

### C20 - Associação entre 2 e 3 anos

- CNPJ: `53.071.884/0001-31`.
- Entidade: INSTITUTO AVALANCHE AZUL.
- O que testa: `tempo`: atinge municípios e estados.
- Status final esperado: **APTA COM RESSALVAS**, motivos: `tempo`.

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8800600 (ALTA, regra 88 (divisao)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | ALERTA | Início 01/12/2023 (2 ano(s) completo(s) em 01/10/2026): atinge municípios, estados/DF; União exige 3 anos. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 1422391), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

Variante (data_referencia = 2026-10-01, esfera = estado): status **APTA**.
`tempo`: OK - Início 01/12/2023 (2 ano(s) completo(s) em 01/10/2026): atinge o prazo para estados/DF (2 ano(s)).

Variante (data_referencia = 2026-10-01, esfera = uniao): status **APTA COM RESSALVAS**.
`tempo`: ALERTA - Início 01/12/2023 (2 ano(s) completo(s) em 01/10/2026): não atinge o prazo de 3 ano(s) exigido para União; o gestor pode reduzir o prazo (art. 33, V, a).

### C21 - Associação com exatamente 1 ano na data de referência

- CNPJ: `62.988.692/0001-85`.
- Entidade: INSTITUTO SOCIOASSISTENCIAL E EDUCACIONAL EDNA MATTOS.
- O que testa: Fronteira do art. 33, V, a: início 01/10/2025.
- Status final esperado: **APTA COM RESSALVAS**, motivos: `tempo`.
- Ambiguidades envolvidas: A08.

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 9493600 (ALTA, regra 94.93-6 (classe)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | ALERTA | Início 01/10/2025 (1 ano(s) completo(s) em 01/10/2026): atinge municípios; estados/DF exige 2 anos; União exige 3 anos. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 1482595), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

Variante (data_referencia = 2026-10-01, esfera = municipio): status **APTA**.
`tempo`: OK - Início 01/10/2025 (1 ano(s) completo(s) em 01/10/2026): atinge o prazo para municípios (1 ano(s)).

Variante (data_referencia = 2026-09-30, esfera = municipio): status **APTA COM RESSALVAS**.
`tempo`: ALERTA - Início 01/10/2025 (0 ano(s) completo(s) em 30/09/2026): não atinge o prazo de 1 ano(s) exigido para municípios; o gestor pode reduzir o prazo (art. 33, V, a).

### C22 - Associação a 1 dia de completar 2 anos

- CNPJ: `57.946.201/0001-01`.
- Entidade: ASSOCIACAO DE AGRICULTORES DO PROJETO CREDITO FUNDIARIO RENASCER.
- O que testa: Fronteira: início 02/10/2024.
- Status final esperado: **APTA COM RESSALVAS**, motivos: `tempo`.
- Ambiguidades envolvidas: A08, A09.
- Depende de: [ORIENTADOR Q23].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 9430800 (ALTA, regra 94.30-8 (classe)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | ALERTA | Início 02/10/2024 (1 ano(s) completo(s) em 01/10/2026); situação ATIVA desde 06/07/2026, possível reativação (contado desde o início, Q23): atinge municípios; estados/DF exige 2 anos; União exige 3 anos. [ORIENTADOR Q23] |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 1443295), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

Variante (data_referencia = 2026-10-01, esfera = estado): status **APTA COM RESSALVAS**.
`tempo`: ALERTA - Início 02/10/2024 (1 ano(s) completo(s) em 01/10/2026); situação ATIVA desde 06/07/2026, possível reativação (contado desde o início, Q23): não atinge o prazo de 2 ano(s) exigido para estados/DF; o gestor pode reduzir o prazo (art. 33, V, a).

Variante (data_referencia = 2026-10-02, esfera = estado): status **APTA**.
`tempo`: OK - Início 02/10/2024 (2 ano(s) completo(s) em 02/10/2026); situação ATIVA desde 06/07/2026, possível reativação (contado desde o início, Q23): atinge o prazo para estados/DF (2 ano(s)).

### C23 - Filial ativa com matriz ativa (Santa Casa de SP)

- CNPJ: `62.779.145/0002-70`.
- Entidade: IRMANDADE DA SANTA CASA DE MISERICORDIA DE SAO PAULO.
- O que testa: D5: resolve para a matriz; situação das duas; tempo da matriz.
- Status final esperado: **APTA**.
- Ambiguidades envolvidas: A05, A13.
- Depende de: [ORIENTADOR Q24], [PENDENTE X17].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA (matriz 62.779.145/0001-90); espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8610101 (ALTA, regra 86 (divisao)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 27/04/1970 (56 ano(s) completo(s) em 01/10/2026, data da matriz): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta partiu da filial (ATIVA); entidade avaliada pela matriz 62.779.145/0001-90 (D5). |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 2 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 614393, CNPJ da matriz), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | OK | CEBAS = SIM no SisCEBAS de 30/09/2026, situação 'TEMPESTIVO - MANIFESTAÇÃO MEC (DIGAD)', vigência até -: possível renovação em análise; o requerimento tempestivo mantém a validade até a decisão; confirme com o ministério (D16). (CNPJ usado: 62.779.145/0001-90; consultados matriz e estabelecimento, Q28.) [ORIENTADOR Q24] [PENDENTE X17] |

### C24 - Filial baixada com matriz ativa (Instituto GRPCOM)

- CNPJ: `04.955.882/0005-23`.
- Entidade: INSTITUTO GRPCOM.
- O que testa: D5: filial baixada, matriz ativa; data_situacao_cadastral '0' na matriz (OpenCNPJ).
- Status final esperado: **APTA COM RESSALVAS**, motivos: `estabelecimento`.
- Ambiguidades envolvidas: A04, A05.

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA (matriz 04.955.882/0001-08); espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 9430800 (ALTA, regra 94.30-8 (classe)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 07/03/2002 (24 ano(s) completo(s) em 01/10/2026, data da matriz): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | ALERTA | O estabelecimento informado (filial) está BAIXADA desde 05/01/2017 (motivo: EXTINCAO POR ENCERRAMENTO LIQUIDACAO VOLUNTARIA); a entidade (matriz 04.955.882/0001-08) está ativa. Confira se o CNPJ informado é o correto (Q4). |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 2 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 678768, CNPJ da matriz), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. (CNPJ usado: 04.955.882/0001-08; consultados matriz e estabelecimento, Q28.) |

### C25 - Matriz da Santa Casa de SP (CEBAS em renovação tempestiva)

- CNPJ: `62.779.145/0001-90`.
- Entidade: IRMANDADE DA SANTA CASA DE MISERICORDIA DE SAO PAULO.
- O que testa: `cebas` com renovação tempestiva pendente no SisCEBAS.
- Status final esperado: **APTA**.
- Ambiguidades envolvidas: A13.
- Depende de: [ORIENTADOR Q24], [PENDENTE X17].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8610101 (ALTA, regra 86 (divisao)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 27/04/1970 (56 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 2 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 614393), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | OK | CEBAS = SIM no SisCEBAS de 30/09/2026, situação 'TEMPESTIVO - MANIFESTAÇÃO MEC (DIGAD)', vigência até -: possível renovação em análise; o requerimento tempestivo mantém a validade até a decisão; confirme com o ministério (D16). [ORIENTADOR Q24] [PENDENTE X17] |

### C26 - Matriz com ordem 0004 (IDEAS) e CEIS vigente

- CNPJ: `24.006.302/0004-88`.
- Entidade: INSTITUTO DE DESENVOLVIMENTO, ENSINO E ASSISTENCIA A SAUDE - IDEAS.
- O que testa: D5: estabelecimento 0004 é a matriz; a 0001 é filial. Sanção própria vigente.
- Status final esperado: **INAPTA**, motivos: `ceis`.
- Ambiguidades envolvidas: A06, A16, A17.
- Depende de: [ORIENTADOR Q20].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8660700 (ALTA, regra 86 (divisao)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 19/01/2018 (8 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz com ordem 0004, detectada por `matriz_filial`, não pela ordem (Q27). |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | RESTRICAO | 6 registro(s) vigente(s) em 01/10/2026: Impedimento/proibição de contratar sem prazo determinado (10/03/2026 a sem data final) - 1º Grau - TRF4 / SEÇÃO JUDICIÁRIA DE SANTA CATARINA / SUBSEÇÃO JUDICIÁRIA DE FLORIANÓPOLIS / 2ª VARA FEDERAL DE FLORIANÓPOLIS [estabelecimento 24.006.302/0003-05, outro estabelecimento] (fontes: csv) => RESTRICAO; Impedimento/proibição de contratar sem prazo determinado (10/03/2026 a sem data final) - 1º Grau - TRF4 / SEÇÃO JUDICIÁRIA DE SANTA CATARINA / SUBSEÇÃO JUDICIÁRIA DE FLORIANÓPOLIS / 2ª VARA FEDERAL DE FLORIANÓPOLIS (fontes: csv, opencnpj) => RESTRICAO; Impedimento/proibição de contratar com prazo determinado (07/08/2026 a 06/08/2031) - PREFEITURA MUNICIPAL DE CAXIAS DO SUL - RS (fontes: csv, opencnpj) => RESTRICAO; Impedimento/proibição de contratar sem prazo determinado (10/03/2026 a sem data final) - 1º Grau - TRF4 / SEÇÃO JUDICIÁRIA DE SANTA CATARINA / SUBSEÇÃO JUDICIÁRIA DE FLORIANÓPOLIS / 2ª VARA FEDERAL DE FLORIANÓPOLIS [estabelecimento 24.006.302/0008-01, outro estabelecimento] (fontes: csv) => RESTRICAO; Impedimento/proibição de contratar sem prazo determinado (10/03/2026 a sem data final) - 1º Grau - TRF4 / SEÇÃO JUDICIÁRIA DE SANTA CATARINA / SUBSEÇÃO JUDICIÁRIA DE FLORIANÓPOLIS / 2ª VARA FEDERAL DE FLORIANÓPOLIS [estabelecimento 24.006.302/0005-69, outro estabelecimento] (fontes: csv) => RESTRICAO; Impedimento/proibição de contratar sem prazo determinado (10/03/2026 a sem data final) - 1º Grau - TRF4 / SEÇÃO JUDICIÁRIA DE SANTA CATARINA / SUBSEÇÃO JUDICIÁRIA DE FLORIANÓPOLIS / 2ª VARA FEDERAL DE FLORIANÓPOLIS [estabelecimento 24.006.302/0001-35, outro estabelecimento] (fontes: csv) => RESTRICAO. [ORIENTADOR Q20] |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 2 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 1241257), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | OK | CEBAS ativo (saúde) segundo SisCEBAS de 30/09/2026: portaria 1535 publicada em 18/03/2024, vigência 01/01/2024 a 31/12/2026. |

### C27 - Filial com ordem 0001 (IDEAS)

- CNPJ: `24.006.302/0001-35`.
- Entidade: INSTITUTO DE DESENVOLVIMENTO, ENSINO E ASSISTENCIA A SAUDE - IDEAS.
- O que testa: D5: ordem 0001 que não é matriz; cnpj_da_matriz devolve o próprio CNPJ.
- Status final esperado: **INAPTA**, motivos: `ceis`.
- Ambiguidades envolvidas: A06, A16, A17.
- Depende de: [ORIENTADOR Q20].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; matriz não identificada, avaliado o estabelecimento consultado (Q27); espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8660700 (ALTA, regra 86 (divisao)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 18/01/2016 (10 ano(s) completo(s) em 01/10/2026, data do estabelecimento consultado porque a matriz não foi identificada (Q27)): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | ALERTA | O estabelecimento é FILIAL e 24.006.302/0001-35 (raiz + 0001) não é a matriz: informe o CNPJ da matriz. Avaliação feita com os dados do estabelecimento consultado (Q27). |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | RESTRICAO | 6 registro(s) vigente(s) em 01/10/2026: Impedimento/proibição de contratar sem prazo determinado (10/03/2026 a sem data final) - 1º Grau - TRF4 / SEÇÃO JUDICIÁRIA DE SANTA CATARINA / SUBSEÇÃO JUDICIÁRIA DE FLORIANÓPOLIS / 2ª VARA FEDERAL DE FLORIANÓPOLIS [estabelecimento 24.006.302/0003-05, outro estabelecimento] (fontes: csv) => RESTRICAO; Impedimento/proibição de contratar sem prazo determinado (10/03/2026 a sem data final) - 1º Grau - TRF4 / SEÇÃO JUDICIÁRIA DE SANTA CATARINA / SUBSEÇÃO JUDICIÁRIA DE FLORIANÓPOLIS / 2ª VARA FEDERAL DE FLORIANÓPOLIS [estabelecimento 24.006.302/0004-88, outro estabelecimento] (fontes: csv) => RESTRICAO; Impedimento/proibição de contratar com prazo determinado (07/08/2026 a 06/08/2031) - PREFEITURA MUNICIPAL DE CAXIAS DO SUL - RS [estabelecimento 24.006.302/0004-88, outro estabelecimento] (fontes: csv) => RESTRICAO; Impedimento/proibição de contratar sem prazo determinado (10/03/2026 a sem data final) - 1º Grau - TRF4 / SEÇÃO JUDICIÁRIA DE SANTA CATARINA / SUBSEÇÃO JUDICIÁRIA DE FLORIANÓPOLIS / 2ª VARA FEDERAL DE FLORIANÓPOLIS [estabelecimento 24.006.302/0008-01, outro estabelecimento] (fontes: csv) => RESTRICAO; Impedimento/proibição de contratar sem prazo determinado (10/03/2026 a sem data final) - 1º Grau - TRF4 / SEÇÃO JUDICIÁRIA DE SANTA CATARINA / SUBSEÇÃO JUDICIÁRIA DE FLORIANÓPOLIS / 2ª VARA FEDERAL DE FLORIANÓPOLIS [estabelecimento 24.006.302/0005-69, outro estabelecimento] (fontes: csv) => RESTRICAO; Impedimento/proibição de contratar sem prazo determinado (10/03/2026 a sem data final) - 1º Grau - TRF4 / SEÇÃO JUDICIÁRIA DE SANTA CATARINA / SUBSEÇÃO JUDICIÁRIA DE FLORIANÓPOLIS / 2ª VARA FEDERAL DE FLORIANÓPOLIS (fontes: csv, opencnpj) => RESTRICAO. [ORIENTADOR Q20] |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 2 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 841432), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | OK | CEBAS não vigente (saúde): último ato 'INDEFERIDO' (REQUERIMENTO>>CONCESSÃO), publicado em 18/10/2018; situação 'PUBLICADO INDEFERIDO' no SisCEBAS de 30/09/2026. |

### C28 - CEPIM (fundação ativa)

- CNPJ: `02.203.539/0001-73`.
- Entidade: FUNDACAO ASSIS GURGACZ.
- O que testa: `cepim` positiva.
- Status final esperado: **INAPTA**, motivos: `cepim`.
- Ambiguidades envolvidas: A12.
- Depende de: [ORIENTADOR Q18], [ORIENTADOR Q22].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3069 (Fundação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8531700 (ALTA, regra 85 (divisao)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 21/10/1997 (28 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | RESTRICAO | 1 registro(s) no CEPIM (art. 39; o CEPIM não tem datas, registro presente é impedimento): convênio 522242 - Ministério das Comunicações - Unidades com vínculo direto - INSTAURACAO DE TOMADA DE CONTAS ESPECIAL (fontes: csv, opencnpj) [ORIENTADOR Q18] |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos (histórico fora da janela: processo 024.114/2006-6, trânsito em julgado 06/11/2012). [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Informação sem alerta: Presidente ASSIS GURGACZ aparece na lista de contas irregulares do TCU com os mesmos 6 dígitos centrais do CPF (art. 39, VII, a; processo 024.114/2006-6, trânsito em julgado 09/08/2012, também condenou a própria OSC; a lista não informa se a conta é de parceria, confira o acórdão) [fora da janela de 8 anos]. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. [ORIENTADOR Q22] |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 672362), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C29 - CEIS vigente sem data final

- CNPJ: `00.688.001/0001-70`.
- Entidade: ASSOCIACAO DE MULHERES DE TAIPAS.
- O que testa: `ceis`: vigência por ausência de data final.
- Status final esperado: **INAPTA**, motivos: `ceis`.
- Ambiguidades envolvidas: A09, A12.
- Depende de: [ORIENTADOR Q17], [ORIENTADOR Q22], [ORIENTADOR Q23].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 9430800 (ALTA, regra 94.30-8 (classe)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 06/07/1995 (31 ano(s) completo(s) em 01/10/2026); situação ATIVA desde 25/04/2025, possível reativação (contado desde o início, Q23): atinge o prazo para União, estados e municípios. [ORIENTADOR Q23] |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | RESTRICAO | 1 registro(s) vigente(s) em 01/10/2026: Declaração de Inidoneidade sem prazo determinado (21/02/2019 a sem data final) - Secretaria Municipal de Gestão do Município de São Paulo - SP - abrangência: Em todos os Poderes da Esfera do órgão sancionador (fontes: csv, opencnpj) => RESTRICAO. [ORIENTADOR Q17] |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. 1 homônimo(s) só por nome, sem os dígitos do CPF: sem alerta. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. [ORIENTADOR Q22] |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 962662), perfil preenchido pela OSC (tx_email). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C30 - CEIS vigente com fim futuro

- CNPJ: `30.994.499/0001-60`.
- Entidade: INSTITUTO RAFAEL ARCANJO.
- O que testa: `ceis` com data final no futuro.
- Status final esperado: **INAPTA**, motivos: `ceis`.
- Depende de: [ORIENTADOR Q15], [ORIENTADOR Q17].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8660700 (ALTA, regra 86 (divisao)); melhor faixa ALTA. [ORIENTADOR Q15] |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 29/05/2018 (8 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | RESTRICAO | 1 registro(s) vigente(s) em 01/10/2026: Suspensão/Interdição das atividades com prazo determinado (25/02/2026 a 24/02/2028) - Prefeitura Municipal de São João da Boa Vista (SP) - abrangência: Na Esfera e no Poder do órgão sancionador (fontes: csv, opencnpj) => RESTRICAO. [ORIENTADOR Q17] |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 1276649), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | OK | CEBAS não vigente (saúde): último ato 'INDEFERIDO' (REQUERIMENTO>>CONCESSÃO), publicado em 15/08/2024; situação 'PUBLICADO INDEFERIDO' no SisCEBAS de 30/09/2026. |

### C31 - CEIS vencendo em 22/11/2026

- CNPJ: `02.393.242/0001-18`.
- Entidade: ASSOCIACAO REGIONAL DA ESCOLA FAMILIA AGRICOLA DO SERTAO.
- O que testa: Fronteira de vigência do CEIS (data injetada).
- Status final esperado: **INAPTA**, motivos: `ceis`.
- Ambiguidades envolvidas: A14.
- Depende de: [ORIENTADOR Q17], [PENDENTE X17].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8520100 (ALTA, regra 85 (divisao)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 02/03/1998 (28 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | RESTRICAO | 1 registro(s) vigente(s) em 01/10/2026: Suspensão (25/02/2026 a 22/11/2026) - Governo do Estado da Bahia (BA) - abrangência: Na Esfera e no Poder do órgão sancionador (fontes: csv, opencnpj) => RESTRICAO. [ORIENTADOR Q17] |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 476342), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada decisão de certificação CEBAS (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); o CNPJ aparece só na aba de processos da planilha MDS, sem decisão [PENDENTE X17: o DOU de 12/2023 a 05/2026 pode ter a decisão]. [PENDENTE X17] |

Variante (data_referencia = 2026-11-22): status **INAPTA**.
`tempo`: OK - Início 02/03/1998 (28 ano(s) completo(s) em 22/11/2026): atinge o prazo para União, estados e municípios.
`ceis`: RESTRICAO - 1 registro(s) vigente(s) em 22/11/2026: Suspensão (25/02/2026 a 22/11/2026) - Governo do Estado da Bahia (BA) - abrangência: Na Esfera e no Poder do órgão sancionador (fontes: csv, opencnpj) => RESTRICAO.

Variante (data_referencia = 2026-11-23): status **APTA**.
`tempo`: OK - Início 02/03/1998 (28 ano(s) completo(s) em 23/11/2026): atinge o prazo para União, estados e municípios.
`ceis`: OK - Só sanções expiradas (histórico): Suspensão (25/02/2026 a 22/11/2026) - Governo do Estado da Bahia (BA) - abrangência: Na Esfera e no Poder do órgão sancionador (fontes: csv, opencnpj). TCU devolve CONSTAM_REGISTROS para o CEIS, mas todas as datas finais já passaram (D18): não é divergência.

### C32 - CEIS expirado

- CNPJ: `07.408.449/0001-32`.
- Entidade: INSTITUTO ATUAR.
- O que testa: `ceis`: OK com histórico; TCU diz CONSTAM_REGISTROS (D18).
- Status final esperado: **APTA**.
- Ambiguidades envolvidas: A15.

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8660700 (ALTA, regra 86 (divisao)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 14/02/2005 (21 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Só sanções expiradas (histórico): Declaração de Inidoneidade sem prazo determinado (07/04/2020 a 07/04/2022) - Prefeitura Municipal de Senhor do Bonfim - BA (fontes: csv, opencnpj). TCU devolve CONSTAM_REGISTROS para o CEIS, mas todas as datas finais já passaram (D18): não é divergência. |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 496622), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | OK | CEBAS não vigente (saúde): último ato 'INDEFERIDO' (REQUERIMENTO>>CONCESSÃO), publicado em 21/05/2018; situação 'PUBLICADO INDEFERIDO' no SisCEBAS de 30/09/2026. |

### C33 - CEIS 'com prazo determinado' sem data final

- CNPJ: `09.058.351/0001-28`.
- Entidade: ASSOCIACAO RECREATIVA CULTURAL E CARNAVALESCA DE SAMBA MILLENAR.
- O que testa: Dado inconsistente na fonte: vigente pela regra de data.
- Status final esperado: **INAPTA**, motivos: `ceis`.
- Ambiguidades envolvidas: A17.
- Depende de: [ORIENTADOR Q15].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 9493600 (ALTA, regra 94.93-6 (classe)); melhor faixa ALTA. [ORIENTADOR Q15] |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 24/08/2006 (20 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | RESTRICAO | 1 registro(s) vigente(s) em 01/10/2026: Declaração de Inidoneidade com prazo determinado (07/03/2020 a sem data final) - Governo do Estado da Bahia (BA) (fontes: csv, opencnpj) [categoria 'com prazo determinado' sem data final: vigente pela regra de data, revisar] => RESTRICAO. |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 498007), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C34 - CNEP

- CNPJ: `13.144.375/0001-77`.
- Entidade: INSTITUTO DE PESQUISAS CIENCIA DA METRICA - IPCIM.
- O que testa: `cnep` com multa e publicação extraordinária (Q16 provisório: ALERTA).
- Status final esperado: **APTA COM RESSALVAS**, motivos: `cnep`.
- Ambiguidades envolvidas: A17.
- Depende de: [ORIENTADOR Q16].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8542200 (ALTA, regra 85 (divisao)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 05/01/2011 (15 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | ALERTA | 2 registro(s) vigente(s) em 01/10/2026: Multa (21/10/2022 a sem data final) - Tribunal de Justiça de Minas Gerais - multa R$ 223131,65 (fontes: csv, opencnpj) [fora do art. 39, V: ALERTA] => ALERTA; Publicação extraordinária da decisão condenatória (21/10/2022 a sem data final) - Tribunal de Justiça de Minas Gerais (fontes: csv, opencnpj) [fora do art. 39, V: ALERTA] => ALERTA. [ORIENTADOR Q16] |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 784813), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C35 - Ocorrência no CNIA (CNJ)

- CNPJ: `05.051.898/0001-40`.
- Entidade: ASSOCIACAO CULTURAL DE HIP HOP DE LAGUNA -ACH2L.
- O que testa: `cnj_cnia` positiva com a mesma decisão no CEIS de origem CNJ (Q19, Q42).
- Status final esperado: **INAPTA**, motivos: `ceis`, `cnj_cnia`.
- Ambiguidades envolvidas: A09, A11.
- Depende de: [ORIENTADOR Q19], [ORIENTADOR Q23].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 9430800 (ALTA, regra 94.30-8 (classe)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 11/04/2002 (24 ano(s) completo(s) em 01/10/2026); situação ATIVA desde 25/04/2024, possível reativação (contado desde o início, Q23): atinge o prazo para União, estados e municípios. [ORIENTADOR Q23] |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | RESTRICAO | 1 registro(s) vigente(s) em 01/10/2026: Impedimento/proibição de contratar com prazo determinado (16/04/2025 a 16/04/2037) - Tribunal de Justiça do Estado de Santa Catarina / 1º Grau - TJSC / LAGUNA / Segunda Vara Cível da Comarca de Laguna (fontes: csv, opencnpj) => RESTRICAO. |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | RESTRICAO | CNIA com registro: processo 09000212620168240040 (05.051.898/0001-40): proibição de contratar vigente até 16/04/2037 (mesma decisão já listada em ceis) => RESTRICAO. [ORIENTADOR Q19] |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 724878), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C36 - CNIA + dirigente com sanção (nome e CPF)

- CNPJ: `01.081.476/0001-67`.
- Entidade: ASSOCIACAO MUSICAL 10 DE AGOSTO.
- O que testa: `ceis`, `cnj_cnia` e `dirigentes` (D15) juntas.
- Status final esperado: **INAPTA**, motivos: `cepim`, `ceis`, `cnj_cnia`.
- Ambiguidades envolvidas: A09, A11, A12.
- Depende de: [ORIENTADOR Q18], [ORIENTADOR Q19], [ORIENTADOR Q22], [ORIENTADOR Q23].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 9430800 (ALTA, regra 94.30-8 (classe)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 11/03/1996 (30 ano(s) completo(s) em 01/10/2026); situação ATIVA desde 07/01/2024, possível reativação (contado desde o início, Q23): atinge o prazo para União, estados e municípios. [ORIENTADOR Q23] |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | RESTRICAO | 1 registro(s) no CEPIM (art. 39; o CEPIM não tem datas, registro presente é impedimento): convênio 527824 - Ministério do Turismo - Unidades com vínculo direto - DESCUMPRIMENTO DE PRECEITOS DA LEI NR.8666/93 (fontes: csv, opencnpj) [ORIENTADOR Q18] |
| `ceis` | 7 | CEIS | RESTRICAO | 1 registro(s) vigente(s) em 01/10/2026: Impedimento/proibição de contratar com prazo determinado (16/12/2021 a 16/12/2031) - 1º Grau - TRF5 / Seção Judiciária de Pernambuco / Varas / Juízo / 20ª VARA FEDERAL - SALGUEIRO/PE (fontes: csv, opencnpj) => RESTRICAO. |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | RESTRICAO | CNIA com registro: processo 00011059620134058304 (01.081.476/0001-67): proibição de contratar vigente até 16/12/2031 (mesma decisão já listada em ceis) => RESTRICAO. [ORIENTADOR Q19] |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | ALERTA | Possível correspondência: Presidente JOSE CARLOS MENDES aparece no CEIS com os mesmos 6 dígitos centrais do CPF (Impedimento/proibição de contratar com prazo determinado, 16/12/2021 a 16/12/2031); confira o CPF no documento oficial. Informação sem alerta: Presidente JOSE CARLOS MENDES aparece na lista de contas irregulares do TCU com os mesmos 6 dígitos centrais do CPF (art. 39, VII, a; processo 012.775/2011-8, trânsito em julgado 16/07/2013; a lista não informa se a conta é de parceria, confira o acórdão) [fora da janela de 8 anos]. 3 homônimo(s) só por nome, sem os dígitos do CPF: sem alerta. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. [ORIENTADOR Q22] |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 960715), perfil preenchido pela OSC (tx_email). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C37 - Sanção só na filial, consulta pela filial

- CNPJ: `44.551.605/0005-70`.
- Entidade: INSTITUTO GLOBAL GESTAO EM MEDICINA E SAUDE.
- O que testa: D5: sanção da própria filial consultada.
- Status final esperado: **INAPTA**, motivos: `ceis`.
- Ambiguidades envolvidas: A05.
- Depende de: [ORIENTADOR Q15], [ORIENTADOR Q17].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA (matriz 44.551.605/0001-46); espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8640202 (ALTA, regra 86 (divisao)); melhor faixa ALTA. [ORIENTADOR Q15] |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 10/12/2021 (4 ano(s) completo(s) em 01/10/2026, data da matriz): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta partiu da filial (ATIVA); entidade avaliada pela matriz 44.551.605/0001-46 (D5). |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | RESTRICAO | 1 registro(s) vigente(s) em 01/10/2026: Suspensão (25/03/2026 a 24/03/2028) - GRUPO HOSPITALAR CONCEICAO - abrangência: No órgão sancionador (fontes: csv, opencnpj) => RESTRICAO. Fontes divergem: TCU NADA_CONSTA para 44.551.605/0001-46 e registro vigente nas bases locais; vale a restrição (D3). [ORIENTADOR Q17] |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 1371493, CNPJ da matriz), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. (CNPJ usado: 44.551.605/0001-46; consultados matriz e estabelecimento, Q28.) |

### C38 - Sanção só na filial, consulta pela matriz

- CNPJ: `44.551.605/0001-46`.
- Entidade: INSTITUTO GLOBAL GESTAO EM MEDICINA E SAUDE.
- O que testa: Q20: registro em outro estabelecimento da mesma raiz achado pela busca por raiz no CSV local.
- Status final esperado: **INAPTA**, motivos: `ceis`.
- Ambiguidades envolvidas: A16.
- Depende de: [ORIENTADOR Q15], [ORIENTADOR Q17], [ORIENTADOR Q20].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8640202 (ALTA, regra 86 (divisao)); melhor faixa ALTA. [ORIENTADOR Q15] |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 10/12/2021 (4 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | RESTRICAO | 1 registro(s) vigente(s) em 01/10/2026: Suspensão (25/03/2026 a 24/03/2028) - GRUPO HOSPITALAR CONCEICAO - abrangência: No órgão sancionador [estabelecimento 44.551.605/0005-70, outro estabelecimento] (fontes: csv) => RESTRICAO. [ORIENTADOR Q17] [ORIENTADOR Q20] |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 1371493), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C39 - INAPTA com CEIS vigente, CNIA e dirigente

- CNPJ: `06.287.661/0001-26`.
- Entidade: ASSOCIACAO MOVIMENTO EM DEFESA DE PARIPUEIRA.
- O que testa: Q1: sem parada antecipada, o relatório mostra CEIS, CNIA e dirigente de entidade já INAPTA.
- Status final esperado: **INAPTA**, motivos: `situacao`, `ceis`, `cnj_cnia`.
- Ambiguidades envolvidas: A11, A12.
- Depende de: [ORIENTADOR Q19], [ORIENTADOR Q22].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | RESTRICAO | Situação INAPTA desde 21/11/2018 (motivo: OMISSAO DE DECLARACOES). |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 9430800 (ALTA, regra 94.30-8 (classe)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 25/05/2004 (22 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | RESTRICAO | 1 registro(s) vigente(s) em 01/10/2026: Impedimento/proibição de contratar com prazo determinado (11/10/2022 a 11/10/2027) - 1º Grau - TRF5 / Seção Judiciária de Pernambuco / Varas / Juízo / 26ª VARA FEDERAL - PALMARES-/PE (fontes: csv, opencnpj) => RESTRICAO. |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | RESTRICAO | CNIA com registro: processo 08005101620174058307 (06.287.661/0001-26): proibição de contratar vigente até 11/10/2027 (mesma decisão já listada em ceis) => RESTRICAO. [ORIENTADOR Q19] |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | ALERTA | Possível correspondência: Presidente MARIA MARGARETH PEIXOTO aparece no CEIS com os mesmos 6 dígitos centrais do CPF (Impedimento/proibição de contratar com prazo determinado, 11/10/2022 a 11/10/2032); confira o CPF no documento oficial. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. [ORIENTADOR Q22] |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 925074), perfil preenchido pela OSC (tx_email). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C40 - INAPTA com inidoneidade TCU

- CNPJ: `03.463.763/0001-67`.
- Entidade: I T S - INSTITUTO TERRA SOCIAL.
- O que testa: Único tipo de OSC inidônea no TCU; Q1 mostra `tcu_inidoneos` mesmo com a entidade INAPTA.
- Status final esperado: **INAPTA**, motivos: `situacao`, `ceis`, `tcu_inidoneos`.
- Ambiguidades envolvidas: A12.
- Depende de: [ORIENTADOR Q17], [ORIENTADOR Q21], [ORIENTADOR Q22].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | RESTRICAO | Situação INAPTA desde 11/09/2018 (motivo: OMISSAO DE DECLARACOES). |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8299799 (BAIXA, regra padrao); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 14/10/1999 (26 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | RESTRICAO | 1 registro(s) vigente(s) em 01/10/2026: Declaração de Inidoneidade com prazo determinado (01/03/2023 a 01/03/2028) - TRIBUNAL DE CONTAS DA UNIÃO - abrangência: Em todos os Poderes da Esfera do órgão sancionador (fontes: csv, opencnpj) => RESTRICAO. [ORIENTADOR Q17] |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | RESTRICAO | TCU Consulta Consolidada (03.463.763/0001-67): Data da Decisão: 13/03/2019 - 016.537/2007-6 - 478/2019-PL [mesma decisão já listada em ceis: Declaração de Inidoneidade com prazo determinado até 01/03/2028]; Lista de inidôneos (03.463.763/0001-67): processo 016.537/2007-6, acórdão 478/2019-PL, sanção até 26/01/2029. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | ALERTA | CNPJ na lista de contas irregulares do TCU de 01/10/2026 com trânsito em julgado nos últimos 8 anos: processo 016.537/2007-6, trânsito em julgado 26/01/2024; processo 017.162/2007-1, trânsito em julgado 22/10/2022. A lista não informa se a conta é de parceria (art. 39, VI); confira o acórdão. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | ALERTA | Possível correspondência: Diretor EUDES COSTA DE HOLANDA JUNIOR aparece na lista de contas irregulares do TCU com os mesmos 6 dígitos centrais do CPF (art. 39, VII, a; processo 017.894/2015-8, trânsito em julgado 07/06/2025; processo 027.324/2017-6, trânsito em julgado 01/06/2020; a lista não informa se a conta é de parceria, confira o acórdão); confira o CPF no documento oficial. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. [ORIENTADOR Q22] |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 429481), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C41 - INAPTA com CEPIM + CEIS + CNEP (Santa Casa de Pacaembu)

- CNPJ: `53.524.534/0001-83`.
- Entidade: ASSOCIACAO DA IRMANDADE DA SANTA CASA DE MISERICORDIA DE PACAEMBU.
- O que testa: Q1 com várias restrições; CNEP de multa (Q16).
- Status final esperado: **INAPTA**, motivos: `situacao`, `cepim`, `ceis`.
- Ambiguidades envolvidas: A12.
- Depende de: [ORIENTADOR Q15], [ORIENTADOR Q16], [ORIENTADOR Q18], [ORIENTADOR Q22].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | RESTRICAO | Situação INAPTA desde 21/11/2023 (motivo: OMISSAO DE DECLARACOES). |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8610102 (ALTA, regra 86 (divisao)); melhor faixa ALTA. [ORIENTADOR Q15] |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 31/12/1969 (56 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | RESTRICAO | 2 registro(s) no CEPIM (art. 39; o CEPIM não tem datas, registro presente é impedimento): convênio 871244 - Ministério da Saúde - Unidades com vínculo direto - NAO APRESENTACAO DE DOCUMENTACAO COMPLEMENTAR (fontes: csv, opencnpj); convênio 834105 - Ministério da Saúde - Unidades com vínculo direto - TEVE A PRESTACAO DE CONTAS IMPUGNADA (fontes: csv, opencnpj) [ORIENTADOR Q18] |
| `ceis` | 7 | CEIS | RESTRICAO | 1 registro(s) vigente(s) em 01/10/2026: Declaração de Inidoneidade sem prazo determinado (11/02/2025 a sem data final) - Controladoria-Geral da União (fontes: csv, opencnpj) => RESTRICAO. |
| `cnep` | 8 | CNEP | ALERTA | 4 registro(s) vigente(s) em 01/10/2026: Multa (11/03/2025 a sem data final) - Controladoria-Geral da União - multa R$ 47391386,87 (fontes: csv, opencnpj) [fora do art. 39, V: ALERTA] => ALERTA; Publicação extraordinária da decisão condenatória (11/03/2025 a sem data final) - Controladoria-Geral da União (fontes: csv, opencnpj) [fora do art. 39, V: ALERTA] => ALERTA; Multa (23/01/2025 a sem data final) - Controladoria Geral do Estado de São Paulo - multa R$ 35495395,78 (fontes: csv, opencnpj) [fora do art. 39, V: ALERTA] => ALERTA; Publicação extraordinária da decisão condenatória (23/01/2025 a sem data final) - Controladoria Geral do Estado de São Paulo (fontes: csv, opencnpj) [fora do art. 39, V: ALERTA] => ALERTA. [ORIENTADOR Q16] |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | ALERTA | Possível correspondência: Presidente JOSE RODRIGUES ARAUJO aparece na relação do TCE-SP de contas do Terceiro Setor julgadas irregulares com nome e dígito verificador do CPF conferidos (art. 39, VII, a; processo 15951/989/21, trânsito em julgado 22/06/2026; processo 11297/989/20, trânsito em julgado 19/08/2025; processo 11234/989/20, trânsito em julgado 05/11/2024); confira o CPF no documento oficial. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. [ORIENTADOR Q22] |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 602125), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | OK | CEBAS não vigente (saúde): último ato 'DEFERIDO PRORROGAÇÃO PARÁGRAFO 1° ART 40 LC 187/2021' (REQUERIMENTO>>RENOVAÇÃO), publicado em 27/02/2023; situação 'PUBLICADO DEFERIDO PRORROGAÇÃO PARÁGRAFO 1° ART 40 LC 187/2021 - NÃO VIGENTE - SUPERVISÃO CANCELAMENTO' no SisCEBAS de 30/09/2026. |

### C42 - INAPTA com CEPIM + CEIS + TCU (IMDC)

- CNPJ: `21.145.289/0001-07`.
- Entidade: INSTITUTO MUNDIAL DE DESENVOLVIMENTO E DA CIDADANIA - IMDC..
- O que testa: Q1 com `cepim`, `ceis` e `tcu_inidoneos`.
- Status final esperado: **INAPTA**, motivos: `situacao`, `cepim`, `ceis`, `tcu_inidoneos`.
- Ambiguidades envolvidas: A12.
- Depende de: [ORIENTADOR Q17], [ORIENTADOR Q18], [ORIENTADOR Q21], [ORIENTADOR Q22].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | RESTRICAO | Situação INAPTA desde 18/09/2018 (motivo: OMISSAO DE DECLARACOES). |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 9430800 (ALTA, regra 94.30-8 (classe)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 11/07/1980 (46 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | RESTRICAO | 10 registro(s) no CEPIM (art. 39; o CEPIM não tem datas, registro presente é impedimento): convênio 638459 - Ministério do Turismo - Unidades com vínculo direto - IRREGULARIDADE NA EXECUCAO FIS. E FINANCEIRA (fontes: csv, opencnpj); convênio 742228 - Ministério do Turismo - Unidades com vínculo direto - MOTIVO NÃO ESPECIFICADO (fontes: csv, opencnpj); convênio 623751 - Ministério do Turismo - Unidades com vínculo direto - IRREGULARIDADE NA EXECUCAO FIS. E FINANCEIRA (fontes: csv, opencnpj); convênio 702976 - Ministério do Turismo - Unidades com vínculo direto - MOTIVO NÃO ESPECIFICADO (fontes: csv, opencnpj); convênio 650581 - Ministério do Turismo - Unidades com vínculo direto - IRREGULARIDADE NA EXECUCAO FIS. E FINANCEIRA (fontes: csv, opencnpj); convênio 702395 - Ministério do Turismo - Unidades com vínculo direto - MOTIVO NÃO ESPECIFICADO (fontes: csv, opencnpj); convênio 704323 - Ministério da Cultura - Unidades com vínculo direto - MOTIVO NÃO ESPECIFICADO (fontes: csv, opencnpj); convênio 596053 - Ministério do Turismo - Unidades com vínculo direto - IRREGULARIDADE NA EXECUCAO FIS. E FINANCEIRA (fontes: csv, opencnpj); convênio 702555 - Ministério do Turismo - Unidades com vínculo direto - MOTIVO NÃO ESPECIFICADO (fontes: csv, opencnpj); convênio 702558 - Ministério do Turismo - Unidades com vínculo direto - MOTIVO NÃO ESPECIFICADO (fontes: csv, opencnpj) [ORIENTADOR Q18] |
| `ceis` | 7 | CEIS | RESTRICAO | 3 registro(s) vigente(s) em 01/10/2026: Declaração de Inidoneidade sem prazo determinado (21/03/2015 a sem data final) - Instituto de Desenvolvimento do Norte e Nordeste de Minas Gerais - IDENE (fontes: csv, opencnpj) => RESTRICAO; Declaração de Inidoneidade sem prazo determinado (10/06/2015 a sem data final) - Instituto de Desenvolvimento do Norte e Nordeste de Minas Gerais (fontes: csv, opencnpj) => RESTRICAO; Declaração de Inidoneidade com prazo determinado (16/04/2024 a 16/04/2029) - TRIBUNAL DE CONTAS DA UNIÃO - abrangência: Em todos os Poderes da Esfera do órgão sancionador (fontes: csv, opencnpj) => RESTRICAO. [ORIENTADOR Q17] |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | RESTRICAO | TCU Consulta Consolidada (21.145.289/0001-07): Data da Decisão: 14/08/2019 - 010.925/2015-5 - 1897/2019-PL [mesma decisão já listada em ceis: Declaração de Inidoneidade com prazo determinado até 16/04/2029]; Lista de inidôneos (21.145.289/0001-07): processo 010.925/2015-5, acórdão 1897/2019-PL, sanção até 16/04/2029. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | ALERTA | CNPJ na lista de contas irregulares do TCU de 01/10/2026 com trânsito em julgado nos últimos 8 anos: processo 008.554/2020-0, trânsito em julgado 06/07/2024; processo 025.369/2017-2, trânsito em julgado 19/06/2024; processo 024.291/2020-0, trânsito em julgado 22/05/2024; processo 010.925/2015-5, trânsito em julgado 16/04/2024; processo 034.869/2016-6, trânsito em julgado 31/12/2022; processo 022.853/2015-4, trânsito em julgado 29/11/2022; processo 002.773/2015-5, trânsito em julgado 04/03/2022; processo 002.327/2015-5, trânsito em julgado 15/08/2020; processo 000.708/2015-1, trânsito em julgado 06/06/2020; processo 027.360/2012-1, trânsito em julgado 16/07/2019; processo 032.780/2014-1, trânsito em julgado 23/04/2019; processo 020.154/2015-1, trânsito em julgado 05/01/2019. A lista não informa se a conta é de parceria (art. 39, VI); confira o acórdão. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | ALERTA | Possível correspondência: Presidente DEIVSON OLIVEIRA VIDAL aparece na lista de contas irregulares do TCU com os mesmos 6 dígitos centrais do CPF (art. 39, VII, a; processo 008.554/2020-0, trânsito em julgado 17/04/2024, também condenou a própria OSC; processo 025.369/2017-2, trânsito em julgado 21/07/2023, também condenou a própria OSC; processo 010.925/2015-5, trânsito em julgado 15/06/2023, também condenou a própria OSC; processo 022.853/2015-4, trânsito em julgado 25/08/2022, também condenou a própria OSC; processo 002.773/2015-5, trânsito em julgado 21/12/2021, também condenou a própria OSC; processo 002.327/2015-5, trânsito em julgado 15/08/2020, também condenou a própria OSC; processo 000.708/2015-1, trânsito em julgado 14/12/2019, também condenou a própria OSC; processo 027.360/2012-1, trânsito em julgado 13/07/2019, também condenou a própria OSC; processo 032.780/2014-1, trânsito em julgado 23/04/2019, também condenou a própria OSC; processo 020.154/2015-1, trânsito em julgado 03/01/2019, também condenou a própria OSC; a lista não informa se a conta é de parceria, confira o acórdão); confira o CPF no documento oficial. Informação sem alerta: Presidente DEIVSON OLIVEIRA VIDAL aparece na lista de contas irregulares do TCU com os mesmos 6 dígitos centrais do CPF (art. 39, VII, a; processo 009.434/2016-0, trânsito em julgado 19/10/2017, também condenou a própria OSC; processo 017.864/2014-3, trânsito em julgado 07/01/2016, também condenou a própria OSC; processo 001.239/2015-5, trânsito em julgado 08/08/2015, também condenou a própria OSC; a lista não informa se a conta é de parceria, confira o acórdão) [fora da janela de 8 anos]. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. [ORIENTADOR Q22] |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 506146), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C43 - BAIXADA com CEPIM

- CNPJ: `14.112.015/0001-56`.
- Entidade: ASSOCIACAO DOS PAIS DE BOM JESUS DO TOCANTINS.
- O que testa: Q1: CEPIM de entidade baixada.
- Status final esperado: **INAPTA**, motivos: `situacao`, `cepim`.
- Depende de: [ORIENTADOR Q18].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | RESTRICAO | Situação BAIXADA desde 31/12/2008 (motivo: INAPTIDAO (LEI 11.941/2009 ART.54)). |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8711502 (ALTA, regra 87 (divisao)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 10/02/1988 (38 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | RESTRICAO | 1 registro(s) no CEPIM (art. 39; o CEPIM não tem datas, registro presente é impedimento): convênio 039516 - Ministério da Gestão e da Inovação em Serviços Públicos - Unidades com vínculo direto - DESCUMPRIMENTO DE CLAUSULA/CONDICAO DO INSTR. (fontes: csv, opencnpj) [ORIENTADOR Q18] |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | ALERTA | CNPJ ausente do Mapa das OSCs: possível divergência de classificação; conferir natureza (D2). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C44 - INAPTA com CEIS expirado

- CNPJ: `03.126.200/0001-83`.
- Entidade: ASSOCIACAO PLURAL.
- O que testa: Q1: categoria 'sem prazo' com data final passada (OK com histórico).
- Status final esperado: **INAPTA**, motivos: `situacao`.
- Ambiguidades envolvidas: A12, A14, A15.
- Depende de: [ORIENTADOR Q22], [PENDENTE X17].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | RESTRICAO | Situação INAPTA desde 12/05/2026 (motivo: OMISSAO DE DECLARACOES). |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8630502 (ALTA, regra 86 (divisao)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 07/04/1999 (27 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Só sanções expiradas (histórico): Declaração de Inidoneidade sem prazo determinado (18/11/2019 a 18/11/2021) - Fundação Hospitalar Getúlio Vargas - RS - abrangência: No órgão sancionador (fontes: csv, opencnpj). TCU devolve CONSTAM_REGISTROS para o CEIS, mas todas as datas finais já passaram (D18): não é divergência. |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | ALERTA | Possível correspondência: Diretor LIGIA RIBEIRO DE CARVALHO aparece na relação do TCE-SP de contas do Terceiro Setor julgadas irregulares com nome e dígito verificador do CPF conferidos (art. 39, VII, a; processo 27121/026/16, trânsito em julgado 24/10/2023; processo 12903/026/17, trânsito em julgado 24/10/2023); confira o CPF no documento oficial. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. [ORIENTADOR Q22] |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 591615), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Há pedido em análise sem decisão publicada (SisCEBAS: 'CONCESSÃO - MANIFESTAÇÃO MEC (DIGAD)'). Ausência de decisão não significa que a entidade não possui CEBAS (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026). [PENDENTE X17] |

### C45 - INAPTA com CNEP

- CNPJ: `08.928.169/0001-18`.
- Entidade: INSTITUTO ILUMINA TERRA ACAO PARA DESENVOLVIMENTO SOCIAL.
- O que testa: Q1 com CNEP de multa (Q16).
- Status final esperado: **INAPTA**, motivos: `situacao`.
- Depende de: [ORIENTADOR Q16], [ORIENTADOR Q17].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | RESTRICAO | Situação INAPTA desde 10/01/2022 (motivo: OMISSAO DE DECLARACOES). |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8550302 (ALTA, regra 85 (divisao)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 26/06/2007 (19 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | ALERTA | 1 registro(s) vigente(s) em 01/10/2026: Multa (10/01/2023 a sem data final) - Controladoria-Geral do Município de São Paulo - SP - multa R$ 6000,00 - abrangência: Em todos os Poderes da Esfera do órgão sancionador (fontes: csv, opencnpj) [fora do art. 39, V: ALERTA] => ALERTA. [ORIENTADOR Q16] [ORIENTADOR Q17] |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 586692), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

### C46 - INAPTA com CNIA + CEIS + CEPIM (AVAPE)

- CNPJ: `43.337.682/0001-35`.
- Entidade: ASSOCIACAO PARA VALORIZACAO DE PESSOAS COM DEFICIENCIA.
- O que testa: Q1 com CNIA (Q19) e sanção em outro estabelecimento (Q20).
- Status final esperado: **INAPTA**, motivos: `situacao`, `cepim`, `ceis`, `cnj_cnia`.
- Ambiguidades envolvidas: A11, A12, A14, A16.
- Depende de: [ORIENTADOR Q17], [ORIENTADOR Q18], [ORIENTADOR Q19], [ORIENTADOR Q20], [ORIENTADOR Q21], [ORIENTADOR Q22], [PENDENTE X17].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | RESTRICAO | Situação INAPTA desde 20/12/2018 (motivo: OMISSAO DE DECLARACOES). |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 9430800 (ALTA, regra 94.30-8 (classe)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 06/10/1982 (43 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | RESTRICAO | 1 registro(s) no CEPIM (art. 39; o CEPIM não tem datas, registro presente é impedimento): convênio 708662 - Ministério do Turismo - Unidades com vínculo direto - IRREGULARIDADE NA EXECUCAO FIS. E FINANCEIRA (fontes: csv, opencnpj) [ORIENTADOR Q18] |
| `ceis` | 7 | CEIS | RESTRICAO | 5 registro(s) vigente(s) em 01/10/2026: Impedimento/proibição de contratar com prazo determinado (11/05/2022 a 11/05/2027) - Tribunal de Justiça do Estado de São Paulo / 1º Grau - TJSP / ARACATUBA / FAZENDA PUBLICA DE ARACATUBA (fontes: csv, opencnpj) => RESTRICAO; Impedimento/proibição de contratar com prazo determinado (26/03/2023 a 25/03/2028) - PROCURADORIA GERAL DO ESTADO - abrangência: Em todos os Poderes da Esfera do órgão sancionador (fontes: csv, opencnpj) => RESTRICAO; Impedimento/proibição de contratar com prazo determinado (18/11/2022 a 17/11/2027) - PROCURADORIA GERAL DO ESTADO - abrangência: Em todos os Poderes da Esfera do órgão sancionador (fontes: csv, opencnpj) => RESTRICAO; Impedimento/proibição de contratar com prazo determinado (27/03/2023 a 27/03/2028) - Controladoria Geral do Estado de São Paulo (fontes: csv, opencnpj) => RESTRICAO; Impedimento/proibição de contratar com prazo determinado (27/03/2023 a 27/03/2028) - Controladoria Geral do Estado de São Paulo [estabelecimento 43.337.682/0031-50, outro estabelecimento] (fontes: csv) => RESTRICAO. [ORIENTADOR Q17] [ORIENTADOR Q20] |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | RESTRICAO | CNIA com registro: processo 10021337720158260032 (43.337.682/0001-35): proibição de contratar vigente até 11/05/2027 (mesma decisão já listada em ceis) => RESTRICAO; processo 00031114620128260624 (43.337.682/0001-35): proibição de contratar vigente até 17/11/2027 (mesma decisão já listada em ceis) => RESTRICAO. [ORIENTADOR Q19] |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | ALERTA | CNPJ na lista de contas irregulares do TCU de 01/10/2026 com trânsito em julgado nos últimos 8 anos: processo 025.809/2021-0, trânsito em julgado 27/03/2024. A lista não informa se a conta é de parceria (art. 39, VI); confira o acórdão. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | ALERTA | Possível correspondência: Presidente CARLOS EDUARDO FERRARI aparece na relação do TCE-SP de contas do Terceiro Setor julgadas irregulares com nome e dígito verificador do CPF conferidos (art. 39, VII, a; processo 867/014/14, trânsito em julgado 06/09/2019); confira o CPF no documento oficial. Informação sem alerta: Presidente CARLOS EDUARDO FERRARI aparece na relação do TCE-SP de contas do Terceiro Setor julgadas irregulares com nome e dígito verificador do CPF conferidos (art. 39, VII, a; processo 1293/001/14, trânsito em julgado 20/09/2018) [fora da janela de 8 anos]. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. [ORIENTADOR Q22] |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 594761), perfil preenchido pela OSC (tx_email). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada decisão de certificação CEBAS (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); o CNPJ aparece só na aba de processos da planilha MDS, sem decisão [PENDENTE X17: o DOU de 12/2023 a 05/2026 pode ter a decisão]. [PENDENTE X17] |

### C47 - CEBAS Saúde ativo (Santa Casa de Cerquilho)

- CNPJ: `50.798.453/0001-83`.
- Entidade: SANTA CASA DE MISERICORDIA DE CERQUILHO.
- O que testa: `cebas` OK pelo SisCEBAS Saúde.
- Status final esperado: **APTA**.
- Depende de: [ORIENTADOR Q15].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8610101 (ALTA, regra 86 (divisao)); melhor faixa ALTA. [ORIENTADOR Q15] |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 14/07/1982 (44 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos (histórico fora da janela: processo 010.034/2008-8, trânsito em julgado 22/10/2010). [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 598928), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | OK | CEBAS ativo (saúde) segundo SisCEBAS de 30/09/2026: portaria 4683 publicada em 14/08/2026, vigência 01/01/2024 a 31/12/2026. |

### C48 - CEBAS não vigente (concessão indeferida)

- CNPJ: `00.001.297/0001-00`.
- Entidade: CASA DE APOIO E ASSISTENCIA SOCIAL SANTA LUZIA.
- O que testa: `cebas`: último ato é indeferimento.
- Status final esperado: **APTA**.
- Ambiguidades envolvidas: A09.
- Depende de: [ORIENTADOR Q23].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | OK | CNAE principal 8660700 (ALTA, regra 86 (divisao)); melhor faixa ALTA. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 04/05/1982 (44 ano(s) completo(s) em 01/10/2026); situação ATIVA desde 14/05/2026, possível reativação (contado desde o início, Q23): atinge o prazo para União, estados e municípios. [ORIENTADOR Q23] |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | OK | Nenhum registro no CEPIM (CSV CEPIM de 28/09/2026, OpenCNPJ ?datasets=). |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 955838), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | OK | CEBAS não vigente (saúde): último ato 'INDEFERIDO' (REQUERIMENTO>>CONCESSÃO), publicado em 30/01/2023; situação 'PUBLICADO INDEFERIDO' no SisCEBAS de 30/09/2026. |

### C49 - Associação profissional (CNAE 94.12) com CEPIM

- CNPJ: `26.447.003/0001-61`.
- Entidade: ASSOCIACAO BRASILEIRA DE MASTOLOGIA - REGIONAL DO DISTRITO FEDERAL.
- O que testa: CNAE BAIXA explícita e presença no Mapa de associação de categoria.
- Status final esperado: **INAPTA**, motivos: `cepim`.
- Depende de: [ORIENTADOR Q18].

| id | Spec | Verificação | Estado esperado | Justificativa |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | OK | Formato e dígitos verificadores conferem. |
| `situacao` | 2 | Situação cadastral | OK | ATIVA; espelho cadastral de 15/09/2026. |
| `natureza` | 3 | Natureza jurídica | OK | Natureza 3999 (Associação Privada) elegível. |
| `cnae` | 4 | CNAE de relevância social | ALERTA | CNAE principal 9412099 (BAIXA); melhor faixa BAIXA. Nenhuma atividade cadastrada tem relação direta com relevância social; confira o estatuto. |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | OK | Não se aplica: natureza diferente de 3220 e CNAE principal diferente de 94.91-0. |
| `tempo` | 5 | Tempo de existência | OK | Início 22/08/1990 (36 ano(s) completo(s) em 01/10/2026): atinge o prazo para União, estados e municípios. |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | OK | Consulta feita pela matriz. |
| `cepim` | 6 | CEPIM | RESTRICAO | 1 registro(s) no CEPIM (art. 39; o CEPIM não tem datas, registro presente é impedimento): convênio 400035 - Ministério da Saúde - Unidades com vínculo direto - INSTAURACAO DE TOMADA DE CONTAS ESPECIAL (fontes: csv, opencnpj) [ORIENTADOR Q18] |
| `ceis` | 7 | CEIS | OK | Nenhum registro no CEIS (CSV CEIS de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `cnep` | 8 | CNEP | OK | Nenhum registro no CNEP (CSV CNEP de 30/09/2026, OpenCNPJ ?datasets=, TCU Consulta Consolidada). |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | OK | Nada consta (TCU Consulta Consolidada, lista de inidôneos do TCU de 30/09/2026); vale para hoje, com as ressalvas do spec 12.4. |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | OK | CNIA: NADA_CONSTA na Consulta Consolidada do TCU. |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) | OK | Nada na lista de contas irregulares do TCU de 01/10/2026 nos últimos 8 anos. [ORIENTADOR Q21] |
| `dirigentes` | 10 | Dirigentes (QSA) | OK | 1 dirigente(s) pessoa física sem correspondência (nome + 6 dígitos do CPF; no TCE-SP, nome + DV) em CEIS, CNEP, TCU (contas irregulares nos últimos 8 anos e inabilitados) e TCE-SP Terceiro Setor. Dirigentes fora do QSA, que costuma trazer só o presidente, não são verificados. |
| `mapa_osc` | 11 | Mapa das OSCs | OK | Presente no Mapa (id_osc 784332), só dados automáticos da Receita (sugerir que a OSC complete o perfil). |
| `cebas` | 12 | CEBAS | NAO_VERIFICADO | Não foi encontrada certificação CEBAS nas bases consultadas (SisCEBAS Saúde 30/09/2026, planilhas MDS 2024 e MEC 2023, DOU jun a ago/2026); isso não significa que a entidade não possui CEBAS. |

## Ambiguidades encontradas nas regras e como foram resolvidas

Cada item é um ponto em que o spec 1.1 e as decisões não fechavam o resultado esperado.
A resolução cita a pergunta da revisão pré-código (`revisao_pre_codigo.md`) que a fechou; as marcadas como provisórias seguem a recomendação da revisão até o orientador responder.

### A01 - Estado das verificações não executadas depois de uma eliminatória no portão cadastral (resolvida)

- Regra antes: Spec 1.1, 2.2: DV inválido, situação diferente de ATIVA e natureza não elegível levavam a INAPTA (fim), sem dizer o estado das demais.
- Resolução: Q1 (DONO, D19): sem parada antecipada. Com DV válido e cadastro encontrado, tudo é avaliado e o relatório mostra todas as restrições; o status continua INAPTA. A coluna `estado_sem_parada` deixou de existir.
- Casos afetados: nenhum caso do conjunto (regra registrada para o motor).

### A02 - Status final quando uma eliminatória fica NAO_VERIFICADO (resolvida)

- Regra antes: Spec 1.1, 2.5 só definia INCONCLUSIVA para eliminatória INDISPONIVEL; D4 manda o alfanumérico para NAO_VERIFICADO.
- Resolução: Q2 (DONO, D19): INCONCLUSIVA com mensagem própria do alfanumérico; spec 1.2, 2.5 inclui NAO_VERIFICADO.
- Casos afetados: C05, C06.

### A03 - CNPJ com DV válido que não existe na base cadastral (resolvida)

- Regra antes: Spec 1.1, 5.4 usava INDISPONIVEL para 'não encontrado' e para 'fonte fora do ar'.
- Resolução: Q26 (TECNICO, D20): `situacao` INDISPONIVEL com motivo NAO_ENCONTRADO e texto 'não encontrado no espelho de DD/MM/AAAA'; fan-out não roda; demais NAO_VERIFICADO; status INCONCLUSIVA.
- Casos afetados: C07.

### A04 - Filial com situação diferente da matriz (resolvida)

- Regra antes: D5 só fechava o caso de matriz baixada.
- Resolução: Q4 (DONO, D19): matriz ativa e filial não ativa = ALERTA na verificação `estabelecimento`; `situacao` avalia a entidade (matriz).
- Casos afetados: C24.

### A05 - Qual CNPJ consultar no Mapa das OSCs e no CEBAS quando a entrada é filial (resolvida)

- Regra antes: D5 não definia Mapa nem CEBAS.
- Resolução: Q28 (TECNICO, D20): Mapa pela matriz; CEBAS pela matriz e pelo estabelecimento consultado (vale o mais informativo).
- Casos afetados: C23, C24, C37.

### A06 - Matriz que não tem ordem 0001 (resolvida)

- Regra antes: D5 não dizia em qual verificação cai o ALERTA nem como seguir.
- Resolução: Q27 (TECNICO, D20): matriz detectada só por `matriz_filial`; se raiz + 0001 for filial, ALERTA em `estabelecimento` pedindo o CNPJ da matriz, e avaliação com os dados do estabelecimento consultado (tempo pela data dele, com aviso).
- Casos afetados: C26, C27.

### A07 - Em qual verificação cai o alerta de organização religiosa (resolvida)

- Regra antes: Spec 1.1, 6.3 e 7.5 e casos v1.1 punham o alerta na verificação 4.
- Resolução: Q25 (TECNICO, D20): verificação própria `religiosa` (spec 4).
- Casos afetados: C12, C13.

### A08 - Contagem de anos na fronteira do art. 33, V, a (resolvida)

- Regra antes: Spec e D6 não diziam se o dia do aniversário conta.
- Resolução: Q29 (TECNICO, D20): anos completos, com o aniversário contando; 29/02 faz aniversário em 28/02 em ano não bissexto.
- Casos afetados: C21, C22.

### A09 - Tempo 'com cadastro ativo' quando a entidade foi reativada (provisória)

- Regra antes: Art. 33, V, a pede tempo 'com cadastro ativo'; spec 8.1 usa data_inicio_atividade.
- Resolução: [ORIENTADOR Q23] provisório: conta desde data_inicio_atividade e cita a data da situação no texto (parâmetro Q23_tempo).
- Casos afetados: C17, C22, C29, C35, C36, C48.

### A10 - Sanção no último dia de vigência (resolvida)

- Regra antes: Spec 10.4: vigente sem data de fim ou com data de fim igual ou posterior a hoje (a v1.1 dos casos citava por engano o 10.3).
- Resolução: Q30 (TECNICO, D20): vigente até a data final inclusive. C31 em 22/11/2026 é RESTRICAO; em 23/11/2026 é OK com histórico.
- Casos afetados: nenhum caso do conjunto (regra registrada para o motor).

### A11 - CNIA sem datas (provisória)

- Regra antes: A resposta do CNIA traz só o número do processo, sem data nem prazo.
- Resolução: [ORIENTADOR Q19] provisório: RESTRICAO só se o processo do CNIA tiver proibição de contratar vigente no CEIS (mesmo número de processo); registro achado só expirado ou sem correspondência no CEIS = ALERTA. Q42: o achado indica 'mesma decisão listada em ceis'.
- Casos afetados: C35, C36, C39, C46.

### A12 - Dirigentes: correspondência só por nome e sanção expirada (provisória)

- Regra antes: Spec 13.5 usa nome + 6 dígitos do meio do CPF (a v1.1 dos casos citava por engano o 13.4 como busca só por nome).
- Resolução: [ORIENTADOR Q22] provisório: ALERTA só para nome + 6 dígitos (TCE-SP: nome + DV) com sanção vigente ou trânsito em julgado nos últimos 8 anos e hipótese do art. 39; categorias de servidor (Demissão, Suspensão), achados fora da janela e só nome ficam como informação. Fontes do Q8 (DONO, opção C, D15): CEIS, CNEP, TCU contas irregulares, TCU inabilitados e TCE-SP Terceiro Setor.
- Casos afetados: C28, C29, C36, C39, C40, C41, C42, C44, C46.

### A13 - CEBAS com renovação tempestiva pendente ou vigência vencida (provisória)

- Regra antes: D16: validade vencida sem ato novo = 'possível renovação em análise'.
- Resolução: [ORIENTADOR Q24] provisório: sem limite de tempo, com a idade explícita no texto. Q40: `situacao` EM_RENOVACAO. Casos de planilha MDS/MEC marcados [PENDENTE X17] até a carga do DOU desde 12/2023 (Q39).
- Casos afetados: C16, C23, C25.

### A14 - CEBAS com pedido sem decisão e linhas de processo (resolvida)

- Regra antes: Spec 15.3: nenhuma decisão encontrada = NAO_VERIFICADO.
- Resolução: Q31 (TECNICO, D20): NAO_VERIFICADO com 'há pedido em análise sem decisão publicada' (`situacao` PEDIDO_EM_ANALISE); linha só na aba de processos da planilha MDS fica NAO_ENCONTRADO com a observação.
- Casos afetados: C31, C44, C46.

### A15 - TCU devolve CEIS/CNEP CONSTAM_REGISTROS para sanções expiradas (D18) (resolvida)

- Regra antes: D3 original mandava RESTRICAO em qualquer divergência.
- Resolução: Q7 (DONO, D18 aprovado) e Q35 (TECNICO): vigência pelas datas dos registros (CSV local e OpenCNPJ); só depois a divergência. TCU com registro e nenhuma base local com registro: data entre parênteses da `observacao`; todas passadas = OK com aviso 'registro só no TCU'; alguma futura ou ilegível = RESTRICAO.
- Casos afetados: C32, C44.

### A16 - Sanção registrada só em outro estabelecimento da mesma raiz (provisória)

- Regra antes: D5 não tratava sanção de filial quando a entrada é a matriz; com D14 o CSV local permite busca por raiz.
- Resolução: [ORIENTADOR Q20] provisório: registro em qualquer estabelecimento da raiz conta como o do consultado (RESTRICAO), com o estabelecimento indicado no texto (parâmetro Q20_raiz).
- Casos afetados: C26, C27, C38, C46.

### A17 - Dado de origem inconsistente ou duplicado (resolvida)

- Regra antes: D14: vigência pela data, nunca pela categoria.
- Resolução: Q32 (TECNICO, D20): 'com prazo determinado' sem data final = vigente com aviso; duplicados agrupados por categoria + datas + órgão; '0' e '' em datas = nulo.
- Casos afetados: C26, C27, C33, C34.

## Casos não encontrados

| Caso procurado | O que foi tentado | Cobertura parcial no conjunto |
|---|---|---|
| Associação ATIVA e elegível ausente do Mapa das OSCs (D2 isolado) | Todas as associações ativas consultadas (mais de 30) estavam no Mapa. As 15 marcadas `removida_do_mosc = sim` e 'Ativa' nas fatias da base do Mapa estão BAIXADAS hoje na Receita. 300 raízes sorteadas depois da última carga do Mapa (`buscar_ausente_mapa.py`, sementes 20261001 e 7) não trouxeram nenhuma associação (só MEI, LTDA e afins). | C14 (cooperativa ausente do Mapa, ALERTA junto com a natureza) e C24 (filial ausente, matriz presente, Q28). |
| OSC ATIVA declarada inidônea pelo TCU | A lista de inidôneos tem 128 CNPJs e só 2 OSCs (ITS e IMDC), ambas INAPTAS na Receita. | C40 e C42 cobrem `tcu_inidoneos` em RESTRICAO, agora avaliado mesmo com a entidade INAPTA (Q1). |
| Dirigente com sanção em entidade sem sanção própria | 5 PJs do CEIS com todas as sanções expiradas e ativas na Receita: nenhum dirigente casou nome + CPF. Com as listas do TCU e do TCE-SP (Q8), todos os achados caíram em entidades já sancionadas ou INAPTAS. | C36, C39 a C42, C44 e C46 têm dirigente com achado, mas a própria entidade também é sancionada ou INAPTA; C28 tem achado no TCU só fora da janela de 8 anos. |
| Associação com situação NULA (código 1) | Não apareceu nas fatias da base do Mapa (o Mapa agrupa 'Nula ou Baixada'). | C08 a C10 cobrem BAIXADA, INAPTA e SUSPENSA. |
| CEBAS da Educação (MEC) | Nenhum CNPJ do conjunto está na planilha MEC de 2023 nem em ato do MEC no DOU de jun a ago/2026. | CEBAS saúde (C47, C48, C25) e assistência social (C16). |
| Certificado autodeclarado no Mapa | Pendência P4 (não procurado nesta rodada). | Perfil preenchido pela OSC em C16 e outros. |
| Fonte INDISPONIVEL e base local vencida | Não é reproduzível com um CNPJ real: depende de falha da fonte ou de data. | Os testes do motor precisam injetar timeout, 5xx, `SISTEMA_INDISPONIVEL` e `ERRO` do TCU, matriz sem resposta (Q44) e base mais velha que o limite (Q6). |
| CNIA com proibição já encerrada no CEIS | Nos 6 casos com CNIA, a proibição de contratar no CEIS está vigente. | O caminho ALERTA do Q19 está no código, sem caso real. |

Encontrados na rodada de 01/10/2026: associação INAPTA (C09), associação SUSPENSA (C10), Organização Social 3301 (C15), ocorrência no CNIA (C35 e C36, também C39 e C46), CNAE comercial BAIXA (C17), igreja como associação (C13), fronteiras de 1 e 2 anos (C21, C22), matriz fora da ordem 0001 (C26, C27).

## Achados da coleta que afetam fichas e decisões

- Muitos casos de sanção das fichas anteriores estão INAPTOS ou BAIXADOS na Receita: Paripueira, ITS, IMDC, Pacaembu, AVAPE, Ilumina Terra, Associação Plural e Bom Jesus (BAIXADA). Com Q1 eles mostram todas as restrições (C39 a C46).
- O CNPJ 07.408.449/0001-32 se chama hoje INSTITUTO ATUAR (no CEIS ainda aparece como INSTITUTO CAMINHADA).
- Na IDEAS (24.006.302), o estabelecimento 0004-88 é a matriz e o 0001-35 é filial: o motor precisa usar `matriz_filial` e não a ordem (Q27).
- A IDEAS tem a mesma sanção do TRF4 registrada em 5 estabelecimentos; com a busca por raiz (Q20) todos aparecem.
- O OpenCNPJ devolve `data_situacao_cadastral` = '0' para a matriz do Instituto GRPCOM e registros de sanção duplicados no `?datasets=` (CNEP do IPCIM, CEIS da IDEAS).
- O CNIA devolve só o número do processo, sem data; o mesmo número aparece no CEIS de origem CNJ com as datas (Q19, Q42).
- A Consulta Consolidada do TCU devolve CEIS CONSTAM_REGISTROS também para sanções expiradas (D18), confirmado em C31 (variante de 23/11/2026), C32 e C44.
- Dirigentes com as fontes do Q8 (opção C): TCU contas irregulares em C40 e C42 (em C42, todos os processos também condenaram a própria OSC), TCE-SP Terceiro Setor em C41, C44 e C46 (nome + DV), e só fora da janela de 8 anos em C28 e C36; nenhum achado na lista de inabilitados do TCU.

## Como reproduzir

A partir da raiz do projeto:

1. `.venv/Scripts/python fase0/casos/coletar.py` consulta OpenCNPJ, OpenCNPJ `?datasets=`, TCU e Mapa para todos os casos e salva em `fase0/casos/respostas/<cnpj>/`.
2. `.venv/Scripts/python fase0/casos/montar_casos.py` aplica as regras e gera `fase0/casos_referencia.json` e este arquivo. As bases locais usadas são os CSVs da CGU em `fase0/portal/downloads/`, a lista de inidôneos em `fase0/tcu/respostas/`, as listas do TCU (contas irregulares e inabilitados) e a planilha do TCE-SP em `fase0/dirigentes/downloads/` (lidas com `fase0/dirigentes/casar_dirigentes.py`) e as bases de CEBAS de `fase0/cebas_dou/` e `fase0/mapa_osc/`.
3. Para trocar uma regra provisória do orientador, mudar o valor em `REGRAS_ORIENTADOR` no início de `montar_casos.py` e rodar o passo 2.
4. Scripts de busca usados para achar os casos: `amostra_mapa.py` (fatias da base do Mapa), `buscar_cnia.py`, `buscar_ativos.py`, `buscar_extras.py` e `buscar_ausente_mapa.py`.

Os dados mudam: antes de usar como teste E2E contra as fontes reais, rodar de novo os dois primeiros passos e revisar a diferença no JSON.
Para o teste de regressão do motor, usar as respostas salvas como mocks das fontes.
