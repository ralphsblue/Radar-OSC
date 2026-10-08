# Ficha da fonte: CEBAS via Diário Oficial da União (Estratégia A, roteiro 22.7)

Data dos testes: 30/09/2026 (horário de Brasília).
Responsável: prova de conceito automatizada da Fase 0.
Pasta: `fase0/cebas_dou/`.

## 1. Veredito

A Estratégia A é viável.
O XML mensal do DOU é aberto, gratuito, sem login, e traz o CNPJ em praticamente todos os atos de CEBAS (99,7% dos atos, 99,9% das decisões).
O parser por regex acertou 10 de 10 atos sorteados (T2) e 10 de 10 linhas sorteadas das listas do MDS.
A linha do tempo de uma Santa Casa foi reconstruída pela busca pública do portal, sem login (T3).

Achado mais importante, fora do roteiro original: o SisCEBAS Saúde publica uma planilha pública, gerada na hora, com a situação atual de todas as entidades da área da saúde, com CNPJ, vigência e situação.
Ela cobriu 287 de 287 CNPJs da saúde encontrados no DOU (100%).
Para a área da saúde ela deve virar a fonte principal, com o DOU como evidência documental.
Para MDS e MEC não foi encontrada base viva e pública; para essas áreas a combinação recomendada é planilha oficial de 2023/2024 (base histórica) mais DOU (atualização).

## 2. Como obter o DOU Seção 1 em formato aberto

| Caminho | URL | Formato | Tamanho | Data mais recente | Login |
|---|---|---|---|---|---|
| XML mensal (Base de Dados de Publicações do DOU) | `https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados?ano=2026&mes=Agosto` lista os links `https://www.in.gov.br/documents/49035712/<id>/S01MMAAAA.zip/<uuid>?version=1.0&t=...&download=true` | ZIP com 1 XML por matéria (`<xml><article ...><body><Identifica/><Ementa/><Texto>HTML</Texto>`) e imagens JPG | S01 ago/2026: 52,6 MB (110 MB descompactado, 8.590 XML); jul/2026: 555 MB; jun/2026: 644 MB (o volume é quase todo JPG; o XML de cada mês tem cerca de 100 MB) | Agosto/2026 (publicado em 15/09/2026, `Last-Modified`). Setembro/2026 ainda não saiu. | Não |
| INLABS | `https://inlabs.in.gov.br/acessar.php` | XML diário e PDF | não medido | diário, logo após a publicação | Sim, exige cadastro gratuito (e-mail, senha, nome, UF/cidade). Não foi criada conta. Ver seção 10. |
| Busca do portal | `https://www.in.gov.br/consulta/-/buscar/dou?q=...&s=do1&exactDate=personalizado&publishFrom=DD/MM/AAAA&publishTo=DD/MM/AAAA&sortType=0&delta=50` | HTML com JSON embutido em `<script id="_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params" type="application/json">` | 1 a 4 s por página | dia corrente | Não, e sem CAPTCHA |

Detalhes do XML mensal:

- A página informa que o arquivo sai na primeira terça-feira do mês seguinte; na prática o de agosto saiu em 15/09/2026, então a defasagem é de 2 a 6 semanas.
- O ZIP inclui edições extras (`pubName="DO1E"`); prefixo do arquivo 515 = DO1, 600 a 603 = extras.
- Atributos úteis de `<article>`: `idMateria`, `pubDate`, `pubName`, `artCategory` (órgão/unidade), `artType`, `editionNumber`, `numberPage`, `pdfPage` (link do PDF da página).
- O XML não traz a URL amigável do ato (`/web/dou/-/<slug>-<id>`); o slug só vem da busca do portal. A referência estável usada é `idMateria` + `pdfPage`.
- Uma matéria pode conter vários atos: o MDS publica 5 a 14 portarias numa única matéria, uma delas sem `class="identifica"` no título.
- Uma matéria longa vem partida em arquivos `-1`, `-2`, ... (ex.: `515_20260814_24236510-3.xml`).

Detalhes da busca do portal:

- Paginação por cursor: `currentPage`, `newPage`, `score`, `id` (= `classPK` do último item) e `displayDate` (= `displayDateSortable`).
- `delta` aceita 50 por página.
- URL do ato: `https://www.in.gov.br/web/dou/-/<urlTitle>`; a página do ato tem o texto em `<div class="texto-dou">`.
- A busca é aproximada: "CEBAS" também trouxe "CEB", "CEBA" e "CEBE" (6 falsos positivos em 92 resultados de agosto).
- Termos entre aspas viram busca exata da frase inteira; `"nome" CEBAS` devolveu 0 resultados, então é preciso buscar pelo CNPJ ou pelo nome separadamente.
- O índice não separa CNPJ colado ao texto (`nº50.798.453/0001-83` em 2016 não foi achado pela busca do CNPJ, só pela do nome).

## 3. T1: atos de CEBAS por mês (Seção 1, XML mensal)

Termo usado: `\bCEBAS\b` ou `Entidades? Beneficentes?`, mais um filtro estendido para despachos do MDS que só citam a Lei 12.101/2009 ou a LC 187/2021 e trazem CNPJ.

| Mês | Matérias com o termo (MS / MEC / MDS) | Atos de decisão (MS / MEC / MDS) | Decisões por entidade (MS / MEC / MDS) | Dias com publicação | CNPJs distintos |
|---|---|---|---|---|---|
| jun/2026 | 57 / 10 / 1 | 57 / 10 / 14 | 57 / 26 / 527 | 11 | 600 |
| jul/2026 | 154 / 2 / 3 | 152 / 2 / 4 | 152 / 2 / 21 | 13 | 171 |
| ago/2026 | 86 / 1 / 1 | 85 / 1 / 12 | 85 / 1 / 410 | 7 | 496 |
| Total | 315 | 337 | 1.281 | 31 | |

Leitura dos números:

- Média de cerca de 110 atos e 430 decisões por mês, muito irregular.
- O Ministério da Saúde publica um ato por entidade (portaria SAES/MS ou despacho GM/MS).
- O MDS publica poucas portarias com listas enormes (a Portaria SNAS 111/2026 tem 266 entidades).
- O MEC publica pouco e varia o formato (portaria SERES/MEC individual, tabela em anexo, decisão do Ministro).
- Contar só a palavra "CEBAS" subestima o MDS: as portarias do MDS dizem "certificação de entidade beneficente de assistência social" e não usam a sigla.
- Falsos positivos achados: metas institucionais do MS que citam o DCEBAS (Portaria SE/MS 975/2026), formulário da Portaria SAES 4.350/2026. O parser marca esses casos como "sem decisão de certificação" e eles ficam fora das métricas.
- Distribuição de agosto/2026: renovação deferida 273, concessão deferida 53, indeferimento 151, cancelamento 2, reconsideração 4, outros 13 (consulta pública, prazo para sanar pendências).

## 4. Parser (`parser_cebas.py`)

Unidades: matéria (arquivo XML), ato (portaria, despacho ou decisão dentro da matéria), decisão (uma linha por entidade).

Campos extraídos por decisão: `cnpj` (14 posições, aceita o formato alfanumérico novo), `cnpj_dv_ok`, `entidade`, `municipio_uf`, `tipo_ato`, `deferido` (S, N ou vazio), `detalhe`, `validade`, `area` (pelo órgão em `artCategory`), `data_publicacao`, `data_ato`, `identificacao_ato`, `ref_ato` (`idMateria#n`), `edicao`, `pagina`, `url_pdf`, `trecho` (evidência).

Regras principais:

- CNPJ: formatado com tolerância a espaços e pontos extras (`nº .05.866.492/0001-16`, `nº50.798.453/0001-83`), meio formatado (`03163888/0001-71`) e só dígitos quando precedido de "CNPJ".
- Listas: itens `N) NOME, CNPJ, MUNICÍPIO/UF, processo...` herdam o tipo do `Art.` imediatamente anterior.
- Tabelas em anexo (MEC): cada linha com CNPJ herda o tipo do `Art.` que cita aquele anexo ("ANEXO I", "ANEXO II"); o nome é a célula textual mais longa.
- Tipo do ato: ementa, ou parágrafo "Decisão:" (mais continuação), ou "Art. 1º".
- Armadilhas tratadas: "para CONCEDER o prazo de 30 dias" (é prazo para sanar, não concessão); "anulo o indeferimento ... Determino a renovação" (é renovação); "Não se reconsidera" (reconsideração negada); "nego-lhe provimento" (recurso negado mantém indeferimento ou cancelamento); "Ficam arquivados" (arquivamento); "Prorroga ... a vigência" (prorrogação da LC 187, art. 40, § 1º).

