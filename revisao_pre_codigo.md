# Revisão cruzada antes do código

Data: 01/10/2026.
Documentos lidos por inteiro: `decisoes.md`, `validador_osc_especificacao_mvp.md` (v1.1), `arquitetura.md` (T1 a T18), `fase0/casos_referencia.md` (49 casos, A01 a A17), `fase0/portal/ficha.md` (com a seção da API com chave), `fase0/portal/referencia_cnpjs.md`, `fase0/brasilapi/ficha.md`, `fase0/tcu/ficha.md`, `fase0/mapa_osc/ficha.md`, `fase0/cebas_dou/ficha.md`, `fase0/dv/ficha.md`, `fase0/cnae/proposta.md` e `fase0/dirigentes/ficha.md`.
Fatos novos considerados: D14 a D17 decididos, D18 como proposta forte, API do Portal com chave sem vantagem, e 7 dos CNPJs sancionados de referência INAPTOS ou BAIXADOS (parada antecipada esconde sanções).
Nenhum outro arquivo foi alterado.

Resumo em números:

- 18 contradições entre documentos (seção 1).
- 44 perguntas em aberto, deduplicadas: 13 do DONO, 11 do ORIENTADOR e 20 TECNICAS (seção 2).
- 22 buracos que nenhum documento define (seção 3).
- Lista de correções mecânicas por arquivo (seção 4).
- Checklist de "pronto para codar" (seção 5).

Legenda de quem decide:

- **DONO**: escolha de produto, negócio, exposição ou prazo.
- **ORIENTADOR**: interpretação da Lei 13.019/2014 ou de outra norma.
- **TECNICO**: pode ser fechada pelo agente com a recomendação, salvo objeção.

---

## 1. Contradições entre documentos

Cada item cita os dois lados e a correção proposta.
Quando a correção depende de uma pergunta da seção 2, o número da pergunta aparece no fim.

### X1 - Fonte das sanções: D14 decidido x spec e arquitetura escritos sobre a proposta antiga

- Lado A: `decisoes.md`, D14 (Decidido em 01/10/2026): CSV diário oficial de CEIS/CNEP/CEPIM importado localmente + OpenCNPJ `?datasets=` + TCU; API do Portal com chave só para documentar trade-offs.
- Lado B: spec, seção "Pendente de aprovação" descreve D14 como "TCU + CEPIM via OpenCNPJ (plano B: CSV diário)".
- Lado B: spec 2.2 coloca "Portal da Transparência com chave (opcional)" no fan-out.
- Lado B: spec 3 (último parágrafo) diz que a chave, se existir, entra como fonte adicional das verificações 6, 7 e 8.
- Lado B: spec 9.3, 17 e 19 (introdução) tratam o CSV como "plano B".
- Lado B: spec 19.1 mantém o selo DOCUMENTADO e 19.4 diz "Pendente de chave", mas `fase0/portal/ficha.md` (seção "API com chave") já executou T1 a T8.
- Lado B: `arquitetura.md` T5b diz que D14 "propõe OpenCNPJ datasets como principal e CSV oficial como plano B" e T11a prevê `PORTAL_API_KEY`.
- Correção: o CSV local passa a ser observação principal de CEPIM, CEIS e CNEP desde o primeiro dia; OpenCNPJ `?datasets=` e TCU viram observações adicionais; a API do Portal sai do motor e da configuração e fica só como ferramenta manual de conferência.

### X2 - Divergência entre fontes: D3 x D18

- Lado A: `decisoes.md` D3: "Se Portal e TCU divergirem sobre CEIS/CNEP, vence RESTRICAO".
- Lado A: spec 2.5 (último parágrafo), 10.3, 11.3 e 20.2 (`CONSTAM_REGISTROS` = RESTRICAO para qualquer item, inclusive CEIS e CNEP).
- Lado A: `arquitetura.md` T17, risco R5: "TCU lista sanção que o Portal mostra como expirada: D3 manda RESTRICAO".
- Lado B: `decisoes.md` D18 e `casos_referencia.md` A15: o TCU devolve CEIS `CONSTAM_REGISTROS` também para sanção expirada; isso não é divergência; vigência vem das datas.
- Lado B: os casos C31 (variante de 23/11/2026), C32 e C44 já foram gerados com a regra do D18.
- Correção: reescrever D3 como "avalia-se a vigência de cada registro pelas datas; só depois, se uma fonte tem registro vigente e outra não, vence RESTRICAO"; ajustar spec 2.5, 10.3, 11.3, 20.2 e o R5 da arquitetura (Q7, Q35).

### X3 - Status de D14 a D17 e D18

- Lado A: `decisoes.md` marca D14, D16 e D17 como "Decidido (01/10/2026)" e D15 como "Decidido (base)".
- Lado B: spec, seção "Pendente de aprovação", e todos os marcadores `[PROPOSTA D14]` a `[PROPOSTA D17]`; spec 26.2 passo 9 ("Aprovar ou rejeitar D14, D15, D16 e D17").
- Lado B: `arquitetura.md`, cabeçalho: "D14 a D17 tratadas como prováveis".
- Lado C: D18 continua "Proposto" em `decisoes.md`, mas `casos_referencia.md` já o aplica como regra.
- Correção: remover os marcadores e a seção de pendências de aprovação do spec; registrar D18 como decidido depois de Q7.

### X4 - Eliminatória NAO_VERIFICADO no status final

- Lado A: spec 2.5 só define INCONCLUSIVA para eliminatória INDISPONIVEL e deixa a pendência D4 aberta.
- Lado B: `arquitetura.md` T3c já trata `INDISPONIVEL` e `NAO_VERIFICADO` iguais para INCONCLUSIVA; `casos_referencia.md` A02 adota o mesmo.
- Correção: escrever no spec 2.5 que eliminatória INDISPONIVEL ou NAO_VERIFICADO leva a INCONCLUSIVA (Q2).

### X5 - Catálogo de verificações: 12 números x 15 identificadores

- Lado A: `arquitetura.md` T3b define 15 ids: `religiosa` e `estabelecimento` próprios, e a verificação 9 partida em `tcu_inidoneos` e `cnj_cnia`.
- Lado B: `casos_referencia.md` usa as 12 verificações numeradas do spec: o alerta religioso cai na 4 (A07), o alerta de filial cai na 2 (C24, C27) e TCU e CNIA ficam juntos na 9.
- Lado C: spec 6.3 diz que a natureza 3220 é "sujeita à regra ALERTA_RELIGIOSA", e o spec 7.5 a coloca no capítulo do CNAE.
- Correção: adotar os 15 ids da arquitetura como contrato, com o número do spec como atributo; gerar de novo os casos com essa chave (Q25).

### X6 - Filial baixada com matriz ativa

- Lado A: `fase0/brasilapi/ficha.md`, seção T7, conclusão: "exibindo a situação da filial só como informação" (sem alerta); spec 5.5 cita essa sugestão.
- Lado B: `arquitetura.md` T3e propõe ALERTA ([DECIDIR]); `casos_referencia.md` A04 e C24 adotam ALERTA na verificação 2.
- Correção: decidir em Q4 e alinhar ficha, spec 5.5, arquitetura e casos.

### X7 - Sanção registrada em outro estabelecimento da mesma raiz

- Lado A: `fase0/portal/referencia_cnpjs.md` (observações T4) e `arquitetura.md` T3e: registro em outro estabelecimento da raiz vira ALERTA.
- Lado B: `casos_referencia.md` A16: nenhuma fonte busca por raiz, então C38 (matriz do Instituto Global, filial sancionada) sai APTA.
- Fato novo: com D14 decidido, o CSV local permite a busca por raiz desde o início, e o T4 da API com chave confirmou que a API só busca exato.
- Correção: decidir em Q20 e gerar de novo C38 (e C26/C27, que também têm registros em estabelecimentos irmãos).

### X8 - O que a parada antecipada deixa de avaliar

- Lado A: `arquitetura.md` T3h só fala em pular o fan-out (`precisa_fanout`).
- Lado B: `casos_referencia.md` C08 a C11 marcam também natureza, CNAE e tempo (que são locais e sem custo) como NAO_VERIFICADO.
- Lado C: spec 2.2 diz "situação != ATIVA (matriz) -> INAPTA (fim)", sem dizer se natureza, CNAE e tempo ainda são calculados.
- Correção: resolvida por Q1; se a recomendação for aceita, tudo é avaliado e a contradição some.

### X9 - CNPJ inexistente (404 na fonte cadastral)

