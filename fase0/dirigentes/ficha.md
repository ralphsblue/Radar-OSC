# Ficha - Dirigentes (art. 39 da Lei 13.019/2014) e fontes por pessoa física

Fase 0, verificação 10 do spec (capítulo 13), decisão D15 (ampliação em análise).
Data dos testes: 01/10/2026 (madrugada, horário de Brasília), a partir da máquina do projeto (IP residencial).
User-Agent em todas as chamadas: `validador-osc-ifsp/0.1 (projeto academico de extensao)`, com 2 s entre chamadas.
Nenhum CAPTCHA ou login foi contornado.
Nenhum CPF completo foi gravado fora de `downloads/` (ignorado pelo `.gitignore` desta pasta).

## Resumo

- Dá para cobrir bem mais do art. 39, VII, sem chave e sem CAPTCHA, com o mesmo casamento por nome + 6 dígitos do meio do CPF.
- TCU publica, em API JSON oficial e documentada, a lista completa de responsáveis com contas julgadas irregulares (CADIRREG, 41.071 linhas de PF, 23.665 CPFs) e a de inabilitados para cargo em comissão (774 linhas, 599 CPFs), ambas com CPF completo e nome.
- 22.749 desses CPFs de contas irregulares e 540 dos inabilitados não estão no CEIS nem no CNEP: é cobertura nova de verdade.
- O CEIS já cobre boa parte da improbidade (VII, c): 7.113 das 9.148 linhas de PF do CEIS vêm do CNJ (CNIA), todas com proibição de contratar vigente.
- O CNIA tem consulta pública sem CAPTCHA (o CAPTCHA foi retirado), mas só busca por CPF completo ou nome exato, e a busca por nome não mostra CPF; com o QSA mascarado ele não serve para casamento forte.
- TCE-SP publica, mensalmente, a relação de prestação de contas de repasses ao Terceiro Setor julgadas irregulares (10.026 linhas, cerca de 4.100 pessoas), que é exatamente o VII, a para parcerias em SP.
- O CPF do TCE-SP vem como `999.XXX.XXX-99`, máscara complementar à do QSA (`***999999**`); dá para corroborar o casamento pelo dígito verificador sem gravar o CPF.
- Não existe base agregada nacional de contas julgadas irregulares por tribunais de contas estaduais e municipais; cada TCE publica a sua, em formato próprio.
- Teste ponta a ponta com QSA real: em 25 OSCs condenadas pelo TCU, 12 tiveram o dirigente atual encontrado na lista, 10 delas no mesmo processo da OSC; nenhuma OSC sem sanção conhecida teve achado.
- Recomendação para o MVP: incluir TCU contas irregulares (com janela de 8 anos), TCU inabilitados (vigentes) e TCE-SP Terceiro Setor (com DV), sempre como ALERTA.

## 1. Texto do art. 39 e quem ele atinge

O planalto.gov.br não respondeu a partir desta máquina (conexão resetada após o envio da requisição, com httpx, curl e também com o WebFetch).
Não insisti nem troquei o User-Agent.
O texto abaixo vem da compilação atualizada da Câmara dos Deputados (`https://www2.camara.leg.br/legin/fed/lei/2014/lei-13019-31-julho-2014-779123-normaatualizada-pl.html`), localizada pelo LexML e pelo normas.leg.br.
Vale conferir no planalto quando ele voltar a responder; o texto bate com as declarações-modelo de editais encontradas na busca.

Trecho relevante (redação vigente, com as alterações da Lei 13.204/2015):