Mapeamento para o modelo 22.6:

| Texto no DOU | tipo_ato | deferido | detalhe |
|---|---|---|---|
| Defere a Concessão / Renovação | CONCESSAO / RENOVACAO | S | vazio ou "judicial" (sub judice, liminar) |
| Indefere / Indeferir o pedido | INDEFERIMENTO | N | concessao ou renovacao |
| Cancela / Fica cancelado | CANCELAMENTO | N | |
| Defere, em grau de Reconsideração / Admitir o recurso e RECONSIDERAR | RECONSIDERACAO | S | concessao ou renovacao |
| Não se reconsidera | RECONSIDERACAO | N | |
| NEGO PROVIMENTO ao recurso | INDEFERIMENTO ou CANCELAMENTO (conforme o assunto) | N | recurso negado |
| CONCEDER o prazo de 30 dias para sanar | OUTRO | vazio | prazo para sanar pendencias |
| Abrir prazo para manifestação da sociedade civil / Consulta Pública | OUTRO | vazio | consulta publica do processo |
| Abrir prazo para apresentar documentos (supervisão) | OUTRO | vazio | supervisao |
| Arquivar / Ficam arquivados | OUTRO | vazio | arquivamento |
| Prorroga a vigência (LC 187, art. 40, § 1º) | OUTRO | S | prorrogacao de vigencia |

Sugestão para o spec: incluir `PRORROGACAO` e `ARQUIVAMENTO` no enum `tipo_ato` e um campo `torna_sem_efeito` (várias portarias de reconsideração anulam uma portaria anterior no Art. 2º).

## 5. T2: conferência manual de 10 atos sorteados

Sorteio com semente fixa 20260930 entre os 98 atos de decisão de agosto/2026 (`metricas.py`); conferência lendo o texto integral de cada ato.
Resultado em `amostra_t2_S01082026.csv` (colunas `conf_*` e `obs`).

| Campo | Acertos |
|---|---|
| CNPJ | 10/10 |
| Nome da entidade | 10/10 |
| Tipo do ato | 10/10 |
| Deferido | 10/10 |
| Área | 10/10 |

Composição da amostra: 6 renovações, 2 reconsiderações, 1 recurso negado, 1 despacho de prazo para sanar pendências.
Como a amostra saiu toda do MS (85 de 98 atos), conferi também 10 linhas sorteadas das listas do MDS (Portarias 111 e 114/2026): 10/10 corretas em CNPJ, nome, município, tipo e deferido.

Erros encontrados e corrigidos durante o desenvolvimento (antes do sorteio): título de portaria sem `class="identifica"`, "nº ." antes do CNPJ, decisão do MEC que anula indeferimento, "CONCEDER o prazo", tabelas em anexo do MEC, "1)NOME" sem espaço, "inscritia" (erro de digitação na fonte), "DCEBAS" casando com "CEBAS", palavras coladas em textos de 2016.

Limitações remanescentes: município só com a UF nos despachos do GM/MS (o texto traz só "NOME/UF"); a validade é texto livre (não normalizada para data); nomes errados na fonte são mantidos (ex.: "INSTIT" no item 8 da Portaria MDS 113/2026; CNPJ "403.426.630/0001-10" com dígito a mais na Portaria SERES 229/2026, que o parser não reconhece).

## 6. Métrica: CNPJ presente no texto

| Mês | Atos com CNPJ | Decisões com CNPJ | CNPJ com DV válido |
|---|---|---|---|
| jun/2026 | 81/81 | 610/610 | 610/610 |
| jul/2026 | 157/158 | 174/175 | 174/175 |
| ago/2026 | 98/98 | 496/496 | 496/496 |
| Total | 336/337 (99,7%) | 1.280/1.281 (99,9%) | 99,9% |

O único ato sem CNPJ é uma decisão do Ministro da Educação em recurso (Decisão de 10/07/2026, Associação Beneficente Coração de Cristo).
Atos do MEC desse tipo exigem casamento por nome.

## 7. T3: linha do tempo pela busca do portal

Entidade principal: Santa Casa de Misericórdia de Cerquilho/SP, CNPJ 50.798.453/0001-83 (região do IFSP).
Consultas: `"50.798.453/0001-83"` (9 resultados) e `"Santa Casa de Misericórdia de Cerquilho"` com `s=do1` (13 resultados), 2 s entre requisições.

