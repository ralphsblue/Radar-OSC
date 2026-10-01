# Ficha da fonte: Mapa das OSCs (Ipea)

Fase 0, verificação 11 (informativa), segunda opinião da verificação 3 e fonte secundária da verificação 12 (CEBAS).
Teste feito em 30/09/2026, sem navegador, só com httpx, User-Agent `validador-osc-ifsp/0.1 (projeto academico de extensao)` e 1,5 s entre requisições.

## Resumo

Existe uma API REST pública, sem token, que alimenta o próprio site.
Ela está em `https://mapaosc.ipea.gov.br/api/api/` (o prefixo `/api/api/` é duplo mesmo).
A documentação Swagger fica em https://mapaosc.ipea.gov.br/api/api/documentation (item "API" do menu Ajuda) e o JSON OpenAPI em https://mapaosc.ipea.gov.br/api/docs.
O Swagger está incompleto e mostra caminhos sem o segundo `/api` (ex.: `/api/cnpj/{cnpj}` dá 404).
A lista real de rotas está no código-fonte aberto: https://github.com/Plataformas-Cidadania/mapa-osc-api (arquivo `routes/web.php`).
A consulta por CNPJ é feita em duas etapas: CNPJ para `id_osc` e depois os endpoints do perfil por `id_osc`.
A wiki antiga (`Plataformas-Cidadania/portalosc`, último push em 2022) descreve a API legada em `:8383`, só da rede interna do Ipea.
Essa API legada não responde de fora (timeout de conexão em `mapaosc.ipea.gov.br:8383`) e não é mais necessária.

Selo proposto: **JSON descoberto / API oficial não documentada formalmente** (pública, sem autenticação, usada pelo front do Ipea, rotas confirmadas no código-fonte oficial).

## Ficha 25.2

| Item | Definição |
|---|---|
| Fonte / etapa | Mapa das OSCs (Ipea), verificação 11 e apoio às verificações 3 e 12. |
| Tipo | API oficial (REST/JSON pública, documentada só parcialmente no Swagger; rotas completas no GitHub do Ipea). |
| URL e método | Etapa 1: `GET https://mapaosc.ipea.gov.br/api/api/busca/cnpj/{cnpj_sem_zeros_a_esquerda}`. Etapa 2: `GET https://mapaosc.ipea.gov.br/api/api/osc/{secao}/{id_osc}` (lista abaixo). |
| Parâmetros | CNPJ só com dígitos e **sem zeros à esquerda** (o banco guarda CNPJ como NUMERIC). A busca é por prefixo (`LIKE 'cnpj%'`), então é obrigatório filtrar o resultado por igualdade exata de `cd_identificador_osc`. |
| Autenticação | Nenhuma para leitura. O middleware `auth` (token Passport) só protege rotas de escrita e de área do usuário. |
| Limites | Nenhum cabeçalho de rate limit observado. CORS liberado (`Access-Control-Allow-Origin: *`). Sem CAPTCHA. Recomendado manter 1 a 2 s entre chamadas e cache longo (a base é atualizada mensalmente). |
| Exemplo OK | `respostas/okbr_*.json` (Open Knowledge Brasil, `id_osc` 621480, só dados automáticos); `respostas/abrinq_*.json` (perfil com dados preenchidos pela OSC); `respostas/cebas_saude_*.json` (OSC com CEBAS Saúde e projetos). |
| Exemplo RESTRICAO | Não se aplica (fonte informativa). O caso mais próximo é "presente, só dados automáticos": `respostas/okbr_*.json`. |
| Exemplo erro / não encontrado | CNPJ fora do Mapa: `respostas/nao_osc_petrobras_busca_cnpj.json` (HTTP 200, corpo `[]`). CNPJ inválido: `respostas/cnpj_invalido_busca_cnpj.json` (`[]`). CNPJ alfanumérico: `respostas/erro_cnpj_alfanumerico.json` (`[]`). `id_osc` inexistente: `/osc/{id}` devolve `{}`, `/osc/certificados/{id}` devolve `{"Resposta": "Nenhum Certificado..."}` e `/osc/indice_preenchimento/{id}` devolve texto de erro PHP com HTTP 200 (`respostas/erro_*.json`). Rota errada: HTML 404 (`respostas/erro404_*.html`). |
| Campos usados e interpretação | Ver seções "Endpoints" e "Regra de interpretação" abaixo. |
| Aceita alfanumérico? | Não. O CNPJ é armazenado como NUMERIC no banco do Mapa; um CNPJ alfanumérico nunca será encontrado. Quando os CNPJs alfanuméricos começarem a existir (jul/2026 em diante), o adapter deve devolver INDISPONIVEL ou "não suportado" em vez de "ausente do Mapa". |
| Tempo médio de resposta | 0,05 a 0,6 s por chamada (média 0,13 s em 16 chamadas); um pico isolado de 15,9 s. Perfil completo com 16 chamadas leva cerca de 25 s por causa do intervalo de 1,5 s. |
| Problemas conhecidos | (1) A busca por CNPJ é por prefixo e exige filtro exato. (2) Zeros à esquerda precisam ser removidos. (3) Erros vêm com HTTP 200 e corpo vazio, objeto vazio ou mensagem de texto, então o adapter deve validar o formato. (4) Os campos `ft_*` com valor "Representante de OSC" aparecem também quando o valor está vazio (é o default do banco), então só contam se o valor correspondente estiver preenchido. (5) O índice de preenchimento soma dados automáticos e declarados. (6) Certificados CEBAS do Mapa podem estar desatualizados (exemplos com fim de validade em 2016 e 2021). (7) A base inclui filiais (cada uma com seu `id_osc`) e OSCs baixadas ou inaptas. |
| Data do último teste | 30/09/2026. |

