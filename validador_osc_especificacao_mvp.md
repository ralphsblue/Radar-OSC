# Validador de OSC - Especificação técnica do MVP

Verificação automatizada de CNPJ para parcerias conforme o Marco Regulatório das OSCs (Lei nº 13.019/2014).

Fluxo do motor de regras, critérios de conformidade por verificação, fontes de dados públicas, resultados da Fase 0 e estratégia para o CEBAS.

- **Disciplina:** Atividade de Extensão - TSI / IFSP
- **Autor:** Rafael
- **Versão:** 1.2.1 - 1 de outubro de 2026

> Documento de trabalho.
> Os endpoints de fontes governamentais mudam; a data do último teste de cada fonte está na sua ficha em `fase0/*/ficha.md`.
> As decisões citadas como D1 a D20 e as pendências (P, O, A, F, R) estão em `decisoes.md`, que é a fonte de verdade.
> As perguntas citadas como Q1 a Q44, as contradições X1 a X18 e os buracos B1 a B22 estão em `revisao_pre_codigo.md`.

## Histórico de alterações

| Versão | Data | Alterações |
|---|---|---|
| 1.0 | 30/09/2026 | Versão inicial, escrita antes dos testes das fontes. |
| 1.1 | 01/10/2026 | Incorpora as decisões D1 a D13 e os resultados da Fase 0. Remove o score (D8). Adiciona o parâmetro `esfera` (D6), o tratamento de filial (D5), a regra de divergência entre fontes (D3) e o CNPJ alfanumérico fora das consultas (D4). Troca a tabela CNAE pela proposta completa (D7). Reescreve a Parte III com o que foi executado e adiciona o capítulo 18A (OpenCNPJ). Remove o fallback Playwright/APEX do TCU (D13). Aplica D14 a D17 com marcador de proposta. A numeração dos capítulos da versão 1.0 foi mantida para não quebrar as referências de `decisoes.md` e das fichas. |
| 1.2 | 01/10/2026 | Aplica a revisão cruzada (`revisao_pre_codigo.md`): resolve as contradições X1 a X18, as respostas do dono (D19: Q1 a Q7 e Q9 a Q13), as decisões técnicas Q25 a Q44 (D20) e define os buracos B1 a B22. D14 a D18 deixam de ser proposta: o CSV diário da CGU passa a ser a observação principal de CEPIM, CEIS e CNEP, o OpenCNPJ `?datasets=` e o TCU viram observações adicionais e a API do Portal com chave sai do motor (ferramenta manual de conferência). Novo catálogo de 15 verificações com id textual (Q25, cap. 2.6), status `CNPJ_INVALIDO` (Q3), sem parada antecipada (Q1), contrato do adapter e formato do resultado da arquitetura (cap. 24). Regras do orientador (Q14 a Q24) aplicadas como provisórias com o marcador `[ORIENTADOR Qxx]`; ampliação de dirigentes deixada pendente com o dono (Q8). |
| 1.2.1 | 01/10/2026 | Aplica a decisão do dono no Q8 (opção C, D15): `dirigentes` passa a casar o QSA também com as listas do TCU de contas irregulares (trânsito em julgado nos últimos 8 anos) e de inabilitados (vigentes) e com a relação do TCE-SP de contas do Terceiro Setor julgadas irregulares (nome + dígito verificador, CPF reconstituído só em memória e garantido por teste), sempre ALERTA. Capítulo 13 reescrito; capítulos 2, 3, 16, 17, 24.4, 25.1 e 26 alinhados; idade máxima das novas bases (Q6): listas do TCU 7 dias, TCE-SP 45 dias. Marcador de pendência do Q8 removido e casos de referência gerados de novo. |

## Marcadores deste documento

Não há mais decisão em estado de proposta: D14 a D19 estão decididas em `decisoes.md`.
Restam dois marcadores, ambos visíveis no texto:

| Marcador | Significado | O que acontece quando for resolvido |
|---|---|---|
| `[ORIENTADOR Qxx]` | Interpretação da Lei 13.019/2014 aplicada como regra provisória, igual à recomendação da revisão (Q14 a Q24). | O motor lê a regra de configuração versionada; se o orientador decidir diferente, muda o valor e os casos de referência são gerados de novo (`REGRAS_ORIENTADOR` em `fase0/casos/montar_casos.py`). |
| `[PENDENTE X17]` | Esperado do CEBAS de MDS e MEC sem os atos do DOU de 12/2023 a 05/2026 (Q39). | Carga do DOU e casos de CEBAS gerados de novo. |

## Sumário

- Como ler este documento
- 1. Objetivo e base legal
- 2. Visão geral do fluxo do motor de regras
- 3. Mapa das verificações
- 4. Verificação 1 - Dígito verificador (DV)
- 5. Verificação 2 - Situação cadastral
- 6. Verificação 3 - Natureza jurídica
- 7. Verificação 4 - CNAE de relevância social
- 8. Verificação 5 - Tempo de existência (art. 33, V, a)
- 9. Verificação 6 - CEPIM
- 10. Verificação 7 - CEIS
- 11. Verificação 8 - CNEP
- 12. Verificação 9 - Inidôneos do TCU, improbidade (CNJ) e contas irregulares
- 13. Verificação 10 - Dirigentes (QSA)
- 14. Verificação 11 - Mapa das OSCs (Ipea)
- 15. Verificação 12 - CEBAS (resumo)
- 16. O que fica fora do MVP (e por quê)
- 17. Visão geral das fontes
- 18. Fonte: BrasilAPI e Minha Receita (dados cadastrais)
- 18A. Fonte: OpenCNPJ (dados cadastrais e sanções do Portal)
- 19. Fonte: Portal da Transparência (CEPIM, CEIS, CNEP)
- 20. Fonte: TCU - Consulta Consolidada e Relação de Inidôneos
- 21. Fonte: Mapa das OSCs (Ipea)
- 22. CEBAS em profundidade: o gargalo do projeto
- 23. Política de scraping e engenharia reversa
- 24. Contrato interno: adapter e resultado
- 25. Plano de testes
- 26. Ordem de execução
- Apêndice A - Scripts de teste das fontes (Fase 0)
- Apêndice B - Validação do dígito verificador
- Apêndice C - Glossário
- Apêndice D - Referências

# Como ler este documento

Este documento desenha o fluxo completo do validador antes do código do motor.
Ele está dividido em quatro partes, e cada uma responde a uma pergunta diferente:

| Parte | Pergunta que responde | Conteúdo |
|---|---|---|
| I. Visão geral | O que precisamos e como tudo se encaixa? | Base legal, o que é uma OSC, fluxo do motor, tipos de verificação e status finais. |
| II. Verificações | O que exatamente checamos e o que conta como conforme? | Um capítulo por verificação: o que é, por que importa, retorno esperado (conforme / não conforme / inconclusivo). |
| III. Fontes de dados | De onde vem cada dado e como foi testado? | Um capítulo por fonte: endpoint, autenticação, limites, retorno real, cuidados descobertos na Fase 0. Capítulo aprofundado sobre o CEBAS. |
| IV. Execução | Como sair do papel? | Contrato interno, plano de testes, ordem de trabalho e apêndices. |

## Legenda de status de validação das fontes

Cada fonte recebe um selo que indica o quanto o seu comportamento já foi confirmado.
A versão 1.0 foi escrita sem acesso de rede aos servidores do governo, a partir de documentação e de capturas de terceiros.
Na Fase 0 (30/09/2026) as fontes foram testadas de fato, e o resultado de cada teste está registrado na ficha da fonte.

| Selo | Significado | O que fazer |
|---|---|---|
| EXECUTADO | Testado de fato na Fase 0, com resposta bruta salva e resultado registrado na ficha. | Nada; já pode virar código e teste automatizado. |
| DOCUMENTADO | Endpoint e campos confirmados por documentação oficial (ex.: OpenAPI), mas sem resposta real de sucesso salva. | Rodar o script da fonte (Apêndice A) assim que o bloqueio for resolvido e salvar a resposta bruta. |
| A DESCOBRIR | Não existe caminho técnico confirmado. | Seguir o passo manual indicado no capítulo da fonte. |

---

# PARTE I - Visão geral: o que precisamos para validar uma OSC

# 1. Objetivo e base legal

## 1.1 O problema

Para firmar parceria com a administração pública (termo de colaboração, termo de fomento ou acordo de cooperação), uma organização precisa ser uma Organização da Sociedade Civil (OSC) nos termos da Lei nº 13.019/2014, o Marco Regulatório das Organizações da Sociedade Civil (MROSC), e não pode estar em nenhuma situação de impedimento.
Hoje essa checagem é manual: alguém consulta a Receita, abre o Portal da Transparência, emite certidão no TCU, procura certificações em sites diferentes e junta tudo.
O sistema automatiza essa esteira e entrega um relatório com o que está conforme, o que não está e o que não pôde ser verificado.

Os usuários previstos são a própria OSC, a prefeitura (ou outro ente que vai firmar a parceria) e o público em geral (D10).
Isso não muda o escopo do motor; a principal diferença entre eles é coberta pelo parâmetro `esfera` (capítulo 8).

## 1.2 O que a lei considera OSC (art. 2º, inciso I)

| Alínea | Tipo de entidade | Como o sistema trata |
|---|---|---|
| a | Entidade privada sem fins lucrativos que não distribui resultados entre sócios, dirigentes ou empregados e aplica tudo no objeto social. | Elegível por natureza jurídica (associação 399-9, fundação privada 306-9). O não-lucro em si não é verificável pela Receita; fica como premissa ou revisão de estatuto. |
| b | Sociedades cooperativas específicas: as da Lei nº 9.867/1999 (cooperativas sociais), as integradas por pessoas em situação de risco social, as de programas de combate à pobreza e geração de renda, as voltadas a fomento e capacitação de trabalhadores rurais, e as capacitadas para atividades de interesse público. | Cooperativa (214-3) NÃO é elegível automaticamente: só alguns tipos são. Status: REVISÃO MANUAL. |
| c | Organizações religiosas que se dediquem a atividades de interesse público e de cunho social distintas das destinadas a fins exclusivamente religiosos. | Elegível por natureza (322-0), sujeita à verificação `religiosa` do capítulo 7.5. |

## 1.3 Artigos que o sistema precisa respeitar

| Dispositivo | Exigência | Automatizável no MVP? |
|---|---|---|
| Art. 2º, I | Ser um dos tipos de OSC acima. | Parcial: via natureza jurídica + CNAE. |
| Art. 33, V, a | Tempo mínimo de existência com cadastro ativo no CNPJ: 1 ano (parcerias com municípios), 2 anos (estados/DF) e 3 anos (União). A lei admite redução pelo gestor quando nenhuma organização atingir o prazo. | Sim: data de início de atividade e parâmetro `esfera`. |
| Art. 33, V, b e c | Experiência prévia na atividade e condições materiais/técnicas. | Não (documental). Mapa das OSCs dá indícios. |
| Art. 34 | Certidões de regularidade fiscal, previdenciária, tributária, FGTS e trabalhista; certidão de existência jurídica; cópia da ata de eleição; relação de dirigentes; comprovação de endereço. | Fora do MVP (ver capítulo 16). |
| Art. 39 | Impedimentos: entidade irregular, omissa na prestação de contas, com contas rejeitadas, punida com suspensão ou declaração de inidoneidade, contas julgadas irregulares por Tribunal de Contas, dirigentes em situações vedadas. | Parcial: CEPIM, CEIS, CNEP, TCU e CNJ cobrem os impedimentos registrados em cadastros públicos. |

> **Limite honesto do sistema**
>
> O validador verifica o que está em cadastros públicos.
> Ele não substitui a análise do estatuto, da prestação de contas e das certidões exigidas no edital.
> Por isso o relatório final sempre traz o aviso de que é uma triagem automatizada, e as verificações que dependem de documento aparecem como "não verificado pelo sistema".

# 2. Visão geral do fluxo do motor de regras

## 2.1 Os três tipos de verificação

Nem toda verificação tem o mesmo peso.
Separar isso logo no desenho evita misturar coisas eliminatórias com coisas informativas.

| Tipo | Efeito no resultado | Exemplos |
|---|---|---|
| ELIMINATÓRIA | Se falhar, a entidade é INAPTA, independentemente do resto. | Situação diferente de ATIVA, natureza não elegível, registro no CEPIM, sanção vigente no CEIS/CNEP, inidoneidade no TCU, condenação no CNIA com proibição de contratar vigente. O DV também é eliminatório, mas a sua falha leva ao status próprio `CNPJ_INVALIDO` (Q3). |
| ALERTA | Não reprova, mas gera ressalva e pede revisão humana. | CNAE sem relação social, organização religiosa sem atividade social no CNAE, tempo de existência abaixo do exigido para a esfera, possível correspondência de dirigente em cadastro de sanção, natureza em revisão manual, contas julgadas irregulares no TCU [ORIENTADOR Q21]. |
| INFORMATIVA | Enriquece o relatório. Só afeta o status final quando gera ALERTA. | Perfil no Mapa das OSCs (ausência gera ALERTA, D2), certificação CEBAS, estabelecimento consultado (filial não ativa ou matriz não identificada geram ALERTA, Q4 e Q27). |

Uma verificação eliminatória também pode devolver ALERTA quando a regra pede revisão humana em vez de reprovação (natureza em revisão manual, espelho cadastral defasado, CNEP de multa [ORIENTADOR Q16], CNIA sem proibição vigente [ORIENTADOR Q19]).
O contrário nunca acontece: verificação do tipo ALERTA ou INFORMATIVA nunca devolve RESTRICAO, e isso é um teste automatizado.

O score de 0 a 100 previsto na versão 1.0 foi removido do MVP (D8).
O resultado é o status final, a lista de achados e as explicações de cada um.
O score volta quando houver casos reais para calibrar os pesos.

## 2.2 Sequência completa

O fluxo usa o OpenCNPJ como fonte cadastral principal (D17), o CSV diário oficial da CGU importado localmente como observação principal de CEPIM, CEIS e CNEP (D14) e o OpenCNPJ `?datasets=` e a Consulta Consolidada do TCU como observações adicionais.
O cache é por fonte e por chave (cap. 24.4), não da consulta inteira.

```
 ENTRADA: CNPJ digitado (+ esfera opcional: municipio | estado | uniao)
    |
 [E0] Normalização + Dígito Verificador ........ local, custo zero (validador_osc/cnpj.py)
    |   falhou -> CNPJ_INVALIDO: erro de digitação, sem relatório de entidade (Q3) (fim)
    |   alfanumérico válido -> consultas NAO_VERIFICADO, status INCONCLUSIVA (D4, Q2) (fim)
    v
 [E1] Consulta cadastral (OpenCNPJ ?datasets=cepim,ceis,cnep; fallback BrasilAPI) ... BLOQUEANTE
    |   -> situação, natureza, CNAEs, data de início, QSA, UF e sanções anexadas
    |   não encontrado nas duas fontes -> situacao INDISPONIVEL (NAO_ENCONTRADO),
    |                                     demais NAO_VERIFICADO, INCONCLUSIVA (Q26) (fim)
    |   filial -> consulta também a matriz (raiz + 0001 + DVs) (D5)
    |   situação, natureza, CNAE, religiosa, tempo e estabelecimento: sempre avaliados (Q1)
    v
 [E2] Fan-out assíncrono, sempre que E1 achou o cadastro (Q1) .... asyncio.gather
    |-- Bases locais da CGU: CSV de CEPIM, CEIS e CNEP (exato e por raiz) .... principal (D14)
    |-- TCU Consulta Consolidada (Inidôneos TCU, CNIA, CEIS, CNEP)
    |-- Base local de inidôneos do TCU (Plataforma de Certidões, Q34)
    |-- Base local de contas irregulares do TCU [ORIENTADOR Q21]
    |-- Dirigentes do QSA x pessoas físicas de CEIS/CNEP, listas do TCU e TCE-SP locais (D15)
    |-- Mapa das OSCs (informativo; ausência = ALERTA)
    |-- CEBAS (bases locais: SisCEBAS Saúde, planilhas oficiais, DOU)
    |   cada fonte devolve fatos ou falha tipada; quem decide o estado é o motor (Q41)
    v
 [E3] Motor de regras (puro) e agregação
    |   -> estado por verificação, status final, motivos, avisos e evidências (payload, data, hash)
    v
 SAÍDA: JSON do resultado + página HTML com CSS de impressão (Q10, Q11)
```

## 2.3 Por que essa ordem

- **Falhar cedo e barato.** O DV é calculado localmente. Um CNPJ digitado errado nunca gasta requisição.
- **Um portão cadastral.** Uma única chamada à base da Receita (duas, quando a entrada é filial) responde a cinco verificações (situação, natureza, CNAE, religiosa, tempo) e traz as sanções anexadas pelo OpenCNPJ. Sem cadastro não há QSA nem raiz, e o fan-out não roda (Q26).
- **Relatório completo mesmo quando já reprovou.** Se a entidade está baixada ou é uma LTDA, o status já é INAPTA, mas as sanções ainda são consultadas e mostradas (Q1). 7 dos 13 CNPJs sancionados de referência estão INAPTOS ou BAIXADOS; parar no cadastro esconderia CEPIM, CEIS, CNEP, TCU e CNIA que existem. O custo é de 2 a 4 chamadas e alguns segundos.
- **Paralelismo onde não há dependência.** As consultas de sanção e certificação não dependem umas das outras. Em paralelo, o tempo total é o da fonte mais lenta (hoje a Consulta Consolidada do TCU, cerca de 5,5 s sem cache), e não a soma de todas.
- **Resultado nunca é "aprovado por omissão".** Fonte fora do ar vira INDISPONIVEL e o status final vira INCONCLUSIVA, nunca APTA.
- **"Nada consta" de uma fonte não confirma que o CNPJ existe.** A Consulta Consolidada do TCU devolve NADA_CONSTA para CNPJ inexistente; o motor nunca conclui OK sem a fonte cadastral ter confirmado o CNPJ (D13).

## 2.4 Estados de cada verificação

| Estado | Significado | Exemplo |
|---|---|---|
| OK | A fonte respondeu e não encontrou problema. | CEPIM sem registro para o CNPJ. |
| RESTRICAO | A fonte respondeu e encontrou problema. | CEIS com sanção de data de fim futura. |
| ALERTA | Há sinal que exige revisão humana, sem reprovar. | CNAE principal é comércio varejista. |
| INDISPONIVEL | A fonte não respondeu (timeout, erro 5xx, bloqueio), a base local está mais velha que o limite (Q6) ou o CNPJ não foi encontrado na base cadastral (motivo `NAO_ENCONTRADO`, Q26). | BrasilAPI devolveu HTTP 500 depois de 10 s. |
| NAO_VERIFICADO | O sistema não tem como checar (sem fonte, fora do escopo ou sem o dado de entrada). | CNPJ alfanumérico nas consultas (D4); QSA sem pessoa física (B22); CEBAS não encontrado. |

O motivo da falha também é registrado (`TIMEOUT`, `HTTP_5XX`, `HTTP_4XX`, `FORMATO_INESPERADO`, `NAO_SUPORTADO`, `BASE_VENCIDA`, `NAO_ENCONTRADO`), para a mensagem distinguir "fonte fora do ar" de "CNPJ não encontrado" e de "base desatualizada".

## 2.5 Status final e regra de decisão

| Status final | Regra | Leitura para o usuário |
|---|---|---|
| CNPJ_INVALIDO | A verificação `dv` falhou (formato, base repetida ou DV divergente). Nenhuma fonte é consultada (Q3). | "O CNPJ digitado não é válido (dígito verificador esperado XX)." Mostrado como erro de digitação no formulário, sem relatório de entidade. |
| INAPTA | Pelo menos uma verificação ELIMINATÓRIA com RESTRICAO. | Não pode firmar parceria no estado atual. |
| INCONCLUSIVA | Nenhuma restrição, mas alguma ELIMINATÓRIA ficou INDISPONIVEL ou NAO_VERIFICADO (Q2). | Tente de novo ou verifique manualmente a fonte indicada. O CNPJ alfanumérico cai aqui, com mensagem própria: "CNPJ alfanumérico ainda não é consultado pelo MVP". |
| APTA COM RESSALVAS | Todas as eliminatórias OK e pelo menos um ALERTA em qualquer verificação. | Apta nos cadastros, mas há pontos para conferir. |
| APTA | Todas as eliminatórias OK e nenhum alerta. | Nada consta nos cadastros públicos verificados. |

A ordem de precedência é: CNPJ_INVALIDO vence INAPTA, que vence INCONCLUSIVA, que vence APTA COM RESSALVAS, que vence APTA.
O DV continua sendo resultado de negócio (HTTP 201 na API, sem chamada externa); só muda o rótulo, porque "INAPTA" num print levado a uma prefeitura diria algo falso sobre a entidade.

O resultado traz `motivos`, a lista de ids que decidiram o status: todas as RESTRICAO (com Q1 podem ser várias, inclusive cadastral e sanções juntas), ou todas as eliminatórias sem resposta, ou todos os ALERTA.
A ordem de exibição das restrições segue o capítulo 2.7.

Divergência entre fontes (D3, reescrito pelo D18): primeiro avalia-se a vigência de cada registro pelas datas (CSV local e OpenCNPJ); só depois, se uma fonte tem registro vigente e outra não, vence RESTRICAO, e o relatório mostra as respostas e o achado "fontes divergem".
`CONSTAM_REGISTROS` do TCU para CEIS ou CNEP com todas as sanções expiradas não é divergência (D18); o registro que só o TCU tem segue a regra do capítulo 10.5 (Q35).

