# Ficha de fonte - Portal da Transparência (CEPIM, CEIS, CNEP) e TCU Inidôneos

Fase 0, sem chave da API do Portal.
Data dos testes: 30/09/2026 (horário de Brasília, noite).
User-Agent usado em todas as requisições: `validador-osc-ifsp/0.1 (projeto academico de extensao)`, com 1,5 s entre requisições à mesma fonte.

Arquivos desta pasta:

- `baixar_dados_abertos.py`: descobre a data mais recente e baixa os zips de CEPIM, CEIS e CNEP.
- `analisar_dados_abertos.py`: perfila os CSVs, lista candidatos e gera as amostras (saída em `analise_saida.txt`).
- `consultar_local.py`: consulta local por CNPJ/CPF (protótipo do plano B), busca exata e por raiz.
- `portal_openapi.py`: baixa o OpenAPI, extrai as rotas de sanções (`openapi_sancoes.txt`) e executa o T6.
- `tcu_inidoneos.py`: baixa a lista completa de inidôneos do TCU e testa o filtro.
- `portal-openapi.json`: contrato oficial (versionar).
- `amostras/`: 10 linhas de cada CSV, em UTF-8, com CPF mascarado (versionar).
- `exemplos/`: respostas de erro da API (T6).
- `tcu/`: lista completa de inidôneos e exemplos de filtro.
- `downloads/`: zips e CSVs brutos (cerca de 39 MB, fora do versionamento via `.gitignore`).
- `referencia_cnpjs.md`: casos de teste.

---

## Ficha A - API de dados do Portal da Transparência (sem chave)

| Item | Definição |
|---|---|
| Fonte / etapa | Portal da Transparência, verificações 6 (CEPIM), 7 (CEIS), 8 (CNEP) e 10 (nome de dirigente). |
| Tipo | API oficial. |
| URL e método | `GET https://api.portaldatransparencia.gov.br/api-de-dados/cepim`, `/ceis`, `/cnep` (e `/{id}` de cada uma). Também existe `/acordos-leniencia`. |
| Parâmetros | CEPIM: `cnpjSancionado`, `nomeSancionado`, `ufSancionado`, `orgaoEntidade`, `pagina` (obrigatório, padrão 1). CEIS e CNEP: `codigoSancionado` (CNPJ ou CPF), `nomeSancionado` ("Nome, nome fantasia ou razão social do Sancionado"), `orgaoSancionador`, `dataInicialSancao`, `dataFinalSancao` (DD/MM/AAAA), `pagina` (obrigatório, padrão 1). Todos os filtros são string; não há parâmetro de tamanho de página. |
| Autenticação | Header `chave-api-dados` (securityScheme `apiKey` global no OpenAPI). |
| Limites | Não constam no OpenAPI. Valem os do 19 (400/min, 700/min de 00h a 06h), a confirmar com chave. |
| Exemplo OK | Pendente (precisa de chave). |
| Exemplo RESTRICAO | Pendente (precisa de chave). Usar os CNPJs de `referencia_cnpjs.md`. |
| Exemplo erro / não encontrado | `exemplos/erro_sem_chave_ceis.txt`, `exemplos/erro_sem_chave_cepim.txt`, `exemplos/erro_chave_invalida_ceis.txt`. |
| Campos usados e interpretação | Ver "Schemas" abaixo. |
| Aceita alfanumérico? | Não testável sem chave. Os parâmetros são string, então a entrada não é rejeitada pelo tipo. |
| Tempo médio de resposta | 401 em cerca de 0,02 s (resposta da borda CloudFront). Tempo de resposta real pendente. |
| Problemas conhecidos | O 401 sem chave volta com `cache-control: public, max-age=7200` e `x-cache: Error from cloudfront`; o cliente não deve cachear respostas 401. O content-type do 401 sem chave é `application/json;charset=ISO-8859-1`; o de chave inválida é `application/json` sem charset. O tamanho da página não está documentado (T7). |
| Data do último teste | 30/09/2026. |