- Lado A: `casos_referencia.md` C07: só o OpenCNPJ é consultado, a verificação 2 fica INDISPONIVEL e o fan-out não roda (6 a 9, 11 e 12 NAO_VERIFICADO).
- Lado B: `arquitetura.md` T6c chama a BrasilAPI também em 404, e T3g descreve o TCU com estado INDISPONIVEL "não foi possível confirmar a existência do CNPJ", o que supõe fan-out executado.
- Lado C: spec 5.4 usa INDISPONIVEL para "não encontrado" e para "fonte fora do ar", o que o A03 aponta como confuso.
- Correção: Q26.

### X10 - Condição de OK do TCU

- Lado A: spec 12.3: OK exige `seCnpjEncontradoNaBaseTcu: true` **e** CNPJ confirmado pela fonte cadastral.
- Lado B: spec 20.2: OK se `seCnpjEncontradoNaBaseTcu` for true **ou** a fonte cadastral tiver confirmado.
- Lado C: `arquitetura.md` T3g: OK exige só a confirmação cadastral; `seCnpjEncontradoNaBaseTcu: false` com cadastro confirmado é achado informativo.
- Correção: adotar T3g (Q33).

### X11 - Contrato do adapter e formato do resultado

- Lado A: spec 24.2 (adapter devolve `estado`) e 24.3 (JSON com `achados` e `evidencias` no nível de cima).
- Lado B: `arquitetura.md` T4 (adapter devolve `Coleta[T]` com fatos, sem estado) e T9c (evidências dentro de cada verificação, `motivos`, `resumo`, `cnpj_avaliado`).
- Lado B também cita números errados do spec: T4 diz "Revisão do 24.1" (é o 24.2) e T9c diz "24.2 revisado" (é o 24.3).
- Correção: o spec adota T4 e T9c (Q41).

### X12 - Cortesia por host

- Lado A: spec 23: "Intervalo mínimo de 1 a 2 segundos entre requisições à mesma fonte".
- Lado B: `arquitetura.md` T6e: OpenCNPJ e BrasilAPI sem intervalo; Mapa e TCU com 1 s.
- Correção: Q37.

### X13 - TTL da fonte cadastral

- Lado A: spec 24.4: fonte cadastral 7 dias.
- Lado B: `arquitetura.md` T7b: a chamada do OpenCNPJ com `?datasets=` tem TTL efetivo de 24 h.
- Correção: adotar T7b no spec (Q36).

### X14 - Fatos já resolvidos que os documentos ainda dão como pendentes

- Spec 12.4 ("exemplo de CNIA com ocorrência ainda não foi obtido"), 25.1 ("Faltam: associação INAPTA e ocorrência no CNIA"), 18.3 ("Não foi encontrado um CNPJ INAPTO") e 25.3; `decisoes.md` P3; `fase0/brasilapi/ficha.md` (Pendências).
- Do outro lado: `casos_referencia.md` traz associação INAPTA (C09), SUSPENSA (C10) e CNIA com ocorrência (C35, C36, C39, C46).
- Spec 18A.3 e `arquitetura.md` T5b e R4 dizem que não há exemplo positivo de `?datasets=`; do outro lado, `decisoes.md` A1 e D18 registram exemplo salvo em `fase0/brasilapi/respostas/extras/`, e os 49 casos usaram `?datasets=` com registros e datas.
- Spec 10.5 mantém a pendência sobre vigência do CEIS no TCU, já respondida pelo D18.
- Spec 5.3 diz que "Nula", "Suspensa" e "Inapta" precisam de exemplo real; C09 e C10 confirmam "Inapta" e "Suspensa".
- Correção: atualizar os trechos (seção 4).

### X15 - Dirigentes: aberto ou decidido

- Lado A: `decisoes.md` D15 "Decidido (base)".
- Lado B: `decisoes.md` P6 "Aberto"; spec 13.3 "A escolha final das fontes e da regra continua aberta em P6"; `arquitetura.md` T18 fatia 7 "A definir com P6 e F1".
- Lado C: `casos_referencia.md` A12 diz que "Spec 13.4 gera ALERTA por nome", mas o spec 13.5 já usa nome + 6 dígitos.
- Lado D: `fase0/dirigentes/ficha.md` propõe ampliar fontes e regra (TCU contas irregulares, TCU inabilitados, TCE-SP).
- Correção: fechar P6 junto com Q8 e Q22, e corrigir a citação do A12.

### X16 - Fonte alternativa de inidôneos do TCU

- Lado A: `fase0/portal/ficha.md` Ficha C e `decisoes.md` A2: API ORDS `contas.tcu.gov.br/ords/condenacao/consulta/inidoneos` funciona, 91 registros, todos PJ.
- Lado B: `fase0/tcu/ficha.md`: "Não foi encontrado endpoint ORDS REST"; a Plataforma de Certidões tem 129 registros (128 CNPJs).
- Lado C: spec 20.3 deixa a diferença como pendência; `arquitetura.md` T5a põe a lista fora do MVP.
- Correção: Q34.

### X17 - Cobertura do DOU nos casos de CEBAS

- Lado A: D16 e spec 22.5: planilha MDS (corte 24/10/2024) e MEC (corte 19/12/2023) mais todos os atos do DOU posteriores ao corte.
- Lado B: `casos_referencia.md` usou só o DOU de junho a agosto/2026.
- Efeito: C16 (Abrinq, vigência MDS até 31/12/2023) saiu "possível renovação em análise" sem olhar os atos de 11/2024 a 05/2026; o esperado de C16 e de todo caso MDS/MEC pode estar errado.
- Lado C: `arquitetura.md` T5a fala em "carga histórica desde 2018", bem mais do que o D16 exige.
- Correção: Q39 e geração de novo dos casos de CEBAS.

### X18 - Tipos de ato do CEBAS no parser

- Lado A: D16, spec 22.6 e `arquitetura.md` (tipo `AtoCebas`) têm PRORROGACAO e ARQUIVAMENTO e o campo `torna_sem_efeito`.
- Lado B: `fase0/cebas_dou/ficha.md` seção 4 e o `parser_cebas.py` mapeiam prorrogação e arquivamento para OUTRO e não extraem `torna_sem_efeito`.
- Correção: ajustar o parser na migração (fatia 6) e registrar no spec 22.6 (Q43).

---

## 2. Lista única de decisões em aberto

Ordem: DONO, depois ORIENTADOR, depois TECNICO.
Cada pergunta indica de onde veio, para mostrar a deduplicação.

### 2.1 DONO

#### Q1 - Mostrar sanções de quem já é INAPTA pelo cadastro?

- Origem: `arquitetura.md` T3h [DECIDIR]; `casos_referencia.md` A01; X8.
- Pergunta: quando a entidade já reprova por estar BAIXADA, INAPTA, SUSPENSA ou por natureza não elegível, o sistema ainda consulta e mostra as sanções?
- Opções:
  - A. Parar (spec atual): o relatório mostra só o motivo cadastral.
  - B. Consultar tudo sempre que o DV for válido e o cadastro existir; o status continua INAPTA, mas o relatório mostra todas as restrições.
- Recomendação: B.
- Motivo: 7 dos 13 CNPJs sancionados das fichas (mais a AVAPE) estão INAPTOS ou BAIXADOS; com A, o relatório de C39 a C46 esconde CEPIM, CEIS, CNEP, TCU e CNIA que existem.
- Motivo: o custo é de 2 a 4 chamadas e alguns segundos; natureza, CNAE e tempo não custam nada.
- Motivo: simplifica o motor (sem `precisa_fanout`) e remove a coluna `estado_sem_parada` dos casos.
- Consequência: `motivos` do status lista todas as RESTRICAO, não só a cadastral.
- Quem decide: DONO.

#### Q2 - Status final do CNPJ alfanumérico

- Origem: spec 2.5 (pendência D4); `casos_referencia.md` A02; X4.
- Pergunta: um CNPJ alfanumérico válido, que o MVP não consulta, termina como?
- Opções: A. INCONCLUSIVA com mensagem própria; B. status novo (ex.: NAO_SUPORTADO); C. consultar o que já aceita alfanumérico (OpenCNPJ, TCU sem CNIA).
- Recomendação: A.
- Motivo: segue o princípio "nunca aprovado por omissão" sem criar status novo; C contraria D4 e deixaria o Mapa e o CNIA quebrados.
- Quem decide: DONO.

#### Q3 - CNPJ digitado errado deve aparecer como INAPTA?

- Origem: spec 4.4 e 2.5; `arquitetura.md` T9d; novo nesta revisão.
- Pergunta: hoje DV inválido, base repetida ou formato errado viram status final INAPTA, que para o usuário significa "a entidade não pode firmar parceria".
- Opções:
  - A. Manter INAPTA (spec).
  - B. Status final próprio `CNPJ_INVALIDO`, mostrado como erro de digitação no formulário, com o DV esperado, sem relatório de entidade.