Verificação não eliminatória que fica INDISPONIVEL (dirigentes, CNAE, Mapa, CEBAS, contas irregulares) não muda o status (Q5).
O usuário é avisado de forma explícita: o resultado traz a lista `avisos`, e a página mostra um aviso em destaque no topo, junto do status ("Não foi possível verificar: Mapa das OSCs; tente de novo em alguns minutos"), e não só na lista de verificações.

## 2.6 Catálogo de verificações (Q25)

O contrato da API e dos casos de referência usa um id textual estável por verificação.
O número do spec (coluna "Spec") é atributo, para manter a ligação com os capítulos deste documento.

| id | Spec | Nome | Tipo | Capítulo |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | ELIMINATÓRIA (falha = CNPJ_INVALIDO) | 4 |
| `situacao` | 2 | Situação cadastral da entidade (matriz) | ELIMINATÓRIA | 5 |
| `natureza` | 3 | Natureza jurídica | ELIMINATÓRIA (ALERTA para revisão manual e natureza desconhecida) | 6 |
| `cnae` | 4 | CNAE de relevância social | ALERTA | 7 |
| `religiosa` | 4 | Organização religiosa (art. 2º, I, c) | ALERTA | 7.5 |
| `tempo` | 5 | Tempo de existência | ALERTA | 8 |
| `estabelecimento` | 2 | Estabelecimento consultado (filial ou matriz) | INFORMATIVA (ALERTA para filial não ativa e matriz não identificada) | 5.5 |
| `cepim` | 6 | CEPIM | ELIMINATÓRIA | 9 |
| `ceis` | 7 | CEIS | ELIMINATÓRIA | 10 |
| `cnep` | 8 | CNEP | ELIMINATÓRIA | 11 |
| `tcu_inidoneos` | 9 | Licitantes inidôneos (TCU) | ELIMINATÓRIA | 12 |
| `cnj_cnia` | 9 | Improbidade (CNJ, CNIA) | ELIMINATÓRIA | 12 |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (TCU, art. 39, VI) [ORIENTADOR Q21] | ALERTA | 12.5 |
| `dirigentes` | 10 | Dirigentes (QSA) | ALERTA | 13 |
| `mapa_osc` | 11 | Mapa das OSCs | INFORMATIVA (ausente = ALERTA, D2) | 14 |
| `cebas` | 12 | CEBAS | INFORMATIVA | 15 e 22 |

São 15 verificações fixas e uma provisória (`tcu_contas_irregulares`), que existe enquanto valer a recomendação do Q21.
Separar a verificação 9 em `tcu_inidoneos` e `cnj_cnia` deixa claro qual cadastro falhou ou ficou indisponível.
As verificações informativas trazem também um campo `situacao` próprio, com rótulo para a página (Q40): no CEBAS `ATIVO`, `EM_RENOVACAO`, `NAO_VIGENTE`, `PEDIDO_EM_ANALISE`, `NAO_ENCONTRADO`; no Mapa `PREENCHIDO`, `AUTOMATICO`, `AUSENTE`.
O `estado` continua servindo só para a agregação.

## 2.7 Textos do relatório (B1, B8, B9, B16 a B18, B20, B21)

Esta seção define o que o relatório escreve além do estado de cada verificação.
O motor não monta frases soltas: todo texto vem de um catálogo versionado.

Catálogo de mensagens (B1):

- Arquivo `mensagens.json`, versionado junto de `natureza_juridica.json` e `regras_cnae.json`, com uma mensagem por par (verificação, estado, situação ou motivo de falha).
- As mensagens usam variáveis nomeadas (`{data_fim}`, `{orgao}`, `{fonte}`, `{data_base}`), escritas para leigo, com o artigo da lei quando houver.
- Um teste automatizado garante que existe mensagem para cada par possível e que nenhuma variável fica sem valor.
- Os rótulos dos status finais com acento ("Apta com ressalvas", "CNPJ inválido") ficam no catálogo, separados dos enums.
- O catálogo entra na `versao_regras` (B11), então o replay de uma consulta antiga usa as mensagens da época.

Ordem de exibição quando há várias restrições (B16): cadastrais (`situacao`, `natureza`), depois `tcu_inidoneos` e `cnj_cnia`, depois `cepim`, `ceis` e `cnep`; dentro de cada verificação, registros vigentes primeiro, pela data final mais distante, e depois o histórico.

Quando a mesma decisão aparece em duas verificações (Q42), cada verificação mantém o seu estado, e o achado da segunda diz "mesma decisão já listada em [verificação]", ligando os registros pelo número do processo.

Bloco fixo "O que fazer quando o resultado é INCONCLUSIVA" (B8):

| Verificação sem resposta | Consulta manual indicada |
|---|---|
| `situacao` | Comprovante de inscrição no site da Receita Federal (com CAPTCHA, feito pelo usuário). |
| `cepim`, `ceis`, `cnep` | Página de sanções do Portal da Transparência (portaldatransparencia.gov.br/sancoes). |
| `tcu_inidoneos`, `cnj_cnia` | `linkConsultaManual` devolvido pelo TCU, ou https://certidoes-apf.apps.tcu.gov.br/. |
| `mapa_osc` | Perfil da OSC em mapaosc.ipea.gov.br. |
| `cebas` | SisCEBAS Saúde ou o ministério da área. |

Quando a falha é transitória (timeout, 5xx), o bloco acrescenta "tente de novo em alguns minutos"; quando é base vencida, "a base de DD/MM/AAAA está mais velha que o limite; o operador foi avisado".

Bloco fixo "O que este relatório não verifica" (B9), sempre no fim do relatório: certidões do art. 34; art. 39, incisos III (dirigente que é agente político ou membro de Poder do ente parceiro) e § 2º (ressarcimento do dano); sanções estaduais e municipais que não chegam ao CEIS; tribunais de contas fora do TCU e do TCE-SP; improbidade só com suspensão de direitos políticos (está só no CNIA, que exige CPF completo); dirigentes que não estão no QSA, que costuma trazer só o presidente; o que está no estatuto e na prestação de contas.

Contestação de falso positivo (B17): no MVP não há canal próprio.
Cada achado traz o órgão responsável pelo registro e o link oficial, com a frase "se o registro estiver errado ou já tiver sido revisto, a correção é pedida ao órgão que o publicou".

Atribuição das fontes (B18): rodapé com a fonte, a data da base usada e o link de cada uma (Receita via OpenCNPJ ou BrasilAPI, CGU/Portal da Transparência, TCU, TCE-SP, CNJ, Ipea/Mapa das OSCs, Ministérios da Saúde, da Educação e do Desenvolvimento e Assistência Social, Imprensa Nacional).

Relatório de consulta feita por filial (B20): o título mostra a razão social e o CNPJ da entidade avaliada (matriz); logo abaixo, "Consulta feita a partir do estabelecimento XX.XXX.XXX/XXXX-XX (filial, situação ...)".
A API traz os dois campos (`cnpj` informado e `cnpj_avaliado`) e `estabelecimento` (`MATRIZ` ou `FILIAL`).

Data de referência (B21): a interface não deixa o usuário escolher outra data no MVP.
A data de referência é sempre a data corrente em Brasília; o campo existe só nos testes e no replay.

# 3. Mapa das verificações

Resumo de todas as verificações, com o id do catálogo (cap. 2.6), o tipo, as fontes usadas no MVP e o capítulo onde cada uma é detalhada.
A primeira fonte de cada linha é a observação principal; as demais são observações adicionais combinadas pela regra do capítulo 2.5.

| Spec | id | Tipo | Fontes no MVP | Cap. |
|---|---|---|---|---|
| 1 | `dv` | Eliminatória (falha = CNPJ_INVALIDO) | Cálculo local (`validador_osc/cnpj.py`) | 4 |
| 2 | `situacao`, `estabelecimento` | Eliminatória; informativa | OpenCNPJ (fallback BrasilAPI), D17 | 5 |
| 3 | `natureza` | Eliminatória / Alerta | OpenCNPJ com conversor (fallback BrasilAPI) | 6 |
| 4 | `cnae`, `religiosa` | Alerta | OpenCNPJ (fallback BrasilAPI) + regras CNAE (D7) | 7 |
| 5 | `tempo` | Alerta | OpenCNPJ (fallback BrasilAPI) | 8 |
| 6 | `cepim` | Eliminatória | CSV diário da CGU (local, exato e por raiz) + OpenCNPJ `?datasets=cepim` | 9 |
| 7 | `ceis` | Eliminatória | CSV diário da CGU (local) + OpenCNPJ `?datasets=ceis` + TCU Consulta Consolidada | 10 |
| 8 | `cnep` | Eliminatória | CSV diário da CGU (local) + OpenCNPJ `?datasets=cnep` + TCU Consulta Consolidada | 11 |
| 9 | `tcu_inidoneos` | Eliminatória | TCU Consulta Consolidada + lista de inidôneos da Plataforma de Certidões (local, Q34) | 12 |
| 9 | `cnj_cnia` | Eliminatória | TCU Consulta Consolidada (item CNIA) + CEIS de origem CNJ para as datas (Q19) | 12 |
| 9 | `tcu_contas_irregulares` | Alerta [ORIENTADOR Q21] | Lista de contas irregulares da Plataforma de Certidões (local) | 12.5 |
| 10 | `dirigentes` | Alerta | QSA da fonte cadastral + pessoas físicas dos CSVs de CEIS/CNEP, das listas do TCU de contas irregulares e inabilitados e da relação do TCE-SP do Terceiro Setor (D15, Q8) | 13 |
| 11 | `mapa_osc` | Informativa (ausência = Alerta, D2) | API pública do Ipea | 14 |
| 12 | `cebas` | Informativa | SisCEBAS Saúde, planilhas oficiais MDS/MEC, DOU (bases locais, D16) | 15 e 22 |

A API do Portal da Transparência com chave não entra no motor nem na configuração (D14).
A chave é vinculada ao CPF de uma pessoa física e o teste de 01/10/2026 mostrou que a API não é mais fresca que o CSV diário nem busca por raiz; ela fica só como ferramenta manual de conferência (cap. 19).


---

# PARTE II - As verificações, uma a uma

# 4. Verificação 1 - Dígito verificador (DV)

## 4.1 O que é

O CNPJ tem 14 posições: 8 da raiz (identifica a organização), 4 da ordem (0001 é a matriz, 0002 em diante são filiais) e 2 dígitos verificadores calculados a partir das 12 primeiras.
Desde julho de 2026, novos CNPJs podem ter letras nas 12 primeiras posições (formato alfanumérico, IN RFB 2.229/2024); os 2 dígitos verificadores continuam numéricos, e os CNPJs antigos continuam válidos.
O primeiro CNPJ alfanumérico real (00.000.000/E08G-12, filial do Banco do Brasil, aberta em 31/07/2026) já aparece no OpenCNPJ.

## 4.2 Por que precisamos

É a única verificação sem custo e sem dependência externa.
Ela barra erro de digitação antes de gastar qualquer requisição e protege as APIs de receberem lixo.
Também é onde o sistema já nasce preparado para o formato novo: o DV aceita alfanumérico, mas as consultas às fontes ficam fora do MVP para esse formato (D4, capítulo 16).

## 4.3 Algoritmo (válido para numérico e alfanumérico)

- Remover espaços, pontuação e traços (inclusive os traços Unicode de texto copiado de PDF) e converter a-z para maiúsculas (só letras ASCII).
- Validar o formato: 12 caracteres em [0-9A-Z] seguidos de 2 dígitos [0-9] (com `[0-9]` explícito, nunca `\d`, que aceitaria dígitos de outros alfabetos).
- Rejeitar base repetida: a regra olha as 12 primeiras posições, não os 14 caracteres, para barrar casos como 11111111111180 (base repetida com DV que confere).
- Converter cada caractere em valor: **código ASCII - 48**. Assim, '0' a '9' valem 0 a 9 (igual ao antigo) e 'A' vale 17, 'B' vale 18, até 'Z' valendo 42.
- 1º DV: multiplicar os 12 valores pelos pesos 5,4,3,2,9,8,7,6,5,4,3,2; somar; r = soma mod 11; DV = 0 se r < 2, senão 11 - r.
- 2º DV: repetir com os 13 caracteres (12 + 1º DV) e pesos 6,5,4,3,2,9,8,7,6,5,4,3,2.

A implementação é código próprio, sem biblioteca (D11): nenhuma das seis bibliotecas avaliadas informa o motivo da falha e o DV esperado, e cinco delas aceitam base repetida.
O comparativo está em `fase0/dv/ficha.md`.

## 4.4 Retorno esperado

| **CONFORME (passa)** | **NÃO CONFORME (falha)** |
|---|---|
| Formato correto e os dois DVs calculados batem com os informados. Estado: OK. | Formato inválido, base repetida ou DV divergente. Estado: RESTRICAO. Status final: CNPJ_INVALIDO (Q3), mostrado como erro de digitação no formulário, sem relatório de entidade; as demais verificações ficam NAO_VERIFICADO. A função devolve o motivo (`formato`, `repetido` ou `dv`) e, quando o motivo é `dv`, o DV esperado. Mensagem: "CNPJ inválido: dígito verificador não confere (esperado XX)". |

## 4.5 Testes executados [EXECUTADO]

Implementação em `validador_osc/cnpj.py`, com 36 testes em `tests/test_cnpj.py` (30/09/2026, todos passando; `ruff` e `mypy --strict` sem avisos).
Casos principais:

| Entrada | Resultado | Comentário |
|---|---|---|
| 19.131.243/0001-97 | Válido (DV 97) | Open Knowledge Brasil, associação real. Caso base de OSC. |
| 00.000.000/0001-91 | Válido (DV 91) | Banco do Brasil. Caso de natureza não elegível. |
| 12.ABC.345/01DE-35 | Válido (DV 35) | Exemplo oficial de CNPJ alfanumérico divulgado pela Receita. Confirma que o algoritmo aceita letras. |
| 12.abc.345/01de-35 | Válido (DV 35) | Minúsculas são normalizadas. |
| 19.131.243/0001-98 | Inválido (esperado 97) | Erro de digitação no último dígito. |
| 11111111111111 | Inválido (repetido) | Sequência repetida passa na conta, mas precisa ser barrada. |
| 11111111111180 | Inválido (repetido) | Base de 12 posições repetida com DV que confere; cinco de seis bibliotecas aceitam. |
| 12ABC34501DE3 | Inválido (formato) | 13 caracteres. |

# 5. Verificação 2 - Situação cadastral

## 5.1 O que é

É o estado do CNPJ na Receita Federal.
Os códigos da base aberta são: 1 NULA, 2 ATIVA, 3 SUSPENSA, 4 INAPTA e 8 BAIXADA.
Cada situação diferente de ATIVA vem acompanhada de um motivo (ex.: omissão de declarações, extinção por encerramento) e de uma data.

## 5.2 Por que precisamos

O art. 33 exige cadastro ativo, e uma entidade suspensa, inapta ou baixada não consegue emitir as certidões do art. 34.
Mesmo quando a situação reprova, as demais verificações continuam sendo avaliadas, para o relatório mostrar todas as restrições (Q1).

## 5.3 Campos usados

Nomes do modelo interno, que é o mesmo para qualquer fonte cadastral (capítulos 18 e 18A).

| Campo interno | Tipo | Uso | BrasilAPI | OpenCNPJ |
|---|---|---|---|---|
| situacao_codigo | número | Regra: == 2. | `situacao_cadastral` (int) | `situacao_cadastral` em texto ("Ativa", "Baixada"), convertido |
| situacao_descricao | texto | Exibição no relatório. | `descricao_situacao_cadastral` | o próprio texto |
| situacao_data | data | Desde quando está nessa situação. | `data_situacao_cadastral` | `data_situacao_cadastral` |
| motivo_codigo / motivo_descricao | número / texto | Explicação da inaptidão. | `motivo_situacao_cadastral` (int) + `descricao_motivo_situacao_cadastral` | `motivo_situacao_cadastral` {codigo: "01", descricao} |
| matriz | booleano | Filial dispara a regra 5.5. | `identificador_matriz_filial` (1 matriz, 2 filial) | `matriz_filial` ("Matriz", "Filial"), convertido |

Com o OpenCNPJ como fonte principal (D17), o conversor transforma situação e matriz/filial de texto em número e trata "" e "0" como nulo (a matriz do Instituto GRPCOM volta `data_situacao_cadastral` = "0").
As grafias "Ativa", "Baixada", "Inapta" (C09) e "Suspensa" (C10) foram confirmadas em `fase0/casos_referencia.md`; "Nula" ainda não tem exemplo real, e o conversor trata grafia desconhecida como falha de formato (INDISPONIVEL), nunca como ATIVA.

## 5.4 Retorno esperado

| **CONFORME (passa)** | **NÃO CONFORME (falha)** |
|---|---|
| situacao_codigo = 2 (ATIVA) e espelho cadastral com até 60 dias. Estado: OK. | Qualquer outro código. Estado: RESTRICAO. Status final: INAPTA. Mensagem inclui a situação, a data e o motivo (ex.: "Situação BAIXADA desde 04/01/2012 - motivo: extinção por encerramento liquidação voluntária"). |

Espelho cadastral defasado (Q6, B6): o OpenCNPJ é comunitário e pode parar de atualizar sem erro HTTP.
Se a data do espelho (`last_updated` do `/info`, ou a data da carga da Minha Receita para a BrasilAPI) tiver mais de 60 dias na data da consulta, a verificação `situacao` de uma entidade ATIVA vira ALERTA com a frase "dados cadastrais de DD/MM/AAAA; uma mudança de situação posterior não aparece".
O relatório sempre mostra a data do espelho usado, mesmo dentro do limite, e lembra que a BrasilAPI pode ter cache de até 16 h a mais.

> **Quando o resultado é inconclusivo**
>
> CNPJ não encontrado (Q26): o OpenCNPJ devolveu 404 e a BrasilAPI, chamada também nesse caso, devolveu 404 ou falhou.
> Estado: INDISPONIVEL com motivo `NAO_ENCONTRADO` e a mensagem "CNPJ não encontrado no espelho de DD/MM/AAAA; pode ser CNPJ recém-criado ou inexistente", nunca INAPTA direto.
> O fan-out não roda: sem cadastro não há QSA nem raiz, e o TCU daria um "nada consta" enganoso (D13); as demais verificações ficam NAO_VERIFICADO e o status é INCONCLUSIVA.
> Fonte cadastral fora do ar (5xx ou timeout) é INDISPONIVEL com o motivo da falha; o motor tenta o fallback antes (capítulo 18).

## 5.5 Filial (D5)

Ser filial não reprova.
O teste T7 da Fase 0 (`fase0/brasilapi/ficha.md`) confirmou o comportamento que D5 previa:

- A filial é detectada só por `identificador_matriz_filial = 2` (ou `matriz_filial = "Filial"` no OpenCNPJ), nunca pela ordem (Q27): na IDEAS, o estabelecimento 0004-88 é a matriz e o 0001-35 é filial.
- Nenhuma fonte traz um campo apontando para a matriz; o motor monta o CNPJ da matriz com `cnpj_da_matriz` (raiz + 0001 + DVs recalculados) e consulta a matriz em paralelo com o fan-out.
- `situacao` avalia a entidade, isto é, a matriz: matriz diferente de ATIVA derruba tudo (RESTRICAO, INAPTA).
- `estabelecimento` avalia o CNPJ informado: filial BAIXADA, INAPTA ou SUSPENSA com matriz ATIVA = ALERTA "o estabelecimento informado não está ativo; a entidade está; confira se o CNPJ é o correto" (Q4). Filial ativa = OK informativo "consulta partiu da filial".
- Matriz fora da ordem 0001 (Q27): se raiz + 0001 não voltar como matriz (ou for o próprio CNPJ informado), `estabelecimento` vira ALERTA pedindo o CNPJ da matriz, e as demais verificações usam os dados do estabelecimento consultado; o tempo usa a data dele, com aviso. Descobrir a matriz verdadeira pela base local ou pelo Mapa fica para depois do MVP.
- Matriz sem resposta (Q44): se o cadastro da matriz ficar INDISPONIVEL, `situacao` fica INDISPONIVEL (status INCONCLUSIVA); natureza e QSA vêm da filial (são da raiz) e o tempo usa a data da filial, com aviso.
- Natureza: avaliada uma vez, porque vem da raiz.
- Tempo de existência: usa a data de início da matriz. A `data_inicio_atividade` da filial é da própria filial (Instituto GRPCOM: filial de 2011, matriz de 2002).
- Sanções: consulta o CNPJ informado, a matriz e, nas bases locais, todos os estabelecimentos da raiz (cap. 10.5, [ORIENTADOR Q20]).
- CNAE: considera os CNAEs das duas.
- QSA: igual nas duas (vem da raiz).
- Mapa das OSCs: consultado pela matriz; CEBAS: consultado pela matriz e pelo estabelecimento informado, porque o SisCEBAS registra o CNPJ requerente, que pode ser de filial (Q28).
- O relatório explicita que a consulta partiu de uma filial, mostra a situação da filial e traz os dois CNPJs (cap. 2.7, B20).

Casos de referência: C23 (filial ativa), C24 (filial baixada com matriz ativa, ALERTA), C26 e C27 (IDEAS, matriz 0004 e filial 0001), C37 e C38 (Instituto Global, sanção só na filial).

# 6. Verificação 3 - Natureza jurídica

## 6.1 O que é

Código de 4 dígitos (na Tabela de Natureza Jurídica publicada como NNN-N) que diz que tipo de pessoa jurídica é a entidade: associação, fundação, LTDA, cooperativa, órgão público etc.
Na BrasilAPI e na Minha Receita ele chega como número inteiro sem hífen (3999 em vez de 399-9), o que está refletido na tabela de regras.