> Art. 39. Ficará impedida de celebrar qualquer modalidade de parceria prevista nesta Lei a organização da sociedade civil que:
> I - não esteja regularmente constituída ou, se estrangeira, não esteja autorizada a funcionar no território nacional;
> II - esteja omissa no dever de prestar contas de parceria anteriormente celebrada;
> III - tenha como dirigente membro de Poder ou do Ministério Público, ou dirigente de órgão ou entidade da administração pública da mesma esfera governamental na qual será celebrado o termo de colaboração ou de fomento, estendendo-se a vedação aos respectivos cônjuges ou companheiros, bem como parentes em linha reta, colateral ou por afinidade, até o segundo grau;
> IV - tenha tido as contas rejeitadas pela administração pública nos últimos cinco anos, exceto se: a) for sanada a irregularidade [...]; b) for reconsiderada ou revista a decisão pela rejeição; c) a apreciação das contas estiver pendente de decisão sobre recurso com efeito suspensivo;
> V - tenha sido punida com uma das seguintes sanções, pelo período que durar a penalidade: a) suspensão de participação em licitação e impedimento de contratar com a administração; b) declaração de inidoneidade para licitar ou contratar com a administração pública; c) a prevista no inciso II do art. 73 desta Lei; d) a prevista no inciso III do art. 73 desta Lei;
> VI - tenha tido contas de parceria julgadas irregulares ou rejeitadas por Tribunal ou Conselho de Contas de qualquer esfera da Federação, em decisão irrecorrível, nos últimos 8 (oito) anos;
> VII - tenha entre seus dirigentes pessoa: a) cujas contas relativas a parcerias tenham sido julgadas irregulares ou rejeitadas por Tribunal ou Conselho de Contas de qualquer esfera da Federação, em decisão irrecorrível, nos últimos 8 (oito) anos; b) julgada responsável por falta grave e inabilitada para o exercício de cargo em comissão ou função de confiança, enquanto durar a inabilitação; c) considerada responsável por ato de improbidade, enquanto durarem os prazos estabelecidos nos incisos I, II e III do art. 12 da Lei nº 8.429, de 2 de junho de 1992.
> § 2º Em qualquer das hipóteses previstas no caput, persiste o impedimento para celebrar parceria enquanto não houver o ressarcimento do dano ao erário, pelo qual seja responsável a organização da sociedade civil ou seu dirigente.

Ajustes de leitura em relação ao pedido original:

- O VII, a não fala de contas rejeitadas "por qualquer ente": fala de contas relativas a parcerias julgadas irregulares ou rejeitadas por Tribunal ou Conselho de Contas, em decisão irrecorrível, nos últimos 8 anos.
- "Contas rejeitadas pela administração pública" (inciso IV, 5 anos) é hipótese da OSC, não do dirigente.
- O VII não tem alínea sobre sanções de licitação ao dirigente; sanções do inciso V são da OSC.
- Os dirigentes aparecem em três pontos: inciso III (vínculo com o poder público e parentes), inciso VII (a, b, c) e § 2º (dano não ressarcido pelo dirigente).
- O VII, c remete aos prazos dos incisos I a III do art. 12 da Lei 8.429/1992, que são a suspensão dos direitos políticos e a proibição de contratar; o CNIA registra os dois separadamente (ver seção 3.3).

## 2. Mapa art. 39 x fonte

Legenda: coberto = fonte pública com o recorte exato da hipótese; parcial = fonte cobre parte (esfera, natureza ou prazo); não coberto = sem fonte pública utilizável.
"Hoje" é o MVP aprovado (D14 e D15); "proposta" é com as fontes desta ficha.

| Hipótese | Alvo | Hoje | Proposta | Fonte e observação |
|---|---|---|---|---|
| I | OSC | coberto | coberto | Receita (situação cadastral), fora do escopo desta ficha. |
| II | OSC | não coberto | não coberto | Omissão no dever de prestar contas; sem fonte nacional por OSC (CEPIM cobre parte, ver ficha do Portal). |
| III | dirigente e parentes | não coberto | não coberto | Não há fonte pública por pessoa que diga quem é membro de Poder, do MP ou dirigente de órgão da mesma esfera, e parentesco é impossível de verificar. Fica para declaração da OSC. |
| IV | OSC | parcial (CEPIM) | parcial (CEPIM) | Fora do escopo desta ficha. |
| V | OSC | coberto | coberto | CEIS, CNEP, TCU inidôneos (D14). |
| VI | OSC | não coberto | parcial | Achado lateral: a lista de contas irregulares do TCU traz 6.817 linhas com CNPJ, filtráveis por CNPJ. Não informa se a conta é de parceria. |
| VII, a | dirigente | não coberto | parcial | TCU contas irregulares (esfera federal, natureza não informada) + TCE-SP Terceiro Setor (SP, exatamente contas de parceria). Demais TCEs e TCMs sem base agregada. |
| VII, b | dirigente | não coberto | coberto (TCU) | TCU inabilitados, só vigentes, com data final. Inabilitações por TCEs, se houver na lei orgânica local, ficam de fora. |
| VII, c | dirigente | parcial (CEIS via CNJ) | parcial | CEIS traz as condenações do CNIA com proibição de contratar vigente. Suspensão de direitos políticos sem proibição de contratar só está no CNIA, que exige CPF completo para casamento forte. |
| § 2º | OSC e dirigente | não coberto | não coberto | Nenhuma lista diz se o dano foi ressarcido. A lista do TCU para fins eleitorais (com débito) é só indício. |