### OpenAPI

- `GET https://api.portaldatransparencia.gov.br/v3/api-docs` responde 200 sem chave (OpenAPI 3.0.1, 109 rotas, cerca de 170 KB).
- Também abertos sem chave: `/swagger-ui/index.html` e `/v3/api-docs/swagger-config`.
- `/` e `/swagger-ui.html` respondem 302.
- Salvo em `portal-openapi.json`; o resumo das rotas de sanções está em `openapi_sancoes.txt`.
- Todas as respostas 200 estão declaradas como `*/*` e como array do DTO; não há envelope de paginação.
- As datas são declaradas como string sem formato; pelo parâmetro de entrada, o formato provável é DD/MM/AAAA, a confirmar com chave.

### Schemas (nomes exatos do OpenAPI)

`CeisDTO` e `CnepDTO` têm a mesma estrutura; o CNEP acrescenta `valorMulta` (string).

```
id, dataReferencia, dataInicioSancao, dataFimSancao, dataPublicacaoSancao,
dataTransitadoJulgado, dataOrigemInformacao,
tipoSancao { descricaoResumida, descricaoPortal },
fonteSancao { nomeExibicao, telefoneContato, enderecoContato },
fundamentacao [ { codigo, descricao } ],
orgaoSancionador { nome, siglaUf, poder, esfera },
sancionado { nome, codigoFormatado },
pessoa { id, cpfFormatado, cnpjFormatado, numeroInscricaoSocial, nome,
         razaoSocialReceita, nomeFantasiaReceita, tipo },
valorMulta (só CNEP),
textoPublicacao, linkPublicacao, detalhamentoPublicacao, numeroProcesso,
abrangenciaDefinidaDecisaoJudicial, informacoesAdicionaisDoOrgaoSancionador
```

`CepimDTO`:

```
id, dataReferencia, motivo,
orgaoSuperior { nome, codigoSIAFI, cnpj, sigla, descricaoPoder,
                orgaoMaximo { codigo, sigla, nome } },
pessoaJuridica { id, cpfFormatado, cnpjFormatado, numeroInscricaoSocial, nome,
                 razaoSocialReceita, nomeFantasiaReceita, tipo },
convenio { codigo, objeto, numero }
```

Consequências para o adapter:

- O CNPJ do sancionado vem aninhado e formatado: `pessoa.cnpjFormatado` (CEIS/CNEP), `pessoaJuridica.cnpjFormatado` (CEPIM) e também `sancionado.codigoFormatado`; normalizar para dígitos antes de comparar (9.4).
- Vigência: `dataFimSancao` (string, possivelmente vazia).
- A categoria da sanção fica em `tipoSancao.descricaoResumida` / `descricaoPortal`.
- O CEPIM da API não declara campo de data de início; tem só `dataReferencia`.
- Filtro por nome existe nas três rotas (`nomeSancionado`); o filtro de CPF no CEIS/CNEP é o mesmo `codigoSancionado` (T8 respondido no contrato, falta confirmar o comportamento: exato ou "contém").

### T6 - chamadas sem chave e com chave inválida

| Chamada | HTTP | Corpo |
|---|---|---|
| `/ceis?codigoSancionado=19131243000197&pagina=1` sem header | 401 | `{"Erro na API":"Chave de API não informada! Para obter a chave acesse http://www.portaldatransparencia.gov.br/api-de-dados/cadastrar-email"}` |
| `/cepim?cnpjSancionado=19131243000197&pagina=1` sem header | 401 | igual ao anterior |
| `/ceis?...` com `chave-api-dados: 000...0` | 401 | `{"Erro na API":"Chave de API inválida!"}` |

A chave do corpo de erro é `"Erro na API"` (com espaços); o adapter pode distinguir os dois casos pelo texto, mas o estado é INDISPONIVEL nos dois (19.3).

---

## Ficha B - Arquivos de dados abertos do Portal (plano B sem chave)