| Publicação | Ato | Decisão | Vigência |
|---|---|---|---|
| 07/12/2016 | Portaria SAS/MS 1.831/2016 | Renovação deferida | 10/11/2016 a 09/11/2019 |
| 10/10/2019 | Portaria SAES/MS 1.163/2019 | Renovação deferida | 10/11/2019 a 09/11/2022 |
| 27/02/2023 | Portaria SAES/MS 179/2023 (linha 128 da tabela) | Prorrogação da vigência (LC 187, art. 40, § 1º) | até 31/12/2023 |
| 11/06/2026 | Portaria SAES/MS 4.189/2026 | Renovação indeferida (processo 25000.194125/2023-17) | |
| 14/08/2026 | Portaria SAES/MS 4.683/2026 | Renovação deferida em reconsideração; torna sem efeito a 4.189 | 01/01/2024 a 31/12/2026 |

Status em 30/09/2026: CEBAS ativo até 31/12/2026, último ato de 14/08/2026.
Ruído da busca: Despacho GM/MS 7/2018 é sobre o PROSUS (não é CEBAS) e outras portarias GM/MS citam a entidade em tabelas de repasse.
O SisCEBAS Saúde mostra exatamente o mesmo estado (portaria 4.683, vigência 01/01/2024 a 31/12/2026, "PUBLICADO DEFERIDO EM GRAU DE RECONSIDERAÇÃO COM RECURSO - VIGENTE").

Entidade de controle: Santa Casa de Misericórdia de Paranaíba/MS, CNPJ 03.163.888/0001-71.
Renovações publicadas em 16/11/2018 (vigência 23/10/2018 a 22/10/2021), 10/10/2022 (23/10/2021 a 22/10/2024) e 04/08/2026 (23/10/2024 a 22/10/2027).
Entre 23/10/2024 e 04/08/2026 não havia ato vigente no DOU, mas a entidade não perdeu o certificado: o requerimento tempestivo mantém a validade até a decisão.

Lições para a regra de status do 22.6:

- "Último ato define o estado" funciona, desde que reconsideração e "torna sem efeito" anulem o ato anterior.
- Validade vencida sem ato novo não significa "não vigente"; pode ser renovação tempestiva pendente. O relatório deve dizer "vigência vencida em DD/MM/AAAA, possível renovação em análise" e não "sem CEBAS".
- A validade de várias renovações é retroativa e às vezes já começa vencida na data da publicação; usar sempre as datas de vigência do ato, não a data de publicação.
- Atos antigos (antes de 2018) têm palavras coladas e só aparecem na busca pelo nome; a carga histórica completa precisa dos XMLs mensais antigos.

## 8. Bases abertas oficiais de entidades com CEBAS

| Ministério | Existe? | URL | Formato | Atualização / data de corte | CNPJ | Validade / situação |
|---|---|---|---|---|---|---|
| Saúde | Sim, viva | `http://siscebas.saude.gov.br/siscebas/WebApplication/consultaPublicaPorCnpj.php?list=2258803b6e4f1ef992229c3cef66d75d&ass=87d4eeb7dec7686410748d174c0e0a11` (ícone "Lista Entidades Situação Atual") | XLS (2 MB, gerado na hora, cerca de 24 s) | coluna DATA ATUALIZAÇÃO = 30/09/2026; publicação mais recente 30/09/2026 | Sim | Sim: início e fim da vigência, nº e data da portaria, data da publicação, CEBAS SIM/NÃO, situação atual |
| Saúde | Sim, retrato | Mapa das OSCs, `1434-cebassaude.xlsx` | XLSX | arquivo de 04/12/2024; início de vigência mais recente 23/11/2023 | Sim | Sim (vigência e situação) |
| Assistência social (MDS) | Só retrato | Mapa das OSCs, `7684-cebassuas.xlsx` | XLSX (abas SITUAÇÃO CNPJ CEBAS e PRINCIPAL) | "24/10/2024" no cabeçalho | Sim | Sim (VIGENTE/VÁLIDA, início e fim); a aba PRINCIPAL tem 30.712 processos com fase e portarias |
| Assistência social (MDS) | Não achada base viva | CNEAS (`aplicacoes.mds.gov.br/cneas/`) redireciona para área restrita; lista de manifestação da sociedade civil só traz processos em consulta | | | | |
| Educação (MEC) | Só retrato | Mapa das OSCs, `8420-cebaseducacao.xlsx`, aba "SITUAÇÃO 2023" | XLSX | portaria mais recente 19/12/2023 | Sim | Sim (início, fim, nº da portaria) |
| Educação (MEC) | Não confirmada | `https://cebas.mec.gov.br/` aponta "Consulta CEBAS" para `https://siscebas2.mec.gov.br/visao-publica`, mas o host não resolve DNS em 30/09/2026; `dadosabertos.mec.gov.br` está atrás de desafio do Cloudflare (não foi contornado) | | | | |
| dados.gov.br | Não verificável sem chave | a API (`/dados/api/publico/...` e `/api/3/action/package_search`) devolve 401 sem token; a busca do site é SPA | | | | |