## 3. Fontes avaliadas

### 3.1 TCU - Cadastro de responsáveis com contas julgadas irregulares (CADIRREG)

| Item | Definição |
|---|---|
| Hipótese | VII, a (parcial) e, por CNPJ, VI (parcial). |
| URL e método | `POST https://certidoes.apps.tcu.gov.br/api/publico/responsaveis-contas-irregulares`, corpo JSON. `{}` devolve a lista inteira. Documentado em https://sites.tcu.gov.br/dados-abertos/webservices-tcu/. |
| Alternativas | Paginado: `POST .../responsaveis-contas-irregulares-com-paginacao?paginaAtual=1&tamanhoPagina=50`. CSV: `POST .../responsaveis-contas-irregulares/exportar-para-csv?paginaAtual=1&tamanhoPagina=50000` (cp1252, separador `\|`, primeira linha `sep=\|`, 11 MB). Página: https://certidoes.apps.tcu.gov.br/lista-responsaveis. |
| Filtros | `parteNome`, `cpf`, `cnpj`, `uf`, `municipio`. Testado (`teste_filtros_tcu.json`): `cpf` aceita com ou sem pontuação; CPF mascarado (`***XXXXXX**`, `***.XXX.XXX-**`) ou só os 6 dígitos devolvem 0. `parteNome` não diferencia maiúsculas e casa por palavras (primeiro + último nome devolveu 39 pessoas). |
| Autenticação | Nenhuma. Sem CAPTCHA (o ALTCHA só existe na emissão de certidão individual em PDF). |
| Formato | JSON, 24 MB, 47.889 itens, 1,7 s. Campos: `nome`, `tipoRegistro` (CPF/CNPJ), `numeroRegistro` (formatado), `uf`, `municipio`, `numeroProcessoFormatado`, `numeroAcordaoFormatado`, `dataTransitoEmJulgado` (DD/MM/AAAA), `linkDeliberacoesProcesso`, `linkAcompanhamentoProcesso`, `codigoProcesso`, `seProcessoGestao` (S/N, significado não documentado). |
| Identificação | 41.072 linhas CPF e 6.817 CNPJ. CPF completo e formatado em 41.071 linhas, todos com DV válido; 1 linha com documento vazio. Nome sempre preenchido. 23.665 CPFs distintos. |
| Atualização | Trânsito em julgado mais recente: 23/09/2026, o que indica atualização contínua (o TCU fala em atualização diária no período eleitoral). |
| Janela | A lista é histórica (trânsitos desde a década de 1980). O filtro de 8 anos é nosso: 14.702 linhas, 7.755 CPFs. 3 linhas têm ano "0202" (erro de cadastro). |
| Natureza da conta | Não informada. A lista mistura tomada de contas especial de convênio, contas de gestão e outras. Recorte útil: 814 CPFs (janela de 8 anos) estão em processos onde também foi condenada uma PJ com nome de OSC. |
| Casamento nome + 6 | Possível e forte: nenhuma chave (nome normalizado, 6 dígitos do meio) aponta para mais de um CPF; os 6 dígitos sozinhos colidem em 296 casos. |
| Falso positivo esperado | Muito baixo para identidade. O risco real é jurídico: conta irregular que não é de parceria (a lei exige "contas relativas a parcerias"). Por isso fica em ALERTA. |
| Falso negativo esperado | Grafia diferente entre QSA e TCU, mudança de nome, dirigente ausente do QSA, contas julgadas por TCE/TCM. |
| Sobreposição | 916 dos 23.665 CPFs também estão no CEIS; 22.749 só no TCU. |
| Amostra | `amostras/amostra_tcu_responsaveis-contas-irregulares.json` (CPF mascarado, só primeiro nome). |