| Item | Definição |
|---|---|
| Fonte / etapa | Download de dados do Portal da Transparência: CEPIM, CEIS, CNEP. |
| Tipo | Arquivo oficial (zip com CSV). |
| URL e método | 1) `GET https://portaldatransparencia.gov.br/download-de-dados/<cadastro>` devolve HTML com a data disponível no trecho `arquivos.push({"ano" : "2026", "mes" : "09", "dia" : "28", "origem" : "CEPIM"})`. 2) `GET https://portaldatransparencia.gov.br/download-de-dados/<cadastro>/AAAAMMDD` responde 302 para `https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/<cadastro>/AAAAMMDD_<CADASTRO>.zip` (S3 + CloudFront). `<cadastro>` em minúsculas (`cepim`, `ceis`, `cnep`). |
| Parâmetros | Só a data no caminho. A página lista uma única data (a mais recente). |
| Autenticação | Nenhuma. Não houve CAPTCHA nas duas URLs acima. O JavaScript estático do site (`/static/js/...`) é protegido por AWS WAF com CAPTCHA, mas não é necessário. |
| Limites | Não documentados. Os arquivos são servidos por CDN. |
| Exemplo OK | Ausência do CNPJ no CSV. |
| Exemplo RESTRICAO | `amostras/amostra_CEPIM.csv`, `amostras/amostra_CEIS.csv` (inclui PF, PJ vigente e PJ expirada), `amostras/amostra_CNEP.csv`. |
| Exemplo erro / não encontrado | Não testado (data inexistente). |
| Campos usados e interpretação | Ver tabela de colunas abaixo. |
| Aceita alfanumérico? | Hoje todos os documentos são numéricos (14 dígitos PJ, 11 PF). A coluna é texto, então suportará alfanumérico se a CGU publicar. |
| Tempo médio de resposta | Download completo dos três em poucos segundos (zip de 81 KB, 3,4 MB e 202 KB). |
| Problemas conhecidos | Ver "Qualidade do dado" abaixo. |
| Data do último teste | 30/09/2026. |

### Formato

| Cadastro | Data do arquivo | Last-Modified | Zip | CSV | Linhas de dados |
|---|---|---|---|---|---|
| CEPIM | 28/09/2026 | 30/09/2026 13:35 GMT | 81 KB | `20260928_CEPIM.csv`, 640 KB | 3.526 (1.941 CNPJs distintos) |
| CEIS | 30/09/2026 | 30/09/2026 21:15 GMT | 3,4 MB | `20260930_CEIS.csv`, 34 MB | 23.720 |
| CNEP | 30/09/2026 | 30/09/2026 21:15 GMT | 202 KB | `20260930_CNEP.csv`, 1,8 MB | 1.819 |

- Encoding ISO-8859-1 (latin-1), separador `;`, todos os campos entre aspas, quebra de linha CRLF, cabeçalho na primeira linha.
- Datas em DD/MM/AAAA; valores com vírgula decimal (`517662,90`).
- CEIS e CNEP são atualizados diariamente; o CEPIM tinha dois dias de defasagem no momento do teste.
- O HTML da página de download traz um texto "Última atualização: 01/10/2024" que não corresponde ao arquivo; usar a data do nome do arquivo.

### Colunas

CEPIM (5): `CNPJ ENTIDADE`, `NOME ENTIDADE`, `NÚMERO CONVÊNIO`, `ÓRGÃO CONCEDENTE`, `MOTIVO DO IMPEDIMENTO`.