O OpenCNPJ não tem o código: traz só a descrição em texto ("Associação Privada", "Organização Religiosa", "Cooperativa", "Sociedade de Economia Mista").
O conversor mapeia a descrição para o código usando a tabela oficial de naturezas jurídicas da Receita (D17).
Descrição desconhecida no mapeamento gera ALERTA, nunca NÃO ELEGÍVEL por omissão.

Como a tabela de conversão é feita (B12):

- `natureza_juridica.json` é gerado da Tabela de Natureza Jurídica oficial da Receita (código NNN-N, descrição oficial), com a regra do capítulo 6.3 e a justificativa em cada linha.
- A comparação normaliza a descrição: sem acento, maiúsculas, espaços e pontuação colapsados; sinônimos observados entram numa lista `sinonimos` da própria linha.
- Um teste percorre todas as descrições já vistas nas respostas da Fase 0 e dos 49 casos de referência e exige que cada uma tenha código; descrição nova aparece em log de aviso.

## 6.2 Por que precisamos

É o critério objetivo mais forte para saber se a entidade pode ser OSC.
Uma sociedade empresária nunca será OSC, por mais social que seja a atividade.

## 6.3 Tabela de regras proposta

| Código API | Código tabela | Descrição | Regra |
|---|---|---|---|
| 3999 | 399-9 | Associação Privada | ELEGÍVEL |
| 3069 | 306-9 | Fundação Privada | ELEGÍVEL |
| 3220 | 322-0 | Organização Religiosa | ELEGÍVEL, sujeita à verificação `religiosa` (cap. 7.5) |
| 2143 | 214-3 | Cooperativa | REVISÃO MANUAL (só cooperativas do art. 2º, I, b) |
| 3301 | 330-1 | Organização Social (OS) | REVISÃO MANUAL (contratos de gestão com OS estão fora do MROSC, art. 3º) |
| 3204 | 320-4 | Estabelecimento no Brasil de fundação ou associação estrangeira | REVISÃO MANUAL |
| 3077 | 307-7 | Serviço Social Autônomo | NÃO ELEGÍVEL (parcerias com o Sistema S estão fora do MROSC, art. 3º) |
| demais | - | Empresárias (2xxx), administração pública (1xxx), pessoas físicas etc. | NÃO ELEGÍVEL |
| desconhecida | - | Descrição do OpenCNPJ sem correspondência no mapeamento | ALERTA |

> **[ORIENTADOR Q14] Regra provisória**
>
> Os casos de REVISÃO MANUAL (214-3, 330-1, 320-4) e a exclusão de 307-7 são interpretação da lei feita para o projeto (O1).
> A tabela acima vale como está até a resposta do orientador; se ele decidir diferente, muda só `natureza_juridica.json`, sem código.

## 6.4 Retorno esperado

| **CONFORME (passa)** | **NÃO CONFORME (falha)** |
|---|---|
| Código na lista ELEGÍVEL. Estado: OK. Código em REVISÃO MANUAL ou descrição desconhecida: estado ALERTA e o fluxo continua. | Código NÃO ELEGÍVEL. Estado: RESTRICAO. Status final: INAPTA. Mensagem: "Natureza jurídica 206-2 (Sociedade Empresária Limitada) não é compatível com OSC (Lei 13.019/2014, art. 2º, I)". |

Casos reais da Fase 0: Open Knowledge Brasil 3999 (OK), Banco do Brasil 2038 Sociedade de Economia Mista (RESTRICAO), Mitra Arquidiocesana de Brasília 3220 (OK, com `religiosa` em ALERTA), Cooperativa do Alto Cajari 2143 (ALERTA).

# 7. Verificação 4 - CNAE de relevância social

## 7.1 O que é

A Classificação Nacional de Atividades Econômicas (CNAE) descreve o que a entidade declara fazer.
Cada CNPJ tem um CNAE principal e uma lista de secundários.

O código é sempre normalizado para string de 7 dígitos com zero à esquerda.
A BrasilAPI e a Minha Receita devolvem `cnae_fiscal` como inteiro e perdem o zero das divisões 01 a 09 (cooperativa do Alto Cajari: `220903` em vez de `0220903`); o OpenCNPJ já devolve string de 7 dígitos.

## 7.2 Por que precisamos (e por que não é eliminatória)

O MROSC exige que a OSC tenha objetivos voltados a atividades de relevância pública e social, mas quem define isso é o estatuto, não o CNAE.
Muitas associações legítimas têm CNAE genérico (94.99-5, "atividades associativas não especificadas").
Por isso o CNAE funciona como sinal: ele gera alerta, mas nunca reprova.

## 7.3 Classificação (D7)

A classificação completa está em `fase0/cnae/regras_cnae.json` (regras) e `fase0/cnae/proposta.md` (justificativas), com o resultado para as 1.332 subclasses da CNAE 2.3 em `fase0/cnae/cnae_classificado.csv` e 22 testes em `fase0/cnae/test_classificar_cnae.py`.
Os 8 pontos abaixo dependem do orientador (O2) e valem como regra provisória [ORIENTADOR Q15]; a recomendação é aprovar a proposta e, para saúde, manter ALTA com ressalva no texto sobre o art. 3º, IV.
Se o orientador decidir diferente, muda só `regras_cnae.json`.

Como as regras funcionam:

- Cada regra tem um prefixo de 2 (divisão), 3 (grupo), 5 (classe) ou 7 dígitos (subclasse), uma faixa e uma justificativa.
- Para cada subclasse vence a regra de prefixo mais longo que casar (a mais específica).
- Sem regra que case, vale o padrão BAIXA.
- A faixa só é avaliada depois do filtro de natureza jurídica: a pergunta é "para uma associação, fundação ou organização religiosa, este CNAE sinaliza atividade de relevância pública e social?".

Critério das faixas:

- **ALTA**: a atividade corresponde diretamente a uma finalidade do art. 84-C da Lei 13.019/2014 ou a uma área central do Mapa das OSCs.
- **MEDIA**: a atividade é compatível com uma finalidade social, mas o CNAE sozinho não distingue o uso social do comercial ou de interesse particular.
- **BAIXA**: atividade econômica comum, de interesse de categoria, estatal ou vedada (padrão).

Resumo das regras:

| Faixa | Prefixos principais | Subclasses |
|---|---|---|
| ALTA | 85 educação, 86 saúde, 87 e 88 assistência social, 90 artes e espetáculos, 91 bibliotecas, museus e patrimônio, 94.30-8 defesa de direitos sociais, 94.93-6 associações culturais, 72.20-7 P&D em ciências sociais, 0220-9/06 conservação de florestas nativas, 6499-9/05 microcrédito de OSCIP | 86 (6,5%) |
| MEDIA | 94.99-5 associativas não especificadas, 94.91-0 organizações religiosas ou filosóficas, 93.1 esporte, 38.11-4 e 38.3 coleta e reciclagem, 59.11-1 e 59.14-6 audiovisual, 60.10-1 rádio, 72.10-0 P&D em ciências naturais, 7490-1/03 ATER, 75.00-1 veterinária, 85.93-7 idiomas, 8599-6/03 a /05 cursos livres, 8711-5/05 condomínio para idosos, 9001-9/05 rodeios | 25 (1,9%) |
| BAIXA explícita | 94.1 patronais e profissionais, 94.2 sindicatos, 94.92-8 organizações políticas, 84 administração pública, 99 organismos internacionais, 92 apostas, 93.13-1 e 93.2 academias e entretenimento, 96.09-2, 8599-6/01 e /02 autoescola, 9001-9/06 sonorização, 5911-1/02 publicidade | 37 |
| BAIXA (padrão) | Todo o resto (comércio, indústria, serviços empresariais etc.) | 1.184 |

A linha de 94.91-0 deixou de carregar "com alerta": a faixa é sempre MEDIA, e o alerta do art. 2º, I, c passou para a regra própria do item 7.5.

Pontos que dependem do orientador (seção 8 de `fase0/cnae/proposta.md`):

- [ORIENTADOR Q15] 94.93-6 (associações culturais) sobe de MÉDIA, como estava na versão 1.0, para ALTA.
- [ORIENTADOR Q15] Saúde (86) inteira em ALTA, apesar de o art. 3º, IV excluir do MROSC os convênios do SUS complementar; o relatório traz a ressalva no texto.
- [ORIENTADOR Q15] Esporte (93.1) em MÉDIA, incluindo clubes sociais (9312-3/00).
- [ORIENTADOR Q15] Proteção animal: sem CNAE próprio (fica em 94.99-5); 75.00-1 (veterinária) em MÉDIA.
- [ORIENTADOR Q15] Meio ambiente em ALTA por 94.30-8, 91.03-1 e 0220-9/06; reciclagem e coleta em MÉDIA.
- [ORIENTADOR Q15] Regra religiosa: gatilho por CNAE principal 94.91-0 também para natureza 399-9, e lojas maçônicas (mesma subclasse) recebendo o mesmo alerta.
- [ORIENTADOR Q15] Inclusões fora das divisões sociais clássicas: microcrédito de OSCIP em ALTA; rádio, ATER e audiovisual em MÉDIA.
- [ORIENTADOR Q15] Exceções dentro de divisões ALTA: autoescola e sonorização em BAIXA; idiomas, informática, treinamento, cursinhos, condomínio para idosos e rodeios em MÉDIA.

## 7.4 Retorno esperado

| **CONFORME (passa)** | **NÃO CONFORME (falha)** |
|---|---|
| CNAE principal ou algum secundário em ALTA ou MÉDIA. Estado: OK, com a faixa registrada no relatório. | Nenhum CNAE em ALTA ou MÉDIA. Estado: ALERTA (não reprova). Mensagem: "Nenhuma atividade cadastrada tem relação direta com relevância social; confira o estatuto". |

Para filial, entram os CNAEs da filial e da matriz (D5).

## 7.5 Verificação `religiosa` (art. 2º, I, c)

A faixa e o alerta religioso são coisas separadas: o alerta é a verificação própria `religiosa` (spec 4, Q25), e não um estado da verificação `cnae`.
Quando a regra não se aplica (natureza diferente de 3220 e CNAE principal diferente de 94.91-0), o estado é OK com a mensagem "não se aplica".
O alerta é avaliado sobre a entidade inteira:

```
ALERTA_RELIGIOSA =
    (natureza_juridica == 3220  OU  cnae_principal == 9491000)
    E nenhum CNAE (principal ou secundário) em faixa ALTA
```

Mensagem: "Organização religiosa sem atividade social de alta aderência no CNAE: a Lei 13.019/2014, art. 2º, I, c, exige atividades de interesse público e de cunho social distintas das exclusivamente religiosas; confira estatuto e plano de trabalho."

- Natureza 322-0 cobre quem se declara organização religiosa.
- [ORIENTADOR Q15] CNAE principal 94.91-0 cobre igrejas registradas como associação privada (399-9). Só o CNAE principal conta nesse gatilho.
- Exigir ALTA, e não MÉDIA, é o que torna a regra objetiva.
- A regra não reprova; ela só pede revisão do estatuto.
- A verificação `religiosa` e a verificação `cnae` são independentes e podem dar ALERTA juntas (ex.: natureza 322-0 com CNAE principal de comércio).

Caso real da Fase 0: Mitra Arquidiocesana de Brasília (00.108.217/0001-10), natureza 3220, CNAE 9491000, sem secundários: `religiosa` em ALERTA (caso C12 de `fase0/casos_referencia.md`).

# 8. Verificação 5 - Tempo de existência (art. 33, V, a)

## 8.1 O que é

Tempo decorrido entre `data_inicio_atividade` e a data da consulta.
O MROSC pede no mínimo 1 ano de CNPJ ativo para parcerias com municípios, 2 com estados/DF e 3 com a União.
Para filial, vale a data de início da matriz (D5); se a matriz não for identificada, vale a data do estabelecimento consultado, com aviso (Q27).

Contagem (Q29): anos completos, com o dia do aniversário contando (início em 01/10/2025 tem 1 ano em 01/10/2026 e 0 ano em 30/09/2026); início em 29/02 faz aniversário em 28/02 nos anos não bissextos.

Reativação [ORIENTADOR Q23]: o art. 33, V, a fala em existência "com cadastro ativo".
A base aberta não informa se houve interrupção, e `data_situacao_cadastral` muda por outros motivos.
Regra provisória: o tempo conta desde `data_inicio_atividade`; quando `data_situacao_cadastral` é posterior ao início e a entidade está ATIVA (sinal de reativação), o texto cita a data ("ATIVA desde DD/MM/AAAA; contado desde o início"), sem mudar o estado.

## 8.2 Por que precisamos

É um requisito objetivo, verificável por dado público e frequentemente esquecido.
Como o prazo depende de qual ente vai firmar a parceria (e pode ser reduzido pelo gestor), a verificação nunca reprova: no máximo gera ALERTA.

## 8.3 Parâmetro `esfera` (D6)

A consulta aceita o parâmetro opcional `esfera`, com os valores `municipio` (prazo de 1 ano), `estado` (2 anos) e `uniao` (3 anos).

| Situação | Estado | Mensagem |
|---|---|---|
| `esfera` informada e o prazo da esfera foi atingido | OK | "Atinge o prazo de N ano(s) exigido para parcerias com [esfera]". |
| `esfera` informada e o prazo da esfera não foi atingido | ALERTA | "Não atinge o prazo de N ano(s) exigido para [esfera]; o gestor pode reduzir o prazo quando nenhuma organização o atingir (art. 33, V, a)". |
| `esfera` não informada | OK só com 3 anos ou mais; senão ALERTA | O relatório mostra os 3 cenários. Com menos de 3 anos, o ALERTA lista as esferas atendidas (ex.: "atinge municípios e estados; União exige 3 anos"); com menos de 1 ano, "ainda não atinge o prazo mínimo para nenhuma esfera". |

Caso real da Fase 0: Associação Maturidade em Movimento (65.478.551/0001-00), aberta em 03/02/2026, menos de 1 ano: ALERTA em qualquer esfera.

# 9. Verificação 6 - CEPIM

## 9.1 O que é

Cadastro de Entidades Privadas Sem Fins Lucrativos Impedidas, mantido pela CGU e publicado no Portal da Transparência.
Lista entidades impedidas de celebrar novos convênios, contratos de repasse ou termos de parceria com a administração pública federal por irregularidades não resolvidas em parcerias anteriores.

## 9.2 Por que precisamos

É o cadastro feito especificamente para o terceiro setor e o impedimento mais direto para uma parceria.
Estar no CEPIM é, na prática, o "nome sujo" de uma OSC perante a União.

## 9.3 Fonte no MVP

Observação principal: arquivo CSV diário oficial da CGU, importado localmente (capítulo 19.5), com busca pelo CNPJ exato e pela raiz (D14).
Observação adicional: OpenCNPJ com `?datasets=cepim` (capítulo 18A), que vem de graça na chamada cadastral.
As duas são combinadas pela regra do capítulo 2.5; com o CSV dentro da idade máxima de 7 dias (Q6), a verificação responde mesmo se o OpenCNPJ cair e o cadastro vier da BrasilAPI.
A API do Portal com chave não é usada pelo motor.

## 9.4 Retorno esperado

| **CONFORME (passa)** | **NÃO CONFORME (falha)** |
|---|---|
| Nenhum registro para o CNPJ consultado, a matriz ou outro estabelecimento da raiz. Estado: OK. | Pelo menos um registro. Estado: RESTRICAO. Status final: INAPTA. O CEPIM não tem datas: registro presente é impedimento. Mensagem inclui órgão concedente, convênio e motivo, a base legal (art. 39) e, quando for o caso, o estabelecimento do registro. |

[ORIENTADOR Q18] Regra provisória: o CEPIM reprova em qualquer esfera, inclusive parceria municipal ou estadual, porque os seus motivos (prestação de contas impugnada, omissão, tomada de contas especial) correspondem aos incisos II e IV do art. 39, que valem para qualquer esfera.
A alternativa em análise é ALERTA quando `esfera` for `municipio` ou `estado`.

> **Quando o resultado é inconclusivo**
>
> Nenhuma observação válida: CSV local mais velho que o limite (ou ainda não carregado) e OpenCNPJ com falha ou sem datasets (cadastro vindo da BrasilAPI). Estado: INDISPONIVEL.
> Status final vira INCONCLUSIVA se nada mais reprovar.

## 9.5 Cuidados

- Confirmar no retorno que o CNPJ do registro é exatamente o consultado; nunca confiar só no filtro da fonte.
- O CEPIM não tem data de início nem de fim, nem no CSV nem na API (só `dataReferencia`); não existe "CEPIM expirado".
- Um CNPJ pode ter muitos registros (até 67 convênios; 10 no IMDC). O relatório agrupa por convênio.
- Há 23 registros de filial no CEPIM; a busca por raiz no CSV local os encontra (cap. 10.5, [ORIENTADOR Q20]).
- O CSV do CEPIM tinha dois dias de defasagem no teste (arquivo de 28/09/2026 em 30/09/2026); por isso o limite de idade é 7 dias (Q6).
- O CEPIM é federal. Impedimentos em estados e municípios não aparecem aqui; a limitação está no bloco fixo do capítulo 2.7.

Casos de referência: Associação dos Pais de Bom Jesus do Tocantins (14.112.015/0001-56), Associação Cultural Depósito do Teatro (05.315.570/0001-94) e Fundação Assis Gurgacz (02.203.539/0001-73), todos só no CEPIM (`fase0/portal/referencia_cnpjs.md`).

# 10. Verificação 7 - CEIS

## 10.1 O que é

Cadastro Nacional de Empresas Inidôneas e Suspensas.
Reúne pessoas físicas e jurídicas punidas com restrição de licitar ou contratar com a administração pública, alimentado por órgãos de todas as esferas.

## 10.2 Por que precisamos

O art. 39 impede parcerias com entidades punidas com suspensão ou declaração de inidoneidade.
Diferentemente do CEPIM, o CEIS não é exclusivo do terceiro setor, mas pega OSCs punidas em licitações e contratos.

## 10.3 Fonte no MVP

Observação principal: CSV diário oficial da CGU importado localmente (capítulo 19.5), com as datas de cada sanção e busca pelo CNPJ exato e pela raiz (D14).
Observações adicionais: OpenCNPJ `?datasets=ceis` (capítulo 18A), que também traz as datas, e a Consulta Consolidada do TCU (item `CEIS`, capítulo 20), que só diz se constam registros.
Primeiro avalia-se a vigência de cada registro pelas datas; só depois, se uma fonte tem registro vigente e outra não, vence RESTRICAO, e o relatório mostra as respostas (D3, D18).

## 10.4 Retorno esperado

| **CONFORME (passa)** | **NÃO CONFORME (falha)** |
|---|---|
| Nenhum registro para o CNPJ, ou só registros com data de fim da sanção já passada. Estado: OK (sanções expiradas vão para o histórico do relatório). | Registro com sanção vigente (sem data de fim, ou data de fim igual ou posterior à data de referência, inclusive o último dia, Q30). Estado: RESTRICAO. Status final: INAPTA. Mensagem inclui tipo de sanção, órgão sancionador, período, abrangência e fundamentação. |

> **Quando o resultado é inconclusivo**
>
> Nenhuma observação válida (CSV local vencido ou ausente, OpenCNPJ sem datasets e TCU sem resposta): INDISPONIVEL.
> Basta uma observação válida para concluir OK; as que falharam aparecem na lista de fontes da verificação.

## 10.5 Cuidados

- A vigência é sempre decidida pela data de fim, nunca pela categoria (D14). Os arquivos têm "sem prazo determinado" com data final (Associação Plural, 2019 a 2021) e "com prazo determinado" sem data final (Associação Millenar). Este último caso é tratado como vigente, com texto pedindo revisão humana (Q32).
- Dado de origem (Q32): `"0"`, `""` e "Sem informação" em datas são nulos; registros duplicados com códigos diferentes e mesmo conteúdo são agrupados por categoria, datas e órgão antes de exibir.
- 2.030 linhas do CEIS não têm data final.
- [ORIENTADOR Q17] Algumas sanções têm abrangência limitada (só o órgão sancionador ou só a esfera dele). Regra provisória: toda sanção vigente é RESTRICAO, e a abrangência aparece em destaque no texto; o sistema não sabe qual ente vai firmar a parceria, só a esfera. A alternativa em análise é ALERTA para abrangência limitada.
- O teste de vigência precisa injetar a data de referência (caso Escola Família Agrícola do Sertão, vigente até 22/11/2026, C31).
- [ORIENTADOR Q20] Sanção em outro estabelecimento da mesma raiz: a filial não tem personalidade jurídica própria, e a sanção é aplicada à pessoa jurídica. Regra provisória: registro em qualquer estabelecimento da raiz (achado pela busca por raiz no CSV local) conta como RESTRICAO, com o texto indicando o estabelecimento. A alternativa em análise é RESTRICAO só para o consultado e a matriz e ALERTA para os demais. O CEIS tem 172 registros de filial; a IDEAS tem a mesma sanção em 5 estabelecimentos.
- D18 (decidido): a Consulta Consolidada do TCU devolve CEIS `CONSTAM_REGISTROS` também para sanções expiradas (Associação Plural, fim em 18/11/2021; Instituto Atuar, antigo Instituto Caminhada, fim em 07/04/2022). Isso não é divergência: com todas as datas finais passadas, o estado é OK com histórico.
- Registro que só o TCU tem (Q35): quando o TCU diz `CONSTAM_REGISTROS` e nenhuma base local nem o OpenCNPJ têm registro para o CNPJ (por exemplo, sanção publicada depois do último CSV), o motor extrai as datas entre parênteses da `observacao`. Todas passadas: OK com histórico e o aviso "registro só no TCU". Alguma futura ou ilegível: RESTRICAO (D3).