Números das planilhas:

- SisCEBAS Saúde (30/09/2026): 4.458 CNPJs (uma linha por requerimento mais recente), 1.642 com CEBAS = SIM, 1.871 NÃO, 945 encaminhados a outro ministério.
- MS no Mapa das OSCs: 1.641 entidades, todas SIM; 1.320 vigentes ou prorrogadas e cerca de 170 "tempestivo" (renovação em análise).
- MDS: 6.076 entidades (5.276 VIGENTE e 800 VÁLIDA).
- MEC: 1.330 linhas, 1.329 "COM CEBAS".

Cruzamento com os CNPJs que o parser extraiu do DOU (jun a ago/2026):

| Área | CNPJs no DOU | Na base do mesmo ministério | Renovações do DOU achadas | Concessões do DOU achadas |
|---|---|---|---|---|
| Saúde x SisCEBAS (30/09/2026) | 287 | 287 (100%) | 141/141 | 18/18 |
| Saúde x planilha 2024 | 287 | 195 (67,9%) | 140/141 | 4/18 |
| MDS x planilha 2024 (situação) | 957 | 571 (59,7%) | 385/388 | 0/109 |
| MDS x planilha 2024 (aba de processos) | 957 | 922 (96,3%) | | |
| MEC x planilha 2023 | 19 | 3 (15,8%) | 0/3 | 0/1 |

Interpretação:

- As planilhas de 2023/2024 têm quase todas as entidades que renovaram em 2026 (são as já certificadas), mas não têm as concessões novas nem os indeferimentos de quem nunca teve CEBAS. Isso é esperado de um retrato.
- O SisCEBAS Saúde já reflete os atos do DOU (236 dos 287 CNPJs com a mesma data de publicação; os demais têm ato posterior ou são despachos sem efeito na situação).
- O SisCEBAS mostrou uma divergência pequena com o DOU: Paranaíba tem fim de vigência 21/10/2027 no sistema e 22/10/2027 na portaria. A portaria publicada prevalece.
- No MEC a sobreposição é baixa porque os 19 CNPJs do DOU são majoritariamente arquivamentos e indeferimentos.

Recomendação:

- Saúde: usar a lista do SisCEBAS como fonte principal (download diário, um arquivo, sem login), guardando o arquivo bruto e o hash; usar o DOU como evidência do ato e como reserva se o link mudar.
- MDS e MEC: carregar a planilha oficial (data de corte 24/10/2024 no MDS e dez/2023 no MEC) como base histórica e aplicar por cima todos os atos do DOU publicados depois da data de corte, ordenados por data (último ato vence).
- Antes da data de corte, a carga histórica do DOU (XMLs mensais desde 2018) serve para reconstruir indeferimentos e cancelamentos que não aparecem nas planilhas.
- No relatório, a mensagem precisa citar a fonte e a data de corte: "CEBAS ativo segundo SisCEBAS Saúde em DD/MM/AAAA" ou "segundo planilha MDS de 24/10/2024 e DOU até DD/MM/AAAA".

## 9. Ficha 25.2

### 9.1 DOU XML mensal