CEIS (24): `CADASTRO`, `CÓDIGO DA SANÇÃO`, `TIPO DE PESSOA` (F/J), `CPF OU CNPJ DO SANCIONADO`, `NOME DO SANCIONADO`, `NOME INFORMADO PELO ÓRGÃO SANCIONADOR`, `RAZÃO SOCIAL - CADASTRO RECEITA`, `NOME FANTASIA - CADASTRO RECEITA`, `NÚMERO DO PROCESSO`, `CATEGORIA DA SANÇÃO`, `DATA INÍCIO SANÇÃO`, `DATA FINAL SANÇÃO`, `DATA PUBLICAÇÃO`, `PUBLICAÇÃO`, `DETALHAMENTO DO MEIO DE PUBLICAÇÃO`, `DATA DO TRÂNSITO EM JULGADO`, `ABRAGÊNCIA DA SANÇÃO` (sic), `ÓRGÃO SANCIONADOR`, `UF ÓRGÃO SANCIONADOR`, `ESFERA ÓRGÃO SANCIONADOR`, `FUNDAMENTAÇÃO LEGAL`, `DATA ORIGEM INFORMAÇÃO`, `ORIGEM INFORMAÇÕES`, `OBSERVAÇÕES`.

CNEP (25): as mesmas do CEIS, com `VALOR DA MULTA` entre `CATEGORIA DA SANÇÃO` e `DATA INÍCIO SANÇÃO`.

Correspondência provável com a API: `CÓDIGO DA SANÇÃO` = `id`; `CATEGORIA DA SANÇÃO` = `tipoSancao.descricaoResumida`; `ABRAGÊNCIA DA SANÇÃO` = `abrangenciaDefinidaDecisaoJudicial`; `ORIGEM INFORMAÇÕES` = `fonteSancao.nomeExibicao`.
A confirmar com a primeira resposta real.

### Identificação do sancionado e pessoas físicas

- O sancionado é identificado por `TIPO DE PESSOA` + `CPF OU CNPJ DO SANCIONADO` (só dígitos) + `NOME DO SANCIONADO`.
- CEIS: 14.560 PJ, 9.148 PF, 12 sem tipo. CNEP: 1.779 PJ, 28 PF, 12 sem tipo.
- O CPF de pessoa física vem completo, sem máscara (9.148 de 9.148 com dígito verificador válido), e o nome vem sempre preenchido.
- Isso viabiliza a verificação 10 por nome + 6 dígitos centrais do CPF do QSA, mesmo sem a API.
- Por ser dado pessoal, as amostras versionadas mascaram o CPF.

### Qualidade do dado (cuidados para o motor)

- O código da sanção é único por linha, mas há linhas repetidas com mesmos dados e códigos diferentes (exemplo: IPCIM no CNEP aparece duplicado).
- A categoria não é confiável para vigência: há "sem prazo determinado" com data final e "com prazo determinado" sem data final. A regra deve olhar só a data.
- 2.030 linhas do CEIS e 1.784 do CNEP não têm data final (no CNEP é o normal, porque multa e publicação não têm prazo).
- 12 linhas em cada arquivo têm `TIPO DE PESSOA` vazio e documento com 7, 9, 11 ou 14 dígitos (estrangeiros e erros de cadastro); o parser não pode supor tamanho fixo.
- O CEPIM não tem nenhuma data: estar no arquivo já é o impedimento.
- Um CNPJ pode ter muitas linhas (até 67 convênios no CEPIM; 10 no IMDC), o que indica que a API pode paginar para um único CNPJ (T7).
- Filiais: 172 linhas no CEIS, 25 no CNEP e 23 no CEPIM têm ordem diferente de 0001. Não existe registro só com a raiz. Ver `referencia_cnpjs.md`.

### Uso como plano B

- Baixar os três zips uma vez por dia (o nome do arquivo já traz a data) e carregar numa tabela local indexada pelo documento normalizado.
- A consulta local reproduz as verificações 6, 7 e 8 sem chave e sem limite de requisições (ver `consultar_local.py`).
- Desvantagem: defasagem de até 1 dia (CEIS/CNEP) ou alguns dias (CEPIM) e menos campos que a API (sem link da publicação, sem objeto do convênio).

---

## Ficha C - TCU, Relação de Inidôneos