- Recomendação: B.
- Motivo: um erro de digitação não diz nada sobre a entidade; "INAPTA" num print levado a uma prefeitura é enganoso.
- Motivo: o DV continua sendo resultado de negócio (201, sem chamada externa), como quer o T9d; só muda o rótulo.
- Quem decide: DONO.

#### Q4 - Filial inativa com matriz ativa

- Origem: `arquitetura.md` T3e [DECIDIR]; `casos_referencia.md` A04; spec 5.5 (pendência); X6.
- Pergunta: o usuário informou uma filial BAIXADA (ou INAPTA, SUSPENSA) cuja matriz está ATIVA; o que acontece?
- Opções: A. ALERTA ("o estabelecimento informado não está ativo; a entidade está"); B. OK com a situação da filial só como informação; C. RESTRICAO.
- Recomendação: A.
- Motivo: a parceria é com a entidade (raiz), então C seria injusto; mas o usuário provavelmente copiou o CNPJ errado do edital ou do contrato, e B esconderia isso.
- Quem decide: DONO.

#### Q5 - Verificação que não é eliminatória e fica sem resposta

- Origem: `arquitetura.md` T3c' [DECIDIR].
- Pergunta: se dirigentes, CNAE, Mapa ou CEBAS ficam INDISPONIVEL, o status muda?
- Opções: A. Não muda; aparece em destaque na lista "não verificadas"; B. Leva a APTA COM RESSALVAS.
- Recomendação: A.
- Motivo: B faria toda queda do Mapa (informativo) virar ressalva; o relatório já mostra o que não foi verificado.
- Exceção a considerar: se Q8 ampliar os dirigentes, uma base local de dirigentes vencida também segue A, com o aviso.
- Quem decide: DONO.

#### Q6 - Idade máxima das bases locais e do espelho cadastral

- Origem: `arquitetura.md` T5d [DECIDIR]; buraco B6.
- Pergunta: a partir de que idade uma base deixa de valer e a verificação vira INDISPONIVEL?
- Proposta da arquitetura: CEIS e CNEP 3 dias, CEPIM 7, SisCEBAS Saúde 7, DOU 75, planilhas MDS/MEC sem limite.
- Bases novas a incluir: CSV de inidôneos do TCU 3 dias (Q34); listas TCU de contas irregulares e inabilitados 7 dias e TCE-SP 45 dias (se Q8 aceitar).
- Novo: espelho cadastral (OpenCNPJ, hoje de 15/09/2026) não tem limite em nenhum documento.
- Recomendação: aceitar os valores e acrescentar espelho cadastral com mais de 60 dias = ALERTA na verificação de situação ("dados cadastrais de DD/MM/AAAA").
- Motivo: o OpenCNPJ é comunitário e pode parar de atualizar sem erro HTTP; hoje isso passaria despercebido.
- Quem decide: DONO.

#### Q7 - Aprovar o D18

- Origem: `decisoes.md` D18 (Proposto); `casos_referencia.md` A15; spec 10.5 (pendência); X2.
- Pergunta: sanção de CEIS/CNEP com data final passada é OK com histórico, mesmo que o TCU diga `CONSTAM_REGISTROS`?
- Recomendação: aprovar.
- Motivo: o art. 39, V, da Lei 13.019/2014 fala em impedimento "pelo período que durar a penalidade"; sem o D18, C32 e C44 seriam INAPTAS por sanções vencidas em 2021 e 2022.
- Quem decide: DONO (aprovação formal; a base legal é explícita).

#### Q8 - Ampliar a verificação de dirigentes

- Origem: `decisoes.md` D15 ("em análise") e P6; `fase0/dirigentes/ficha.md` seção 6; X15.
- Pergunta: além de CEIS/CNEP, o MVP inclui as listas do TCU (contas irregulares, inabilitados) e do TCE-SP (Terceiro Setor)?
- Opções:
  - A. Só CEIS/CNEP (D15 base).
  - B. A + TCU contas irregulares (janela de 8 anos) + TCU inabilitados (vigentes).
  - C. B + TCE-SP Terceiro Setor (casamento por nome + DV que reconstitui o CPF só em memória).
  - D. C + CPF completo opcional informado pelo usuário e CNIA on-line por CPF.
- Recomendação: C no MVP; D no pós-MVP, junto com a LGPD (D9).
- Motivo: B acrescenta cerca de 22.700 CPFs que não estão no CEIS/CNEP, com download diário de segundos e o mesmo casamento já aprovado.
- Motivo: o TCE-SP cobre exatamente o art. 39, VII, a para o público do projeto (SP) e custa 0,6 MB por mês.
- Risco a aceitar em C: reconstituir o CPF em memória é tratamento de dado pessoal mesmo sem gravar; a regra "nunca persistir nem exibir" vira teste automatizado.
- Limite a comunicar: o QSA de associações costuma trazer só o presidente (23 de 25 no teste da ficha).
- Quem decide: DONO.

#### Q9 - Quem pode ver uma consulta já feita, e por quanto tempo ela fica guardada

- Origem: novo (buraco); toca `arquitetura.md` T9b e T9e e D9.
- Pergunta: o link permanente `/consultas/{id}` mostra nomes de dirigentes com possível correspondência; quem tem o link vê tudo, para sempre?
- Opções: A. Link aberto com id não adivinhável, sem expiração; B. A + nomes de dirigentes só com token de operador; C. retenção limitada (ex.: 90 dias) e depois só o status.
- Recomendação: B no MVP e C quando a LGPD (D9) for tratada.
- Motivo: o link é o que a OSC vai mandar para a prefeitura; o risco está só nos nomes de pessoas, não no resto.
- Quem decide: DONO.

#### Q10 - Interface do MVP

- Origem: `arquitetura.md` T10 [DECIDIR].
- Opções: só Swagger; páginas HTML no servidor (Jinja2); HTMX; SPA.
- Recomendação: páginas HTML no servidor.
- Motivo: é o que demonstra o projeto para a banca e para a prefeitura sem criar um segundo projeto.
- Quem decide: DONO.

#### Q11 - PDF de auditoria

- Origem: `arquitetura.md` T16 [DECIDIR].
- Opções: fora do MVP; CSS de impressão; PDF no servidor.
- Recomendação: CSS de impressão no MVP.
- Motivo: sai junto com a página, sem dependência nova.
- Quem decide: DONO.

#### Q12 - Onde demonstrar

- Origem: `arquitetura.md` T14c [DECIDIR].
- Recomendação: local na apresentação; túnel público se o orientador precisar testar sozinho.
- Motivo: o TCU nunca foi testado a partir de IP de datacenter.
- Quem decide: DONO.

#### Q13 - Repositório público ou privado

- Origem: `arquitetura.md` T15a [DECIDIR].
- Opções: público com licença MIT; privado.
- Recomendação: privado até a aprovação do projeto; público (MIT) depois de uma varredura de dados pessoais em `fase0/`.
- Motivo: as respostas da Fase 0 têm nomes do QSA e as pastas `downloads/` têm CPF completo; um erro de `.gitignore` num repositório público não tem volta.
- Quem decide: DONO.

### 2.2 ORIENTADOR

#### Q14 - Tabela de natureza jurídica (O1)

- Origem: `decisoes.md` O1; spec 6.3.
- Pergunta: confirmar REVISÃO MANUAL para 214-3 (cooperativa), 330-1 (OS) e 320-4 (estrangeira), e NÃO ELEGÍVEL para 307-7 (Serviço Social Autônomo).
- Recomendação: confirmar como está.
- Motivo: só muda `natureza_juridica.json`, sem código.
- Quem decide: ORIENTADOR.

#### Q15 - Os 8 pontos da classificação CNAE (O2)

- Origem: `decisoes.md` O2; spec 7.3; `fase0/cnae/proposta.md` seção 8.
- Pergunta: 94.93-6 em ALTA, saúde (86) inteira em ALTA, esporte em MÉDIA, proteção animal, meio ambiente, regra religiosa (incluindo maçonaria), inclusões fora das divisões sociais e exceções dentro das divisões ALTA.
- Recomendação: aprovar a proposta; para saúde, ALTA com ressalva no texto sobre o art. 3º, IV.
- Quem decide: ORIENTADOR.

#### Q16 - Multa do CNEP reprova a entidade?