## Endpoints públicos relevantes (prefixo `https://mapaosc.ipea.gov.br/api/api/`)

| Rota | Para que serve | Exemplo salvo |
|---|---|---|
| `busca/cnpj/{cnpj}` | CNPJ para `id_osc` (busca por prefixo). Devolve `id_osc`, `cd_identificador_osc`, razão social, natureza jurídica, `cd_situacao_cadastral`, município, UF. | `okbr_busca_cnpj.json` |
| `busca/osc-autocomplete?texto_busca=...` | Busca usada pela caixa de pesquisa do site (nome ou CNPJ). Com texto não numérico faz busca textual difusa, então não serve para "não encontrado". | `okbr_busca.json`, `cnpj_invalido_busca.json` |
| `osc/{id_osc}` | Flags gerais: `bo_osc_ativa`, `bo_nao_possui_projeto`, `bo_nao_possui_certificacoes` etc., com fonte `ft_*`. | `okbr_osc.json` |
| `osc/cabecalho/{id_osc}` | CNPJ, razão social, natureza jurídica, logo, `dt_atualizacao`. | `okbr_cabecalho.json` |
| `osc/dados_gerais/{id_osc}` | Nome fantasia, sigla, resumo, CNAE, responsável legal, endereço, e-mail, site, telefone, ODS, cada um com `ft_*`. | `okbr_dados_gerais.json` |
| `osc/indice_preenchimento/{id_osc}` | Índice de preenchimento (0 a 100) por seção e total (`transparencia_osc`). | `okbr_indice_preenchimento.json` |
| `osc/areas_atuacao/{id_osc}` | Áreas de atuação (oficiais e declaradas, com `ft_area_atuacao` e `bo_oficial`). | `okbr_areas_atuacao.json` |
| `osc/areas_atuacao_rep/{id_osc}` | Áreas declaradas pelo representante da OSC. | `okbr_areas_atuacao_rep.json` |
| `osc/descricao/{id_osc}` | Histórico, missão, visão, finalidades estatutárias, link do estatuto (todos autodeclarados). | `abrinq_descricao.json` |
| `osc/certificados/{id_osc}` | Títulos e certificações (CEBAS, OSCIP, Utilidade Pública etc.) com `ft_certificado`, `bo_oficial`, datas de início e fim. | `cebas_saude_certificados.json` |
| `certificado/` | Dicionário de tipos de certificado. | `dc_certificado.json` |
| `osc/rel_trabalho_e_governanca/{id_osc}` | Dirigentes (`governanca`), conselho fiscal, trabalhadores (RAIS e declarados). | `okbr_rel_trabalho_e_governanca.json` |
| `osc/participacao_social/{id_osc}` | Conselhos, conferências e outros espaços de participação (autodeclarados). | `okbr_participacao_social.json` |
| `osc/projetos/{id_osc}` e `osc/projeto/{id_projeto}` | Lista de projetos e parcerias; o detalhe traz `ft_*` e `bo_oficial` (ex.: SICONV/MPOG = parceria federal oficial). | `cebas_saude_projetos.json`, `cebas_saude_projeto_2683010.json` |
| `osc/anos_recursos/{id_osc}` e `osc/recursos/{ano}/{id_osc}` | Fontes de recursos por ano (oficiais, como SIGABR, ou declaradas). | `cebas_saude_anos_recursos.json`, `cebas_saude_recursos_2017.json` |
| `osc/quadro-societario-por-osc/{id_osc}` | Quadro societário da Receita (CPF mascarado). | `okbr_quadro_societario.json` |
| `situacao_cadastral` | Dicionário de `cd_situacao_cadastral` (1 Nula, 2 Ativa, 3 Suspensa, 4 Inapta, 5 Baixada). | `dc_situacao_cadastral.json` |