### 3.2 TCU - Inabilitados para cargo em comissão ou função de confiança

| Item | Definição |
|---|---|
| Hipótese | VII, b (coberto para decisões do TCU, art. 60 da Lei 8.443/1992). |
| URL e método | `POST https://certidoes.apps.tcu.gov.br/api/publico/responsaveis-inabilitados`, corpo `{}` ou filtros `parteNome`, `cpf`, `uf`, `municipio`. CSV: `.../responsaveis-inabilitados/exportar-para-csv`. Página: https://certidoes.apps.tcu.gov.br/lista-inabilitados. |
| Formato | JSON, 431 KB, 774 itens, 0,09 s. Campos como os de inidôneos: `nome`, `numeroRegistro`, `numeroProcessoFormatado`, `numeroAcordaoFormatado`, `dataAcordao`, `dataTransitoEmJulgado`, `dataFinalSancao`, links. |
| Identificação | Todos PF, CPF completo com DV válido em 773 linhas (1 vazio), 599 CPFs distintos. |
| Vigência | Só vigentes: `dataFinalSancao` entre 01/10/2026 e 15/09/2034. Mesmo assim o motor deve conferir a data. |
| Casamento nome + 6 | Possível; nenhuma colisão de chave e nenhuma de 6 dígitos. |
| Falso positivo esperado | Muito baixo; a hipótese legal é exatamente esta. |
| Falso negativo esperado | Inabilitações aplicadas por TCEs; grafia; dirigente fora do QSA. |
| Sobreposição | 542 dos 599 também estão em contas irregulares do TCU; 59 no CEIS. |

### 3.3 TCU - Contas irregulares com implicação eleitoral

| Item | Definição |
|---|---|
| URL | `POST https://certidoes.apps.tcu.gov.br/api/publico/responsaveis-fins-eleitorais?anoEleicao=2026` (obrigatório; `GET .../eleicoes/ultimoAno` devolve 2026). |
| Formato | JSON, 9.145 itens, 6.291 CPFs, CPF completo; `dataFinalFinsEleitorais` até 2034. |
| Conclusão | É um subconjunto do CADIRREG (todos os 6.291 CPFs estão lá), restrito a contas com débito e à janela da eleição. Não precisa ser baixada: o CADIRREG com o nosso filtro de 8 anos é mais amplo. |

### 3.4 TCU - Consulta Consolidada em versão pessoa física

Não existe.
`GET https://certidoes-apf.apps.tcu.gov.br/api/rest/publico/certidoes/{cpf}` devolve HTTP 412 "Dígito verificador do CNPJ é inválido" (`teste_consolidada_cpf.json`).
As certidões individuais de PF da Plataforma de Certidões (`/api/publico/certidoes/contas-julgadas-irregulares/pessoa-fisica`, `.../inabilitados`) exigem CAPTCHA ALTCHA e não foram chamadas; as listas acima trazem o mesmo conteúdo.

### 3.5 CNJ - CNIA (Cadastro Nacional de Condenações Cíveis por Ato de Improbidade Administrativa e Inelegibilidade)