- Origem: novo; spec 11.4 e 11.5; casos C34 (IPCIM, só CNEP) e C45.
- Pergunta: o art. 39, V, lista suspensão, impedimento e inidoneidade (e as sanções do art. 73, II e III); a multa e a publicação extraordinária da Lei Anticorrupção (CNEP) não estão na lista. Registro no CNEP sem data final deve reprovar?
- Opções: A. RESTRICAO para todo registro vigente do CNEP (spec atual); B. RESTRICAO só para categorias de suspensão, impedimento ou inidoneidade; ALERTA para multa e publicação extraordinária.
- Recomendação: B.
- Motivo: multa do CNEP não tem prazo e ficaria reprovando a entidade para sempre, sem previsão no art. 39; o ALERTA ainda obriga a revisão humana.
- Quem decide: ORIENTADOR.

#### Q17 - Sanção com abrangência limitada

- Origem: spec 10.5 ("No MVP, toda sanção vigente é RESTRICAO"); casos C30 e C31 ("Na Esfera e no Poder do órgão sancionador"), C37 ("No órgão sancionador").
- Pergunta: uma suspensão aplicada por uma prefeitura, com abrangência só no órgão ou na esfera dela, impede parceria com a União ou com outro município?
- Opções: A. Sempre RESTRICAO (conservador, spec atual); B. RESTRICAO quando a abrangência é total ou não informada, ALERTA quando é limitada; C. usar `esfera` para decidir.
- Recomendação: A no MVP, com a abrangência em destaque no texto.
- Motivo: o sistema não sabe qual ente vai firmar a parceria (só a esfera), então C não é confiável; B depende de interpretação que o orientador precisa validar.
- Quem decide: ORIENTADOR.

#### Q18 - CEPIM em parceria municipal ou estadual

- Origem: novo; spec 9.5 ("O CEPIM é federal").
- Pergunta: o CEPIM impede transferências federais; ele reprova também uma parceria com município ou estado?
- Opções: A. RESTRICAO em qualquer esfera (spec atual); B. RESTRICAO com `esfera = uniao` ou sem esfera, ALERTA com município ou estado.
- Recomendação: A.
- Motivo: os motivos do CEPIM (prestação de contas impugnada, omissão, tomada de contas especial) correspondem aos incisos II e IV do art. 39, que valem para qualquer esfera.
- Quem decide: ORIENTADOR.

#### Q19 - CNIA sem datas

- Origem: `casos_referencia.md` A11; casos C35, C36, C39, C46.
- Pergunta: o item CNIA da Consulta Consolidada traz só o número do processo; uma condenação por improbidade com sanções já cumpridas deve reprovar para sempre?
- Opções: A. Qualquer registro no CNIA = RESTRICAO (adotado); B. RESTRICAO só se houver proibição de contratar vigente (pela data no CEIS de origem CNJ ou na página de detalhe do CNIA), senão ALERTA.
- Recomendação: B.
- Motivo: segue a mesma lógica do D18 e do art. 39, VII, c ("enquanto durarem os prazos").
- Viabilidade técnica: a ficha de dirigentes mostra que o CNIA busca por CPF/CNPJ completo sem CAPTCHA e que a página de detalhe traz as penas com datas; para PJ o CNPJ completo é conhecido; e em 6 de 6 casos testados a condenação também estava no CEIS com datas.
- Quem decide: ORIENTADOR (a parte técnica fica em Q42).

#### Q20 - Sanção em outro estabelecimento da mesma raiz

- Origem: `casos_referencia.md` A16; spec 5.5 (pendência); `arquitetura.md` T3e; `fase0/portal/referencia_cnpjs.md`; X7.
- Pergunta: a filial não tem personalidade jurídica própria; uma sanção registrada no CNPJ de uma filial alcança a entidade?
- Opções:
  - A. RESTRICAO para registro em qualquer estabelecimento da raiz, com o texto indicando o estabelecimento.
  - B. RESTRICAO só para o estabelecimento consultado e a matriz; ALERTA para os demais (arquitetura).
  - C. Só o CNPJ exato (casos atuais; C38 sai APTA).
- Recomendação: A, com B como alternativa se o orientador entender que a abrangência da sanção pode ser só do estabelecimento.
- Motivo: natureza, QSA e tempo já são avaliados na raiz (D5); a sanção é aplicada à pessoa jurídica, que é uma só.
- Motivo: com D14 decidido, o CSV local já permite busca por raiz sem custo.
- Quem decide: ORIENTADOR.

#### Q21 - Contas irregulares da própria OSC (inciso VI) pela lista do TCU

- Origem: `fase0/dirigentes/ficha.md` seção 2 (inciso VI) e seção 6, item 6.
- Pergunta: a lista de contas irregulares do TCU traz 6.817 condenações de PJ por CNPJ, mas não diz se a conta é de parceria; isso entra como verificação da OSC?
- Opções: A. Não usar; B. ALERTA quando o CNPJ (ou a raiz) aparece com trânsito em julgado nos últimos 8 anos; C. RESTRICAO.
- Recomendação: B, como verificação nova `tcu_contas_irregulares` do tipo ALERTA.
- Motivo: é o único sinal público do inciso VI; C seria injusto porque a natureza da conta é desconhecida; o arquivo já é baixado para os dirigentes (Q8).
- Quem decide: ORIENTADOR (e DONO, se não quiser a verificação nova no MVP).

#### Q22 - Que achado de dirigente conta como possível impedimento

- Origem: `casos_referencia.md` A12; `fase0/dirigentes/ficha.md` seções 5.1 e 5.2.
- Pergunta: confirmar a regra da ficha:
  - CEIS/CNEP só com sanção vigente.
  - TCU contas irregulares e TCE-SP só com trânsito em julgado nos últimos 8 anos.
  - TCU inabilitados só vigentes.
  - Categorias de PF do CEIS que não são hipótese do art. 39 (Demissão, Suspensão de servidor) aparecem como informação, sem ALERTA.
  - Correspondência só por nome nunca gera achado.
- Recomendação: confirmar.
- Motivo: a regra segue o texto do art. 39, VII, e o teste ponta a ponta da ficha não teve falso positivo.
- Quem decide: ORIENTADOR.

#### Q23 - "Tempo com cadastro ativo" quando a entidade foi reativada

- Origem: `casos_referencia.md` A09; spec 8.1.
- Pergunta: o art. 33, V, a fala em existência "com cadastro ativo"; uma entidade com `data_situacao_cadastral` posterior ao início (sinal de reativação) conta o tempo desde o início ou desde a reativação?
- Opções: A. Desde `data_inicio_atividade` (spec), citando a data da situação no texto; B. Desde a última reativação.
- Recomendação: A.
- Motivo: a base aberta não informa se houve interrupção; `data_situacao_cadastral` muda por outros motivos; B reprovaria C17 e C22 sem prova.
- Quem decide: ORIENTADOR.

#### Q24 - CEBAS vencido há muito tempo sem ato novo

- Origem: `casos_referencia.md` A13; spec 15.3; D16.
- Pergunta: "possível renovação em análise" vale por quanto tempo? Abrinq (C16) tem vigência vencida em 31/12/2023.
- Opções: A. Sem limite, sempre com a data de vencimento e a fonte; B. Até N anos (ex.: 3, uma validade); depois "situação desconhecida".
- Recomendação: A no texto, mas com a idade explícita ("vencida há 2 anos e 9 meses; o requerimento tempestivo mantém a validade até a decisão; confirme com o ministério").
- Motivo: a LC 187/2021 mantém a validade até a decisão sem prazo; a verificação é informativa e não muda o status.
- Quem decide: ORIENTADOR (redação jurídica da mensagem).

### 2.3 TECNICAS

#### Q25 - Catálogo de verificações

- Origem: X5; `casos_referencia.md` A07.
- Recomendação: adotar os 15 ids da arquitetura T3b (mais `tcu_contas_irregulares` se Q21 = B); o número do spec vira atributo; gerar os casos de novo com essa chave.
- Motivo: deixa claro qual cadastro falhou (CNIA x Inidôneos) e onde fica cada alerta.

#### Q26 - CNPJ inexistente

- Origem: `casos_referencia.md` A03; X9; spec 5.4; `arquitetura.md` T3g e T6c.
- Recomendação: `Coleta` com `NaoEncontrado` distinto de `Falha`; BrasilAPI só em `Falha` do OpenCNPJ ou em 404 (como T6c), com o mesmo prazo; os dois 404 levam a situação INDISPONIVEL com motivo `NAO_ENCONTRADO` e texto "não encontrado no espelho de DD/MM/AAAA"; fan-out não roda; demais verificações NAO_VERIFICADO.
- Motivo: sem cadastro não há QSA nem raiz para sanções, e o TCU daria um "nada consta" enganoso (D13).

#### Q27 - Matriz fora da ordem 0001