# 11. Verificação 8 - CNEP

## 11.1 O que é

Cadastro Nacional de Empresas Punidas: pessoas jurídicas sancionadas com base na Lei Anticorrupção (Lei nº 12.846/2013), como multa e publicação extraordinária da decisão.

## 11.2 Por que precisamos

Punições por atos lesivos à administração pública são incompatíveis com parcerias, e a Lei Anticorrupção vale também para associações e fundações.

## 11.3 Fonte no MVP

Mesma combinação do CEIS: CSV diário local (principal, exato e por raiz), OpenCNPJ `?datasets=cnep` e TCU Consulta Consolidada (item `CNEP`), com vigência pelas datas antes da divergência (D3, D18).

## 11.4 Retorno esperado

| **CONFORME (passa)** | **NÃO CONFORME (falha)** |
|---|---|
| Nenhum registro vigente para o CNPJ. Estado: OK. | Punição vigente de suspensão, interdição, proibição de receber incentivos ou outra hipótese do art. 39, V. Estado: RESTRICAO. Status final: INAPTA. Multa e publicação extraordinária vigentes: ALERTA [ORIENTADOR Q16]. O relatório mostra tipo, valor da multa quando houver, órgão e data do trânsito em julgado. |

[ORIENTADOR Q16] Regra provisória: o art. 39, V lista suspensão, impedimento e inidoneidade (e as sanções do art. 73, II e III); a multa e a publicação extraordinária da Lei Anticorrupção não estão na lista e não têm prazo, então reprovariam a entidade para sempre.
Por isso, registro vigente do CNEP de multa ou publicação extraordinária é ALERTA, que ainda obriga a revisão humana; as demais categorias são RESTRICAO.
A alternativa em análise (spec 1.1) é RESTRICAO para todo registro vigente.

> **Quando o resultado é inconclusivo**
>
> Mesma regra de indisponibilidade do CEIS.

## 11.5 Cuidados

- No CNEP a ausência de data final é o normal (1.784 de 1.819 linhas), porque multa e publicação extraordinária não têm prazo: registro sem data final é vigente (e cai na regra do Q16 acima).
- Há linhas repetidas com os mesmos dados e códigos de sanção diferentes; o relatório deve agrupar.
- O mesmo processo pode gerar registros no CEIS e no CNEP (Associação Beneficente Nossa Senhora da Saúde, 43.190.337/0001-11).

# 12. Verificação 9 - Inidôneos do TCU, improbidade (CNJ) e contas irregulares

## 12.1 O que é

Duas listas de órgãos diferentes, que viram duas verificações (Q25): `tcu_inidoneos`, a relação de licitantes declarados inidôneos pelo Tribunal de Contas da União (art. 46 da Lei nº 8.443/1992), e `cnj_cnia`, o Cadastro Nacional de Condenações Cíveis por Ato de Improbidade Administrativa e Inelegibilidade (CNIA), do Conselho Nacional de Justiça.
A Consulta Consolidada de Pessoa Jurídica do TCU devolve as duas de uma vez, junto com CEIS e CNEP, sem chave e sem CAPTCHA (D13).
A lista de inidôneos da Plataforma de Certidões do TCU, baixada uma vez por dia (CSV de 35 KB), é a segunda observação de `tcu_inidoneos` (Q34).

## 12.2 Por que precisamos

O art. 39 impede parceria com entidade cujas contas tenham sido julgadas irregulares ou que tenha sido punida por Tribunal de Contas.
Essa é a fonte mais próxima disso que existe de forma pública e automatizável.
A consulta consolidada também serve de validação cruzada do CEIS e do CNEP.
O CEIS não substitui o TCU: 13 dos 91 inidôneos da lista do TCU consultada em 30/09/2026 não aparecem no CEIS.

## 12.3 Retorno esperado

| **CONFORME (passa)** | **NÃO CONFORME (falha)** |
|---|---|
| Verificação | CONFORME (passa) | NÃO CONFORME (falha) |
|---|---|---|
| `tcu_inidoneos` | Item `Inidôneos` com `NADA_CONSTA` e nenhum registro vigente na lista local, com o CNPJ confirmado pela fonte cadastral. Estado: OK. | Item `Inidôneos` com `CONSTAM_REGISTROS` ou registro com data final igual ou posterior à data de referência na lista local. Estado: RESTRICAO. Status final: INAPTA. Mensagem com processo, acórdão e data da decisão. |
| `cnj_cnia` | Item `CNIA` com `NADA_CONSTA`, com o CNPJ confirmado pela fonte cadastral. Estado: OK. | Item `CNIA` com `CONSTAM_REGISTROS`: estado conforme a regra do Q19 abaixo. |

Condição de OK (Q33): basta a confirmação do CNPJ pela fonte cadastral; `seCnpjEncontradoNaBaseTcu: false` com o cadastro confirmado é achado informativo, porque um CNPJ recém-criado pode existir na Receita e ainda não no TCU.
Sem cadastro confirmado o fan-out nem roda (cap. 5.4).

[ORIENTADOR Q19] CNIA sem datas: o item CNIA traz só o número do processo.
Regra provisória: o motor procura o mesmo número de processo nos registros do CEIS da entidade (o CEIS recebe do CNJ as condenações com proibição de contratar, com as datas).
Proibição vigente achada: RESTRICAO, com o achado "mesma decisão já listada em ceis" (Q42).
Registro achado só expirado, ou nenhum registro correspondente no CEIS: ALERTA, com a frase "confira as penas na página de detalhe do CNIA".
A alternativa em análise (spec 1.1) é RESTRICAO para qualquer registro no CNIA.
Nos 6 casos testados, a condenação do CNIA também estava no CEIS com as datas; a consulta à página de detalhe do CNIA por CNPJ fica para depois do MVP.

> **Quando o resultado é inconclusivo**
>
> `SISTEMA_INDISPONIVEL`, `ERRO`, `CNPJ_NAO_ENCONTRADO_NO_TCU` ou valor desconhecido em um item: INDISPONIVEL para aquela verificação, com o `linkConsultaManual` da resposta.
> Timeout, 5xx ou JSON inválido: `cnj_cnia` fica INDISPONIVEL, com link para https://certidoes-apf.apps.tcu.gov.br/; `tcu_inidoneos` ainda conclui pela lista local, se ela estiver dentro da idade máxima (3 dias, Q6).

## 12.4 Cuidados importantes

- **CNPJ inexistente volta "nada consta".** Um CNPJ com DV válido que não existe volta HTTP 200 com tudo `NADA_CONSTA`, `seCnpjEncontradoNaBaseTcu: false` e `razaoSocial: null`. Isso não é restrição, mas impede concluir OK sem a fonte cadastral ter confirmado o CNPJ (D13).
- **Alcance da certidão.** A certidão do TCU não lista responsáveis ainda não notificados, condenações com prazo vencido ou decisões suspensas por recurso. "Nada consta" significa "nada consta hoje, com efeito", e o relatório deve deixar isso claro.
- **CNIA e alfanumérico.** O CNIA devolve `ALFANUMERICO_NAO_SUPORTADO` para CNPJ alfanumérico; no MVP isso não chega a acontecer, porque o alfanumérico não é consultado (D4).
- **Exemplo de CNIA com ocorrência.** Obtido na rodada de 01/10/2026: Associação Cultural de Hip Hop de Laguna (05.051.898/0001-40, C35), com o mesmo processo no CEIS de origem TJSC; também C36, C39 e C46.
- **Mesma condenação em duas verificações (Q42).** A inidoneidade do TCU aparece também no CEIS (C40, C42), e a condenação do CNIA aparece no CEIS de origem CNJ (C35). Cada verificação mantém o seu estado, e o relatório liga os achados pelo número do processo.
- **Lista local de inidôneos (Q34).** O CSV da Plataforma de Certidões de 30/09/2026 tem 129 linhas: 128 com CNPJ (121 CNPJs distintos, porque há mais de um processo por CNPJ), 1 sem documento e nenhuma pessoa física; 4 linhas já têm data final passada em 01/10/2026, então o motor confere a data. A API ORDS da Ficha C do Portal tinha 91 registros; a diferença (121 contra 91 CNPJs) não se explica só pela duplicidade e fica para conferir na carga. O ORDS não é usado, porque não é documentado pelo TCU.

Casos de referência: Instituto Terra Social (03.463.763/0001-67) e IMDC (21.145.289/0001-07), OSCs inidôneas vigentes (C40, C42); Athena Construções (08.028.648/0001-88), inidôneo fora do CEIS.

## 12.5 Contas julgadas irregulares da própria OSC (art. 39, VI) [ORIENTADOR Q21]

O art. 39, VI impede a OSC que "tenha tido contas de parceria julgadas irregulares ou rejeitadas por Tribunal ou Conselho de Contas de qualquer esfera da Federação, em decisão irrecorrível, nos últimos 8 anos".
A lista de responsáveis com contas julgadas irregulares do TCU (Plataforma de Certidões, CSV de 11 MB, baixado uma vez por dia) traz 6.817 condenações de pessoa jurídica por CNPJ, mas não diz se a conta é de parceria.

Regra provisória (verificação `tcu_contas_irregulares`, tipo ALERTA):

| Situação | Estado | Texto |
|---|---|---|
| CNPJ (ou outro estabelecimento da raiz) na lista com trânsito em julgado nos últimos 8 anos | ALERTA | "Contas julgadas irregulares pelo TCU no processo N, trânsito em julgado em DD/MM/AAAA; a lista não informa se a conta é de parceria (art. 39, VI); confira o acórdão." |
| Só registros com trânsito há mais de 8 anos, ou nenhum registro | OK | Histórico fora da janela citado como informação. |
| Base local mais velha que 7 dias (Q6) | INDISPONIVEL | Aviso em destaque (Q5). |

RESTRICAO seria injusto, porque a natureza da conta é desconhecida.
As alternativas em análise são não usar a lista (sem a verificação) ou RESTRICAO; o dono também pode tirar a verificação do MVP.
Casos de referência com achado: C40 (ITS), C42 (IMDC) e C46 (AVAPE).


# 13. Verificação 10 - Dirigentes (QSA)

## 13.1 O que é

O Quadro de Sócios e Administradores da Receita traz nome, qualificação (presidente, diretor, tesoureiro etc.) e data de entrada de cada dirigente.
Nos dados abertos, o CPF vem mascarado e só os 6 dígitos do meio aparecem (ex.: `***112108**`).

## 13.2 Por que precisamos

O art. 39 também impede parcerias quando dirigentes estão em situações vedadas, como condenação por improbidade ou contas rejeitadas.
Checar a pessoa jurídica sem olhar para quem a dirige deixa um buraco.

## 13.3 Fontes e regra de correspondência

Decisão D15, com a opção C do Q8 (dono, 01/10/2026): o motor casa cada dirigente pessoa física do QSA com cinco listas públicas de pessoas físicas, todas importadas como bases locais.
Detalhes técnicos, volumes e teste ponta a ponta em `fase0/dirigentes/ficha.md`.

| Fonte | Hipótese do art. 39 | Casamento | Janela | Atualização e idade máxima (Q6) |
|---|---|---|---|---|
| CEIS e CNEP, CSV diário da CGU (cap. 19.5): 9.148 linhas de PF no CEIS e 28 no CNEP, CPF completo | VII, c (CEIS de origem CNJ); demais categorias como indício | Nome + 6 dígitos do meio do CPF | Sanção vigente na data de referência | Diária; 3 dias |
| TCU, responsáveis com contas julgadas irregulares (CADIRREG): 23.665 CPFs | VII, a, parcial (a lista não diz se a conta é de parceria) | Nome + 6 dígitos do meio do CPF | Trânsito em julgado nos últimos 8 anos | Diária; 7 dias |
| TCU, inabilitados para cargo em comissão ou função de confiança: 599 CPFs | VII, b | Nome + 6 dígitos do meio do CPF | Data final da inabilitação igual ou posterior à data de referência | Diária; 7 dias |
| TCE-SP, prestação de contas de repasses ao Terceiro Setor julgadas irregulares: cerca de 4.100 pessoas | VII, a (parcerias fiscalizadas pelo TCE-SP) | Nome + dígito verificador do CPF | Trânsito em julgado nos últimos 8 anos | Mensal; 45 dias |

As listas do TCU acrescentam cerca de 22.700 CPFs que não estão no CEIS/CNEP, e o TCE-SP cobre exatamente o art. 39, VII, a para as parcerias paulistas, que são o público do projeto.
Endereços, formatos e papel de cada lista no capítulo 17.

Regra de correspondência (protótipo em `fase0/dirigentes/casar_dirigentes.py`):

1. Só entram sócios do QSA com CPF mascarado de 6 dígitos (pessoa física); o nome é normalizado (maiúsculas, sem acento, só letras e espaços simples).
2. CEIS, CNEP e as duas listas do TCU trazem o CPF completo: há correspondência quando o nome normalizado e os 6 dígitos do meio são iguais aos do QSA.
3. O TCE-SP publica o CPF como `999.XXX.XXX-99`, máscara complementar à do QSA (`***999999**`): há correspondência quando o nome normalizado é igual e o dígito verificador calculado com os 3 primeiros dígitos do TCE-SP e os 6 do QSA é igual aos 2 últimos do TCE-SP.
   Um homônimo passa por acaso com chance de cerca de 1 em 100.
4. Correspondência só por nome (6 dígitos ou DV diferentes) nunca gera achado; aparece só como contagem de homônimos, sem alerta.
5. Quando o processo do TCU em que o dirigente foi condenado também condenou a própria OSC, o texto diz isso, porque reforça que a pessoa é a mesma.
6. Qualificação e data de entrada no QSA aparecem no resultado, mas não mudam o achado: a lei olha quem é dirigente hoje.

[ORIENTADOR Q22] Regra provisória sobre o que conta como possível impedimento:

- CEIS e CNEP: só sanção vigente na data de referência.
- Categorias de pessoa física do CEIS que não são hipótese do art. 39 (Demissão, Suspensão de servidor) aparecem como informação, sem ALERTA.
- TCU contas irregulares e TCE-SP: só trânsito em julgado nos últimos 8 anos; achado mais antigo aparece como informação, sem ALERTA.
- TCU inabilitados: só inabilitação vigente.
- Correspondência só por nome nunca gera achado; fica registrada como informação.

CPF reconstituído (risco aceito com a opção C): juntar a máscara do TCE-SP e a do QSA reconstitui o CPF completo, o que é tratamento de dado pessoal mesmo sem gravar.
Esse CPF só existe em memória, durante o cálculo do dígito verificador, e o motor guarda apenas o resultado booleano.
Ele nunca é persistido (banco, arquivo, cache ou evidência), logado nem exibido, e um teste automatizado garante isso (`arquitetura.md` T13).
O CPF completo das listas do TCU e do CEIS/CNEP segue a política B13: o banco guarda só o nome normalizado, os 6 dígitos do meio e os 2 finais.

Base vencida: cada lista tem a sua idade máxima (Q6); lista vencida não é consultada e o texto da verificação diz qual faltou.
Se todas as listas estiverem vencidas, `dirigentes` fica INDISPONIVEL, com o aviso em destaque (Q5), sem mudar o status.

Limites a comunicar no relatório (bloco B9, cap. 2.7):

- O QSA de associações costuma trazer só o presidente (23 de 25 no teste de `fase0/dirigentes/ficha.md`); dirigentes fora do QSA não são verificados.
- Contas julgadas por outros tribunais de contas (TCEs fora de SP, TCM-SP e TCM-RJ) não têm base agregada e não são verificadas.
- Condenação por improbidade só com suspensão de direitos políticos está só no CNIA, que exige CPF completo; o MVP vê apenas a que chega ao CEIS.
- Art. 39, inciso III e § 2º não têm fonte pública.

Fica para o pós-MVP (opção D do Q8, junto com a LGPD, D9): CPF completo dos dirigentes informado pelo usuário, com casamento por CPF exato e consulta ao CNIA por CPF, e o levantamento dos demais tribunais de contas.

Casos de referência: C36 e C39 (CEIS, origem CNJ), C40 e C42 (TCU contas irregulares; em C42 todos os processos também condenaram a própria OSC), C41, C44 e C46 (TCE-SP, nome + DV); C28 e C36 têm achado no TCU só fora da janela de 8 anos (informação, sem ALERTA).
Nenhum caso do conjunto aparece na lista de inabilitados do TCU.

## 13.4 Por que continua sendo só ALERTA

Mesmo com nome e 6 dígitos do CPF, a correspondência não é prova de identidade.
Reprovar uma OSC por um falso positivo sobre o presidente seria grave.
O sistema apenas sinaliza "possível correspondência" e mostra o que encontrou para conferência humana.

## 13.5 Retorno esperado

| **CONFORME (passa)** | **NÃO CONFORME (falha)** |
|---|---|
| Nenhum dirigente do QSA com correspondência dentro da janela nas cinco listas (CEIS, CNEP, TCU contas irregulares, TCU inabilitados e TCE-SP Terceiro Setor). Estado: OK, com a lista do que foi verificado e do que não foi. Achado fora da janela (sanção expirada, trânsito em julgado há mais de 8 anos, inabilitação encerrada) aparece como informação, sem mudar o estado. | Correspondência por nome e 6 dígitos do meio do CPF (no TCE-SP, nome e dígito verificador), com sanção vigente ou trânsito em julgado nos últimos 8 anos, em hipótese do art. 39. Estado: ALERTA "Possível correspondência: [qualificação] [nome] aparece em [fonte] (art. 39, VII, [alínea]; processo [n], [datas]); confira o CPF no documento oficial". Na lista de contas irregulares do TCU o texto acrescenta "a lista não informa se a conta é de parceria, confira o acórdão" e, quando for o caso, que o processo também condenou a própria OSC. Nunca INAPTA. |

QSA sem pessoa física (B22): quando o QSA está vazio ou só tem pessoas jurídicas, o estado é NAO_VERIFICADO com a mensagem "o cadastro não informa dirigentes pessoas físicas"; não é OK, porque nada foi verificado.

> **LGPD (adiada, D9) e o que o MVP já faz**
>
> Nomes e CPFs de dirigentes são dados pessoais.
> O tratamento completo de LGPD (retenção, base legal, direitos do titular) fica para depois da aprovação do projeto (F5).
> Mesmo no MVP: o link permanente da consulta é aberto, mas os nomes de dirigentes com possível correspondência só aparecem para o operador autenticado por token; o público vê "possível correspondência em 1 dirigente; consulte o operador" (Q9).
> As amostras versionadas mascaram o CPF, o arquivo bruto completo fica fora do versionamento, e o banco guarda das pessoas físicas só o nome normalizado e os 6 dígitos do meio (B13, `arquitetura.md` T8c).
> O CPF reconstituído com o TCE-SP nunca sai da memória do processo (cap. 13.3).

# 14. Verificação 11 - Mapa das OSCs (Ipea)

## 14.1 O que é

Plataforma do Instituto de Pesquisa Econômica Aplicada criada em 2016 e prevista no Decreto nº 8.726/2016 (que regulamenta o MROSC).
O Ipea cadastra automaticamente as OSCs a partir dos CNPJs ativos, e a própria organização pode completar o perfil com projetos, parcerias, governança, fontes de recursos e certificações.

## 14.2 Por que precisamos

Não é requisito legal, mas é um bom indicador de transparência: uma OSC com perfil completo e parcerias registradas tem histórico demonstrável.
Também confirma que o próprio Ipea reconhece aquele CNPJ como OSC, o que funciona como segunda opinião para a verificação de natureza jurídica.

## 14.3 Retorno esperado (informativo)

| Situação | Estado | `situacao` (Q40) | Efeito |
|---|---|---|---|
| CNPJ presente com perfil preenchido pela OSC (algum valor não vazio com `ft_* == "Representante de OSC"` ou `bo_oficial == false`) | OK | `PREENCHIDO` | Relatório mostra o perfil e o índice de preenchimento. |
| CNPJ presente só com dados automáticos | OK | `AUTOMATICO` | Relatório sugere à OSC completar o perfil. |
| CNPJ ausente do Mapa (lista vazia ou sem igualdade exata) | ALERTA | `AUSENTE` | Leva o status final a APTA COM RESSALVAS (D2). O relatório explica que a ausência pode indicar divergência de classificação e pede conferir a natureza. |
| Fonte inacessível, erro ou formato inesperado | INDISPONIVEL | - | Não afeta o status final (é informativa), mas aparece no aviso em destaque (Q5). |

Seções consultadas (Q38): `busca/cnpj`, `osc/dados_gerais`, `osc/descricao`, `osc/areas_atuacao_rep` e `osc/indice_preenchimento`, ou seja, 5 chamadas, cerca de 5 s com 1 s de intervalo.
São as seções que decidem "preenchido pela OSC"; o perfil completo (16 chamadas, cerca de 25 s) não muda o estado.
Os certificados (`osc/certificados`) entram só como contexto do CEBAS, se couberem no orçamento de tempo.
Quando a entrada é filial, o Mapa é consultado pela matriz (Q28).

Casos reais da Fase 0: Open Knowledge Brasil presente só com dados automáticos (índice 18,75); Fundação Abrinq com perfil preenchido pela OSC; Petrobras ausente (controle negativo).

# 15. Verificação 12 - CEBAS (resumo)

## 15.1 O que é

Certificação de Entidades Beneficentes de Assistência Social, concedida pelo Ministério da Saúde, pelo Ministério da Educação ou pelo Ministério do Desenvolvimento e Assistência Social, conforme a área predominante da entidade.
Dá acesso à imunidade de contribuições para a seguridade social.
O capítulo 22 detalha a fonte, porque ela é o gargalo do projeto.

## 15.2 Por que precisamos