| Item | Definição |
|---|---|
| Hipótese | VII, c. |
| URL | Página: `https://www.cnj.jus.br/improbidade_adm/consultar_requerido.php`. A busca usa Sajax: `POST` form-urlencoded na mesma URL com `rs=verificarCamposPesquisa` e depois `rs=pesquisarRequeridoGetTabela`, argumentos em `rsargs[]` (esfera, tribunal, órgão, CPF/CNPJ, nome, tipo de pessoa, `I`, `0`, `POSICAO_INICIAL_PAGINACAO_PHP0`, `QUANTIDADE_REGISTROS_PAGINACAO15`). Detalhe: `GET visualizar_condenacao.php?seq_condenacao=N`. |
| CAPTCHA | Não há. Os comentários do próprio JS (SEC-029, SEC-031) registram que o reCAPTCHA foi removido; o argumento `txtImagem` é ignorado pelo servidor. |
| Busca por CPF | Exige os 11 dígitos ("Para CPF deve-se digitar o número completo"). Com CPF completo, devolve nome, CPF formatado e número do processo (testado com uma PF do CEIS de origem CNJ). |
| Busca por nome | Funciona com o nome completo; primeiro + último nome não encontrou nada (busca exata ou por prefixo). O resultado mostra nome e processo, mas não mostra CPF; a página de detalhe também não. |
| Detalhe | Penas com datas: suspensão dos direitos políticos (de/até), proibição de contratar (de/até), multa, ressarcimento, perda da função, inelegibilidade, trânsito em julgado. Traz "Esta informação não tem valor de Certidão". |
| Download em massa | Não existe (busca e documentação do CNJ não mostram dados abertos do CNIA). Enumerar `seq_condenacao` seria raspagem em massa e fica fora da política do capítulo 23. |
| Casamento nome + 6 | Impossível: não há CPF parcial nem completo na busca por nome. Só nome exato. |
| Falso positivo esperado | Alto para nomes comuns (sem segundo identificador). |
| Falso negativo esperado | Nome com grafia diferente; condenações não cadastradas pelos tribunais. |
| Relação com o CEIS | O CNJ alimenta o CEIS: 7.113 linhas de PF no CEIS têm origem "Conselho Nacional de Justiça (CNJ-DF)", todas com categoria "Impedimento/proibição de contratar com prazo determinado", fundamentação "LEI 8429 - ART. 12" e data final entre 01/10/2026 e 24/09/2040 (só vigentes). O que fica de fora do CEIS é a condenação só com suspensão de direitos políticos (ou com proibição já vencida e suspensão ainda vigente). |
| Uso possível | Só com CPF completo informado pelo usuário (seção 5.3). Por nome, no máximo um link de conferência manual. |

### 3.6 Contas julgadas irregulares por tribunais estaduais e municipais

- Não existe base agregada nacional.
- Cada TCE envia sua lista à Justiça Eleitoral (LC 64/1990 e Lei 9.504/1997, art. 11, § 5º), mas a Justiça Eleitoral não publica um consolidado com identificação por pessoa que tenha sido encontrado nesta pesquisa (a notícia do TSE de 08/2026 respondeu 403 ao WebFetch; não insisti).
- Cada TCE publica em formato próprio (PDF, planilha, sistema de consulta), com máscara de CPF própria, e o levantamento completo dos 33 tribunais de contas (26 TCEs, TCDF, 3 TCMs estaduais, TCM-SP e TCM-RJ) fica para o pós-MVP.
- Exemplo avaliado em detalhe por ser o estado do projeto: TCE-SP (3.7).

### 3.7 TCE-SP - Relação de responsáveis por contas julgadas irregulares