- Origem: `casos_referencia.md` A06; casos C26 e C27.
- Recomendação: detectar matriz só por `matriz_filial`; se raiz + 0001 for filial, ALERTA em `estabelecimento` pedindo o CNPJ da matriz e avaliação com os dados do estabelecimento consultado (tempo pela data dele, com aviso).
- Melhoria se Q20 = A: o CSV local e a base do Mapa (coluna `matriz_filial`) podem indicar a matriz verdadeira; fica para depois do MVP.

#### Q28 - Mapa e CEBAS quando a entrada é filial

- Origem: `casos_referencia.md` A05.
- Recomendação: Mapa pela matriz; CEBAS pela matriz e pelo estabelecimento consultado (o SisCEBAS registra o CNPJ requerente, que pode ser de filial).
- Motivo: são atributos da entidade; consultar os dois no CEBAS evita falso "não encontrado".

#### Q29 - Contagem de anos na fronteira

- Origem: `casos_referencia.md` A08.
- Recomendação: anos completos com o dia do aniversário contando; 29/02 faz aniversário em 28/02 em ano não bissexto (como adotado).

#### Q30 - Último dia de vigência

- Origem: `casos_referencia.md` A10.
- Recomendação: vigente até a data final inclusive (`data_fim >= data_referencia`), como no spec 10.4.

#### Q31 - CEBAS com pedido sem decisão

- Origem: `casos_referencia.md` A14.
- Recomendação: NAO_VERIFICADO com a frase "há pedido em análise sem decisão publicada" (como adotado), e acrescentar a linha à tabela do spec 15.3.

#### Q32 - Dado de origem inconsistente ou duplicado

- Origem: `casos_referencia.md` A17.
- Recomendação: como adotado ("com prazo determinado" sem data final = vigente com aviso; duplicados agrupados por categoria + datas + órgão; `"0"` e `""` em datas = nulo; "Sem informação" da API = nulo).

#### Q33 - Condição de OK do TCU

- Origem: X10.
- Recomendação: regra do T3g (OK exige só a confirmação cadastral; `seCnpjEncontradoNaBaseTcu: false` é achado informativo).
- Motivo: CNPJ recém-criado pode existir na Receita e ainda não no TCU.

#### Q34 - Fonte alternativa de inidôneos

- Origem: spec 20.3 (pendência); X16.
- Recomendação: usar a Plataforma de Certidões oficial (`POST .../responsaveis-inidoneos/exportar-para-csv`, 35 KB) como base local diária e segunda observação da verificação `tcu_inidoneos`; não usar o ORDS (não documentado pelo TCU).
- Motivo: custo quase zero e a verificação 9 deixa de depender só da Consulta Consolidada.
- Pendência pequena: explicar 129 x 91 ao carregar (provavelmente a Plataforma inclui pessoas físicas e mais de um registro por CNPJ); registrar na ficha do TCU.

#### Q35 - TCU com CEIS/CNEP `CONSTAM_REGISTROS` e nenhum registro local

- Origem: D18; `casos_referencia.md` A15.
- Recomendação: extrair a data entre parênteses da `observacao`; se todas as datas forem passadas, OK com histórico e aviso "registro só no TCU"; se alguma for futura ou ilegível, RESTRICAO (D3).
- Motivo: cobre o intervalo entre a publicação na CGU e o CSV do dia seguinte sem gerar falso INAPTA.

#### Q36 - Papel do OpenCNPJ `?datasets=` e TTL

- Origem: X13; D14.
- Recomendação: manter como observação adicional, sem custo extra porque vem na chamada cadastral; TTL de 24 h para a chave com datasets (T7b).
- Motivo: cobre o CSV local vencido ou com falha de carga.

#### Q37 - Intervalo entre requisições por host

- Origem: X12.
- Recomendação: reescrever a regra do spec 23 como "intervalo mínimo por host para chamadas em sequência de uma mesma consulta e em lote: 1 s para TCU e Mapa; APIs servidas por CDN (OpenCNPJ, BrasilAPI) só com limite de concorrência".
- Motivo: uma consulta faz no máximo 2 chamadas ao OpenCNPJ (filial e matriz); o espírito da regra é não sobrecarregar serviço público.

#### Q38 - Quais seções do Mapa consultar

- Origem: `fase0/mapa_osc/ficha.md` (perfil completo = 16 chamadas, cerca de 25 s); buraco B14.
- Recomendação: `busca/cnpj`, `osc/dados_gerais`, `osc/descricao`, `osc/areas_atuacao_rep` e `osc/indice_preenchimento` (5 chamadas, cerca de 5 s com 1 s de intervalo); certificados só como contexto do CEBAS, se couber no prazo.
- Motivo: são as seções que decidem "preenchido pela OSC"; o resto não muda o estado.

#### Q39 - Período da carga do DOU e atualização

- Origem: X17; spec 22.5; `arquitetura.md` T5a.
- Recomendação: carga a partir de dezembro/2023 (corte do MEC), cerca de 22 meses de XML; descartar imagens na hora; atualização só pelo XML mensal no MVP; INLABS (P5) depois.
- Motivo: é o mínimo que o D16 exige; desde 2018 seriam dezenas de GB sem efeito no status.
- Consequência: gerar de novo os casos C16, C23, C25 e os que usam planilha MDS/MEC.

#### Q40 - Estado das verificações informativas

- Origem: spec 15.3 (CEBAS indeferido = OK); casos C27, C30, C48.
- Recomendação: manter `estado` para a agregação e acrescentar `situacao` própria da verificação (`ATIVO`, `EM_RENOVACAO`, `NAO_VIGENTE`, `PEDIDO_EM_ANALISE`, `NAO_ENCONTRADO` no CEBAS; `PREENCHIDO`, `AUTOMATICO`, `AUSENTE` no Mapa).
- Motivo: "OK" para "CEBAS não vigente" confunde o leitor; a página precisa de um rótulo próprio.

#### Q41 - Contrato do adapter e formato do resultado

- Origem: X11.
- Recomendação: adotar `arquitetura.md` T4 e T9c no spec 24.

#### Q42 - Mesma condenação em duas verificações

- Origem: novo; casos C35 (CEIS de origem TJSC e CNIA), C40 e C42 (inidoneidade TCU no CEIS e em Inidôneos).
- Recomendação: cada verificação mantém o seu estado, mas o relatório liga os achados com a mesma origem ("mesma decisão já listada em ...") por processo ou órgão; investigar a busca do CNIA por CNPJ e a página de detalhe para obter datas (Q19).

#### Q43 - Vigência do CEBAS como data

- Origem: spec 22.6 (pendência); X18.
- Recomendação: o parser converte a validade em `vigencia_inicio` e `vigencia_fim`, extrai `torna_sem_efeito` e usa PRORROGACAO e ARQUIVAMENTO; linhas sem data ficam com a validade em texto e geram "vigência não identificada".

#### Q44 - Entrada filial e matriz sem resposta

- Origem: novo; `arquitetura.md` T3e (`matriz: Coleta[Cadastro] | None`).
- Recomendação: se a matriz ficar INDISPONIVEL, a verificação de situação fica INDISPONIVEL (status INCONCLUSIVA), natureza e QSA vêm da filial (são da raiz) e o tempo usa a data da filial com aviso.
- Motivo: "nunca aprovado por omissão"; D5 diz que matriz baixada derruba tudo, então não dá para concluir sem ela.

---

## 3. Buracos: o que o motor precisa e nenhum documento define

### B1 - Catálogo de mensagens ao usuário

- Existem frases soltas no spec e justificativas técnicas nos casos, mas não há um texto final por verificação e estado, escrito para leigo.
- Proposta: arquivo versionado de mensagens (junto de `natureza_juridica.json` e `regras_cnae.json`), com variáveis nomeadas, coberto por teste que garante uma mensagem para cada par (verificação, estado, situação).
- Incluir rótulos dos status finais com acento ("Apta com ressalvas") separados dos enums.

### B2 - Formato de datas, números e textos vindos das fontes

- As fontes usam AAAA-MM-DD, DD/MM/AAAA, ISO em UTC (ORDS), `""`, `"0"` e "Sem informação" para vazio, e vírgula decimal.
- Proposta: API sempre ISO 8601 (data `AAAA-MM-DD`, instante com `-03:00`); página sempre `DD/MM/AAAA` e `R$ 1.234,56`; um parser de data por fonte, testado com os casos reais (GRPCOM `"0"`, C33 sem data final).

### B3 - Fuso e o que é "hoje"