| Item | Definição |
|---|---|
| Fonte / etapa | TCU, licitantes inidôneos (verificação 9). |
| Tipo | API oficial não documentada no 20 (Oracle ORDS REST, JSON), usada pela lista pública de dados abertos do TCU. |
| URL e método | `GET https://contas.tcu.gov.br/ords/condenacao/consulta/inidoneos` |
| Parâmetros | Paginação ORDS: `offset`, `limit` (aceitou `limit=100`). Filtro ORDS: `q={"cpf_cnpj":"30.139.983/0001-02"}`. |
| Autenticação | Nenhuma. Sem CAPTCHA. |
| Limites | Não documentados. 2 requisições de lista + 3 de filtro sem bloqueio. |
| Exemplo OK | `tcu/exemplo_nada_consta.json` (filtro com 19.131.243/0001-97: `{"items":[],"hasMore":false,...,"count":0}`). |
| Exemplo RESTRICAO | `tcu/exemplo_filtro_fmt.json` (filtro com CNPJ formatado, 1 item). |
| Exemplo erro / não encontrado | `tcu/exemplo_filtro_digitos.json`: filtro com CNPJ só em dígitos devolve 0 itens. O filtro é igualdade de string; é obrigatório formatar o CNPJ como `00.000.000/0000-00`. |
| Campos usados e interpretação | Envelope: `items`, `hasMore`, `limit`, `offset`, `count`, `links`. Item: `nome`, `cpf_cnpj` (formatado, 18 caracteres), `processo`, `deliberacao` (ex.: `AC-002180/2023-PL`), `data_transito_julgado`, `data_final`, `data_acordao` (ISO 8601 em UTC, ex.: `2028-02-01T03:00:00Z`), `uf`, `municipio`. Qualquer item para o CNPJ = RESTRICAO; conferir `data_final` mesmo assim. |
| Aceita alfanumérico? | O filtro é string; deve funcionar com a máscara alfanumérica se o TCU cadastrar assim. Não testável hoje. |
| Tempo médio de resposta | 0,18 s. |
| Problemas conhecidos | Ver abaixo. |
| Data do último teste | 30/09/2026. |

Resultado da coleta (`tcu/inidoneos_completo.json`):

- 91 registros, todos PJ, todos com `data_final` futura: a lista só traz inidôneos vigentes.
- 78 dos 91 também aparecem no CEIS com origem "TRIBUNAL DE CONTAS DA UNIÃO"; 13 não aparecem no CEIS. O CEIS não substitui a consulta ao TCU.
- Duas OSCs inidôneas vigentes: 03.463.763/0001-67 (Instituto Terra Social) e 21.145.289/0001-07 (IMDC).
- O link `describedby` do envelope (`/ords/condenacao/metadata-catalog/consulta/item`) responde 404.

Caminhos que não funcionaram:

- `https://contas.tcu.gov.br/ords/f?p=1660:2` (APEX citado no 20): HTTP 500 com o nosso User-Agent; com User-Agent de navegador, bloqueio do firewall de aplicação do TCU ("Requisição rejeitada", com ID de suporte). Não insisti.
- `dadosabertos.tcu.gov.br`: o domínio não resolve.
- A página de dados abertos `https://sites.tcu.gov.br/dados-abertos/inidoneos-irregulares/` aponta para `https://certidoes.apps.tcu.gov.br/lista-inidoneos` (e `lista-inabilitados`, `lista-responsaveis`, `lista-implicacao-eleitoral`), que é uma SPA com download em CSV pelo navegador; o dicionário de dados está em `.../dicionario-dados.html`. A API ORDS acima entrega o mesmo conteúdo em JSON.
- A Consulta Consolidada (certidoes-apf) e o CNJ CNIA não foram testados nesta etapa.

---

## O que ainda depende da chave do Portal