| Item | Definição |
|---|---|
| Hipótese | VII, a, para parcerias fiscalizadas pelo TCE-SP (estado e municípios de SP, exceto a capital, que é do TCM-SP). |
| Página | https://www.tce.sp.gov.br/relacao-de-responsaveis-por-contas-julgadas-irregulares (Comunicados GP 41/2026 e 52/2022). |
| Arquivos | Planilhas xlsx e PDF em `https://www.tce.sp.gov.br/sites/default/files/portal/`. O nome do arquivo leva o período (ex.: `contas irregulares de 01-01-1900 a 01-09-2026_Prest_Contas_CPF_anonimizado.xlsx`), então o adapter precisa ler a página e achar os links a cada mês. |
| Relações | (a) Prestação de contas de repasses ao Terceiro Setor julgadas irregulares, com ou sem débito: 10.026 linhas, 4.126 nomes, trânsitos de 2006 a 19/08/2026, 5.057 linhas nos últimos 8 anos. (b) Contas anuais (balanço, câmara, previdência): 6.394 linhas. (c) Lista para fins eleitorais (com débito, 2018 a 2026): 917 linhas. |
| Matérias do Terceiro Setor | Repasses com valor informado (4.308), contrato de gestão (2.085), auxílios/subvenções/contribuições (1.764), convênio com entidade privada (1.306), termo de parceria (465), termo de colaboração (81), termo de fomento (17). |
| Colunas | `Responsável`, `#`, `Responsável` (nome), `CPF`, `Processo TC`, `Matéria`, `Origem` (órgão concedente), `Trânsito em Julgado`, `Exercício`. |
| Identificação | CPF "anonimizado" no formato `999.XXX.XXX-99`: aparecem os 3 primeiros e os 2 últimos dígitos (100% das linhas). Nome completo sempre presente. Não traz o CNPJ da OSC. |
| Atualização | Mensal. Arquivos de 03/09/2026 (Last-Modified), "Última atualização em 01/09/2026". |
| Autenticação | Nenhuma, sem CAPTCHA. |
| Casamento | Os dígitos visíveis do TCE-SP e do QSA são complementares: juntos formam o CPF inteiro. Regra proposta: nome normalizado igual e DV calculado com (3 primeiros do TCE-SP + 6 do meio do QSA) igual aos 2 últimos do TCE-SP. Um homônimo passa por acaso com probabilidade de cerca de 1/100. |
| Falso positivo esperado | Baixo (homônimo com 1% de chance de DV coincidir); 7 dos 4.126 nomes aparecem com mais de um CPF parcial (homônimos reais, separáveis pelo DV). A lista inclui também agentes públicos responsáveis pelo repasse (prefeitos, secretários), o que não muda a hipótese: se forem dirigentes de OSC, estão impedidos. |
| Falso negativo esperado | Grafia; dirigentes fora do QSA; parcerias de outros estados e da capital paulista. |
| Cuidado LGPD | Como as máscaras são complementares, cruzar QSA e TCE-SP reconstitui o CPF completo. O motor só pode calcular o DV em memória e guardar o resultado booleano; nunca persistir nem exibir o CPF reconstituído. |
| Amostras | `amostras/amostra_tcesp_*.json` (CPF totalmente mascarado, só primeiro nome). |

### 3.8 CEIS e CNEP - pessoas físicas (confirmação)

Arquivos de 30/09/2026 já baixados em `fase0/portal/downloads/` (`analise_ceis_cnep_pf.json`).

| Item | CEIS | CNEP |
|---|---|---|
| Linhas PF | 9.148 | 28 |
| CPF com 11 dígitos e DV válido | 9.148 | 28 |
| CPF mascarado | 0 | 0 |
| Nome vazio | 0 | 0 |
| CPFs distintos | 7.276 | 20 |
| Linhas PF vigentes em 01/10/2026 | 9.112 | 28 |
| Origem CNJ (improbidade) | 7.113 | 0 |
| Chaves nome + 6 com mais de um CPF | 0 | 0 |

Outras origens de PF no CEIS: governos e controladorias estaduais e municipais, Ministério da Fazenda, CGU, MPMG, tribunais de justiça.
Nenhuma linha de PF tem origem no TCU (as inabilitações do TCU não vão para o CEIS).
Categorias de PF fora do CNJ incluem "Demissão" (64) e "Suspensão" (96), que são sanções a servidores e não são hipótese do art. 39; devem aparecer como informação, não como ALERTA de impedimento (ver 5.2).

## 4. Teste ponta a ponta (QSA real)

Script: `testar_e2e.py`, resultado: `teste_e2e.json` (sem nomes nem CPFs).
QSA obtido na OpenCNPJ (mesma fonte do MVP).

Grupo 1, positivos prováveis: 25 OSCs (associações e fundações) condenadas como PJ na lista de contas irregulares do TCU nos últimos 8 anos, em processos que também condenaram pessoas físicas.

- 25 de 25 tinham pelo menos um PF no QSA (23 tinham só um, o presidente).
- 12 tiveram achado por nome + 6 dígitos, todos na lista de contas irregulares do TCU.
- Em 10 delas o dirigente atual foi condenado no mesmo processo que a OSC, o que confirma que o casamento acha a pessoa certa.
- Nas 13 sem achado, o dirigente atual não é o condenado (troca de diretoria) ou a condenação foi de outra pessoa; não é falha de casamento.

Grupo 2, controle: 47 CNPJs de `fase0/casos` (148 PF no QSA).