Página humana do perfil: `https://mapaosc.ipea.gov.br/detalhar/{id_osc}` (renderizada no servidor, mesmo conteúdo da API).

Existe também a rota pública `representantes/buscar-representacoes/{cnpj}`, que devolve os usuários cadastrados como representantes da OSC.
Ela expõe dados pessoais de usuários do portal, então **não deve ser usada** pelo validador (LGPD e política do projeto); foi chamada uma única vez e voltou `[]`.

### Exemplo de resposta (Open Knowledge Brasil, CNPJ 19.131.243/0001-97)

`GET busca/cnpj/19131243000197`:

```json
[{"id_osc":621480,"cd_identificador_osc":"19131243000197","cd_situacao_cadastral":2,
  "tx_razao_social_osc":"OPEN KNOWLEDGE BRASIL","tx_nome_fantasia_osc":"REDE PELO CONHECIMENTO LIVRE",
  "tx_nome_natureza_juridica_osc":"Associação Privada","dt_fundacao_osc":"2013-10-03",
  "tx_nome_municipio":"São Paulo","tx_sigla_uf":"SP"}]
```

`GET osc/indice_preenchimento/621480` (resumido):

```json
{"transparencia_dados_gerais":50,"transparencia_area_atuacao":100,"transparencia_descricao":0,
 "transparencia_titulos_certificacoes":0,"transparencia_relacoes_trabalho_governanca":0,
 "transparencia_espacos_participacao_social":0,"transparencia_projetos_atividades_programas":0,
 "transparencia_fontes_recursos":0,"transparencia_osc":18.75}
```

`GET osc/certificados/621480`:

```json
{"Resposta":"Nenhum Certificado foi encontrado para essa OSC!"}
```

Conclusão para a OKBR: presente no Mapa, ativa, natureza "Associação Privada", perfil **só com dados automáticos** (nenhum campo com valor e fonte "Representante de OSC"), índice 18,75, sem certificações.

## Regra de interpretação (rascunho, implementada em `scripts/resumo_perfil.py`)

### Presença

- `busca/cnpj` devolve item com `cd_identificador_osc` igual ao CNPJ (comparando com 14 dígitos, `zfill(14)`): presente.
- Lista vazia ou sem igualdade exata: ausente do Mapa, estado ALERTA leve.
- Timeout, 5xx ou corpo fora do formato esperado: INDISPONIVEL.
- `cd_situacao_cadastral` diferente de 2 deve ser repassado como contexto (o Mapa mantém baixadas e inaptas).

### Quem preencheu cada dado

Cada valor tem um campo irmão `ft_*` (fonte) e os registros de lista têm `bo_oficial`.
Fontes automáticas observadas: `CNPJ/SRF/MF/AAAA_MM`, `RAIS/MTE AAAA`, `SICONV/MPOG data`, `SIGABR mm/aaaa`, `CEBAS/MS`, `CEBAS/MEC`, `CEBAS/MDS`, `OSCIP/MJ`, `AreaAtuacaoOSC.R_AAAA_MM`.
Fonte de autodeclaração: `Representante de OSC` (no dicionário de dados aparece como "Autodeclaração OSC").
Um dado conta como **preenchido pela OSC** quando o valor não é nulo nem vazio **e** (`ft_* == "Representante de OSC"` **ou** `bo_oficial == false`).
`ft_* == "Representante de OSC"` com valor nulo é só o default do banco e não conta.

Seções que só existem por autodeclaração (qualquer conteúdo já indica perfil preenchido pela OSC):

- `osc/descricao`: histórico, missão, visão, finalidades, link do estatuto.
- `osc/areas_atuacao_rep`: áreas declaradas pelo representante.
- `rel_trabalho_e_governanca.governanca` (dirigentes) e `conselho_fiscal`.
- `osc/participacao_social`: conselhos, conferências, outros espaços.
- Campos de `dados_gerais` como `tx_site`, `tx_resumo_osc`, `tx_sigla_osc`, `tx_nome_responsavel_legal` quando a fonte é "Representante de OSC".

Seções mistas (contam como histórico, mas não como prova de perfil preenchido sem olhar `ft_*`/`bo_oficial` de cada item):

- Projetos (`osc/projeto/{id}`): muitos vêm do SICONV (parcerias federais oficiais).
- Fontes de recursos (`osc/recursos/{ano}/{id}`): muitas vêm do SIGABR.
- Certificados: em geral oficiais.