| Item | Definição |
|---|---|
| Fonte / etapa | DOU Seção 1, base de dados mensal em XML da Imprensa Nacional (carga histórica). |
| Tipo | Arquivo aberto oficial (ZIP com XML). |
| URL e método | GET `https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados?ano=AAAA&mes=NomeDoMes` para listar; GET no link `.../S01MMAAAA.zip/...&download=true` para baixar (`baixar_dou.py`). |
| Parâmetros | ano, mês por extenso com acento (ex.: `Março`), seção S01/S02/S03. |
| Autenticação | Nenhuma. |
| Limites | Sem limite observado; CDN Azion; download de 52 MB em 13 s e de 640 MB em cerca de 100 s. Defasagem de 2 a 6 semanas. |
| Exemplo OK | `downloads/S01082026.zip`, matéria `515_20260804_24184362.xml` (renovação deferida, Santa Casa de Paranaíba). |
| Exemplo RESTRICAO | `515_20260814_24234799.xml` (cancelamento, FAMAD/RJ) e `515_20260807_24204978.xml` (Portarias MDS 112 a 114, indeferimentos em lista). |
| Exemplo erro / não encontrado | Mês ainda não publicado: setembro/2026 não aparece na lista de meses de 2026. |
| Campos usados e interpretação | Ver seção 4. |
| Aceita alfanumérico? | O regex aceita letras nas 12 primeiras posições e calcula o DV pelo valor ASCII menos 48; nenhum CNPJ alfanumérico apareceu nos atos. |
| Tempo médio de resposta | Parser: cerca de 8 s por mês (8.500 a 9.500 matérias). |
| Problemas conhecidos | Defasagem mensal; matérias com vários atos; títulos sem `class`; texto antigo com palavras coladas; erros de digitação na fonte; sem URL amigável do ato. |
| Data do último teste | 30/09/2026. |

### 9.2 Busca do portal da Imprensa Nacional

| Item | Definição |
|---|---|
| Fonte / etapa | Busca pública do DOU (atualização diária e reconstrução de linha do tempo por CNPJ). |
| Tipo | JSON descoberto (embutido no HTML). |
| URL e método | GET `https://www.in.gov.br/consulta/-/buscar/dou` (`busca_dou.py`). |
| Parâmetros | `q`, `s` (todos, do1, do2, do3), `exactDate` (all, dia, semana, mes, ano, personalizado), `publishFrom`/`publishTo` (mesmo ano), `sortType`, `delta`, e o cursor de paginação. |
| Autenticação | Nenhuma; sem CAPTCHA. |
| Limites | Não observados com 2 s entre requisições; período personalizado não pode atravessar o ano. |
| Exemplo OK | `downloads/busca/t3_50798453000183.json`. |
| Exemplo RESTRICAO | Portaria 4.189/2026 (indeferimento) em `downloads/busca/t3/711425683.html`. |
| Exemplo erro / não encontrado | `downloads/busca/t3_SantaCasadeMisericrdiadeCerquilhoCEBAS.json` (0 resultados com nome entre aspas mais outra palavra). |
| Campos usados e interpretação | `title`, `pubDate`, `pubName`, `hierarchyStr` (órgão), `urlTitle` (URL do ato), `content` (trecho com destaque), `classPK`, `score`, `displayDateSortable`. |
| Aceita alfanumérico? | Busca textual; deve aceitar, não testado. |
| Tempo médio de resposta | 1,2 a 1,8 s por página. |
| Problemas conhecidos | Busca aproximada traz falsos positivos; não acha CNPJ colado ao texto; precisa de duas consultas (CNPJ e nome). |
| Data do último teste | 30/09/2026. |

### 9.3 SisCEBAS Saúde, lista de situação atual