- T1: formato real de "nada consta" (lista vazia esperada pelo contrato).
- T2 e T3: respostas reais de RESTRICAO para os CNPJs de `referencia_cnpjs.md`, e confirmação do formato das datas.
- T4: se `codigoSancionado`/`cnpjSancionado` é exato ou por raiz (usar Instituto Global 44.551.605/0001-46 e IDEAS 24.006.302/0001-35).
- T5: CNPJ com e sem pontuação.
- T7: tamanho da página (não está no OpenAPI) e paginação de um CNPJ com muitos registros (IMDC no CEPIM, 10 linhas).
- T8: comportamento do `nomeSancionado` (exato, prefixo ou "contém"; acentos).
- Limites reais de requisições e tempo de resposta.

## API com chave - execução do roteiro 19.4 (01/10/2026)

Script: `fase0/portal/testar_api_com_chave.py`.
A chave é lida do `.env` e usada só no header; foi verificado por script que nenhum arquivo salvo em `respostas_api/` contém a chave.
Respostas brutas em `fase0/portal/respostas_api/`.

| Teste | Resultado |
|---|---|
| T1 nada consta | HTTP 200 com lista vazia `[]` nas três rotas. |
| T2 CEPIM positivo | Bom Jesus do Tocantins: 1 registro. Santa Casa de Pacaembu: 2 registros. Campos: `id`, `dataReferencia`, `motivo`, `orgaoSuperior`, `pessoaJuridica`, `convenio`. Sem datas de impedimento. |
| T3 CEIS/CNEP positivo | Vigente, expirado e "vence em 22/11/2026" retornam 1 registro cada; CNEP Pacaembu 4 registros. Datas em DD/MM/AAAA (`dataInicioSancao`, `dataFimSancao`); ausência vem como texto "Sem informação". CNPJ em `sancionado.codigoFormatado` e `pessoa.cnpjFormatado`. |
| T4 exato ou raiz | Busca exata pelos 14 dígitos: a filial sancionada retorna 1 registro e a matriz limpa retorna 0. Busca só pela raiz (8 dígitos) retorna 0. Portanto não há busca por raiz: para cobrir matriz e filial é preciso consultar cada CNPJ. |
| T5 formatado | CNPJ com pontuação funciona igual ao CNPJ só com dígitos. |
| T6 erros | Já documentado sem chave: HTTP 401 com chave ausente ou inválida. |
| T7 paginação | Página com até 15 registros. IMDC (10 convênios no CEPIM) cabe na página 1; página 2 vem vazia. |
| T8 nome | `nomeSancionado` faz busca parcial e ampla ("PLURAL" trouxe 7 registros, incluindo empresas não relacionadas). A consulta pelo nome completo levou 7,3 s. Útil só como apoio, não para casamento de dirigentes. |
| Latência | Mediana 136 ms, máximo 7,3 s (busca por nome), 22 chamadas, nenhum 429. |

### Trade-offs: API com chave x caminho sem chave

| Critério | API com chave | CSV diário + OpenCNPJ + TCU (sem chave) |
|---|---|---|
| Atualidade | `dataReferencia` 30/09/2026, a mesma data dos CSVs diários: a API não é mais fresca que o download. | CSV do dia; OpenCNPJ atualizado no mesmo dia. |
| Credencial | Chave vinculada ao CPF de uma pessoa física; inviável para produção. | Nenhuma. |
| Limites | 400 req/min (700 de madrugada); estourar suspende a chave. | Download diário; consultas locais sem limite. |
| Matriz e filial | Uma chamada por CNPJ, por rota (3 rotas x 2 CNPJs = 6 chamadas). | Consulta local por raiz ou CNPJ, na mesma query. |
| Dirigentes | Busca por nome ampla e lenta; sem CPF. | CSV tem CPF completo de PF: casamento nome + 6 dígitos. |
| Disponibilidade | Depende do Portal no momento da consulta. | Base local continua funcionando se o Portal cair (dentro da idade máxima). |
| Evidência | Resposta JSON por consulta. | Arquivo do dia com hash + linha usada. |

Conclusão: a API com chave não traz dado mais recente nem campo que falte no CSV.
O caminho sem chave (D14) é superior para produção; a API fica só como ferramenta de conferência manual.