Não é requisito do MROSC, mas é o título mais relevante do terceiro setor: indica que a entidade passou por análise ministerial rigorosa e é critério de preferência ou pontuação em vários editais.

## 15.3 Retorno esperado (informativo)

A mensagem sempre cita a fonte e a data de corte (ex.: "segundo SisCEBAS Saúde em 30/09/2026" ou "segundo planilha MDS de 24/10/2024 e DOU até DD/MM/AAAA") (D16).
O CEBAS é consultado pela matriz e pelo estabelecimento informado (Q28), e vale o resultado mais informativo.
O `estado` serve só para a agregação; a página usa o rótulo da coluna `situacao` (Q40), para "CEBAS não vigente" não aparecer como "OK".

| Situação | Estado | `situacao` (Q40) | Texto no relatório |
|---|---|---|---|
| Última decisão encontrada é concessão, renovação ou prorrogação deferida e dentro da validade | OK | `ATIVO` | "CEBAS ativo (área X) até DD/MM/AAAA, segundo [fonte] em DD/MM/AAAA" |
| Validade vencida sem ato novo [ORIENTADOR Q24] | OK | `EM_RENOVACAO` | "Vigência vencida em DD/MM/AAAA, há N anos e M meses; o requerimento tempestivo mantém a validade até a decisão; possível renovação em análise; confirme com o ministério" (não é o mesmo que "sem CEBAS") |
| Última decisão é indeferimento ou cancelamento | OK | `NAO_VIGENTE` | "CEBAS não vigente: último ato foi [indeferimento/cancelamento] em DD/MM/AAAA" |
| Pedido em análise sem decisão publicada (Q31) | NAO_VERIFICADO | `PEDIDO_EM_ANALISE` | "Há pedido em análise sem decisão publicada" |
| Nenhuma decisão encontrada | NAO_VERIFICADO | `NAO_ENCONTRADO` | "Não foi encontrada certificação CEBAS nas bases consultadas" (não é o mesmo que "não possui") |
| Fonte inacessível ou base vencida | INDISPONIVEL | - | "Não foi possível consultar", no aviso em destaque (Q5) |

[ORIENTADOR Q24] Regra provisória: "possível renovação em análise" vale sem limite de tempo, porque a LC 187/2021 mantém a validade até a decisão sem prazo e a verificação é informativa; a idade da vigência vencida aparece sempre no texto.
A alternativa em análise é limitar a N anos (ex.: 3, uma validade) e depois disso dizer "situação desconhecida".

O relatório traz o bloco fixo "Sobre o CEBAS" do capítulo 22.7 (B7).

# 16. O que fica fora do MVP (e por quê)

Para o relatório ser honesto, é importante listar o que o MROSC exige e o sistema ainda não verifica.

| Exigência | Fonte possível | Motivo para ficar fora agora |
|---|---|---|
| CND federal (Receita/PGFN) | API Consulta CND no Conecta gov.br | API de uso governamental, sem acesso gratuito para o público. |
| CRF do FGTS (Caixa) | Site da Caixa | Site com CAPTCHA e bloqueio de IP de datacenter. Não burlamos CAPTCHA. |
| CNDT (TST) | Site do TST | Idem. |
| Certidões estaduais e municipais | Um site por ente | Milhares de fontes diferentes. |
| Estatuto, ata de eleição, prestação de contas | Documentos da própria OSC | Não estão em base pública; exigem upload e análise humana. |
| Consultas para CNPJ alfanumérico (D4) | As mesmas fontes | O DV aceita o formato, mas as fontes recebem só CNPJ numérico no MVP. Mapa das OSCs e CNIA não suportam o formato; só o OpenCNPJ já tem dado real. Resultado: NAO_VERIFICADO com mensagem explicativa e status INCONCLUSIVA (Q2). |
| Art. 39, III: dirigente que é membro de Poder, do Ministério Público ou dirigente de órgão da administração do ente parceiro | Folhas e cadastros de cada ente | Não existe base pública agregada que cruze o QSA com os agentes de cada ente. |
| Art. 39, § 2º: ressarcimento do dano, que afasta o impedimento | Processos de cada tribunal | Nenhuma lista informa se o dano foi ressarcido; a lista do TCU para fins eleitorais (com débito) é só indício. |
| Sanções estaduais e municipais fora do CEIS | Cadastros próprios de cada ente | Só aparecem quando o ente alimenta o CEIS. |
| Contas julgadas por tribunais de contas fora do TCU e do TCE-SP | Um site por TCE e TCM | Não há base agregada nacional; cada tribunal publica em formato próprio. O TCE-SP (Terceiro Setor) já entra em `dirigentes` (Q8); os demais ficam para o pós-MVP, uma ficha por tribunal. |
| CNIA por CPF (improbidade só com suspensão de direitos políticos) e CPF completo dos dirigentes | CNJ e a própria OSC | Exige CPF completo informado pelo usuário, o que depende da LGPD (D9); opção D do Q8, pós-MVP. |
| Página de detalhe do CNIA (penas e prazos) | CNJ | O motor usa as datas do CEIS de origem CNJ (Q19); a consulta ao detalhe fica para depois do MVP. |
| Tratamento completo de LGPD (D9) | - | Adiado para depois da aprovação do projeto (retenção, base legal, direitos do titular); o MVP já restringe nomes de dirigentes ao operador (Q9). |
| Score de qualidade (D8) | - | Volta quando houver casos reais para calibrar. |

Essas lacunas também aparecem para o usuário no bloco fixo "O que este relatório não verifica" (cap. 2.7, B9).


Uma evolução natural para depois do MVP é permitir que a OSC anexe essas certidões e o sistema apenas registre validade e data, compondo um dossiê completo.

---

# PARTE III - Fontes de dados: o que é cada uma e como foi testada

# 17. Visão geral das fontes

Todas as fontes abaixo foram testadas em 30/09/2026 e 01/10/2026 (horário de Brasília), a partir de conexão residencial, com o User-Agent `validador-osc-ifsp/0.1 (projeto academico de extensao)` e pausa entre requisições.
Nenhum bloqueio, CAPTCHA ou HTTP 429 foi encontrado nos caminhos escolhidos.
Em 01/10/2026 os 49 casos de referência foram consultados de novo em OpenCNPJ, OpenCNPJ `?datasets=`, TCU e Mapa (`fase0/casos/`), e a API do Portal com chave foi testada (roteiro 19.4).

| Fonte | Verificações atendidas (id) | Papel no MVP | Tipo | Autenticação | Selo |
|---|---|---|---|---|---|
| Cálculo local (`validador_osc/cnpj.py`) | `dv` | Único | Código | - | EXECUTADO |
| OpenCNPJ | `situacao`, `estabelecimento`, `natureza`, `cnae`, `religiosa`, `tempo`, `dirigentes` (QSA) | Principal cadastral (D17) | API comunitária sobre dados abertos da Receita | Nenhuma | EXECUTADO |
| BrasilAPI (proxy da Minha Receita) | as mesmas do OpenCNPJ | Fallback cadastral (D17) | API comunitária sobre dados abertos da Receita | Nenhuma | EXECUTADO |
| CGU, CSV diário de CEPIM, CEIS e CNEP | `cepim`, `ceis`, `cnep`, `dirigentes` (pessoas físicas) | Observação principal, base local (D14) | Arquivo oficial | Nenhuma | EXECUTADO |
| OpenCNPJ `?datasets=cepim,ceis,cnep` | `cepim`, `ceis`, `cnep` | Observação adicional, na mesma chamada do cadastro (Q36) | Dados da CGU anexados pela API comunitária | Nenhuma | EXECUTADO (registros com datas nos 49 casos; campos no 18A.3) |
| TCU Consulta Consolidada | `tcu_inidoneos`, `cnj_cnia`, e `ceis`, `cnep` | Principal de `cnj_cnia`; observação de `tcu_inidoneos`, `ceis` e `cnep` (D13) | API oficial JSON documentada | Nenhuma | EXECUTADO |
| TCU Plataforma de Certidões, lista de inidôneos (CSV) | `tcu_inidoneos` | Segunda observação, base local diária (Q34) | API oficial JSON e CSV | Nenhuma | EXECUTADO |
| TCU Plataforma de Certidões, lista de responsáveis com contas julgadas irregulares (`POST https://certidoes.apps.tcu.gov.br/api/publico/responsaveis-contas-irregulares`, corpo `{}`; JSON de 24 MB ou CSV de 11 MB) | `tcu_contas_irregulares` (CNPJ), `dirigentes` (CPF, trânsito em julgado nos últimos 8 anos) | Base local diária, idade máxima de 7 dias (Q6) [ORIENTADOR Q21] (D15, Q8) | API oficial JSON e CSV | Nenhuma | EXECUTADO (`fase0/dirigentes/ficha.md`) |
| TCU Plataforma de Certidões, lista de inabilitados para cargo em comissão ou função de confiança (`POST https://certidoes.apps.tcu.gov.br/api/publico/responsaveis-inabilitados`, corpo `{}`; JSON de 0,4 MB) | `dirigentes` (CPF, inabilitação vigente) | Base local diária, idade máxima de 7 dias (Q6) (D15, Q8) | API oficial JSON e CSV | Nenhuma | EXECUTADO (`fase0/dirigentes/ficha.md`) |
| TCE-SP, relação de responsáveis por contas de repasses ao Terceiro Setor julgadas irregulares (xlsx mensal de 0,6 MB, link descoberto na página https://www.tce.sp.gov.br/relacao-de-responsaveis-por-contas-julgadas-irregulares) | `dirigentes` (nome + dígito verificador, trânsito em julgado nos últimos 8 anos) | Base local mensal, idade máxima de 45 dias (Q6) (D15, Q8) | Arquivo oficial XLSX, CPF publicado como `999.XXX.XXX-99` | Nenhuma | EXECUTADO (`fase0/dirigentes/ficha.md`) |
| Portal da Transparência, API de dados | nenhuma | Ferramenta manual de conferência, fora do motor e da configuração (D14) | API oficial REST/JSON | Chave vinculada a CPF | EXECUTADO com chave em 01/10/2026 (roteiro 19.4) |
| Mapa das OSCs (Ipea) | `mapa_osc`, e apoio a `natureza` e `cebas` | Único | API REST pública do Ipea | Nenhuma | EXECUTADO |
| SisCEBAS Saúde, lista de situação atual | `cebas` (saúde) | Principal da saúde, base local diária (D16) | Arquivo oficial XLS gerado na hora | Nenhuma | EXECUTADO |
| Planilhas oficiais CEBAS MDS e MEC (via Mapa das OSCs) | `cebas` (assistência social e educação) | Base histórica, carga única (D16) | Arquivo oficial XLSX (retrato 2024/2023) | Nenhuma | EXECUTADO |
| DOU (XML mensal e busca do portal da Imprensa Nacional) | `cebas` | Atos posteriores ao corte das planilhas; evidência na saúde (D16, Q39) | Dados abertos e JSON embutido no HTML | Nenhuma | EXECUTADO (jun a ago/2026; carga desde 12/2023 pendente, X17) |
| Consulta pública CEBAS do MEC (`siscebas2.mec.gov.br`) | 12 (educação) | Desconhecido | - | A DESCOBRIR (sem DNS em 30/09/2026, P5) |
| Pedidos LAI do CEBAS | 12 (medição de cobertura) | Pedido de acesso à informação | Cadastro no Fala.BR | Adiado para depois do MVP (D12) |

Custo total do MVP: zero.
Todas as fontes são públicas e gratuitas; o que se paga é tempo de integração e manutenção.

# 18. Fonte: BrasilAPI e Minha Receita (dados cadastrais)

| Item | Definição |
|---|---|
| Selo | EXECUTADO em 30/09/2026 (roteiro T1 a T7 e casos extras; ficha em `fase0/brasilapi/ficha.md`). |
| Papel no MVP | Fallback da fonte cadastral (D17). Fonte principal é o OpenCNPJ (capítulo 18A). |
| Serve para | Verificações `situacao`, `estabelecimento`, `natureza`, `cnae`, `religiosa`, `tempo` e o QSA de `dirigentes`. |
| Endpoint | `GET https://brasilapi.com.br/api/cnpj/v1/{cnpj}` (14 caracteres, sem pontuação; a barra da máscara quebraria a rota). |
| Autenticação | Nenhuma. |
| Origem dos dados | A BrasilAPI é um proxy da Minha Receita (`GET https://minhareceita.org/{cnpj}`) com cache na Vercel, atrás do Cloudflare. Schema e valores são idênticos. Espelho da Minha Receita: `2026-09` (`GET https://minhareceita.org/updated`). |
| Limites | Nenhum header de rate limit e nenhum 429 em 20 chamadas seguidas. O problema real é capacidade: quando a Minha Receita cai, toda consulta sem cache falha com HTTP 500 ou 504 depois de cerca de 10 s; o 504 vem com `retry-after: 120`. |
| Latência | Com cache: média 38 ms. Sem cache, com a Minha Receita no ar: 0,5 a 10 s. Sem cache, com a Minha Receita fora: 100% de falha (média 11,7 s). |
| Depois do MVP | Importar no Postgres o dump dos dados abertos do CNPJ (da Receita ou o publicado pelo OpenCNPJ), o que elimina a dependência de terceiros; fica para o projeto pós-MVP (D17). |

## 18.1 Uso como fallback

O motor chama a BrasilAPI quando o OpenCNPJ falha ou devolve 404 (Q26): o 404 pode ser espelho desatualizado, e uma segunda base aumenta a confiança antes de concluir "não encontrado".

- Timeout do cliente em torno de 12 s, dentro do orçamento de tempo da fase cadastral (`arquitetura.md` T6a, B10).
- Quando o cadastro vem da BrasilAPI não há `?datasets=`: CEPIM, CEIS e CNEP dependem do CSV local e do TCU.
- Fallback acionado em 5xx e timeout, não só em 429.
- Sem retry imediato em 5xx; respeitar o `retry-after`.
- A Minha Receita não é chamada como fallback independente: ela e a BrasilAPI caem juntas.
- Vantagem do fallback: o cache da BrasilAPI cobre CNPJs consultados recentemente por qualquer usuário, e os códigos numéricos servem para conferir o mapeamento do OpenCNPJ.

## 18.2 Campos e tipos reais

| Campo | Tipo real | Verificação | Observação |
|---|---|---|---|
| cnpj | string | - | 14 caracteres, sem máscara. Conferir que é igual ao consultado. |
| razao_social / nome_fantasia | string | - | `nome_fantasia` vem "" quando vazio. |
| situacao_cadastral | int | 2 | 2 ATIVA e 8 BAIXADA confirmados. |
| descricao_situacao_cadastral | string | 2 | Maiúsculas ("ATIVA", "BAIXADA"). |
| data_situacao_cadastral | string AAAA-MM-DD | 2 | - |
| motivo_situacao_cadastral / descricao_motivo_situacao_cadastral | int / string | 2 | 0 = "SEM MOTIVO". Descrição sem acentos. |
| identificador_matriz_filial | int | 2 | 1 matriz, 2 filial. Há também `descricao_identificador_matriz_filial`. |
| codigo_natureza_juridica | int | 3 | 3999, 3220, 2143, 2038 (sem hífen). |
| natureza_juridica | string | 3 | Só a descrição. |
| cnae_fiscal / cnae_fiscal_descricao | int / string | 4 | **Perde o zero à esquerda** (`220903`). Normalizar com `str(x).zfill(7)`. |
| cnaes_secundarios | list[{codigo: int, descricao}] | 4 | Vem `[]` quando não há secundários. O "código 0" citado na versão 1.0 não foi observado, mas o normalizador deve tolerar. |
| data_inicio_atividade | string AAAA-MM-DD | 5 | Na filial é a data da própria filial. |
| qsa | list[dict] | 10 | `nome_socio`, `qualificacao_socio`, `codigo_qualificacao_socio`, `data_entrada_sociedade`, `cnpj_cpf_do_socio` mascarado (`***112108**`), `identificador_de_socio` (2 = pessoa física), `faixa_etaria`. Igual entre filial e matriz. |
| regime_tributario | list[{ano, forma_de_tributacao, ...}] | contexto | "ISENTO DO IRPJ", "IMUNE DE IRPJ". Só na matriz; `[]` nas filiais e em entidades novas. Sinal fraco, só contexto. |
| email | string ou null | - | Vem null mesmo quando o OpenCNPJ traz e-mail. |

Trecho da resposta real para 19.131.243/0001-97 (campos selecionados; resposta completa em `fase0/brasilapi/respostas/brasilapi_T1_19131243000197.json`):

```
{
  "cnpj": "19131243000197",
  "razao_social": "OPEN KNOWLEDGE BRASIL",
  "situacao_cadastral": 2,
  "descricao_situacao_cadastral": "ATIVA",
  "identificador_matriz_filial": 1,
  "codigo_natureza_juridica": 3999,
  "natureza_juridica": "Associação Privada",
  "cnae_fiscal": 9430800,
  "data_inicio_atividade": "2013-10-03"
}
```

Interpretação pelo motor: ATIVA (`situacao` OK); natureza 3999 (`natureza` OK); CNAE 94.30-8 em ALTA (`cnae` OK, `religiosa` não se aplica); início em 2013, mais de 3 anos (`tempo` OK para todas as esferas).

## 18.3 Roteiro de teste executado [EXECUTADO]

| Caso | CNPJ | BrasilAPI | Minha Receita | OpenCNPJ |
|---|---|---|---|---|
| T1 OSC regular | 19131243000197 | 200, nat 3999, sit 2 | 200, igual | 200, "Associação Privada", "Ativa" |
| T2 natureza não elegível | 00000000000191 | 200, nat 2038 | 200, igual | 200, "Sociedade de Economia Mista" |
| T3 inexistente com DV válido | 94580730000152 | só 5xx | só 5xx | 404 `{"error": "not found"}` |
| T3b DV inválido | 19131243000198 | 400 "CNPJ ... inválido." | 400 | 404 (não valida DV) |
| T4 situação não ativa | 08942107000160 | 200, sit 8 desde 2012-01-04, motivo 1 | 200, igual | 200, "Baixada" |
| T5 alfanumérico fictício | 12ABC34501DE35 | 404 | 404 | 404 |
| T5r alfanumérico real | 00000000E08G12 | só 5xx | só 5xx | 200, filial do Banco do Brasil |
| T6 latência | 20 seguidas | média 38 ms (cache); sem cache 100% de falha | 2 de 5 com 503 | média 32 ms, nenhuma falha |
| T7 filial | 62779145000270 | 200, mf 2 | 200, mf 2 | 200, "Filial" |

Cuidados descobertos:

- Das 6 primeiras raízes aleatórias com ordem 0001, 5 existiam; um CNPJ "inexistente" gerado para teste precisa ser conferido antes de virar caso de regressão.
- Cache da BrasilAPI de até 16 h (header `age`): o dado pode estar um dia mais velho que o espelho.
- Falhas arquivadas na janela de 2 h: 67 na BrasilAPI e 77 na Minha Receita, todas em cerca de 10,2 s; nenhuma no OpenCNPJ.

> **Pendências**
>
> T3 e T5r ficaram sem resposta definitiva na BrasilAPI e na Minha Receita; rodar `fase0/brasilapi/retentar_pendentes.sh` quando a Minha Receita voltar.
> Repetir o T6b em outro horário para saber se a instabilidade da Minha Receita é crônica.
> Associação INAPTA (situação 4) e SUSPENSA (situação 3) foram encontradas em 01/10/2026 (C09 e C10 de `fase0/casos_referencia.md`); falta só um exemplo de situação NULA.

# 18A. Fonte: OpenCNPJ (dados cadastrais e sanções do Portal)

| Item | Definição |
|---|---|
| Selo | EXECUTADO em 30/09/2026 (mesmo roteiro do capítulo 18; ficha em `fase0/brasilapi/ficha.md`, seção "Ficha 3"). |
| Papel no MVP | Fonte cadastral principal (D17). Com `?datasets=`, observação adicional de CEPIM, CEIS e CNEP, na mesma chamada (D14, Q36). |
| Serve para | Verificações `situacao`, `estabelecimento`, `natureza` (com mapeamento), `cnae`, `religiosa`, `tempo`, o QSA de `dirigentes` e, com `?datasets=`, `cepim`, `ceis` e `cnep`. |
| Endpoint | `GET https://api.opencnpj.org/{cnpj}`. Aceita CNPJ com ou sem máscara. Parâmetro opcional `?datasets=ceis,cepim,cnep,acordos_leniencia,...`. |
| Autenticação | Nenhuma. |
| Origem dos dados | Pipeline próprio a partir dos dados abertos da Receita (NDJSON + índice servidos por Cloudflare Worker), independente da Minha Receita. `GET https://api.opencnpj.org/info` informa `last_updated: 2026-09-15T00:54:41Z`, 73.354.529 registros e os datasets do Portal da Transparência atualizados diariamente. |
| Limites | Nenhum header de rate limit e nenhum 429. Nenhum limite documentado no README do projeto. |
| Latência | Mediana 74 ms nas respostas definitivas; 200 a 480 ms sem cache. 100% das chamadas responderam. |
| Alfanumérico | Já tem dado real: 00.000.000/E08G-12 devolveu 200. No MVP não é consultado (D4). |
| Depois do MVP | O OpenCNPJ publica o próprio dump (`zip_url` no `/info`, cerca de 14 GB), que pode simplificar a importação no Postgres. |

## 18A.1 Campos reais e conversão para o modelo interno

O formato é bem diferente do da BrasilAPI: tudo é string, situação e matriz/filial vêm em texto e não existe código de natureza jurídica.

| Campo OpenCNPJ | Tipo real | Exemplo | Conversão |
|---|---|---|---|
| situacao_cadastral | string | "Ativa", "Baixada" | Texto para código numérico (2, 8 etc.). |
| motivo_situacao_cadastral | dict {codigo: string, descricao} | {"codigo": "01", ...} | `codigo` para inteiro. |
| matriz_filial | string | "Matriz", "Filial" | Para 1 / 2. |
| natureza_juridica | string | "Associação Privada" | Descrição para código pela tabela oficial da Receita; desconhecida = ALERTA. |
| cnae_principal | string de 7 dígitos | "0220903" | Já vem com o zero à esquerda. |
| cnaes_secundarios | list[string] | ["9493600"] | Direto. Há também `cnaes` com código, descrição e `is_principal`. |
| data_inicio_atividade | string AAAA-MM-DD | "2026-02-03" | Direto. |
| QSA (maiúsculo) | list[dict] | `cnpj_cpf_socio` "***112108**", `identificador_socio` "Pessoa Física", `qualificacao_socio` "Presidente" | Renomear campos; não traz o código numérico da qualificação. |
| capital_social | string com vírgula | "0,00" | Para número. |
| datas opcionais | string | "" | "" para null. |
| regime_tributario | ausente | - | Só disponível pela BrasilAPI. |

Modelo interno (independente da fonte, D17; tipo `Cadastro` em `arquitetura.md` T4): `cnpj`, `razao_social`, `situacao_codigo`, `situacao_descricao`, `situacao_data`, `motivo_codigo`, `motivo_descricao`, `matriz` (bool), `natureza_codigo`, `natureza_descricao`, `cnae_principal` (string 7), `cnaes_secundarios` (list de string 7), `data_inicio_atividade`, `qsa` (nome, qualificacao, data_entrada, documento_mascarado), `fonte`, `data_espelho`.

## 18A.2 Cuidados

- Não valida DV: DV errado volta 404, indistinguível de CNPJ inexistente. O motor valida o DV antes (capítulo 4).
- Formato inválido (ex.: `/status`) volta 400 `{"error": "invalid cnpj"}`.
- O espelho é de 15/09/2026; uma mudança de situação posterior a essa data não aparece. Espelho com mais de 60 dias gera ALERTA em `situacao` (Q6, cap. 5.4).
- Registros de sanção duplicados no `?datasets=` (CNEP do IPCIM, CEIS da IDEAS) com códigos diferentes e mesmo conteúdo: o normalizador agrupa (Q32).

## 18A.3 Sanções via `?datasets=`

Com `?datasets=ceis,cepim,cnep`, a resposta traz essas chaves, com `null` quando não há registro.
É uma observação adicional de CEPIM, CEIS e CNEP (D14), sem custo extra porque vem na chamada cadastral; ela cobre o CSV local vencido ou com falha de carga (Q36).
Estrutura confirmada com as respostas salvas dos 49 casos (`fase0/casos/respostas/<cnpj>/opencnpj_datasets.json`, coletadas em 01/10/2026):

```
ceis | cnep: { cnpj, updated_at, sancoes: [ {
    cadastro, codigo, tipo_pessoa, nome_sancionado, nome_informado_orgao,
    razao_social_receita, nome_fantasia_receita, numero_processo, categoria,
    valor_multa, data_inicio, data_final, data_publicacao, publicacao,
    detalhamento_publicacao, data_transito_julgado, abrangencia,
    orgao_sancionador, uf_orgao_sancionador, esfera_orgao_sancionador,
    fundamentacao_legal, data_origem_informacao, origem_informacoes, observacoes } ] }
cepim: { cnpj, updated_at, impedimentos: [ {
    nome_entidade, numero_convenio, orgao_concedente, motivo } ] }
```

- Os campos têm os mesmos nomes e valores das colunas do CSV da CGU; `codigo` é o "CÓDIGO DA SANÇÃO" do CSV e serve para casar as duas observações.
- Datas em DD/MM/AAAA; ausência de data final vem como `""`; `valor_multa` com vírgula decimal (`"223131,65"`, `"0,00"`).
- A busca é só pelo CNPJ exato: sanções de outro estabelecimento da raiz não aparecem (por isso a busca por raiz é feita no CSV local).
- `updated_at` foi 30/09/2026 21:15 UTC para CEIS e CNEP, o mesmo horário de publicação do CSV do dia: o dataset não é mais fresco que o CSV, só redundante.

# 19. Fonte: Portal da Transparência (CEPIM, CEIS, CNEP)

O Portal oferece dois caminhos: a API de dados (exige chave) e os arquivos diários de dados abertos (sem chave).
No MVP o CSV diário é a observação principal de CEPIM, CEIS e CNEP e a base da verificação de dirigentes (D14).
A API com chave foi testada em 01/10/2026 só para documentar os trade-offs: ela não entra no motor nem na configuração e fica como ferramenta manual de conferência, porque a chave é vinculada ao CPF de uma pessoa física e a API não traz dado mais recente nem campo que falte no CSV.
Ficha completa em `fase0/portal/ficha.md`.

## 19.1 API de dados

| Item | Definição |
|---|---|
| Selo | EXECUTADO: OpenAPI oficial baixado sem chave e erros em 30/09/2026; roteiro T1 a T8 com chave em 01/10/2026 (P2). |
| Serve para | Conferência manual de CEPIM, CEIS e CNEP. Não é chamada pelo motor. |
| Base URL | `https://api.portaldatransparencia.gov.br/api-de-dados` |
| Rotas | `/cepim`, `/ceis`, `/cnep` (e `/{id}` de cada uma). Também existe `/acordos-leniencia`. |
| Parâmetros | CEPIM: `cnpjSancionado`, `nomeSancionado`, `ufSancionado`, `orgaoEntidade`, `pagina` (obrigatório). CEIS e CNEP: `codigoSancionado` (CNPJ ou CPF), `nomeSancionado`, `orgaoSancionador`, `dataInicialSancao`, `dataFinalSancao` (DD/MM/AAAA), `pagina` (obrigatório). Todos string; não há parâmetro de tamanho de página. |
| Autenticação | Header `chave-api-dados`. |
| Como obter a chave | Em portaldatransparencia.gov.br/api-de-dados/cadastrar-email, com conta gov.br nível Prata ou Ouro, ou com verificação em duas etapas. A chave chega no e-mail da conta. |
| Limites | Não constam no OpenAPI. Página oficial: 400 requisições/min, 700/min de 00h a 06h; estourar suspende a chave. Nenhum 429 em 22 chamadas no teste. |
| Documentação | `GET https://api.portaldatransparencia.gov.br/v3/api-docs` responde sem chave (OpenAPI 3.0.1, 109 rotas). Versionado em `fase0/portal/portal-openapi.json`. |

## 19.2 Estrutura de retorno (do OpenAPI)

As respostas 200 são um array do DTO, sem envelope de paginação.

`CeisDTO` e `CnepDTO` têm a mesma estrutura; o CNEP acrescenta `valorMulta`:

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

- O CNPJ do sancionado vem aninhado e formatado (`pessoa.cnpjFormatado`, `pessoaJuridica.cnpjFormatado`, `sancionado.codigoFormatado`); normalizar para dígitos antes de comparar.
- A vigência vem de `dataFimSancao` (string, possivelmente vazia).
- O CEPIM não declara data de início nem de fim; só `dataReferencia`.

## 19.3 Regras de interpretação

| Retorno | Estado | Observação |
|---|---|---|
| HTTP 200 + [] | OK | Nada consta (confirmado com a chave, T1). |
| HTTP 200 + registros de outro CNPJ | OK | Filtro aproximado. Sempre comparar CNPJ normalizado. |
| HTTP 200 + registro do CNPJ, sanção vigente | RESTRICAO | Vigente = sem data de fim ou data de fim >= data de referência, decidido só pela data (D14). No CEPIM, qualquer registro é RESTRICAO. |
| HTTP 200 + registro do CNPJ, sanção expirada | OK + histórico | Mostrar no relatório como informação. |
| HTTP 401 | INDISPONIVEL | Sem chave: `{"Erro na API":"Chave de API não informada! ..."}`. Chave inválida: `{"Erro na API":"Chave de API inválida!"}`. Não cachear: o 401 volta com `cache-control: public, max-age=7200`. |
| HTTP 429 | retry | Esperar e tentar de novo com backoff; se persistir, INDISPONIVEL. |
| HTTP 5xx / timeout | INDISPONIVEL | Até 3 tentativas com backoff exponencial. |

## 19.4 Roteiro de teste [EXECUTADO em 01/10/2026]

Script `fase0/portal/testar_api_com_chave.py`; respostas brutas em `fase0/portal/respostas_api/` (verificado por script que nenhuma contém a chave).

| Teste | Resultado |
|---|---|
| T1 - Nada consta (19131243000197) | HTTP 200 com `[]` nas três rotas. |
| T2 - Positivo CEPIM | Bom Jesus do Tocantins: 1 registro; Santa Casa de Pacaembu: 2. Sem datas de impedimento. |
| T3 - Positivo CEIS e CNEP, vigente e expirado | Vigente, expirado e "vence em 22/11/2026" com 1 registro cada; CNEP de Pacaembu com 4. Datas em DD/MM/AAAA; ausência vem como texto "Sem informação". |
| T4 - Filtro exato ou por raiz | Busca só exata: a filial sancionada do Instituto Global volta 1 registro, a matriz volta 0, e a raiz de 8 dígitos volta 0. Não há busca por raiz na API. |
| T5 - CNPJ com e sem pontuação | Iguais. |
| T6 - Erros sem chave e com chave inválida | HTTP 401 (tabela 19.3). |
| T7 - Paginação | Até 15 registros por página; o IMDC (10 convênios) cabe na página 1. |
| T8 - Nome de dirigente | `nomeSancionado` faz busca parcial e ampla ("PLURAL" trouxe 7 registros, inclusive empresas sem relação) e levou até 7,3 s: não serve para casar dirigentes. |

Conclusão: a `dataReferencia` da API é a mesma do CSV diário (30/09/2026); a API não é mais fresca, não busca por raiz e depende de uma chave pessoal.
O CSV diário com busca local é superior para o motor (D14).

## 19.5 Arquivos diários de dados abertos [EXECUTADO]

| Item | Definição |
|---|---|
| URL e método | 1) `GET https://portaldatransparencia.gov.br/download-de-dados/<cadastro>` devolve HTML com a data mais recente no trecho `arquivos.push({...})`. 2) `GET https://portaldatransparencia.gov.br/download-de-dados/<cadastro>/AAAAMMDD` responde 302 para `https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/<cadastro>/AAAAMMDD_<CADASTRO>.zip`. `<cadastro>` em minúsculas (`cepim`, `ceis`, `cnep`). |
| Autenticação | Nenhuma e sem CAPTCHA nesses dois caminhos (o JavaScript estático do site tem WAF com CAPTCHA, mas não é necessário). |
| Formato | Zip com CSV em ISO-8859-1, separador `;`, campos entre aspas, CRLF. Datas DD/MM/AAAA; valores com vírgula decimal. |
| Tamanho em 30/09/2026 | CEPIM 28/09/2026: 3.526 linhas (1.941 CNPJs). CEIS 30/09/2026: 23.720 linhas. CNEP 30/09/2026: 1.819 linhas. Download dos três em poucos segundos. |
| Atualização | CEIS e CNEP diários; CEPIM com dois dias de defasagem no teste. Usar a data do nome do arquivo (o texto "Última atualização" da página está errado). |
| Scripts | `baixar_dados_abertos.py`, `analisar_dados_abertos.py`, `consultar_local.py` (consulta local por CNPJ/CPF, exata e por raiz) em `fase0/portal/`. |
| Papel no MVP | Observação principal de CEPIM, CEIS e CNEP desde a primeira fatia de sanções (D14); idade máxima de 3 dias para CEIS e CNEP e 7 dias para o CEPIM (Q6). |