- 8 tiveram achado, e todos os 8 são casos escolhidos justamente por terem sanção (C28, C36, C39, C40, C41, C42, C44, C46).
- Nenhum dos casos sem sanção conhecida teve achado.
- O TCE-SP (nome + DV) achou dirigentes em 3 OSCs paulistas (Santos, São Bernardo do Campo, Pacaembu), todos com DV conferindo.
- Em C36 o dirigente aparece no CEIS (vigente, origem CNJ) e no TCU com trânsito em 2013, fora da janela de 8 anos: o filtro temporal separou os dois corretamente.

Efeito dos filtros, somando os 179 PF dos dois grupos:

- 18 tiveram nome igual em alguma fonte com CPF completo; 17 passaram também nos 6 dígitos (1 homônimo descartado).
- 3 tiveram nome igual no TCE-SP; os 3 passaram no DV.

Homônimos nas próprias listas (CEIS + TCU, 30.025 CPFs): 172 nomes têm mais de um CPF, e em nenhum deles os 6 dígitos do meio coincidem.
Grafias diferentes para o mesmo CPF entre CEIS e TCU: 19 casos (cerca de 0,06%), uma estimativa do falso negativo por grafia.

## 5. Proposta de regra de casamento e estados

### 5.1 Regra

1. Considerar só sócios do QSA com CPF mascarado de 6 dígitos (PF). Normalizar o nome (maiúsculas, sem acento, só letras e espaços simples).
2. Fontes com CPF completo (CEIS, CNEP, TCU contas irregulares, TCU inabilitados): casar por (nome normalizado, 6 dígitos do meio). Igualdade exata nos dois.
3. TCE-SP: casar por nome normalizado e conferir o DV com (3 primeiros do TCE-SP + 6 do QSA); descartar se o DV não bater.
4. Filtro temporal por fonte: TCU contas irregulares e TCE-SP, trânsito em julgado nos últimos 8 anos; TCU inabilitados, data final >= hoje; CEIS e CNEP, data final vazia ou >= hoje.
5. Se o usuário informar o CPF completo de um dirigente (opcional), conferir que os 6 dígitos do meio batem com o QSA e casar por CPF exato; nesse caso o CNIA pode ser consultado on-line por CPF.
6. Data de entrada no QSA e qualificação não mudam o impedimento (a lei olha quem é dirigente hoje), mas devem aparecer no resultado. Reforço útil: o achado é do mesmo processo em que a própria OSC foi condenada.

O protótipo está em `casar_dirigentes.py`.

### 5.2 Estados

| Situação | Estado | Mensagem |
|---|---|---|
| Nenhum achado dentro da janela | OK | "Nenhum dirigente do QSA encontrado em: CEIS, CNEP, TCU (contas irregulares, inabilitados), TCE-SP Terceiro Setor." Deixar explícito o que não é coberto (inciso III, outros TCEs, CNIA sem proibição de contratar). |
| Nome + 6 (ou nome + DV) em fonte de hipótese direta, dentro da janela: TCU inabilitados vigente, CEIS de origem CNJ vigente, TCE-SP Terceiro Setor em 8 anos | ALERTA | "Possível impedimento (art. 39, VII, [alínea]): [nome] aparece em [fonte], processo [n], [datas]; confira o CPF no documento oficial." |
| Nome + 6 em TCU contas irregulares em 8 anos | ALERTA | Mesma mensagem, com a ressalva "a lista não informa se a conta é de parceria; confira o acórdão" e o link `linkDeliberacoesProcesso`. Indicar "mesmo processo da OSC" quando for o caso. |
| Nome + 6 em CEIS/CNEP fora do CNJ (demissão, suspensão, multa) | ALERTA leve ou informação | Não é hipótese direta do VII; mostrar como indício. Sugestão: manter ALERTA só para categorias de proibição de contratar e inidoneidade, e informação para as demais. |
| Achado fora da janela (TCU > 8 anos, CEIS expirado) | OK com informação | Mostrar como histórico, sem mudar o estado. |
| Só nome (sem 6 dígitos ou DV), inclusive CNIA por nome | Não gerar achado | No máximo um link de conferência manual. |
| CPF completo informado pelo usuário + CPF exato + fonte de hipótese direta | ALERTA no MVP; candidato a RESTRICAO no pós-MVP | Com CPF exato a identidade deixa de ser dúvida; a dúvida que sobra é jurídica (vigência, natureza da conta). TCU contas irregulares continua ALERTA mesmo com CPF, porque a lista não diz se a conta é de parceria. |