- T3i fixa `data_referencia` em America/Sao_Paulo, mas não diz como comparar datas de fontes em UTC (OpenCNPJ `last_updated`, ORDS) nem o que acontece numa consulta perto da meia-noite com cache.
- Proposta: toda comparação de vigência é entre datas (sem hora) no fuso de Brasília; datas em UTC são convertidas antes de truncar; o resultado grava `data_referencia` e o instante.

### B4 - Idempotência das consultas

- T5c define ingestão idempotente, mas `POST /api/v1/consultas` cria um registro novo a cada clique.
- Proposta: header `Idempotency-Key` opcional; sem ele, mesma combinação (CNPJ, esfera, atualizar=false) em menos de 10 s devolve a mesma consulta; o formulário desabilita o botão durante a espera.

### B5 - Base local velha ou ausente

- T5d diz que a observação vira `Falha(BASE_VENCIDA)`, mas não define:
  - a mensagem ao usuário ("base de sanções de DD/MM/AAAA, mais velha que o limite");
  - o primeiro uso, quando ainda não há nenhuma carga;
  - o aviso ao operador (página `/fontes` em destaque e log de nível de erro);
  - a regra de que uma sanção publicada depois da data da base não aparece, o que precisa estar no texto ("consultado na base de DD/MM/AAAA").

### B6 - Espelho cadastral defasado

- O OpenCNPJ é de 15/09/2026 e a BrasilAPI tem cache de até 16 h; uma baixa posterior não aparece.
- Nenhum documento define limite de idade nem a frase do relatório; ver Q6.

### B7 - Como o relatório explica as nuances do CEBAS

- D16 exige que defasagem, cobertura por ministério e "ausência não prova nada" estejam explicadas, mas não há texto.
- Proposta: bloco fixo "Sobre o CEBAS" com: quais bases foram usadas e as datas de corte; saúde viva, MDS e MEC por retrato + DOU com até 6 semanas de atraso; renovação tempestiva; ausência não significa "não possui"; portaria publicada prevalece sobre o SisCEBAS; entidade de várias áreas certifica pela área predominante.

### B8 - O que fazer quando o resultado é INCONCLUSIVA

- Proposta: tabela de links de consulta manual por verificação (TCU `linkConsultaManual`, página de download do Portal, perfil do Mapa, SisCEBAS) e a frase "tente de novo em alguns minutos" quando a falha for transitória.

### B9 - Bloco fixo de limites do sistema

- O spec 1.3 e 16 listam o que fica fora, mas o relatório não tem texto definido.
- Proposta: bloco "O que este relatório não verifica": certidões do art. 34, art. 39 incisos III e § 2º, sanções estaduais e municipais fora do CEIS, tribunais de contas fora do TCU e do TCE-SP, dirigentes fora do QSA.

### B10 - Orçamento de tempo da consulta

- T6a e T6b somam mais que o prazo global de 45 s: OpenCNPJ 2 x 5 s + BrasilAPI 12 s antes do fan-out, e depois TCU 2 x 30 s.
- Proposta: orçamento explícito por fase (cadastro até 20 s; fan-out até 25 s), retry só se couber no que sobra do prazo, e o TCU com uma tentativa longa.

### B11 - Versão das regras

- `versao_regras` (T8c) cobre só natureza e CNAE.
- Proposta: incluir mensagens, limites de idade, janela de 8 anos, tabela de vigência e a lista de fontes; replay usa a mesma versão.

### B12 - Tabela de natureza a partir do texto do OpenCNPJ

- D17 manda mapear descrição para código, mas ninguém definiu de onde vem a tabela oficial nem a normalização (acento, caixa, sinônimos).
- Proposta: gerar `natureza_juridica.json` da tabela oficial da Receita, normalizar sem acento e em maiúsculas, e testar com todas as descrições já vistas nas respostas da Fase 0 e dos 49 casos.

### B13 - CPF completo no banco

- `sancao_registro` (T8c) guarda `documento` completo de pessoa física e a linha original em JSONB; o mesmo valeria para as listas do TCU.
- Mesmo com LGPD adiada (D9), falta a regra: quem acessa, se o CPF completo precisa ser guardado (o casamento só usa nome + 6 dígitos) e por quanto tempo.
- Proposta: guardar só nome normalizado + 6 dígitos + DV dos 2 últimos para as PF; o arquivo bruto fica em `var/` com acesso local.

### B14 - Tempo do Mapa dentro do prazo

- Ver Q38; nenhum documento define quantas chamadas o adapter faz.

### B15 - Concorrência entre usuários

- O limite por host é por processo (T6e), mas não há regra para duas consultas ao mesmo CNPJ ao mesmo tempo (duas chamadas ao TCU).
- Proposta: coalescer chamadas iguais em andamento (mesma fonte e chave) dentro do processo.

### B16 - Precedência de mensagens quando há várias restrições

- Com Q1 = B, uma entidade pode ter 5 restrições; falta a ordem de exibição.
- Proposta: cadastrais, depois TCU/CNIA, CEPIM, CEIS, CNEP; dentro de cada uma, vigentes por data final mais distante.

### B17 - Contestação de falso positivo

- Não há canal para a OSC dizer "esse dirigente não sou eu" ou "a sanção foi suspensa".
- Proposta para o MVP: texto com o órgão responsável e o link oficial; canal próprio fica para depois.

### B18 - Atribuição das fontes

- O relatório cita fontes, mas não há regra de crédito e licença (OpenCNPJ, Portal, TCU, Ipea, Imprensa Nacional).
- Proposta: rodapé com fonte, data da base e link de cada uma.

### B19 - Teste de contrato das bases locais

- T13 cobre fontes on-line com testes vivos; para os CSV e XLS, a sanidade da carga (T5c) não define limites (linhas mínimas, colunas).
- Proposta: limites por fonte na configuração, com valor inicial de 80% da carga anterior.

### B20 - Relatório quando a entrada foi filial

- D5 manda explicitar, mas não há layout: qual CNPJ aparece no título, como mostrar "consultado" x "avaliado" (T9c tem os campos, a página não).

### B21 - Data de referência na interface

- O replay fixa `data_referencia`, mas não está definido se o usuário pode escolher outra data (ex.: data da assinatura da parceria).
- Proposta: não no MVP; o campo existe só nos testes.

### B22 - Mensagem para QSA sem pessoa física

- Entidades cujo QSA só tem PJ ou está vazio não têm regra; hoje cairiam em OK.
- Proposta: NAO_VERIFICADO com "o cadastro não informa dirigentes pessoas físicas".

---

## 4. Correções mecânicas (aplicar depois das decisões, não agora)

### 4.1 `decisoes.md`

- D3: reescrever com a ordem "vigência primeiro, divergência depois" e trocar "Portal" por "CSV/OpenCNPJ" (X2).
- D5: remover "aguarda confirmação do comportamento real no teste T7" (feito); acrescentar as regras de Q4, Q20, Q27, Q28 e Q44.
- D15: atualizar com Q8 e Q22; fechar P6.
- D18: status Decidido depois de Q7.
- Novas decisões D19 em diante para cada pergunta fechada (citar o Q correspondente).
- P3: o exemplo de CNIA com ocorrência já existe (C35, C36); sobra só a conferência opcional de headers.
- R1: apontar para as perguntas Q1, Q4, Q5, Q6, Q10 a Q13; R2: Feito (esta revisão).
- A2: registrar que a fonte alternativa de inidôneos é a Plataforma de Certidões (Q34).
- "Dependem de terceiros": remover "E-mail com a chave do Portal".
- F1: registrar que os casos serão gerados de novo depois das decisões.

### 4.2 `validador_osc_especificacao_mvp.md` (vira v1.2)