`indice_preenchimento.transparencia_osc` é útil como número único para o score, mas mistura dados automáticos e declarados (a OKBR tem 18,75 sem nenhuma autodeclaração).

Resultado do resumo nos casos testados (`respostas/_resumo_perfis.json`):

| Caso | id_osc | Índice | Campos autodeclarados | Projetos | Certificados | Perfil |
|---|---|---|---|---|---|---|
| Open Knowledge Brasil | 621480 | 18,75 | nenhum | 0 | nenhum | só dados automáticos |
| Santa Casa e Hospital São Vicente (22.683.783/0001-98) | 507788 | 49,45 | nenhum | 6 (SICONV) | CEBAS Saúde, oficial, fim 31/03/2021 | só dados automáticos |
| Instituto Sou da Paz (03.483.568/0001-07) | 604546 | 46,32 | nenhum | 2 | OSCIP, oficial | só dados automáticos |
| Fundação Abrinq (38.894.796/0001-46) | 594130 | 52,36 | site, missão, visão | 14 | CEBAS Assistência Social, oficial, fim 09/11/2016 | preenchido pela OSC |
| Petrobras (33.000.167/0001-01, controle negativo) | - | - | - | - | - | ausente do Mapa |

Mapeamento sugerido para a tabela 14.3 do spec:

| Situação | Estado |
|---|---|
| Presente e `perfil == preenchido_pela_osc` | OK (soma mais no score) |
| Presente e `perfil == so_dados_automaticos` | OK (soma menos, sugerir que a OSC complete o perfil) |
| Ausente (`[]` ou sem igualdade exata) | ALERTA leve |
| Erro, timeout, formato inesperado ou CNPJ alfanumérico | INDISPONIVEL |

## Certificações e CEBAS

O campo existe: `osc/certificados/{id_osc}`, com `cd_certificado` do dicionário `certificado/`.
Tipos: 1 Entidade Ambientalista, 2 CEBAS Educação, 3 CEBAS Saúde, 4 OSCIP, 5 Utilidade Pública Federal, 6 CEBAS Assistência Social, 7 Utilidade Pública Estadual, 8 Utilidade Pública Municipal, 9 Não Possui.

Achado importante: o CEBAS no Mapa **não é autodeclarado**.
Ele vem de cargas oficiais dos ministérios (`ft_certificado` = `CEBAS/MS`, `CEBAS/MEC` ou `CEBAS/MDS`, `bo_oficial = true`), feitas por ETL do repositório `Plataformas-Cidadania/mapa_osc_database`.
No front atual, o formulário de certificados da área do representante só permite declarar Utilidade Pública Municipal (8) e Estadual (7); esses entram com `ft_certificado = "Representante de OSC"` (default do model `Certificado` na API).
Ressalva: as datas mostram que a carga pode estar defasada (Abrinq com CEBAS encerrado em 2016, Santa Casa de São Vicente com CEBAS encerrado em 2021), então o CEBAS do Mapa serve como **indício histórico oficial**, não como prova de certificação vigente.
Regra sugerida para a verificação 12: `dt_fim_certificado >= hoje` vira "CEBAS vigente segundo o Mapa (fonte X, carga possivelmente defasada)"; fim no passado vira "teve CEBAS até data", sempre informativo.

## Base de dados para download (menu Dados > Base de Dados)

Página: https://mapaosc.ipea.gov.br/base-dados.
Metadados obtidos por HEAD em `respostas/downloads/_head_arquivos.json`.