Colunas:

- CEPIM (5): `CNPJ ENTIDADE`, `NOME ENTIDADE`, `NÚMERO CONVÊNIO`, `ÓRGÃO CONCEDENTE`, `MOTIVO DO IMPEDIMENTO`. Nenhuma data.
- CEIS (24): inclui `TIPO DE PESSOA` (F/J), `CPF OU CNPJ DO SANCIONADO`, `NOME DO SANCIONADO`, `CATEGORIA DA SANÇÃO`, `DATA INÍCIO SANÇÃO`, `DATA FINAL SANÇÃO`, `ABRAGÊNCIA DA SANÇÃO` (sic), `ÓRGÃO SANCIONADOR`, `ESFERA ÓRGÃO SANCIONADOR`, `FUNDAMENTAÇÃO LEGAL`.
- CNEP (25): as do CEIS mais `VALOR DA MULTA`.

Cuidados de qualidade do dado:

- A categoria não serve para vigência; só a data final (D14).
- Linhas repetidas com mesmos dados e códigos de sanção diferentes.
- 12 linhas em cada arquivo com `TIPO DE PESSOA` vazio e documento de 7, 9, 11 ou 14 dígitos; o parser não pode supor tamanho fixo.
- Não existe sanção registrada só com a raiz; todo documento de PJ tem 14 dígitos.
- O CPF de pessoa física vem completo (base da verificação `dirigentes`, D15). Por ser dado pessoal, as amostras versionadas mascaram o CPF, e o banco guarda só o nome normalizado e os 6 dígitos do meio (B13).
- Frente à API: a mesma data de referência (o teste de 01/10/2026 mostrou `dataReferencia` igual à do CSV), defasagem de alguns dias só no CEPIM, e menos campos (sem link da publicação, sem objeto do convênio).
- Uma sanção publicada depois da data do arquivo não aparece; o texto de cada verificação diz "consultado na base de DD/MM/AAAA" (B5), e o TCU cobre esse intervalo pela regra do Q35.

# 20. Fonte: TCU - Consulta Consolidada e Relação de Inidôneos

