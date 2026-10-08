# Fase 0 - Fontes cadastrais de CNPJ (BrasilAPI, Minha Receita, OpenCNPJ)

Ficha de documentação no formato da seção 25.2 do spec, com o roteiro 18.3 (T1 a T7) executado nas três fontes.
Testes executados entre 01/10/2026 01:00 e 03:00 UTC (noite de 30/09/2026 no horário de Brasília), a partir de conexão residencial no Brasil.
User-Agent usado em todas as chamadas: `validador-osc-ifsp/0.1 (projeto academico de extensao)`.
Pausa de 1 s entre chamadas, exceto na rajada do T6.
Nenhum bloqueio, CAPTCHA ou HTTP 429 foi encontrado.

## Resumo executivo

- **OpenCNPJ foi a única fonte estável**: 100% das chamadas responderam, com mediana abaixo de 100 ms, e é a única que já devolve CNPJ alfanumérico real.
- **Minha Receita esteve instável durante toda a janela de teste**: a maioria das chamadas sem cache devolveu HTTP 503 depois de cerca de 10 s.
- **BrasilAPI é um proxy da Minha Receita com cache na Vercel**: o schema e os valores são idênticos aos da Minha Receita, e quando a Minha Receita cai, toda consulta sem cache na BrasilAPI falha (HTTP 500 ou 504 depois de cerca de 10 s).
  Ou seja, Minha Receita não é um fallback independente da BrasilAPI: as duas caem juntas.
- **OpenCNPJ não tem `codigo_natureza_juridica`**: só a descrição em texto ("Associação Privada").
  Isso quebra a tabela de regras do cap. 6 se o OpenCNPJ for usado sem um mapeamento descrição -> código.
- **`cnae_fiscal` é número na BrasilAPI/Minha Receita e perde o zero à esquerda** (cooperativa E3: `220903` em vez de `0220903`).
  No OpenCNPJ é string de 7 dígitos com o zero.
- **Recomendação**: OpenCNPJ como fonte principal da etapa cadastral, BrasilAPI como fallback (que já cobre a Minha Receita por baixo), com um normalizador comum que converte as duas para o mesmo modelo interno.
  Detalhes na seção "Recomendação".

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `comum.py` | Cliente HTTP, gravação das respostas, algoritmo de DV do cap. 4 e gerador de CNPJ com DV válido. |
| `roteiro.py` | Executa T1-T5, T7 e os extras do 25.1 nas três fontes. `--so-pendentes` refaz só o que falhou (5xx/timeout) e arquiva a falha em `respostas/falhas/`. |
| `retentar_pendentes.sh` | Laço que chama `roteiro.py --so-pendentes` a cada 5 min (usado por causa da instabilidade da Minha Receita). |
| `t6_latencia.py` | T6: rajada de 20 consultas na BrasilAPI e 5 em cada fallback, sem pausa. `--distintos` força cache miss (T6b). |
| `consultar.py` | Consulta avulsa (usado na triagem de candidatos). |
| `tabela_resultados.py` | Gera a tabela caso x fonte e as estatísticas de falha a partir de `respostas/`. |
| `respostas/{fonte}_{caso}_{cnpj}.json` | Resposta bruta definitiva (200/400/404): HTTP, ms, headers relevantes e corpo. |
| `respostas/falhas/` | Todas as tentativas com 5xx ou timeout, preservadas como evidência de instabilidade. |
| `respostas/extras/` | `/info` do OpenCNPJ e exemplo do parâmetro `?datasets=`. |
| `respostas/_log_roteiro.txt` | Saída de console de todas as rodadas. |

Para reproduzir, a partir de `fase0\brasilapi`: `..\..\.venv\Scripts\python roteiro.py`, depois `bash retentar_pendentes.sh` se houver 5xx, `..\..\.venv\Scripts\python t6_latencia.py` e `..\..\.venv\Scripts\python tabela_resultados.py`.

## CNPJs de referência encontrados (para o conjunto 25.1)