- Histórico: nova linha 1.2; "D1 a D17" vira "D1 a D18 e seguintes".
- Remover a seção "Pendente de aprovação" e todos os marcadores `[PROPOSTA D14]` a `[PROPOSTA D17]`.
- 2.2: tirar "Portal com chave (opcional)"; acrescentar CSV local, lista de inidôneos e listas de dirigentes; refletir Q1 e Q26; cache por fonte em vez de cache da consulta inteira.
- 2.5: incluir NAO_VERIFICADO (Q2), remover a pendência D4, reescrever o parágrafo do D3 (X2) e, se Q3 = B, o status `CNPJ_INVALIDO`.
- 3: tabela com as fontes do D14 decidido e os ids do Q25; remover o parágrafo da chave.
- 4.4: rótulo do status do DV conforme Q3.
- 5.3: grafias "Inapta" e "Suspensa" confirmadas (C09, C10); "Nula" ainda sem exemplo.
- 5.4: motivo `NAO_ENCONTRADO` (Q26) e limite do espelho (Q6).
- 5.5: trocar as pendências pelas regras de Q4, Q20, Q27, Q28 e Q44.
- 6.3 e 7.3: remover `[ORIENTADOR]` depois de Q14 e Q15.
- 8: nota de reativação conforme Q23.
- 9.3, 10.3, 11.3: fontes do D14 decidido; 9.4 conforme Q18; 10.4 e 10.5 conforme Q7, Q17 e Q35; 11.4 e 11.5 conforme Q16.
- 12.3: condição de OK do Q33 e regra do CNIA do Q19; 12.4: exemplo de CNIA obtido (C35).
- 13: fontes e regra de Q8 e Q22; remover a frase sobre P6; acrescentar o limite "QSA costuma ter só o presidente".
- 13 ou capítulo novo: verificação `tcu_contas_irregulares` se Q21 = B.
- 14.3: seções consultadas (Q38) e rótulos de situação (Q40).
- 15.3: linhas de "pedido em análise" (Q31) e "possível renovação" com idade (Q24); rótulos do Q40.
- 16: incluir art. 39, III e § 2º e tribunais de contas não cobertos (B9).
- 17: papéis e selos das fontes; testes de 30/09 e 01/10/2026; Portal com chave como "ferramenta manual".
- 18.3: remover a pendência do INAPTO.
- 18A.3: remover a pendência e documentar os campos de `?datasets=` a partir das respostas salvas.
- 19: introdução, 19.1 (selo EXECUTADO com chave) e 19.4 (resultados do roteiro), e o papel de "conferência manual".
- 20.2: linha `CONSTAM_REGISTROS` separando Inidôneos e CNIA de CEIS e CNEP (D18).
- 20.3: resolver a pendência conforme Q34.
- 22.5 e 22.6: período do DOU (Q39), tipos de ato e vigência como data (Q43), bloco de explicação (B7).
- 23: regra de intervalo do Q37.
- 24.2, 24.3, 24.4: adotar T4, T9c e T7b (Q41, Q36).
- 25.1: remover "Faltam: associação INAPTA e CNIA"; listar os casos ainda não encontrados de `casos_referencia.md`.
- 25.3 e 26.2: atualizar o que está pronto e o que falta (passos 9, 11, 12, 13, 16 e 18).

### 4.3 `arquitetura.md`

- Cabeçalho: D1 a D18; D14 a D17 decididos.
- Estado atual: `casos_referencia.json` já existe.
- T3b: catálogo final do Q25 (e `tcu_contas_irregulares` se Q21 = B); fontes de `dirigentes` do Q8.
- T3c', T3e e T3h: trocar [DECIDIR] pelas respostas de Q5, Q4 e Q1; se Q1 = B, remover `precisa_fanout`.
- T3d: regra "vigência antes da divergência" (D18) e o tratamento do Q35.
- T3g: alinhar com Q26 e Q33.
- T4: "Revisão do 24.1" vira "24.2"; T9c: "24.2 revisado" vira "24.3".
- T5a: CSV da CGU como observação principal desde o início; novas bases locais (inidôneos, listas de dirigentes, TCE-SP); DOU desde 12/2023 (Q39).
- T5b: reescrever sem "plano B"; remover a pendência de exemplo positivo de `?datasets=`.
- T5d: valores do Q6 com as bases novas.
- T6a e T6b: orçamento de tempo do B10.
- T6e: regra do Q37.
- T8c: tabelas das listas novas, política de CPF do B13, `carga.fonte` com os nomes novos.
- T9b e T9e: regras do Q9 e do B4.
- T11a: remover `PORTAL_API_KEY` (ou marcar como uso só em script manual).
- T17: R4 resolvido; R5 reescrito conforme D18.
- T18: ingestão dos CSV da CGU entra junto com o TCU (fatia 3 ou 4 no mesmo marco); fatia 7 com C36 e os casos da ficha de dirigentes.
- Tabela-resumo e "Lista só das [DECIDIR]": atualizar.

### 4.4 `fase0/casos_referencia.md` e `montar_casos.py`

- Gerar de novo depois de Q1, Q4, Q7, Q16 a Q20, Q25, Q39 e Q40.
- Trocar as colunas 1 a 12 pelos ids do Q25.
- Se Q1 = B, `estado_sem_parada` vira o estado de fato em C08 a C11 e C39 a C46.
- Corrigir citações: A10 cita "Spec 10.3", mas a regra está no 10.4 e já usa "igual ou posterior"; A12 cita o spec 13.4 como busca só por nome, mas o 13.5 já usa nome + 6 dígitos.
- Marcar cada ambiguidade como resolvida, com o Q correspondente.

### 4.5 Fichas

- `fase0/brasilapi/ficha.md`: conclusão do T7 conforme Q4; pendência do INAPTO resolvida; teste de `?datasets=` feito.
- `fase0/tcu/ficha.md`: "cruzar com a BrasilAPI" vira "cruzar com a fonte cadastral"; nota do D18 sobre CEIS expirado; explicação de 129 x 91 (Q34).
- `fase0/portal/ficha.md`: título "sem chave" e a seção "O que ainda depende da chave" ficam históricas; Ficha C marcada como não usada (Q34).
- `fase0/portal/referencia_cnpjs.md`: remover "repetir na API com chave"; T4 respondido (busca só exata); recomendação conforme Q20; o CNPJ 07.408.449/0001-32 hoje se chama INSTITUTO ATUAR.
- `fase0/mapa_osc/ficha.md`: "ALERTA leve" vira ALERTA (D2); remover menções a score (D8); alfanumérico vira NAO_VERIFICADO (D4).
- `fase0/cebas_dou/ficha.md` e `parser_cebas.py`: tipos de ato e vigência como data (Q43).
- `fase0/dirigentes/ficha.md`: registrar as respostas de Q8, Q21 e Q22.

---

## 5. Veredito: o que falta para "pronto para codar"

A fatia 0 da arquitetura (git, uv, CI, Compose, migração do `cnpj.py` e do classificador CNAE) não depende de nenhuma pergunta aberta e pode começar já.
Só Q13 (visibilidade do repositório) afeta a fatia 0, e mesmo assim o repositório local pode nascer antes.
O motor (fatia 1 em diante) ainda não está pronto: faltam as respostas abaixo.

Checklist:

- [ ] DONO responde Q1 a Q9 (mudam regra e contrato; bloqueiam o motor).
- [ ] DONO responde Q10 a Q12 (bloqueiam só a página e o deploy; fatia 1 e fatia 8).
- [ ] ORIENTADOR responde Q14 a Q24; até a resposta, o motor usa a recomendação de cada uma como valor padrão configurável, e os casos marcam quais esperados dependem dela.
- [ ] Agente fecha Q25 a Q44 com as recomendações (salvo objeção do dono).
- [ ] Correções mecânicas da seção 4 aplicadas: spec v1.2 sem marcadores de proposta, `decisoes.md` com D19 em diante, arquitetura sem [DECIDIR] abertos.
- [ ] Carga do DOU desde 12/2023 e casos de CEBAS gerados de novo (Q39).
- [ ] `casos_referencia.md` e `.json` gerados de novo com o catálogo final, sem ambiguidade aberta.
- [ ] Rascunho do catálogo de mensagens (B1) e dos blocos fixos de CEBAS e de limites (B7, B9) para as verificações da fatia 1.
- [ ] Orçamento de tempo definido (B10) e seções do Mapa escolhidas (Q38).
- [ ] `natureza_juridica.json` gerado da tabela oficial e testado com as descrições do OpenCNPJ (B12).
- [ ] Política de CPF no banco definida (B13).
- [ ] Checagem de wheels do Python 3.14 e Docker no ar (R8 da arquitetura), que é a primeira tarefa da fatia 0.

---

## 6. Status das correções (01/10/2026)

Aplicado no mesmo dia, depois das respostas do dono (D19) e da autorização para fechar as perguntas técnicas pela recomendação (D20).
Arquivos alterados: `validador_osc_especificacao_mvp.md` (versão 1.2), `arquitetura.md`, `decisoes.md`, `fase0/casos/montar_casos.py`, `fase0/casos/fatos.py`, `fase0/casos/casos_def.py`, `fase0/casos_referencia.md` e `fase0/casos_referencia.json`.
Nenhuma coleta de rede foi refeita: os casos usam as respostas salvas em `fase0/casos/respostas/` e as bases locais já baixadas na Fase 0.

### 6.1 Contradições