| Item | Definição |
|---|---|
| Selo | EXECUTADO em 30/09/2026 (ficha em `fase0/tcu/ficha.md`). |
| Serve para | Verificações `tcu_inidoneos` e `cnj_cnia` e, por D13, observação adicional de `ceis` e `cnep`. |
| Fonte principal | Consulta Consolidada de Pessoa Jurídica: `GET https://certidoes-apf.apps.tcu.gov.br/api/rest/publico/certidoes/{cnpj}?seEmitirPDF=false`. Documentada pelo TCU na página "Webservices TCU" (https://sites.tcu.gov.br/dados-abertos/webservices-tcu/). |
| Parâmetros | `{cnpj}` só com letras maiúsculas e dígitos, sem pontuação (a barra quebra o caminho). `seEmitirPDF=true` devolve o PDF da certidão em base64 em `certidaoPDF`. |
| Autenticação | Nenhuma. Bastou o User-Agent do projeto: sem cookies, Referer, token ou CAPTCHA. |
| Limites | Nenhum rate limit em cerca de 15 chamadas espaçadas de 2 s. Primeira consulta de um CNPJ: cerca de 5,5 s (o servidor consulta TCU, CNJ e CGU na hora). Repetição em poucos minutos: cerca de 0,04 s, com o mesmo `dataHoraGeracaoInMillis` (cache do servidor de pelo menos 3 minutos). Usar timeout de pelo menos 30 s. |
| Risco conhecido | Bloqueio de IP de datacenter ainda não testado; testar a partir do servidor do projeto quando houver. |

## 20.1 Estrutura da resposta (HTTP 200)

```json
{
  "certidaoPDF": null,
  "certidoes": [
    {
      "dataHoraEmissao": "30/09/2026 22:02",
      "descricao": "Licitantes Inidôneos",
      "emissor": "TCU",
      "linkConsultaManual": "https://certidoes.apps.tcu.gov.br/lista-inidoneos",
      "observacao": null,
      "situacao": "NADA_CONSTA",
      "tempoGeracao": 16,
      "tipo": "Inidôneos"
    }
  ],
  "cnpj": "19.131.243/0001-97",
  "dataHoraGeracaoInMillis": 1790816539692,
  "nomeFantasia": null,
  "razaoSocial": "OPEN KNOWLEDGE FOUNDATION BRASIL",
  "seCnpjEncontradoNaBaseTcu": true,
  "uf": null
}
```

A lista `certidoes` traz sempre quatro itens, identificados por `tipo`: `Inidôneos` (TCU), `CNIA` (CNJ), `CEIS` e `CNEP` (Portal da Transparência).
A lista de tipos também vem de `GET /api/rest/publico/tipos-certidoes`.
`tempoGeracao` está em milissegundos.

## 20.2 Regras de interpretação

| `situacao` do item | Estado |
|---|---|
| `NADA_CONSTA` | OK para aquele cadastro, desde que a fonte cadastral tenha confirmado o CNPJ (Q33); `seCnpjEncontradoNaBaseTcu: false` com o cadastro confirmado é só informativo. |
| `CONSTAM_REGISTROS` em `Inidôneos` | RESTRICAO em `tcu_inidoneos`. Mostrar `observacao` (ex.: "Data da Decisão: 23/07/2025 - 024.778/2024-9 - 1610/2025-PL"). |
| `CONSTAM_REGISTROS` em `CNIA` | Regra do Q19 (cap. 12.3) em `cnj_cnia`: RESTRICAO com proibição vigente achada no CEIS pelo processo, senão ALERTA [ORIENTADOR Q19]. |
| `CONSTAM_REGISTROS` em `CEIS` ou `CNEP` | Não decide sozinho: a vigência vem das datas do CSV local e do OpenCNPJ (D18). Com todas as datas passadas, OK com histórico; sem registro nas outras fontes, regra do Q35 (cap. 10.5). |
| `SISTEMA_INDISPONIVEL` | INDISPONIVEL para aquele cadastro, com `linkConsultaManual`. |
| `ERRO` | INDISPONIVEL para aquele cadastro, com `linkConsultaManual`. |
| `ALFANUMERICO_NAO_SUPORTADO` | NAO_VERIFICADO para aquele cadastro (hoje só CNIA). |
| `CNPJ_NAO_ENCONTRADO_NO_TCU` | INDISPONIVEL. |
| qualquer outro | INDISPONIVEL, registrado para revisão. |

Regras adicionais:

- `seCnpjEncontradoNaBaseTcu: false` com tudo `NADA_CONSTA` é o retorno de CNPJ inexistente: não é restrição, mas impede concluir OK sem a fonte cadastral (D13).
- HTTP 412 com `{"violacoes":[{"mensagem":"Dígito verificador do CNPJ é inválido","tipo":"ALERTA"}]}`: CNPJ inválido, que o motor já barra na verificação `dv` (status CNPJ_INVALIDO).
- `SISTEMA_INDISPONIVEL` e `ERRO` não foram reproduzidos; só se sabe que existem pelo código do frontend.

Exemplos salvos em `fase0/tcu/respostas/`: OK (`apf_certidoes_19131243000197.json`), RESTRICAO (`apf_certidoes_28025673000115.json`, ALFATEC SERVICOS LTDA), inexistente (`apf_certidoes_98765432000198.json`), DV inválido (`apf_certidoes_19131243000198.json`), alfanumérico (`apf_certidoes_12ABC34501DE35.json`).

## 20.3 Fonte alternativa: Relação de Licitantes Inidôneos

A antiga aplicação Oracle APEX (`contas.tcu.gov.br/ords/f?p=1660:...`) foi desativada pelo TCU em 22/05/2026 e não é mais usada.
O fallback por scraping com Playwright previsto na versão 1.0 foi descartado (D13).
A substituta oficial é a Plataforma de Certidões:

| Item | Definição |
|---|---|
| Endpoint oficial | `POST https://certidoes.apps.tcu.gov.br/api/publico/responsaveis-inidoneos` com corpo JSON. `{}` devolve tudo; filtros `cnpj` (com ou sem pontuação), `cpf`, `nome`, `uf`, `municipio`. |
| Paginado | `POST .../api/publico/responsaveis-inidoneos-com-paginacao?paginaAtual=1&tamanhoPagina=50` |
| CSV da lista inteira | `POST .../api/publico/responsaveis-inidoneos/exportar-para-csv?paginaAtual=1&tamanhoPagina=50000` (cp1252, separador `|`, primeira linha `sep=|`, cerca de 35 KB). |
| Autenticação | Nenhuma; sem CAPTCHA nesses endpoints. |
| Retorno | Não encontrado = `[]`. Registro com `nome`, `numeroRegistro`, `numeroProcessoFormatado`, `numeroAcordaoFormatado`, `dataAcordao`, `dataTransitoEmJulgado`, `dataFinalSancao`, links do processo. A lista só traz sanções vigentes. |
| Uso no MVP | Baixar o CSV uma vez por dia e consultar localmente, como segunda observação de `tcu_inidoneos` (Q34), com idade máxima de 3 dias (Q6). Mantém a verificação respondendo se a Consulta Consolidada cair. |

A emissão de certidão individual em PDF na mesma plataforma usa CAPTCHA ALTCHA e não é chamada pelo projeto.

Decisão (Q34): a fonte alternativa é a Plataforma de Certidões, documentada pelo TCU.
A API ORDS `GET https://contas.tcu.gov.br/ords/condenacao/consulta/inidoneos`, achada na Ficha C de `fase0/portal/ficha.md` (91 registros, todos PJ), não é usada, porque o TCU não a documenta.
A diferença de contagem foi conferida em 01/10/2026 no CSV salvo: 129 linhas, 128 com CNPJ, 121 CNPJs distintos, nenhuma pessoa física e 4 linhas com data final já passada; o ORDS tinha 91 registros, todos com data final futura.
Parte da diferença vem de processos repetidos por CNPJ e de sanções que vencem no dia; o restante (121 contra 91 CNPJs) fica para conferir na implementação da carga (fatia 3), que registra as contagens e a explicação na ficha do TCU.

# 21. Fonte: Mapa das OSCs (Ipea)

| Item | Definição |
|---|---|
| Selo | EXECUTADO em 30/09/2026 (ficha em `fase0/mapa_osc/ficha.md`). |
| Serve para | Verificação `mapa_osc`, segunda opinião de `natureza` e indício histórico para `cebas`. |
| Tipo | API REST pública do Ipea, sem token, usada pelo próprio site. Swagger em https://mapaosc.ipea.gov.br/api/api/documentation (incompleto); rotas completas no código aberto https://github.com/Plataformas-Cidadania/mapa-osc-api (`routes/web.php`). |
| Prefixo | `https://mapaosc.ipea.gov.br/api/api/` (o `/api/api/` é duplo mesmo; o Swagger mostra caminhos sem o segundo `/api`, que dão 404). |
| Etapa 1 | `GET busca/cnpj/{cnpj}` devolve `id_osc`, `cd_identificador_osc`, razão social, natureza, `cd_situacao_cadastral`, município e UF. |
| Etapa 2 | `GET osc/{secao}/{id_osc}`: `cabecalho`, `dados_gerais`, `indice_preenchimento`, `areas_atuacao`, `areas_atuacao_rep`, `descricao`, `certificados`, `rel_trabalho_e_governanca`, `participacao_social`, `projetos`, `anos_recursos` e `recursos/{ano}`. |
| Autenticação | Nenhuma para leitura. CORS liberado, sem CAPTCHA. |
| Limites | Nenhum cabeçalho de rate limit. 0,05 a 0,6 s por chamada (um pico isolado de 15,9 s). Manter 1 s entre chamadas em sequência (Q37) e cache longo (base atualizada mensalmente). |
| Seções consultadas | 5 chamadas por consulta (Q38): `busca/cnpj`, `osc/dados_gerais`, `osc/descricao`, `osc/areas_atuacao_rep`, `osc/indice_preenchimento` (cap. 14.3). |
| API legada | A API em `:8383` descrita na wiki antiga não responde de fora e não é mais necessária. |

## 21.1 Cuidados descobertos

- **Busca por prefixo.** `busca/cnpj` faz `LIKE 'cnpj%'`; o resultado precisa ser filtrado por igualdade exata de `cd_identificador_osc` (comparando com `zfill(14)`).
- **CNPJ sem zeros à esquerda.** O banco guarda o CNPJ como NUMERIC, então a chamada vai sem os zeros iniciais.
- **Alfanumérico não suportado.** Pelo mesmo motivo, um CNPJ alfanumérico nunca será encontrado; no MVP ele nem é consultado (D4).
- **Erros com HTTP 200.** Não encontrado volta `[]`; `id_osc` inexistente volta `{}` ou mensagem de texto; o índice de preenchimento pode voltar erro PHP com 200. O adapter valida o formato e trata o inesperado como INDISPONIVEL.
- **Código de situação próprio.** O dicionário do Mapa usa 5 para Baixada, enquanto a Receita usa 8; não reaproveitar `cd_situacao_cadastral` do Mapa na verificação `situacao`.
- **Quem preencheu o dado.** Um dado conta como preenchido pela OSC quando o valor não é nulo nem vazio e (`ft_* == "Representante de OSC"` ou `bo_oficial == false`). `ft_*` com "Representante de OSC" e valor vazio é só o default do banco.
- **Índice de preenchimento** mistura dados automáticos e declarados (a Open Knowledge Brasil tem 18,75 sem nenhuma autodeclaração); serve como contexto, não como prova de perfil preenchido.
- **Base inclui filiais** (cada uma com seu `id_osc`) e OSCs baixadas ou inaptas.
- **Dados pessoais.** A rota `representantes/buscar-representacoes/{cnpj}` expõe usuários do portal e não deve ser usada.

## 21.2 Certificações e CEBAS no Mapa

A rota `osc/certificados/{id_osc}` traz títulos e certificações com `ft_certificado`, `bo_oficial` e datas.
O CEBAS no Mapa não é autodeclarado: vem de cargas oficiais (`CEBAS/MS`, `CEBAS/MEC`, `CEBAS/MDS`, `bo_oficial = true`).
A carga é defasada (Abrinq com CEBAS encerrado em 2016, Santa Casa de São Vicente em 2021), então serve como indício histórico oficial, nunca como prova de certificação vigente.

## 21.3 Base de dados para download

A base principal (`20260806_MOSC_baseDivulgacao.csv`, 344 MB, CSV `;` em Latin-1, coleta de agosto/2026) tem CNPJ com 14 dígitos, natureza, situação, CNAE e a coluna `removida_do_mosc`.
Ela não traz certificações, projetos, governança nem índice de preenchimento.
Uso: fallback offline e testes em lote; o caminho principal é a API.
A mesma página publica as três planilhas oficiais de CEBAS usadas no capítulo 22.

> **Pendências opcionais (P4)**
>
> Conferir no DevTools as chamadas da página da OSC; achar um certificado autodeclarado real (tipo 7 ou 8); escrever a mapaosc@gmail.com sobre limite de uso e periodicidade da carga de CEBAS.

# 22. CEBAS em profundidade: o gargalo do projeto

## 22.1 O que é, com mais detalhe

A Certificação de Entidades Beneficentes de Assistência Social é concedida a entidades privadas sem fins lucrativos que atuam em saúde, educação ou assistência social e cumprem contrapartidas definidas em lei (por exemplo, oferta mínima de serviços ao SUS na saúde ou bolsas de estudo na educação).
Com o certificado, a entidade tem direito à imunidade das contribuições para a seguridade social, além de facilidades como parcelamento de dívidas com o governo federal.
A regra atual é a Lei Complementar nº 187/2021, que substituiu a antiga Lei nº 12.101/2009.
O certificado tem validade limitada (em regra, 3 anos) e precisa ser renovado.
O requerimento tempestivo de renovação mantém a validade até a decisão, e a LC 187 (art. 40, § 1º) previu prorrogações de vigência.

## 22.2 Quem concede

| Área predominante | Ministério | Sistema de requerimento | Pré-requisito típico |
|---|---|---|---|
| Saúde | Ministério da Saúde (Departamento de Certificação de Entidades Beneficentes de Assistência Social em Saúde) | SisCEBAS Saúde | Prestação de serviços ao SUS em percentual mínimo, ou atuação gratuita em promoção da saúde. |
| Educação | Ministério da Educação (SERES) | SisCEBAS Educação | Concessão de bolsas conforme a lei. |
| Assistência social | Ministério do Desenvolvimento e Assistência Social (MDS) | Plataforma digital do MDS | Inscrição no Conselho Municipal de Assistência Social (CMAS) e no Cadastro Nacional de Entidades de Assistência Social (CNEAS). |

Entidades que atuam em mais de uma área pedem ao ministério da área predominante.
Entidades de acolhimento a dependentes de álcool e outras drogas têm um fluxo próprio no MDS.

## 22.3 Por que é gargalo

- **Não existe API.** Nenhum dos três ministérios oferece consulta por CNPJ em formato de API pública. A consulta individual do SisCEBAS Saúde tem CAPTCHA e não é usada.
- **Só uma base viva.** O SisCEBAS Saúde publica a lista completa de situação atual. MDS e MEC só têm retratos de 2024 e 2023 publicados via Mapa das OSCs. O CNEAS redireciona para área restrita, e a consulta do MEC (`siscebas2.mec.gov.br`) não resolvia DNS em 30/09/2026.
- **Os dados abertos prometidos não saíram.** O Plano de Dados Abertos do MEC registra a base de entidades CEBAS com pendência por ausência de base de dados, com prazo empurrado para outubro de 2026.
- **A certificação muda com o tempo.** Concessão, renovação, prorrogação, indeferimento, cancelamento, reconsideração e decisão judicial alteram o status, então um retrato estático envelhece rápido.
- **Ausência não prova nada.** Não encontrar o CNPJ numa fonte incompleta não significa que a entidade não tem CEBAS. CNPJ ausente do SisCEBAS Saúde só indica que nunca requereu CEBAS na saúde.

## 22.4 Fontes avaliadas na Fase 0 (todas gratuitas)

### Fonte 1 - SisCEBAS Saúde, lista de situação atual [EXECUTADO]

| Item | Definição |
|---|---|
| URL e método | `GET http://siscebas.saude.gov.br/siscebas/WebApplication/consultaPublicaPorCnpj.php?list=2258803b6e4f1ef992229c3cef66d75d&ass=87d4eeb7dec7686410748d174c0e0a11` (ícone "Lista Entidades Situação Atual"). |
| Formato | XLS gerado na hora (2 MB, cerca de 24 s). Container OLE levemente corrompido: `xlrd` precisa de `ignore_workbook_corruption=True`. |
| Autenticação | Nenhuma; sem CAPTCHA no download da lista. |
| Campos | CNPJ REQUERENTE, NOME, UF, MUNICÍPIO, PROTOCOLO, ASSUNTO, TIPO DE DECISÃO, NÚMERO/DATA DA PORTARIA, DATA DA PUBLICAÇÃO, INÍCIO/FIM DA VIGÊNCIA, CEBAS (SIM, NÃO, ENCAMINHADO PARA OUTRO MINISTÉRIO), SITUAÇÃO ATUAL, DATA ATUALIZAÇÃO. |
| Conteúdo em 30/09/2026 | 4.458 CNPJs (uma linha por requerimento mais recente), 1.642 com CEBAS = SIM. Cobriu 287 de 287 CNPJs da saúde encontrados no DOU de junho a agosto/2026. |
| Cuidados | Link com tokens opacos que podem mudar; servidor só HTTP; no máximo 1 download por dia; pequenas divergências de data com o DOU (a portaria publicada prevalece). |

### Fonte 2 - Planilhas oficiais (retrato) [EXECUTADO]

Publicadas pelo Mapa das OSCs (capítulo 21.3) em 04/12/2024:

| Ministério | Arquivo | Data de corte | Conteúdo |
|---|---|---|---|
| MDS | `7684-cebassuas.xlsx` | 24/10/2024 | 6.076 entidades (VIGENTE ou VÁLIDA, com início e fim); aba PRINCIPAL com 30.712 processos. |
| MEC | `8420-cebaseducacao.xlsx`, aba "SITUAÇÃO 2023" | portaria mais recente de 19/12/2023 | 1.330 linhas, 1.329 "COM CEBAS". |
| MS | `1434-cebassaude.xlsx` | início de vigência mais recente 23/11/2023 | 1.641 entidades; superada pelo SisCEBAS Saúde. |

Por serem retratos, têm quase todas as entidades que renovaram em 2026, mas não têm as concessões novas nem os indeferimentos de quem nunca teve CEBAS.

### Fonte 3 - Diário Oficial da União [EXECUTADO]

Toda decisão de CEBAS é publicada no DOU, e o texto traz o CNPJ em 99,7% dos atos (99,9% das decisões por entidade).

| Caminho | Uso | Detalhes |
|---|---|---|
| XML mensal da Seção 1 | Carga a partir de 12/2023 e atualização mensal (Q39) | Lista em `https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados?ano=AAAA&mes=NomeDoMes`; ZIP com 1 XML por matéria. Sem login. Defasagem de 2 a 6 semanas (agosto/2026 saiu em 15/09/2026). Volume de 50 a 650 MB por mês, quase tudo imagem, descartada na hora da carga. |
| Busca do portal | Atualização diária e linha do tempo por CNPJ | `GET https://www.in.gov.br/consulta/-/buscar/dou?q=...&s=do1&...` com JSON embutido no HTML. Sem login e sem CAPTCHA. Busca aproximada ("CEBAS" também traz "CEB"); não acha CNPJ colado ao texto; precisa de duas consultas (CNPJ e nome). |
| INLABS | XML diário | Exige cadastro gratuito (P5, opcional). |

Números de junho a agosto/2026: cerca de 110 atos e 430 decisões por mês, muito irregular.
O MS publica um ato por entidade; o MDS publica poucas portarias com listas enormes (uma com 266 entidades) e não usa a sigla "CEBAS"; o MEC publica pouco e varia o formato.

### Fonte 4 - Pedido pela Lei de Acesso à Informação (adiado, D12)

Pedir pela plataforma Fala.BR ao MDS e ao MEC a lista atual de entidades com CEBAS (CNPJ, situação, início e fim da vigência), citando que o MS já publica a sua.
Não é bloqueante: será feito depois do MVP pronto, para medir a cobertura da fonte do CEBAS (F4).
O prazo legal de resposta é de 20 dias prorrogáveis por mais 10, e o pedido é bom material para o relatório de extensão.

### Fonte 5 - Sinais indiretos (só contexto)

- O campo `regime_tributario` (só na BrasilAPI) pode indicar imune ou isenta. É um sinal fraco: imunidade de impostos não é o mesmo que CEBAS.
- Certificações do Mapa das OSCs (capítulo 21.2), oficiais mas defasadas.
- Nenhum desses sinais pode, sozinho, gerar "CEBAS ativo" no relatório.

## 22.5 Recomendação para o MVP

Composição por área (D16):

| Área | Fonte principal | Complemento | Mensagem no relatório |
|---|---|---|---|
| Saúde | Lista do SisCEBAS Saúde (download diário, arquivo bruto e hash guardados) | DOU como evidência do ato e reserva se o link mudar | "CEBAS ativo segundo SisCEBAS Saúde em DD/MM/AAAA" |
| Assistência social (MDS) | Planilha oficial de 24/10/2024 como base histórica | Atos do DOU publicados depois da data de corte, em ordem de data; último ato vale | "segundo planilha MDS de 24/10/2024 e DOU até DD/MM/AAAA" |
| Educação (MEC) | Planilha oficial de 2023 como base histórica | Idem | "segundo planilha MEC de 2023 e DOU até DD/MM/AAAA" |

Período do DOU (Q39): a carga começa em dezembro/2023, o corte da planilha do MEC (o corte do MDS é 24/10/2024), cerca de 22 meses de XML.
É o mínimo que o D16 exige: os atos posteriores ao corte das planilhas.
A carga desde 2018 prevista antes seria de dezenas de GB sem efeito no status.
A atualização no MVP é só pelo XML mensal; o INLABS (P5) fica para depois.
[PENDENTE X17] Na Fase 0 só foram baixados os meses de junho a agosto/2026; os esperados de CEBAS de MDS e MEC em `fase0/casos_referencia.md` estão marcados e serão gerados de novo depois da carga.

Regra de status por CNPJ (D16):

- O último ato define o estado.
- Reconsideração e "torna sem efeito" anulam o ato anterior.
- Usar sempre as datas de vigência do ato, não a data de publicação (várias renovações são retroativas e já começam vencidas na publicação).
- Validade vencida sem ato novo vira "possível renovação em análise", não "sem CEBAS" (caso Santa Casa de Paranaíba, sem ato vigente no DOU entre 23/10/2024 e 04/08/2026 e sem perder o certificado).

## 22.6 Modelo de dados para o CEBAS

O enum `tipo_ato` ganha PRORROGACAO e ARQUIVAMENTO, e a tabela ganha `torna_sem_efeito` e as datas de vigência (D16).

```
tabela cebas_ato
  id                serial
  cnpj              char(14)
  entidade          text
  area              text      -- SAUDE | EDUCACAO | ASSISTENCIA
  tipo_ato          text      -- CONCESSAO | RENOVACAO | PRORROGACAO | INDEFERIMENTO
                              -- | CANCELAMENTO | RECONSIDERACAO | ARQUIVAMENTO | OUTRO
  deferido          boolean
  detalhe           text      -- judicial, recurso negado, prazo para sanar pendencias etc.
  vigencia_inicio   date
  vigencia_fim      date
  torna_sem_efeito  text      -- referência do ato anulado, quando houver
  data_publicacao   date
  fonte             text      -- SISCEBAS_SAUDE | PLANILHA_MDS | PLANILHA_MEC | DOU_XML | DOU_BUSCA
  referencia        text      -- idMateria + pdfPage (DOU) ou nº da portaria
  trecho            text      -- texto que originou a extração (evidência)

-- status atual = último ato válido por cnpj, descartando os anulados
```

Regras do parser na migração para o pacote (fatia 6, Q43):

- A validade em texto ("1º de janeiro 2024 a 31 de dezembro de 2026") é convertida em `vigencia_inicio` e `vigencia_fim`; o texto original fica em `validade_texto`.
- Linha sem data reconhecível fica com a validade só em texto e gera a mensagem "vigência não identificada; confira o ato".
- PRORROGACAO e ARQUIVAMENTO deixam de cair em OUTRO, e "torna sem efeito" é extraído para `torna_sem_efeito`, com a referência do ato anulado.
- O `parser_cebas.py` da Fase 0 ainda mapeia prorrogação e arquivamento para OUTRO (X18); a correção é parte da fatia 6.

## 22.7 Bloco fixo "Sobre o CEBAS" no relatório (B7)

Todo relatório traz este bloco, com as datas preenchidas pela carga ativa de cada base:

- Bases usadas: lista do SisCEBAS Saúde de DD/MM/AAAA; planilha do MDS com corte em 24/10/2024; planilha do MEC com corte em 19/12/2023; atos do DOU até DD/MM/AAAA.
- Saúde: a lista do Ministério da Saúde é atual; o DOU serve de evidência do ato.
- Assistência social e educação: os ministérios não publicam lista atual; a situação é reconstruída pelo retrato oficial mais os atos do DOU publicados depois, com atraso de até 6 semanas.
- Renovação tempestiva: o pedido feito no prazo mantém a validade até a decisão, por isso "vigência vencida" não é o mesmo que "sem CEBAS".
- Ausência não prova nada: não encontrar o CNPJ não significa que a entidade não possui CEBAS.
- A portaria publicada no DOU prevalece sobre o registro do SisCEBAS quando as datas divergem.
- Entidade de várias áreas certifica pela área predominante; o CNPJ pode aparecer em um ministério só.

## 22.8 Roteiro de teste do CEBAS

| Teste | Resultado em 30/09/2026 |
|---|---|
| T1 - Atos de CEBAS por mês no XML do DOU | EXECUTADO: 315 matérias, 337 atos e 1.281 decisões por entidade em junho a agosto/2026. |
| T2 - Conferência manual de 10 atos sorteados | EXECUTADO: 10/10 corretos em CNPJ, nome, tipo, deferido e área; mais 10/10 em linhas das listas do MDS. |
| T3 - Linha do tempo de uma entidade da região | EXECUTADO: Santa Casa de Misericórdia de Cerquilho/SP (50.798.453/0001-83), 5 atos de 2016 a 2026; CEBAS ativo até 31/12/2026, igual ao SisCEBAS Saúde. |
| T4 - Cobertura contra lista oficial | Parcial: saúde 287/287 no SisCEBAS; MDS 59,7% na aba de situação e 96,3% na aba de processos; MEC 3/19. A medição contra a resposta da LAI fica para depois do MVP (D12). |

Parser em `fase0/cebas_dou/parser_cebas.py`; limitações conhecidas: município só com UF nos despachos do GM/MS, nomes errados na fonte mantidos, CNPJ com dígito a mais não reconhecido, e um ato do MEC sem CNPJ (exige casamento por nome).

# 23. Política de scraping e engenharia reversa

| Regra | Motivo |
|---|---|
| Sempre procurar primeiro o JSON por trás da página (DevTools ou bundle JS) antes de fazer parsing de HTML. | JSON muda menos que layout e é mais fácil de validar. Foi assim que TCU e Mapa das OSCs foram resolvidos na Fase 0. |
| Intervalo mínimo por host para chamadas em sequência de uma mesma consulta e em lote: 1 s para TCU e Mapa das OSCs; APIs servidas por CDN (OpenCNPJ, BrasilAPI) só com limite de concorrência. Downloads de bases locais no máximo 1 por dia por arquivo. User-Agent identificando o projeto em todas as chamadas (Q37). | Respeito ao serviço público e menor chance de bloqueio. Uma consulta faz no máximo 2 chamadas ao OpenCNPJ (filial e matriz); o espírito da regra é não sobrecarregar serviço público. |

| Nunca burlar CAPTCHA, login ou controle de acesso. Fonte com CAPTCHA vira verificação manual. | Ética, termos de uso e credibilidade do projeto acadêmico. Por isso não são usadas a certidão individual do TCU (ALTCHA), a consulta individual do SisCEBAS Saúde (reCAPTCHA) nem o desafio do Cloudflare de `dadosabertos.mec.gov.br`. |
| Não usar rotas que exponham dados pessoais sem necessidade. | Ex.: `representantes/...` do Mapa das OSCs. |
| Guardar a resposta bruta (HTML, JSON ou arquivo), a URL, a data e o hash de cada consulta. | Evidência de auditoria e depuração quando a fonte mudar. |
| Não cachear respostas de erro. | O 401 do Portal volta com `cache-control: public, max-age=7200`. |
| Teste de contrato diário: consultar um CNPJ conhecido e comparar a estrutura da resposta com a esperada. | Detectar mudança de layout antes do usuário. |
| Cada fonte atrás de um adapter com interface comum (D1). | Trocar a fonte sem mexer no motor. |

---

# PARTE IV - Execução

# 24. Contrato interno: adapter e resultado

## 24.1 Stack (D1)

- FastAPI para a API, httpx para as consultas assíncronas e PostgreSQL para cache, log e evidências.
- Fila (RQ ou Celery) só se houver processamento em lote.
- Cada fonte atrás de um adapter com a interface abaixo.

## 24.2 Interface de cada fonte (Q41, `arquitetura.md` T4)

O adapter devolve fatos normalizados ou uma falha tipada; quem decide o estado é o motor.
Isso permite aplicar D3, D5, D13 e D18, que precisam ver dados de mais de uma fonte ao mesmo tempo.

```python
@dataclass(frozen=True, slots=True)
class Obtido(Generic[T]):
    dados: T
    evidencia: RefEvidencia  # id + sha256 + recebida_em + de_cache


@dataclass(frozen=True, slots=True)
class NaoEncontrado:
    evidencia: RefEvidencia


@dataclass(frozen=True, slots=True)
class Falha:
    motivo: MotivoFalha  # TIMEOUT, HTTP_5XX, HTTP_4XX, FORMATO_INESPERADO,
    # NAO_SUPORTADO, BASE_VENCIDA
    detalhe: str
    evidencia: RefEvidencia | None


type Coleta[T] = Obtido[T] | NaoEncontrado | Falha


class FonteCadastral(Protocol):
    nome: str
    aceita_alfanumerico: bool

    async def consultar(self, cnpj: str) -> Coleta[CadastroComDatasets]: ...
```

- Cada fonte tem um protocolo pequeno (cadastral, certidões do TCU, perfil do Mapa, consultas às bases locais), em vez de uma interface genérica com `dict`.
- O TTL sai do adapter e vai para a configuração do cache (cap. 24.4); a ligação entre dado e verificação fica no motor.
- Os tipos de domínio (`Cadastro`, `Dirigente`, `Sancao`, `CertidaoTcu`, `PerfilMapa`, `AtoCebas`, `SituacaoCebas`) estão em `arquitetura.md` T4.

## 24.3 Resultado final (JSON) (Q41, `arquitetura.md` T9c)

O exemplo usa o OpenCNPJ como fonte cadastral e uma consulta feita por filial.
O campo `score` da versão 1.0 foi removido (D8); as evidências ficam dentro de cada verificação, para o rastreio ser direto.

```json
{
  "id": "6f1c...",
  "cnpj": "62779145000270",
  "cnpj_avaliado": "62779145000190",
  "estabelecimento": "FILIAL",
  "razao_social": "IRMANDADE DA SANTA CASA DE MISERICORDIA DE SAO PAULO",
  "esfera": "municipio",
  "data_referencia": "2026-10-05",
  "consultado_em": "2026-10-05T14:32:10-03:00",
  "status": "APTA_COM_RESSALVAS",
  "motivos": ["mapa_osc"],
  "avisos": [],
  "resumo": {"ok": 14, "alerta": 1, "restricao": 0, "indisponivel": 0, "nao_verificado": 1},
  "verificacoes": [
    {"id": "situacao", "spec": 2, "nome": "Situação cadastral", "tipo": "ELIMINATORIA",
     "estado": "OK", "mensagem": "Matriz ATIVA; consulta partiu da filial 0002 (ATIVA).",
     "achados": [],
     "fontes": [{"fonte": "opencnpj", "data_base": "2026-09-15", "obtida_em": "2026-10-05T14:32:09-03:00",
                 "de_cache": false, "evidencia": 1832, "sha256": "..."}]},
    {"id": "cebas", "spec": 12, "nome": "CEBAS", "tipo": "INFORMATIVA", "estado": "OK",
     "situacao": "ATIVO",
     "mensagem": "CEBAS ativo segundo SisCEBAS Saúde em 30/09/2026 (portaria ..., vigência até ...).",
     "achados": [{"tipo": "ato_cebas", "data_publicacao": "...", "url_pdf": "..."}],
     "fontes": [{"fonte": "siscebas_saude", "data_base": "2026-09-30", "carga": 41, "sha256": "..."}]}
  ],
  "versao": {"app": "0.1.0", "regras": "sha256:..."},
  "aviso": "Triagem automatizada de cadastros públicos. Não substitui certidões oficiais."
}
```

- `motivos` traz os ids que decidiram o status; `avisos` traz as verificações não eliminatórias INDISPONIVEL, mostradas em destaque (Q5).
- Para `CNPJ_INVALIDO` o resultado traz só `dv` com o motivo e o DV esperado (Q3).
- O QSA completo não aparece; a verificação `dirigentes` mostra só as possíveis correspondências, e os nomes só para o operador autenticado (Q9).
- Datas da API sempre em ISO 8601 (data `AAAA-MM-DD`, instante com `-03:00`); a página mostra `DD/MM/AAAA` e valores como `R$ 1.234,56` (B2).
- `data_referencia` é a data corrente em America/Sao_Paulo; toda comparação de vigência é entre datas, sem hora, e datas vindas em UTC são convertidas para Brasília antes de truncar (B3).

## 24.4 Cache (TTL por fonte) (Q36, `arquitetura.md` T7b)

O cache é por fonte e por chave, guardado na mesma tabela das evidências; uma consulta servida pelo cache aponta para a evidência original.

| Fonte | TTL | Motivo |
|---|---|---|
| OpenCNPJ com `?datasets=` (chamada cadastral) | 24 horas | A chamada é uma só e traz sanções, que podem entrar a qualquer dia; custa uma chamada de 100 ms por dia por CNPJ. |
| BrasilAPI (fallback cadastral) | 7 dias | Sem datasets; o espelho só muda a cada carga dos dados abertos. |
| TCU Consulta Consolidada | 24 horas | Sanções podem entrar a qualquer dia. |
| Mapa das OSCs | 30 dias | Muda pouco; base mensal. |
| Não encontrado (404) | 6 horas | Evita repetir 404 em sequência sem congelar um CNPJ recém-criado. |
| Falhas | nunca | Erro não é cacheado (o 401 do Portal vinha com `max-age=7200`). |
| Bases locais (CSV da CGU, listas do TCU, SisCEBAS, planilhas, DOU) | sem cache | Consulta direta à carga ativa, com download no máximo diário e idade máxima (Q6): CEIS e CNEP 3 dias, CEPIM 7, inidôneos do TCU 3, contas irregulares do TCU 7, inabilitados do TCU 7, TCE-SP Terceiro Setor 45 (base mensal), SisCEBAS Saúde 7, DOU 75, planilhas MDS/MEC sem limite. |

O parâmetro `atualizar=true` ignora o cache das fontes on-line (relatório de auditoria sempre fresco).

Base local acima da idade máxima (B5): a observação vira `Falha(BASE_VENCIDA)`; a mensagem ao usuário é "base de [fonte] de DD/MM/AAAA, mais velha que o limite de N dias"; a página `/fontes` mostra a base em destaque e o log registra nível de erro.
No primeiro uso, sem nenhuma carga concluída, a observação é `Falha(BASE_VENCIDA)` com "base ainda não carregada".
Se outra observação da mesma verificação responder, a verificação conclui com ela; senão fica INDISPONIVEL.

# 25. Plano de testes

## 25.1 Conjunto de CNPJs de referência

O conjunto de casos de referência, com um caso por linha e o resultado esperado de cada uma das verificações do catálogo (cap. 2.6), fica em `fase0/casos_referencia.md` e `fase0/casos_referencia.json`, gerados por `fase0/casos/montar_casos.py` (F1).
São 49 casos e 11 variantes, consultados de novo em 01/10/2026, já com as regras desta versão (Q1, Q3, Q4, Q20 por raiz, Q25, as fontes de dirigentes do Q8 e as provisórias do orientador).
Cada esperado que depende de regra provisória ou pendente traz o marcador (`[ORIENTADOR Qxx]`, `[PENDENTE X17]`); trocar uma regra do orientador é mudar um valor em `REGRAS_ORIENTADOR` e gerar de novo.
Esse conjunto vira o teste de regressão automatizado do projeto.

Ele reúne os casos já encontrados na Fase 0:

- Cadastrais (situação, natureza, filial, tempo de existência, organização religiosa, cooperativa, alfanumérico): `fase0/brasilapi/ficha.md`.
- Sanções (CEPIM, CEIS vigente e expirado, CNEP, multi-cadastro, filial sancionada, inidôneos do TCU, nada consta): `fase0/portal/referencia_cnpjs.md`.
- TCU (OK, RESTRICAO, inexistente, DV inválido, alfanumérico): `fase0/tcu/ficha.md`.
- Mapa das OSCs (perfil automático, perfil preenchido, ausente): `fase0/mapa_osc/ficha.md`.
- CEBAS (Santa Casa de Cerquilho, Santa Casa de Paranaíba): `fase0/cebas_dou/ficha.md`.

Casos ainda não encontrados (lista completa na seção "Casos não encontrados" de `fase0/casos_referencia.md`): associação ATIVA ausente do Mapa isolada, OSC ATIVA inidônea no TCU, dirigente sancionado em entidade limpa, situação NULA, CEBAS do MEC, certificado autodeclarado no Mapa e CNIA com proibição já encerrada; INDISPONIVEL e base vencida só por simulação.
Os casos de sanção mudam diariamente; cada um precisa ser reconferido antes de virar teste de regressão, e os testes de vigência precisam injetar a data de referência.

## 25.2 Ficha de documentação de cada fonte

As fichas da Fase 0 seguem este modelo e estão em `fase0/*/ficha.md`.

| Item | Definição |
|---|---|
| Fonte / etapa |  |
| Tipo | API oficial \| API comunitária \| JSON descoberto \| scraping HTML \| arquivo oficial |
| URL e método |  |
| Parâmetros |  |
| Autenticação |  |
| Limites | rate limit, horário, bloqueios |
| Exemplo OK | arquivo em `fase0/<fonte>/respostas/` |
| Exemplo RESTRICAO |  |
| Exemplo erro / não encontrado |  |
| Campos usados e interpretação |  |
| Aceita alfanumérico? |  |
| Tempo médio de resposta |  |
| Problemas conhecidos |  |
| Data do último teste |  |

## 25.3 Critérios para considerar a fonte pronta para código

- Existe pelo menos um exemplo salvo de cada tipo de retorno (OK, RESTRICAO e erro).
- A regra de interpretação foi escrita e revisada contra esses exemplos.
- O comportamento em falha (timeout, 4xx, 5xx) está documentado.
- A ficha 25.2 está completa.

Situação em 01/10/2026: cumprem os critérios o cálculo local, BrasilAPI, OpenCNPJ (parte cadastral e `?datasets=`, com registros nos 49 casos), TCU Consulta Consolidada (inclusive CNIA com ocorrência, C35), lista de inidôneos e de contas irregulares do TCU, CSVs da CGU, Mapa das OSCs, SisCEBAS Saúde e DOU.
A API do Portal com chave também foi executada (cap. 19.4), mas não é fonte do motor.
Falta para os testes de contrato das bases locais o limite de sanidade de cada carga (`arquitetura.md` T5c, B19).

# 26. Ordem de execução

## 26.1 Feito na Fase 0

| Passo | Tarefa | Entrega |
|---|---|---|
| 1 | DV implementado e testado (D11). | `validador_osc/cnpj.py`, 36 testes. |
| 2 | Roteiro 18.3 nas três fontes cadastrais. | `fase0/brasilapi/`, recomendação D17. |
| 3 | Portal sem chave: OpenAPI, erros, CSVs diários, CNPJs de referência. | `fase0/portal/`. |
| 4 | Backend do TCU descoberto sem navegador (D13). | `fase0/tcu/`. |
| 5 | API do Mapa das OSCs e regra de perfil preenchido. | `fase0/mapa_osc/`. |
| 6 | Prova de conceito do DOU e descoberta do SisCEBAS Saúde e das planilhas oficiais. | `fase0/cebas_dou/`, recomendação D16. |
| 7 | Classificação CNAE completa (D7). | `fase0/cnae/`. |
| 8 | Spec atualizado para a versão 1.1 (F2). | Este documento. |
| 9 | D14 a D18 decididos; marcadores `[PROPOSTA Dxx]` removidos (versão 1.2). | Este documento. |
| 10 | Revisão cruzada e respostas do dono (D19) e decisões técnicas (D20) aplicadas; pendências do spec 1.1 (alfanumérico, filial, vigência do CEIS no TCU, campos de `?datasets=`, fonte alternativa de inidôneos, vigência do CEBAS como data) fechadas. | `revisao_pre_codigo.md`, este documento. |
| 11 | Conjunto de referência gerado de novo com o catálogo de 15 ids, incluindo associação INAPTA (C09) e CNIA com ocorrência (C35). | `fase0/casos_referencia.md` e `.json`. |
| 12 | API do Portal com chave testada (T1 a T8) para documentar os trade-offs (P2). | Cap. 19.4. |
| 13 | Ampliação de dirigentes decidida pelo dono (Q8, opção C, D15) e capítulo 13 reescrito; casos de referência gerados de novo com as listas do TCU e do TCE-SP (versão 1.2.1). | Cap. 13; `fase0/casos_referencia.md` e `.json`. |

## 26.2 O que falta

| Passo | Tarefa | Depende de | Entrega |
|---|---|---|---|
| 14 | Validar Q14 a Q24 (natureza, CNAE, CNEP de multa, abrangência, CEPIM por esfera, CNIA, raiz, contas irregulares, dirigentes, reativação, CEBAS vencido) e informar a saída do score (O3). | Orientador | Marcadores `[ORIENTADOR Qxx]` resolvidos; casos gerados de novo se alguma regra mudar. |
| 15 | Carga do DOU desde 12/2023 e casos de CEBAS gerados de novo (Q39). | - | Marcador `[PENDENTE X17]` resolvido. |
| 16 | Codar o motor em fatias (`arquitetura.md` T18): fatia 0 já pode começar. | Passo 15 só para a fatia 6 (CEBAS) | MVP. |
| 17 | Completar T3 e T5r na BrasilAPI (`retentar_pendentes.sh`). | Minha Receita no ar | Ficha da BrasilAPI completa. |
| 18 | Testar a Consulta Consolidada do TCU a partir do IP do servidor. | Servidor do projeto | Confirmação de que não há bloqueio de datacenter. |
| 19 | (Opcional) DevTools no TCU e no Mapa, INLABS, retestar `siscebas2.mec.gov.br` (P3, P4, P5). | - | Fichas complementadas. |
| 20 | Pedidos LAI do CEBAS ao MDS e ao MEC (D12, F4). | MVP pronto | Métrica de cobertura da fonte do CEBAS. |
| 21 | LGPD completa (D9, F5), incluindo a retenção limitada das consultas (Q9, opção C). | Aprovação do projeto | Política de retenção e exibição. |

# Apêndice A - Scripts de teste das fontes (Fase 0)

O script `testar_fontes.py` da versão 1.0 ficou obsoleto: ele consultava só a BrasilAPI e o Portal com chave.
Os testes da Fase 0 foram feitos com scripts próprios de cada fonte, que salvam a resposta bruta (com URL, status, tempo, data e hash) e geram as fichas.

| Pasta | Scripts | O que fazem |
|---|---|---|
| `fase0/brasilapi/` | `comum.py`, `roteiro.py`, `retentar_pendentes.sh`, `t6_latencia.py`, `consultar.py`, `tabela_resultados.py` | Roteiro 18.3 nas três fontes cadastrais, reexecução das falhas, latência, consulta avulsa e tabela de resultados. |
| `fase0/portal/` | `baixar_dados_abertos.py`, `analisar_dados_abertos.py`, `consultar_local.py`, `portal_openapi.py`, `tcu_inidoneos.py`, `testar_api_com_chave.py` | Download e análise dos CSVs diários, consulta local (observação principal, D14), OpenAPI e T6, lista ORDS de inidôneos (não usada, Q34), roteiro 19.4 com chave. |
| `fase0/dirigentes/` | `baixar_tcu_listas.py`, `baixar_tcesp.py`, `casar_dirigentes.py`, `testar_e2e.py` e outros | Listas do TCU (contas irregulares, inabilitados), TCE-SP e teste de casamento de dirigentes (Q8, Q21, Q22). |
| `fase0/casos/` | `coletar.py`, `fatos.py`, `montar_casos.py` e scripts de busca | Coleta das respostas dos 49 casos e geração de `fase0/casos_referencia.md` e `.json`. |
| `fase0/tcu/` | `baixar_frontend.py`, `testar_certidoes_apf.py`, `testar_lista_inidoneos.py` | Bundle JS do frontend, Consulta Consolidada e Relação de Inidôneos. |
| `fase0/mapa_osc/scripts/` | `fetch.py`, `probe_osc.py`, `resumo_perfil.py`, `busca_nome.py`, `bases_download.py`, `xlsx_resumo.py` | Consulta completa por CNPJ, regra de perfil preenchido, busca por nome e bases para download. |
| `fase0/cebas_dou/` | `baixar_dou.py`, `parser_cebas.py`, `metricas.py`, `busca_dou.py`, `cruzar_planilhas.py` | Download do XML mensal, parser dos atos, métricas, busca do portal e cruzamento com as planilhas e o SisCEBAS. |
| `fase0/cnae/` | `baixar_cnae.py`, `classificar_cnae.py`, `test_classificar_cnae.py` | CNAE do IBGE, aplicação das regras e testes. |

Cada ficha traz o comando para reproduzir os testes da sua pasta.

# Apêndice B - Validação do dígito verificador

O código do DV está em `validador_osc/cnpj.py` (D11), com os testes em `tests/test_cnpj.py`.
O resultado dos casos da seção 4.5 está registrado na própria seção, e o comparativo com bibliotecas em `fase0/dv/ficha.md`.

| Função | O que faz |
|---|---|
| `normalizar(cnpj) -> str` | Remove espaços, `.`, `/`, `-` e traços Unicode e converte a-z ASCII para maiúsculas. |
| `validar(cnpj) -> ResultadoDV` | Verifica formato, depois base repetida, depois DV; devolve `cnpj` normalizado, `valido`, `motivo` (`Motivo.FORMATO`, `Motivo.REPETIDO` ou `Motivo.DV`) e `dv_esperado` quando o motivo é DV. |
| `calcular_dvs(base12) -> str` | Calcula os 2 DVs de uma base de 12 posições [0-9A-Z]; levanta `ValueError` se a base for inválida. |
| `cnpj_da_matriz(cnpj) -> str` | Monta o CNPJ da matriz (raiz + `0001` + DVs) a partir de qualquer estabelecimento (D5). |

Para rodar os testes: `.\.venv\Scripts\python -m pytest -q`.

# Apêndice C - Glossário

| Termo | Significado |
|---|---|
| MROSC | Marco Regulatório das Organizações da Sociedade Civil, Lei nº 13.019/2014. |
| OSC | Organização da Sociedade Civil, nos termos do art. 2º, I, do MROSC. |
| CEPIM | Cadastro de Entidades Privadas Sem Fins Lucrativos Impedidas (CGU). |
| CEIS | Cadastro Nacional de Empresas Inidôneas e Suspensas (CGU). |
| CNEP | Cadastro Nacional de Empresas Punidas, Lei Anticorrupção (CGU). |
| CNIA | Cadastro Nacional de Condenações Cíveis por Ato de Improbidade Administrativa e Inelegibilidade (CNJ). |
| CEBAS | Certificação de Entidades Beneficentes de Assistência Social (MS, MEC, MDS), Lei Complementar nº 187/2021. |
| SisCEBAS | Sistema de requerimento do CEBAS (Saúde e Educação têm sistemas próprios). |
| CNEAS | Cadastro Nacional de Entidades de Assistência Social (MDS). |
| QSA | Quadro de Sócios e Administradores do CNPJ. |
| CNAE | Classificação Nacional de Atividades Econômicas. |
| DOU | Diário Oficial da União, publicado pela Imprensa Nacional. |
| INLABS | Serviço da Imprensa Nacional com o XML diário do DOU, mediante cadastro gratuito. |
| LAI | Lei de Acesso à Informação, Lei nº 12.527/2011. |
| Espelho | Cópia dos dados abertos do CNPJ mantida por um serviço comunitário (OpenCNPJ, Minha Receita), com data de carga própria. |
| TTL | Time to live: por quanto tempo um resultado em cache é considerado válido. |
| Fan-out | Disparar várias consultas independentes ao mesmo tempo e esperar todas terminarem. |

# Apêndice D - Referências

- Lei nº 13.019/2014 (MROSC) e Decreto nº 8.726/2016 - planalto.gov.br
- Lei Complementar nº 187/2021 (CEBAS) - planalto.gov.br
- OpenCNPJ: api.opencnpj.org (e `/info`)
- BrasilAPI: brasilapi.com.br/docs
- Minha Receita - dicionário de dados: docs.minhareceita.org/dicionario
- Portal da Transparência - API de dados e cadastro da chave: portaldatransparencia.gov.br/api-de-dados
- OpenAPI do Portal: api.portaldatransparencia.gov.br (/v3/api-docs)
- Portal da Transparência - download de dados: portaldatransparencia.gov.br/download-de-dados
- TCU - Webservices (dados abertos): sites.tcu.gov.br/dados-abertos/webservices-tcu/
- TCU - Consulta Consolidada de Pessoa Jurídica: certidoes-apf.apps.tcu.gov.br
- TCU - Relação de Licitantes Inidôneos: certidoes.apps.tcu.gov.br/lista-inidoneos
- Mapa das OSCs: mapaosc.ipea.gov.br, API em mapaosc.ipea.gov.br/api/api/documentation e código em github.com/Plataformas-Cidadania/mapa-osc-api
- CEBAS Saúde: SisCEBAS Saúde (siscebas.saude.gov.br) e gov.br/saude
- Serviço "Certificar-se como Entidade Beneficente de Assistência Social": gov.br/pt-br/servicos
- Imprensa Nacional - Diário Oficial da União e base de dados em XML: in.gov.br
- IBGE - CNAE 2.3 (API v2 de classificações)
- Fala.BR (pedidos de acesso à informação): falabr.cgu.gov.br

*Versão 1.2, atualizada em 01/10/2026 com a revisão cruzada (`revisao_pre_codigo.md`) e as decisões D14 a D20.*

*Endpoints e limites de fontes governamentais mudam; a data do último teste de cada fonte deve constar da sua ficha.*