| Caso | CNPJ | Razão social | O que testa |
|---|---|---|---|
| T1 | 19.131.243/0001-97 | OPEN KNOWLEDGE BRASIL | OSC regular: natureza 3999, situação 2, CNAE 9430800 (ALTA), desde 2013. |
| T2 | 00.000.000/0001-91 | BANCO DO BRASIL SA | Natureza 2038 (Sociedade de Economia Mista), não elegível. |
| T3 | 94.580.730/0001-52 | (inexistente) | Raiz aleatória com DV válido (seed 5 de `gerar_aleatorio`); 404 no OpenCNPJ; BrasilAPI e Minha Receita só deram 5xx. |
| T3b | 19.131.243/0001-98 | - | DV inválido: mostra quais fontes validam o DV. |
| T4 | 08.942.107/0001-60 | ASSOCIACAO DE INCLUSAO E DESENVOLVIMENTO SOCIAL POR UM RIO MELHOR | Associação privada BAIXADA (situação 8) desde 2012-01-04, motivo 01 "EXTINCAO POR ENCERRAMENTO LIQUIDACAO VOLUNTARIA". |
| T5 | 12.ABC.345/01DE-35 | (exemplo oficial, não existe) | Alfanumérico com DV válido: as três fontes aceitam o formato e devolvem 404. |
| T5r | 00.000.000/E08G-12 | BANCO DO BRASIL SA (filial) | Alfanumérico REAL, primeiro emitido pela Receita (31/07/2026). Natureza 2038, filial. |
| T7 | 62.779.145/0002-70 | IRMANDADE DA SANTA CASA DE MISERICORDIA DE SAO PAULO (Hospital São Luiz Gonzaga) | Filial ATIVA (identificador_matriz_filial = 2) de associação com CEBAS. |
| T7m | 62.779.145/0001-90 | IRMANDADE DA SANTA CASA DE MISERICORDIA DE SAO PAULO | Matriz da T7. Também serve para o caso "Entidade com CEBAS" do 25.1. |
| T7b | 04.955.882/0005-23 | INSTITUTO GRPCOM | Filial BAIXADA (desde 2017-01-05) com matriz ATIVA; data_inicio_atividade da filial (2011) difere da matriz (2002). |
| T7bm | 04.955.882/0001-08 | INSTITUTO GRPCOM | Matriz ATIVA da T7b, natureza 3999, CNAE 9430800. |
| E1 | 65.478.551/0001-00 | ASSOCIACAO MATURIDADE EM MOVIMENTO | Associação ATIVA aberta em 2026-02-03 (menos de 1 ano): ALERTA de tempo de existência. |
| E2 | 00.108.217/0001-10 | MITRA ARQUIDIOCESANA DE BRASILIA | Organização religiosa (3220), CNAE 9491000 só religioso, sem secundários: ALERTA art. 2º, I, c. |
| E3 | 04.311.762/0001-60 | COOPERATIVA MISTA DOS TRABALHADORES AGRO-EXTRATIVISTAS DO ALTO CAJARI | Cooperativa (2143): REVISÃO MANUAL; CNAE com zero à esquerda (0220903). |

Outros CNPJs vistos na triagem e que podem ser úteis: 24.658.352/0001-05 (COMFORMED VINTEM, associação baixada), 00.007.138/0001-12 (MITRA DIOCESANA DE TOCANTINOPOLIS, 3220), 04.513.910/0001-29 (cooperativa de trabalho de atletas, 2143), 62.779.145/0003-51 e 0005-13 (filiais baixadas da Santa Casa).
Não foi encontrado um CNPJ INAPTO (situação 4) de associação em tempo razoável; fica como pendência para o conjunto 25.1.

## Resultados por caso