| Item | Situação | Onde |
|---|---|---|
| X1 | Resolvida: CSV local principal, OpenCNPJ e TCU adicionais, API do Portal fora do motor e da configuração. | Spec 2.2, 3, 9.3, 10.3, 11.3, 17, 18A, 19; arquitetura T5a, T5b, T11a. |
| X2 | Resolvida: vigência pelas datas antes da divergência (D18); D3 com status atualizado. | Spec 2.5, 10.3, 10.5, 20.2; arquitetura T3d, R5. |
| X3 | Resolvida: seção "Pendente de aprovação" e marcadores `[PROPOSTA Dxx]` removidos; D18 decidido. | Spec, histórico 1.2. |
| X4 | Resolvida (Q2): eliminatória NAO_VERIFICADO leva a INCONCLUSIVA. | Spec 2.5. |
| X5 | Resolvida (Q25): catálogo de 15 ids com o número do spec como atributo; casos gerados de novo com essa chave. | Spec 2.6; arquitetura T3b; casos. |
| X6 | Resolvida (Q4): filial não ativa com matriz ativa = ALERTA em `estabelecimento`. A ficha da BrasilAPI ainda tem a conclusão antiga. | Spec 5.5; arquitetura T3e; caso C24. |
| X7 | Resolvida provisoriamente [ORIENTADOR Q20]: busca por raiz no CSV local; C38 virou INAPTA. | Spec 5.5, 10.5; arquitetura T3e; casos C26, C27, C38, C46. |
| X8 | Resolvida (Q1): sem parada antecipada. | Spec 2.2, 2.3; arquitetura T3h; casos C08 a C11 e C39 a C46. |
| X9 | Resolvida (Q26): motivo NAO_ENCONTRADO, BrasilAPI também no 404, sem fan-out. | Spec 5.4, 18.1; arquitetura T3g, T6c; caso C07. |
| X10 | Resolvida (Q33): OK do TCU com o cadastro confirmado. | Spec 12.3, 20.2; arquitetura T3g. |
| X11 | Resolvida (Q41): spec 24.2 e 24.3 adotam T4 e T9c; números de seção corrigidos na arquitetura. | Spec 24; arquitetura T4, T9c. |
| X12 | Resolvida (Q37). | Spec 21, 23; arquitetura T6e. |
| X13 | Resolvida (Q36): TTL de 24 h para a chamada com datasets. | Spec 24.4; arquitetura T7b. |
| X14 | Resolvida: INAPTA, SUSPENSA, CNIA com ocorrência e `?datasets=` com registros documentados; pendências do spec 1.1 removidas. | Spec 5.3, 10.5, 12.4, 18.3, 18A.3, 25.1, 25.3; `decisoes.md` P3. |
| X15 | Resolvida: Q22 aplicada como provisória, citação do A12 corrigida e fontes decididas pelo dono no Q8 (opção C, D15); P6 fechada. | Spec 13; arquitetura T3b, T5a, T5d, T8c, T13, T18; casos A12. |
| X16 | Resolvida (Q34): Plataforma de Certidões como segunda observação; ORDS não usado. A contagem do CSV foi conferida (129 linhas, 121 CNPJs, nenhuma PF); a diferença para os 91 do ORDS fica para a carga. | Spec 12.4, 20.3; `decisoes.md` A2. |
| X17 | Aberta: os dados do DOU de 12/2023 a 05/2026 não estão no disco (só jun a ago/2026). Os esperados de CEBAS afetados estão marcados [PENDENTE X17] (C16, C23, C25, C31, C44, C46). | Spec 22.5; casos. |
| X18 | Resolvida no texto (Q43); a correção do `parser_cebas.py` fica para a fatia 6. | Spec 22.6. |

### 6.2 Perguntas

- Q1 a Q7 e Q9 a Q13 (DONO): aplicadas conforme D19 no spec, na arquitetura (selos [DECIDIDO Qxx]) e nos casos.
- Q8 (DONO): resolvida pela opção C (D15): CEIS/CNEP, TCU contas irregulares (trânsito em julgado nos últimos 8 anos), TCU inabilitados (vigentes) e TCE-SP Terceiro Setor (nome + DV, CPF reconstituído só em memória e garantido por teste), sempre ALERTA; CPF completo e CNIA por CPF no pós-MVP.
  Aplicada no spec 1.2.1 (cap. 13 reescrito, fontes no cap. 17, idade máxima das listas do TCU de 7 dias e do TCE-SP de 45 dias), na arquitetura (T3b, T5a, T5d, T8c, T13 com o teste de proteção do CPF, T18 fatia 5) e nos casos; o marcador de pendência do Q8 saiu de todos os documentos.
- Q14 a Q24 (ORIENTADOR): aplicadas como regra provisória com o marcador [ORIENTADOR Qxx] no spec e na arquitetura; nos casos, Q16 a Q24 são parâmetros de `REGRAS_ORIENTADOR` em `montar_casos.py`, e Q14 e Q15 ficam nas tabelas de natureza e CNAE; cada esperado afetado traz o marcador em `depende_de`.
- Q25 a Q44 (TECNICO): fechadas pela recomendação e resumidas em D20.

Efeitos nos casos de referência (49 casos e 11 variantes): status final APTA 7, APTA COM RESSALVAS 12, CNPJ INVÁLIDO 3, INAPTA 24, INCONCLUSIVA 3.
Mudanças de status em relação à versão anterior: C02 a C04 viraram CNPJ_INVALIDO (Q3); C34 virou APTA COM RESSALVAS (CNEP só de multa, Q16); C38 virou INAPTA (sanção da filial pela raiz, Q20).
C08 a C11 e C39 a C46 agora mostram todas as verificações (Q1), e C40, C42 e C46 têm ALERTA em `tcu_contas_irregulares` (Q21).
Com o Q8, `dirigentes` passou de OK para ALERTA em C40 e C42 (TCU contas irregulares) e em C41, C44 e C46 (TCE-SP, nome + DV); C28 e C36 ganharam achado do TCU fora da janela de 8 anos, só como informação, e C29 um homônimo só por nome.
Nenhum status final mudou, porque essas entidades já eram INAPTAS.

### 6.3 Buracos

Todos os 22 têm definição concreta: B1, B7, B8, B9, B12, B14, B16, B17, B18, B20, B21 e B22 no spec (2.7, 6.1, 13.5, 14.3, 22.7); B2, B3, B4, B5, B6, B10, B11, B13, B15 e B19 na arquitetura (T3i, T5c, T5d, T6a, T6e, T8c, T9b), com B5 e B6 também no spec (5.4, 24.4).
Os que seguem a recomendação mas são escolhas de produto e podem ser revistos pelo dono: B13 (prazo de retenção do arquivo bruto com CPF completo), B17 (sem canal próprio de contestação no MVP), B21 (usuário não escolhe a data de referência) e a retenção limitada das consultas (Q9, opção C, adiada para a LGPD).

### 6.4 O que resta

Checklist da seção 5:

- [x] DONO responde Q1 a Q9 (Q8 respondida depois, opção C, D15).
- [x] DONO responde Q10 a Q12 (e Q13).
- [ ] ORIENTADOR responde Q14 a Q24; até lá as recomendações valem como regra provisória configurável e os casos marcam os esperados que dependem delas (feito).
- [x] Agente fecha Q25 a Q44 com as recomendações (D20).
- [ ] Correções mecânicas da seção 4: spec 1.2, `decisoes.md` (D19, D20, P3, P6, A2, R1, R2, F1, F2) e arquitetura sem [DECIDIR] aplicados; faltam as fichas da seção 4.5 (brasilapi, tcu, portal, referencia_cnpjs, mapa_osc, cebas_dou, dirigentes), que não foram tocadas nesta rodada; o texto de D3, D5 e D15 em `decisoes.md` não foi reescrito (só o status), por regra do dono.
- [ ] Carga do DOU desde 12/2023 e casos de CEBAS gerados de novo (Q39, X17).
- [x] `casos_referencia.md` e `.json` gerados de novo com o catálogo final; as ambiguidades A01 a A17 estão marcadas como resolvidas ou provisórias.
- [ ] Rascunho do catálogo de mensagens (B1): estrutura e regras definidas no spec 2.7, e blocos fixos de CEBAS e de limites (B7, B9) escritos no spec 22.7 e 2.7; falta o arquivo `mensagens.json` com as frases de cada par (fatia 7).
- [x] Orçamento de tempo definido (B10) e seções do Mapa escolhidas (Q38).
- [ ] `natureza_juridica.json` gerado da tabela oficial e testado com as descrições do OpenCNPJ (B12): regra definida no spec 6.1, arquivo a fazer na fatia 1.
- [x] Política de CPF no banco definida (B13).
- [ ] Checagem de wheels do Python 3.14 e Docker no ar (R8 da arquitetura), primeira tarefa da fatia 0.

Veredito atualizado: as fatias 0 a 5 podem começar; só a fatia 6 depende da carga do DOU.