| Arquivo | Tamanho | Last-Modified | Observação |
|---|---|---|---|
| `/download/20260806_MOSC_baseDivulgacao.csv` (Base principal) | 344 MB (343.956.497 bytes) | 18/08/2026 | CSV `;`, Latin-1, CRLF. Coleta e envio: agosto/2026. Cerca de 1,1 milhão de linhas (estimativa pela amostra). **Tem CNPJ** (14 dígitos com zeros). Não foi baixado inteiro; amostra dos primeiros 256 KB via Range em `respostas/downloads/amostra_256KB_...csv`. |
| `arquivos/subitems/4038-dicionario-de-dados-mapa-oscs.xlsx` | 125 KB | 08/11/2024 | Baixado. Abas de variáveis, tabelas e fontes (inclui "Autodeclaração OSC"). |
| `arquivos/subitems/8420-cebaseducacao.xlsx` | 110 KB | 04/12/2024 | Baixado. CNPJ, situação, portaria, validade (MEC). |
| `arquivos/subitems/1434-cebassaude.xlsx` | 175 KB | 04/12/2024 | Baixado. `NU_CNPJ`, situação atual, vigência, `ST_CEBAS` (MS). |
| `arquivos/subitems/7684-cebassuas.xlsx` | 3,7 MB | 04/12/2024 | Baixado. Processos e "SITUAÇÃO CNPJ CEBAS - 24/10/2024" (MDS), com status e vigência. |
| `arquivos/subitems/6793-certificadolistaantiga.xls` | 2,1 MB | 20/03/2025 | Base anterior de títulos e certificados. Não baixado. |
| `download/area_subarea.xlsx` | 86 MB | 10/01/2023 | Áreas e subáreas. Não baixado. |
| `arquivos/subitems/4168-baseprojetososcantiga.xlsx` | 14,9 MB | 19/03/2025 | Projetos. Não baixado. |
| `arquivos/subitems/4786-recursososc.xls` | 3,5 MB | 20/03/2025 | Recursos. Não baixado. |
| `arquivos/subitems/4600-conselhoconferencia.xls` | 116 KB | 20/03/2025 | Conselhos e conferências. Não baixado. |
| `download/CNES_MJ.zip` | 25 MB | 03/07/2019 | Extinto CNES/MJ. Não baixado. |

Colunas da base principal (44): `cnpj`, `tx_razao_social_osc`, `tx_nome_fantasia_osc`, `natureza_juridica`, `matriz_filial`, `situacao_cadastral`, `dt_fundacao_osc`, `removida_do_mosc`, `data_fechamento`, `ano_fechamento`, `tx_endereco_completo`, `cd_municipio`, `municipio_nome`, `UF_Sigla`, `longitude`, `latitude`, `cnae`, `cnae_secundaria`, 8 colunas `Area_*` e 18 colunas `SubArea_*` (0/1).
A base principal **não traz** certificações, projetos, governança nem índice de preenchimento; serve para presença e segunda opinião de natureza jurídica (coluna `removida_do_mosc` indica CNPJs retirados do Mapa).
Recomendação: usar a API como caminho principal e a base CSV só como fallback offline ou para testes em lote.
As três planilhas CEBAS (MEC, MS, MDS, outubro a dezembro de 2024) são um bônus para a verificação 12, com a mesma ressalva de defasagem.

## Scripts (em `scripts/`)

- `fetch.py`: baixa uma URL com o User-Agent do projeto, salva corpo e metadados (status, tempo, sha256, cabeçalhos) em `respostas/`.
- `probe_osc.py CNPJ prefixo`: faz a consulta completa (CNPJ para `id_osc` e as 14 seções do perfil) e salva tudo com log.
- `resumo_perfil.py prefixo...`: aplica a regra de interpretação sobre as respostas salvas.
- `busca_nome.py "texto"`: busca OSCs por nome e mostra índice e certificados (usado para achar exemplos).
- `bases_download.py`: HEAD em todos os arquivos da Base de Dados, baixa os pequenos e uma amostra da base principal.
- `xlsx_resumo.py`: lê cabeçalho e primeiras linhas de um `.xlsx` sem dependências.

## Passos manuais pendentes

O caminho técnico foi fechado sem navegador; os passos abaixo são confirmações opcionais.

1. Conferir no navegador que o perfil bate com a API.
   Abrir https://mapaosc.ipea.gov.br/detalhar/621480 no Chrome.
   Apertar F12, aba Network, filtro "Fetch/XHR", recarregar com Ctrl+F5.
   Conferir que aparece a chamada `api/api/osc/indice_preenchimento/621480` e que o JSON (aba Response) é igual a `respostas/okbr_indice_preenchimento.json`.
   O resto da página é renderizado no servidor, então não aparecerão outras chamadas XHR do perfil; isso é esperado.
2. Conferir a busca por CNPJ do site.
   Na home, digitar `19131243000197` na caixa de busca com o DevTools aberto na aba Network.
   Deve aparecer `api/api/busca/osc-autocomplete?texto_busca=19131243000197&_=...` com o mesmo JSON de `respostas/okbr_busca.json`.
3. Achar um exemplo real de certificado autodeclarado (`bo_oficial = false`, `ft_certificado = "Representante de OSC"`, tipo 7 ou 8).
   Não encontrei nos casos testados; basta procurar uma OSC municipal pequena que tenha "Utilidade Pública Municipal" no perfil (seção "Titulações e certificações") e rodar `python scripts/probe_osc.py <CNPJ> autodeclarado`.
4. Opcional e recomendado: mandar um e-mail para `mapaosc@gmail.com` (contato do Swagger) informando o uso acadêmico da API, perguntando se há limite de requisições e qual a periodicidade de atualização da carga CEBAS.