| Caso | CNPJ | brasilapi | minhareceita | opencnpj |
|---|---|---|---|---|
| E1 | 65478551000100 | 200 (582 ms) nat=3999 sit=2 mf=1 | 200 (9737 ms) nat=3999 sit=2 mf=1 | 200 (64 ms) nat=Associação Privada sit=Ativa mf=Matriz |
| E2 | 00108217000110 | 200 (10134 ms) nat=3220 sit=2 mf=1 | 200 (310 ms) nat=3220 sit=2 mf=1 | 200 (73 ms) nat=Organização Religiosa sit=Ativa mf=Matriz |
| E3 | 04311762000160 | 200 (5912 ms) nat=2143 sit=2 mf=1 | 200 (6714 ms) nat=2143 sit=2 mf=1 | 200 (66 ms) nat=Cooperativa sit=Ativa mf=Matriz |
| T1 | 19131243000197 | 200 (136 ms) nat=3999 sit=2 mf=1 | 200 (434 ms) nat=3999 sit=2 mf=1 | 200 (62 ms) nat=Associação Privada sit=Ativa mf=Matriz |
| T2 | 00000000000191 | 200 (62 ms) nat=2038 sit=2 mf=1 | 200 (605 ms) nat=2038 sit=2 mf=1 | 200 (25 ms) nat=Sociedade de Economia Mista sit=Ativa mf=Matriz |
| T3 | 94580730000152 | 500 (10083 ms) falha 5xx (histórico em respostas/falhas/) | 503 (10138 ms) falha 5xx (histórico em respostas/falhas/) | 404 (76 ms) {"error": "not found"} |
| T3b | 19131243000198 | 400 (507 ms) {"message": "CNPJ 19.131.243/0001-98 inválido.", "type": "ba | 400 (295 ms) {"message": "CNPJ 19.131.243/0001-98 inválido."} | 404 (240 ms) {"error": "not found"} |
| T4 | 08942107000160 | 200 (3512 ms) nat=3999 sit=8 mf=1 | 200 (264 ms) nat=3999 sit=8 mf=1 | 200 (91 ms) nat=Associação Privada sit=Baixada mf=Matriz |
| T5 | 12ABC34501DE35 | 404 (87 ms) {"message": "CNPJ 12.ABC.345/01DE-35 não encontrado.", "type | 404 (6291 ms) {"message": "CNPJ 12.ABC.345/01DE-35 não encontrado."} | 404 (248 ms) {"error": "not found"} |
| T5r | 00000000E08G12 | 504 (10243 ms) falha 5xx (histórico em respostas/falhas/) | 503 (10064 ms) falha 5xx (histórico em respostas/falhas/) | 200 (246 ms) nat=Sociedade de Economia Mista sit=Ativa mf=Filial |
| T7 | 62779145000270 | 200 (574 ms) nat=3999 sit=2 mf=2 | 200 (3277 ms) nat=3999 sit=2 mf=2 | 200 (67 ms) nat=Associação Privada sit=Ativa mf=Filial |
| T7b | 04955882000523 | 200 (503 ms) nat=3999 sit=8 mf=2 | 200 (6792 ms) nat=3999 sit=8 mf=2 | 200 (69 ms) nat=Associação Privada sit=Baixada mf=Filial |
| T7bm | 04955882000108 | 200 (495 ms) nat=3999 sit=2 mf=1 | 200 (3388 ms) nat=3999 sit=2 mf=1 | 200 (432 ms) nat=Associação Privada sit=Ativa mf=Matriz |
| T7m | 62779145000190 | 200 (101 ms) nat=3999 sit=2 mf=1 | 200 (5867 ms) nat=3999 sit=2 mf=1 | 200 (96 ms) nat=Associação Privada sit=Ativa mf=Matriz |

T3 e T5r ficaram sem resposta definitiva na BrasilAPI e na Minha Receita: todas as tentativas deram 5xx (T3 em cerca de 18 rodadas ao longo de quase 2 h, T5r em cerca de 8 rodadas ao longo de 40 min, com 5 min entre rodadas).
Para esses dois casos, a tabela mostra a última tentativa e o histórico completo está em `respostas/falhas/`.
Basta rodar `bash retentar_pendentes.sh` quando a Minha Receita voltar para completar.

Falhas arquivadas em `respostas/falhas/` (todas as tentativas, inclusive as que depois deram certo):

- BrasilAPI: 67 falhas (36 x HTTP 500 "Request failed with status code 503", 31 x HTTP 504 do Cloudflare), todas em cerca de 10,2 s.
- Minha Receita: 77 falhas (HTTP 503), todas em cerca de 10,2 s.
- OpenCNPJ: nenhuma falha.

Latência das respostas definitivas (200/400/404), fora do T6: BrasilAPI mediana 505 ms (máx. 10,1 s), Minha Receita mediana 3,3 s (máx. 9,7 s), OpenCNPJ mediana 74 ms (máx. 432 ms).

Legenda: `nat` = natureza jurídica, `sit` = situação cadastral, `mf` = matriz/filial, exatamente como cada fonte devolve.

---

## Ficha 1 - BrasilAPI

| Item | Definição |
|---|---|
| Fonte / etapa | BrasilAPI, verificações 2, 3, 4, 5 e 10. |
| Tipo | API comunitária. Na prática, um proxy da Minha Receita hospedado na Vercel, atrás do Cloudflare. |
| URL e método | `GET https://brasilapi.com.br/api/cnpj/v1/{cnpj}` |
| Parâmetros | CNPJ com 14 caracteres, sem pontuação (a barra da máscara quebraria a rota). |
| Autenticação | Nenhuma. |
| Limites | Nenhum header de rate limit e nenhum 429 em 20 chamadas seguidas (T6) nem em 20 chamadas sem cache (T6b). Em erro 504 vem `retry-after: 120`. |
| Exemplo OK | `respostas/brasilapi_T1_19131243000197.json` |
| Exemplo RESTRICAO | `respostas/brasilapi_T4_08942107000160.json` (BAIXADA), `brasilapi_T2_00000000000191.json` (natureza 2038), `brasilapi_T7_62779145000270.json` (filial). |
| Exemplo erro / não encontrado | `brasilapi_T3b_19131243000198.json` (400 DV inválido), `brasilapi_T5_12ABC34501DE35.json` (404), `respostas/falhas/brasilapi_*` (500 e 504). |
| Campos usados e interpretação | Ver tabela de campos abaixo. |
| Aceita alfanumérico? | Aceita o formato (T5 devolve 404 "não encontrado", não 400). T5r (alfanumérico real) não foi respondido: só 5xx durante o teste. |
| Tempo médio de resposta | Com cache (T6, 20 chamadas): média 38 ms, p95 50 ms. Sem cache, quando a Minha Receita responde: 0,5 a 10 s. Sem cache, quando a Minha Receita está fora (T6b): média 11,7 s e 100% de falha. |
| Problemas conhecidos | Depende da Minha Receita (ver abaixo). Cache longo (header `age` de até 16 h): dado pode estar um dia mais velho que o espelho. |
| Data do último teste | 01/10/2026 (UTC). |

### Evidências de que a BrasilAPI é proxy da Minha Receita

- Para T1, T2, T4, T7 e demais casos, as chaves e os valores do JSON são idênticos aos da Minha Receita (comparação campo a campo, inclusive `email: null` e ordem de `qsa`).
- Quando a Minha Receita devolvia 503, a BrasilAPI devolvia `HTTP 500 {"message": "Request failed with status code 503", "type": "internal_error", "name": "AxiosError"}` ou `HTTP 504` do Cloudflare, sempre depois de cerca de 10 s.
- CNPJs que já estavam em cache na BrasilAPI (`x-vercel-cache: HIT`, `age` de 15 a 16 h, como T1, T2 e T5) responderam em menos de 150 ms mesmo com a Minha Receita fora.
- Depois que a Minha Receita conseguia responder um CNPJ, a BrasilAPI passava a responder o mesmo CNPJ (T7, T7b, E1, E2, E3).

Consequência: a frase do cap. 18 "Fallbacks: Minha Receita" precisa ser revista, porque as duas não falham de forma independente.

### Campos e tipos reais (BrasilAPI e Minha Receita, idênticos)

| Campo | Tipo real | Exemplo | Observação |
|---|---|---|---|
| cnpj | string | "19131243000197" | 14 caracteres, sem máscara. |
| razao_social / nome_fantasia | string | "OPEN KNOWLEDGE BRASIL" | nome_fantasia vem "" quando vazio. |
| situacao_cadastral | int | 2, 8 | 2 ATIVA, 8 BAIXADA confirmados. |
| descricao_situacao_cadastral | string | "ATIVA", "BAIXADA" | Maiúsculas. |
| data_situacao_cadastral | string AAAA-MM-DD | "2012-01-04" | - |
| motivo_situacao_cadastral | int | 0, 1 | 0 = "SEM MOTIVO". |
| descricao_motivo_situacao_cadastral | string | "EXTINCAO POR ENCERRAMENTO LIQUIDACAO VOLUNTARIA" | Sem acentos. |
| identificador_matriz_filial | int | 1, 2 | Há também `descricao_identificador_matriz_filial` ("MATRIZ"/"FILIAL"). |
| codigo_natureza_juridica | int | 3999, 3220, 2143, 2038 | Sem hífen, como o spec previa. |
| natureza_juridica | string | "Associação Privada" | Só a descrição, sem código. |
| cnae_fiscal | **int** | 9430800, **220903** | Perde o zero à esquerda. Normalizar com `str(x).zfill(7)`. |
| cnae_fiscal_descricao | string | - | - |
| cnaes_secundarios | list[{codigo: int, descricao: string}] | - | Vem `[]` quando não há secundários (T4, E2). Não foi visto o caso "código 0" citado no spec. |
| data_inicio_atividade | string AAAA-MM-DD | "2013-10-03" | Na filial é a data da própria filial (ver T7). |
| qsa | list[dict] | - | `nome_socio`, `qualificacao_socio` (texto), `codigo_qualificacao_socio` (int), `data_entrada_sociedade` (AAAA-MM-DD), `cnpj_cpf_do_socio` mascarado `"***112108**"`, `identificador_de_socio` (int, 2 = pessoa física), `faixa_etaria` ("Entre 41 a 50 anos"). |
| regime_tributario | list[{ano: int, forma_de_tributacao: string, ...}] | "ISENTO DO IRPJ", "IMUNE DE IRPJ" | Só vem preenchido na matriz; nas filiais vem `[]`. Vazio também em entidades novas (E1). |
| capital_social | int | 0 | - |
| email | string ou null | null | Vem null mesmo quando o OpenCNPJ traz e-mail (T1, E1): a Minha Receita parece omitir. |
| datas opcionais | string ou null | `data_opcao_pelo_simples: null` | Datas ausentes vêm `null`. |

---

## Ficha 2 - Minha Receita

| Item | Definição |
|---|---|
| Fonte / etapa | Minha Receita, verificações 2, 3, 4, 5 e 10. |
| Tipo | API comunitária (projeto open source, hospedado em fly.io atrás do Cloudflare, sem SLA). |
| URL e método | `GET https://minhareceita.org/{cnpj}` |
| Parâmetros | CNPJ com 14 caracteres (a documentação também mostra o CNPJ com máscara). |
| Autenticação | Nenhuma. |
| Limites | Nenhum header de rate limit e nenhum 429. A limitação real é de capacidade: 503 "Serviço temporariamente indisponível, tente novamente." depois de cerca de 10 s. |
| Exemplo OK | `respostas/minhareceita_T1_19131243000197.json` |
| Exemplo RESTRICAO | `minhareceita_T4_08942107000160.json` (BAIXADA), `minhareceita_T7b_04955882000523.json` (filial baixada). |
| Exemplo erro / não encontrado | `minhareceita_T3b_19131243000198.json` (400 DV inválido), `minhareceita_T5_12ABC34501DE35.json` (404), `respostas/falhas/minhareceita_*` (503). |
| Campos usados e interpretação | Idênticos aos da BrasilAPI (tabela acima). |
| Aceita alfanumérico? | Aceita o formato (T5 devolve 404 "não encontrado", não 400). T5r (alfanumérico real) não foi respondido: só 5xx durante o teste. |
| Tempo médio de resposta | Nas respostas definitivas: mediana em torno de 2 s, máximo de 9,7 s. T6 (5 seguidas, mesmo CNPJ): média 5,3 s, 2 de 5 com 503. T6b (5 sem cache): 5 de 5 com 503. |
| Problemas conhecidos | Instabilidade forte: na janela de 2 h de teste, a maioria das tentativas sem cache falhou com 503 (ver contagem na tabela de resultados). O 404 de CNPJ inexistente (T3) foi o caso mais difícil de obter. |
| Data do último teste | 01/10/2026 (UTC). |

Data do espelho: `GET https://minhareceita.org/updated` devolve `{"message": "2026-09"}`.

---

## Ficha 3 - OpenCNPJ

| Item | Definição |
|---|---|
| Fonte / etapa | OpenCNPJ, verificações 2, 3 (com mapeamento), 4, 5 e 10. |
| Tipo | API comunitária com dados estáticos (NDJSON + índice) servidos por Cloudflare Worker, gerados a partir dos dados abertos da Receita. |
| URL e método | `GET https://api.opencnpj.org/{cnpj}` |
| Parâmetros | CNPJ com 14 caracteres; também aceita com máscara (`19.131.243/0001-97` devolveu 200). Parâmetro opcional `?datasets=ceis,cepim,cnep,acordos_leniencia,...` anexa dados do Portal da Transparência. |
| Autenticação | Nenhuma. |
| Limites | Nenhum header de rate limit e nenhum 429 nas rajadas (5 seguidas). Não há limite documentado no README do projeto. |
| Exemplo OK | `respostas/opencnpj_T1_19131243000197.json` |
| Exemplo RESTRICAO | `opencnpj_T4_08942107000160.json` (Baixada), `opencnpj_T7b_04955882000523.json` (filial baixada), `opencnpj_T2_00000000000191.json` (natureza não elegível). |
| Exemplo erro / não encontrado | `opencnpj_T3_94580730000152.json` (404 `{"error": "not found"}`), `opencnpj_T3b_19131243000198.json` (DV inválido também dá 404). Formato inválido (ex.: `/status`) dá 400 `{"error": "invalid cnpj"}`. |
| Campos usados e interpretação | Ver tabela abaixo. |
| Aceita alfanumérico? | **Sim, e já tem dado real**: T5r `00000000E08G12` devolveu 200 (BANCO DO BRASIL SA, filial, início 2026-07-31). T5 (exemplo fictício) devolve 404. |
| Tempo médio de resposta | T6 (5 seguidas): média 32 ms, p95 78 ms. Sem cache (T6b e primeiras consultas): 200 a 480 ms. Todas as chamadas responderam. |
| Problemas conhecidos | Não tem código de natureza jurídica nem códigos numéricos de situação e matriz/filial (só texto). Não valida DV (DV errado vira 404, indistinguível de CNPJ inexistente). Não traz `regime_tributario`. |
| Data do último teste | 01/10/2026 (UTC). |

Data do espelho: `GET https://api.opencnpj.org/info` devolve `last_updated: 2026-09-15T00:54:41Z` e 73.354.529 registros (arquivo em `respostas/extras/opencnpj_info.json`).
O mesmo `/info` lista datasets do Portal da Transparência (CEIS, CEPIM, CNEP, acordos de leniência, convênios etc.) atualizados diariamente; com `?datasets=ceis,cepim,cnep` a resposta traz essas chaves (null quando não há registro).
Isso não substitui a consulta oficial do cap. 19, mas pode servir de fallback ou de verificação cruzada e merece um teste próprio com um CNPJ sancionado.

### Campos e tipos reais (OpenCNPJ)

| Campo | Tipo real | Exemplo | Equivalente BrasilAPI / Minha Receita |
|---|---|---|---|
| cnpj | string | "00000000E08G12" | cnpj |
| razao_social / nome_fantasia | string | - | iguais |
| situacao_cadastral | **string** | "Ativa", "Baixada" | situacao_cadastral (int) + descricao_situacao_cadastral |
| data_situacao_cadastral | string AAAA-MM-DD | "2012-01-04" | igual |
| motivo_situacao_cadastral | **dict {codigo: string "01", descricao}** | {"codigo": "01", "descricao": "EXTINCAO POR ENCERRAMENTO LIQUIDACAO VOLUNTARIA"} | motivo_situacao_cadastral (int) + descricao_motivo_situacao_cadastral |
| matriz_filial | **string** | "Matriz", "Filial" | identificador_matriz_filial (int) |
| natureza_juridica | string | "Associação Privada", "Organização Religiosa", "Cooperativa" | natureza_juridica; **não existe codigo_natureza_juridica** |
| cnae_principal | **string de 7 dígitos** | "0220903" | cnae_fiscal (int) |
| cnaes_secundarios | **list[string]** | ["9493600", ...] | cnaes_secundarios (list[dict]) |
| cnaes | list[{codigo: string, descricao, is_principal: bool}] | - | cnae_fiscal_descricao + cnaes_secundarios[].descricao |
| data_inicio_atividade | string AAAA-MM-DD | "2026-02-03" | igual |
| QSA (maiúsculo) | list[dict] | - | qsa |
| QSA[].cnpj_cpf_socio | string mascarada | "***112108**" | cnpj_cpf_do_socio |
| QSA[].identificador_socio | string | "Pessoa Física" | identificador_de_socio (int) |
| QSA[].faixa_etaria | string | "41 a 50 anos" | faixa_etaria ("Entre 41 a 50 anos") |
| QSA[].qualificacao_socio | string | "Presidente" | igual (sem o código numérico) |
| capital_social | **string com vírgula** | "0,00", "120000000000,00" | capital_social (int) |
| email | string | "TORRES.CONTAB@GMAIL.COM" | email (null na BrasilAPI) |
| telefones | list[{ddd, numero, is_fax}] | - | ddd_telefone_1, ddd_telefone_2, ddd_fax |
| datas opcionais | string vazia "" | `data_opcao_simples: ""` | null |
| regime_tributario | **ausente** | - | regime_tributario |

---

## Comparação das três fontes

| Aspecto | BrasilAPI | Minha Receita | OpenCNPJ |
|---|---|---|---|
| Independência | Depende da Minha Receita | Independente | Independente (pipeline próprio a partir da Receita) |
| Disponibilidade no teste | Só cache; sem cache falhou na maior parte do tempo | Baixa (503 frequente) | 100% |
| Latência típica | 30-150 ms com cache; 0,5-10 s sem cache | 0,3-10 s | 20-480 ms |
| Valida DV | Sim (400) | Sim (400) | Não (404) |
| Formato inválido | 400 | 400 | 400 `invalid cnpj` |
| Inexistente | 404 esperado; no T3 só deu 5xx | 404 em T5; no T3 só deu 5xx | 404 `{"error": "not found"}` |
| Alfanumérico | Aceita o formato; T5r real sem resposta (5xx) | Aceita o formato; T5r real sem resposta (5xx) | Aceita e já tem o primeiro CNPJ alfanumérico real |
| Código de natureza | int (3999) | int (3999) | Não tem, só texto |
| Situação | int + descrição | int + descrição | Só texto ("Ativa") |
| CNAE principal | int (perde zero) | int (perde zero) | string 7 dígitos |
| Datas vazias | null | null | "" |
| QSA | `qsa`, CPF mascarado | `qsa`, CPF mascarado | `QSA`, CPF mascarado |
| regime_tributario | Sim (só matriz) | Sim (só matriz) | Não |
| Data do espelho | Herdada da Minha Receita | 2026-09 (`/updated`) | 2026-09-15 (`/info`) |
| Extras | - | - | `?datasets=ceis,cepim,cnep,...` |

## T6 - Latência e limite

| Rodada | Fonte | N | Média | Mediana | p95 | HTTP | 429? | Header de rate limit |
|---|---|---|---|---|---|---|---|---|
| T6 (mesmo CNPJ, T1) | BrasilAPI | 20 | 38 ms | 34 ms | 50 ms | 20 x 200 | Não | Nenhum |
| T6 | OpenCNPJ | 5 | 32 ms | 21 ms | 78 ms | 5 x 200 | Não | Nenhum |
| T6 | Minha Receita | 5 | 5.315 ms | 5.968 ms | 10.099 ms | 3 x 200, 2 x 503 | Não | Nenhum |
| T6b (CNPJs distintos, sem cache) | BrasilAPI | 20 | 11.702 ms | 10.222 ms | 10.828 ms | 11 x 500, 8 x 504, 1 timeout | Não | `retry-after: 120` nos 504 |
| T6b | OpenCNPJ | 5 | 268 ms | 277 ms | 339 ms | 5 x 404 | Não | Nenhum |
| T6b | Minha Receita | 5 | 10.149 ms | 10.129 ms | 10.446 ms | 5 x 503 | Não | Nenhum |

O T6 com o mesmo CNPJ mede só o cache da Vercel/Cloudflare e não diz nada sobre a capacidade real da BrasilAPI.
O T6b (filiais 0101 a 0120 da raiz da Santa Casa, que não existem) mostra o caminho sem cache, que é o que o validador vai usar na prática.
Arquivos: `respostas/{fonte}_T6_19131243000197.json` e `respostas/{fonte}_T6b_62779145xxxxxx.json`.

## T7 - Filial

- `identificador_matriz_filial = 2` confirmado na BrasilAPI e na Minha Receita para 62.779.145/0002-70 e 04.955.882/0005-23; no OpenCNPJ vem `matriz_filial: "Filial"`.
- Raiz + 0001 devolve a matriz nas três fontes (T7m e T7bm), com a mesma razão social e `identificador_matriz_filial = 1`.
  Nenhuma fonte traz um campo apontando da filial para a matriz: é preciso montar o CNPJ da matriz (raiz + "0001" + DV recalculado).
- `data_inicio_atividade` é da filial, não da entidade: na Santa Casa coincide (1970-04-27 nas duas), mas no Instituto GRPCOM a filial é de 2011-11-29 e a matriz de 2002-03-07.
  Portanto a verificação 5 (tempo de existência) deve usar a data da matriz.
- `situacao_cadastral` também é da filial: a filial T7b está BAIXADA enquanto a matriz T7bm está ATIVA.
  A verificação 2 de uma filial não diz nada sobre a entidade.
- QSA é da raiz (idêntico entre filial e matriz) e `regime_tributario` só vem na matriz (`[]` na filial).
- Conclusão para o motor: ao receber uma filial, consultar também a matriz e rodar as verificações 2, 3, 5 e 10 sobre a matriz, exibindo a situação da filial só como informação.

## Divergências em relação ao spec

| Ponto do spec | O que foi observado |
|---|---|
| Cap. 18: "Fallbacks: Minha Receita (mesmos nomes de campos)" | Os nomes são os mesmos porque a BrasilAPI é proxy da Minha Receita; elas caem juntas, então a Minha Receita não é fallback independente. |
| Cap. 18: "OpenCNPJ (validar formato)" | Formato bem diferente: tudo string, sem `codigo_natureza_juridica`, situação e matriz/filial em texto, `QSA` maiúsculo, `capital_social` com vírgula, datas vazias como "". |
| Cap. 6.1: natureza "chega como número inteiro sem hífen" | Verdade só na BrasilAPI/Minha Receita. No OpenCNPJ é preciso mapear descrição -> código (tabela de natureza jurídica da Receita), ou casar pela descrição. |
| 18.1: `cnae_fiscal` "number ou string" | Na BrasilAPI/Minha Receita é sempre int e perde o zero à esquerda (220903); no OpenCNPJ é string com 7 dígitos. Normalizar com `zfill(7)`. |
| 18.1: `cnaes_secundarios` "pode vir com código 0" | Vem `[]` quando não há secundários (T4, E2, nas duas famílias de fonte). Código 0 não foi observado, mas o normalizador deve tolerar. |
| 18.1: limites "sem limite publicado, tratar 429" | Nenhum 429 visto. O problema real é 500/503/504 depois de cerca de 10 s; timeout do cliente deve ficar em torno de 12 s e o fallback deve ser acionado em 5xx, não só em 429. |
| 5.4: "CNPJ não encontrado (HTTP 404)" | Confirmado nas três fontes. No OpenCNPJ o DV inválido também dá 404, por isso o DV precisa ser validado antes (o cap. 4 já faz isso). |
| 4 / T3: "gerar CNPJ inexistente com raiz aleatória" | Das 6 primeiras raízes aleatórias com ordem 0001, 5 existiam (inclusive um CNPJ de candidato a vereador, natureza "Candidato a Cargo Político Eletivo"). A raiz sorteada deve ser conferida antes de virar caso de teste. |
| 5.3: `identificador_matriz_filial` "se for filial, avisar e sugerir consultar a matriz" | Recomendo consultar a matriz automaticamente, porque situação e data de início da filial podem divergir da matriz (T7b). |
| 18.1: `regime_tributario` | Só existe na BrasilAPI/Minha Receita e só na matriz. |
| 25.1 Alfanumérico "comportamento das APIs a documentar" | As três aceitam o formato; só o OpenCNPJ tinha o primeiro CNPJ alfanumérico real (00.000.000/E08G-12) no momento do teste. |

## Recomendação

**Fonte principal: OpenCNPJ.**
Foi a única fonte disponível durante toda a janela de teste, tem a menor latência, já tem CNPJ alfanumérico real e o espelho mais recente (2026-09-15).
O custo é escrever um normalizador mais cuidadoso: mapear `natureza_juridica` (texto) para o código de 4 dígitos usando a tabela oficial de naturezas jurídicas da Receita, converter `situacao_cadastral` ("Ativa", "Baixada", "Inapta", "Suspensa", "Nula") para o código numérico, `matriz_filial` para 1/2 e tratar "" como nulo.
O mapeamento de natureza deve falhar de forma explícita (estado INDISPONIVEL ou ALERTA) se aparecer uma descrição desconhecida, nunca cair em NÃO ELEGÍVEL por omissão.

**Fallback: BrasilAPI** (que por baixo já é a Minha Receita, então não vale a pena chamar as duas).
Vale como fallback porque o cache dela cobre CNPJs consultados recentemente por qualquer usuário, e porque traz os códigos numéricos que servem para conferir o mapeamento do OpenCNPJ.
Timeout de cerca de 12 s, sem retry imediato em 5xx (respeitar o `retry-after: 120`).

**Plano B continua válido**: como as três fontes são espelhos comunitários dos mesmos dados abertos, a importação do dump da Receita no Postgres (cap. 18) elimina a dependência.
O OpenCNPJ publica o próprio dump (`zip_url` no `/info`, cerca de 14 GB), o que pode simplificar esse plano.

**Modelo interno sugerido** (independente da fonte): `cnpj`, `razao_social`, `situacao_codigo` (int), `situacao_descricao`, `situacao_data`, `motivo_codigo` (int), `motivo_descricao`, `matriz` (bool), `natureza_codigo` (int), `natureza_descricao`, `cnae_principal` (string 7), `cnaes_secundarios` (list string 7), `data_inicio_atividade` (date), `qsa` (nome, qualificacao, data_entrada, documento_mascarado), `fonte`, `data_espelho`.

## Pendências

- Completar T3 e T5r na BrasilAPI e na Minha Receita (`bash retentar_pendentes.sh`), principalmente para saber se a Minha Receita já tem o CNPJ alfanumérico real.
- Achar um CNPJ INAPTO (situação 4) de associação para completar o 25.1.
- Testar o `?datasets=ceis,cepim,cnep` do OpenCNPJ com um CNPJ sabidamente sancionado e comparar com o Portal da Transparência (cap. 19).
- Repetir o T6b em outro horário para saber se a instabilidade da Minha Receita é crônica ou foi pontual nesta noite.