| Item | Definição |
|---|---|
| Fonte / etapa | Lista pública "Entidades Situação Atual" do SisCEBAS Saúde (fonte principal para a área da saúde). |
| Tipo | Arquivo oficial gerado sob demanda (XLS). |
| URL e método | GET `http://siscebas.saude.gov.br/siscebas/WebApplication/consultaPublicaPorCnpj.php?list=2258803b6e4f1ef992229c3cef66d75d&ass=87d4eeb7dec7686410748d174c0e0a11`. |
| Parâmetros | Nenhum além dos tokens fixos do link (copiados da página; podem mudar). |
| Autenticação | Nenhuma. A consulta individual por CNPJ na mesma página tem CAPTCHA e reCAPTCHA e não deve ser usada; o download da lista completa não tem. |
| Limites | Cerca de 24 s para gerar; usar no máximo 1 download por dia. |
| Exemplo OK | `downloads/bases_abertas/siscebas_saude_20260930_ListaEntidadeSituacaoAtual.xls`, linha do CNPJ 50.798.453/0001-83. |
| Exemplo RESTRICAO | Situações "PUBLICADO INDEFERIDO" (1.073) e "PUBLICADO DEFERIDO - NÃO VIGENTE - SUPERVISÃO CANCELAMENTO" (72). |
| Exemplo erro / não encontrado | CNPJ ausente da lista = nunca requereu CEBAS na saúde (não prova ausência em MEC ou MDS). |
| Campos usados e interpretação | CNPJ REQUERENTE, NOME, UF, MUNICÍPIO, PROTOCOLO, ASSUNTO, TIPO DE DECISÃO, NÚMERO/DATA DA PORTARIA, DATA DA PUBLICAÇÃO, INÍCIO/FIM DA VIGÊNCIA, CEBAS (SIM, NÃO, ENCAMINHADO PARA OUTRO MINISTÉRIO), SITUAÇÃO ATUAL, DATA ATUALIZAÇÃO. |
| Aceita alfanumérico? | CNPJ formatado em texto; não testado. |
| Tempo médio de resposta | 24 s. |
| Problemas conhecidos | Container OLE do XLS vem levemente corrompido (`xlrd` precisa de `ignore_workbook_corruption=True`); link com tokens opacos; servidor só HTTP; pequenas divergências de data com o DOU. |
| Data do último teste | 30/09/2026. |

## 10. Passos manuais que restam

INLABS (exige cadastro do dono do projeto; não foi criada conta):

1. Acessar `https://inlabs.in.gov.br/acessar.php`.
2. Na caixa "Registrar", preencher e-mail (login), senha, repetição da senha, nome completo, telefone (opcional), UF/cidade e nome da empresa (pode ser "IFSP - projeto de extensão").
3. Confirmar o cadastro pelo e-mail recebido, se for pedido.
4. Guardar e-mail e senha em variável de ambiente (`INLABS_EMAIL`, `INLABS_SENHA`), nunca no código.
5. Informar ao agente; o download diário do XML da Seção 1 (`DO1`) substitui a defasagem de 2 a 6 semanas do XML mensal. A Imprensa Nacional mantém um script de exemplo no GitHub (`Imprensa-Nacional/inlabs`), a conferir.

Outros:

- Pedido via LAI (Fala.BR) ao MDS e ao MEC pedindo a lista atual de entidades com CEBAS (CNPJ, situação, início e fim da vigência), citando que o MS já publica a sua no SisCEBAS. Isso também serve de teste T4.
- Verificar em outro dia ou rede se `https://siscebas2.mec.gov.br/visao-publica` volta a responder; se sim, documentar se tem lista sem CAPTCHA.
- Opcional: abrir `dados.gov.br` no navegador e buscar "CEBAS" e "entidades beneficentes" (a API exige chave de conta gov.br).
- Baixar a carga histórica de XMLs mensais (2018 em diante, cerca de 0,5 a 0,7 GB por mês de S01, quase tudo imagem; pode ser filtrado na hora sem guardar os JPG).

## 11. Arquivos

| Arquivo | Conteúdo |
|---|---|
| `baixar_dou.py` | Lista e baixa o ZIP mensal da seção pedida, com metadados (URL, bytes, SHA-256). |
| `parser_cebas.py` | Parser (XML para CSV de decisões). |
| `metricas.py` | Métricas do T1 e item 6, e sorteio do T2. |
| `busca_dou.py` | Cliente da busca do portal (JSON embutido, paginação por cursor). |
| `cruzar_planilhas.py` | Análise das planilhas oficiais e do SisCEBAS e cruzamento com o DOU. |
| `cebas_S01062026.csv`, `cebas_S01072026.csv`, `cebas_S01082026.csv` | Decisões extraídas (separador `;`, UTF-8 com BOM). |
| `amostra_t2_S01082026.csv` | 10 atos sorteados com a conferência manual. |
| `metricas_S01*.json`, `cruzamento_planilhas.json` | Números desta ficha. |
| `downloads/` | ZIPs brutos com `.meta.json`, respostas da busca (`busca/`), páginas dos atos do T3 (`busca/t3/`), sondagens de bases abertas e XLS do SisCEBAS (`bases_abertas/`). |