Mantém-se a regra de D15: nunca INAPTA por dirigente.
O único caso que pode merecer mais do que ALERTA é o de CPF completo informado e conferido, em fonte cuja hipótese é a própria alínea (inabilitados TCU, CEIS de origem CNJ, TCE-SP Terceiro Setor); isso depende da decisão de LGPD (D9).

## 6. Recomendação

### MVP

1. Incluir TCU contas irregulares e TCU inabilitados: download diário do JSON oficial (24 MB e 0,4 MB, segundos), índice local por (nome, 6 dígitos), mesmo casamento de D15. Ganho: 23.665 + 599 CPFs, dos quais cerca de 22.700 não estão no CEIS/CNEP.
2. Incluir TCE-SP Terceiro Setor com a regra nome + DV: download mensal de 0,6 MB, descobrindo o link na página. Cobre exatamente o VII, a para as parcerias em SP, que é o público do projeto. Nunca persistir o CPF reconstituído.
3. Manter CEIS/CNEP e rotular os achados de origem CNJ como VII, c.
4. Sempre ALERTA, com fonte, processo, datas, qualificação, data de entrada e link oficial.
5. Mensagem de OK com a lista do que foi e do que não foi verificado.
6. Achado lateral para a verificação da OSC (fora desta ficha): a mesma lista do TCU tem 6.817 condenações de PJ por CNPJ, o que dá cobertura parcial ao inciso VI para a própria OSC; vale registrar como decisão separada.

### Pós-MVP

1. CPF completo opcional dos dirigentes, informado pela OSC ou pela prefeitura (depende de D9/LGPD): casamento por CPF exato, consulta on-line ao CNIA por CPF (cobre suspensão de direitos políticos), e possível estado RESTRICAO para hipóteses diretas.
2. Lista completa da diretoria informada pelo usuário (nome + CPF), porque o QSA de associações costuma trazer só o presidente (23 de 25 no teste).
3. Levantamento dos demais tribunais de contas (TCM-SP primeiro, pela proximidade; depois TCEs de maior volume), uma ficha por tribunal, mesmo padrão do TCE-SP.
4. Classificar a natureza das contas do TCU (parceria ou não) pelo processo e acórdão (`linkDeliberacoesProcesso`), para separar ALERTA forte de fraco.
5. Inciso III continua dependendo de declaração da OSC; não há fonte pública.
6. Tolerância de grafia (ex.: distância de edição pequena) só combinada com os 6 dígitos, para reduzir o falso negativo sem aumentar o falso positivo.

## 7. Arquivos desta pasta

- `comum.py`: cliente HTTP, pausa, validação e máscara de CPF, normalização de nome, datas.
- `baixar_tcu_listas.py`: baixa as três listas do TCU (JSON oficial e CSV) para `downloads/` e grava `downloads/tcu_meta.json`.
- `analisar_tcu_listas.py`: perfil das listas do TCU, saída `analise_tcu.json` e `amostras/amostra_tcu_*.json`.
- `testar_tcu_filtros.py`: testa filtros por CPF completo, mascarado e nome; saída `teste_filtros_tcu.json`.
- `analisar_ceis_cnep_pf.py`: perfil das PF do CEIS/CNEP e sobreposição com o TCU; saída `analise_ceis_cnep_pf.json`.
- `testar_cnia.py`: consulta ao CNIA por CPF, nome e CPF mascarado; saída `teste_cnia.json` (respostas brutas em `downloads/`).
- `baixar_tcesp.py`: baixa e perfila as planilhas do TCE-SP; saída `analise_tcesp.json` e `amostras/amostra_tcesp_*.json`.
- `casar_dirigentes.py`: protótipo do índice e da regra de casamento.
- `testar_e2e.py`: teste ponta a ponta com QSA real; saída `teste_e2e.json`.
- `teste_consolidada_cpf.json`: prova de que a Consulta Consolidada não aceita CPF.
- `downloads/` (fora do versionamento): listas brutas com CPF completo, planilhas do TCE-SP, respostas do CNIA, QSA da OpenCNPJ, texto da Lei 13.019 (`art39.txt`).
