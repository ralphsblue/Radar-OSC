# Decisões e pendências do MVP

Arquivo único de acompanhamento da Fase 0 (antes de codar o motor).
Quando uma decisão alterar o spec (`validador_osc_especificacao_mvp.md`), o capítulo afetado deve ser atualizado e a decisão citada aqui.
Objetivo imediato: MVP funcional para aprovação do projeto.

## Decisões

| # | Tema | Decisão | Status |
|---|---|---|---|
| D1 | Stack | FastAPI + httpx + PostgreSQL (cache, log e evidências). Fila (RQ/Celery) só se houver processamento em lote. Cada fonte atrás de um adapter com interface comum. | Decidido |
| D2 | Mapa das OSCs ausente | Gera ALERTA, que leva o status final a APTA COM RESSALVAS. O relatório explica a situação. | Decidido |
| D3 | Divergência entre fontes | Primeiro avalia-se a vigência de cada registro pelas datas (D18). Depois, se uma fonte tem registro vigente e outra não, vence RESTRICAO. O relatório mostra as respostas de cada fonte. | Decidido (texto atualizado em 01/10/2026) |
| D4 | CNPJ alfanumérico | Fora do MVP nas consultas. O DV aceita alfanumérico; as fontes recebem apenas CNPJ numérico e o alfanumérico gera NAO_VERIFICADO com mensagem explicativa. | Decidido |
| D5 | Filial | Ser filial não reprova. Detecta por `identificador_matriz_filial = 2` (nunca pela ordem: há matriz fora da 0001) e resolve para a matriz. Se raiz+0001 não for a matriz: ALERTA pedindo o CNPJ da matriz. Situação: matriz não ativa = RESTRICAO; filial não ativa com matriz ativa = ALERTA em `estabelecimento` (Q4). Natureza e QSA: da raiz. Tempo de existência: da matriz. Sanções: busca por raiz no CSV local, alcança a entidade inteira [ORIENTADOR Q20]. CNAE: considera os dois. Mapa e CEBAS: pela matriz. Relatório explicita que a consulta partiu de filial. | Decidido (texto atualizado em 01/10/2026) |
| D6 | Esfera da parceria e tempo de existência | Parâmetro `esfera` opcional (municipio, estado, uniao). Informado: OK se atinge o prazo da esfera (1, 2 ou 3 anos), ALERTA se não. Não informado: relatório mostra os 3 cenários; OK só com 3 anos ou mais, senão ALERTA listando as esferas atendidas. | Decidido |
| D7 | Classificação CNAE | Tabela completa (1.332 subclasses IBGE), regras hierárquicas, prefixo mais específico vence, padrão BAIXA. Alerta religioso é regra separada: (natureza 3220 OU CNAE principal 9491000) E nenhum CNAE em ALTA. Proposta em `fase0/cnae/proposta.md`. | Proposto; 8 pontos valem como regra provisória [ORIENTADOR Q15] até o orientador |
| D8 | Score | Removido do MVP. Resultado = status final + achados + explicações. Volta quando houver casos reais para calibrar. | Decidido |
| D9 | LGPD | Fora do escopo do MVP. Tratar se o projeto for aprovado (retenção, acesso, exibição de nomes de dirigentes). | Adiado |
| D10 | Usuário | OSC, prefeitura e público em geral. Não muda o escopo do motor; o parâmetro `esfera` cobre a diferença principal. | Decidido |
| D11 | DV do CNPJ | Código próprio em `validador_osc/cnpj.py` (sem biblioteca). Nenhuma lib informa motivo e DV esperado; 5 de 6 aceitam base repetida. Repetição é checada na base de 12 posições. Comparativo em `fase0/dv/ficha.md`. | Feito (36 testes) |
| D13 | TCU como fonte | Consulta Consolidada vira a fonte da verificação 9 e cobre CEIS e CNEP sem chave. CNPJ inexistente volta NADA_CONSTA com `seCnpjEncontradoNaBaseTcu: false`: o motor nunca conclui OK sem a BrasilAPI ter confirmado o CNPJ. Fallback do cap. 20.3 (Playwright/APEX) descartado. | Decidido; condição de OK pela fonte cadastral (OpenCNPJ ou BrasilAPI) por Q33 (D20) |
| D14 | Fonte das sanções | Sem chave do Portal em produção: a chave é vinculada ao CPF de uma pessoa física e não serve para operar o sistema. Fontes: CSV diário oficial de CEIS/CNEP/CEPIM importado localmente (datas e vigência, sem chave) + OpenCNPJ `?datasets=` + Consulta Consolidada TCU (Inidôneos, CNIA e cruzamento de CEIS/CNEP). Vigência sempre pela data de fim (ver D18). CEPIM sem datas: registro presente = RESTRICAO. A API do Portal com chave será testada só para documentar trade-offs (P2). | Decidido (01/10/2026); aplicado no spec 1.2 e na arquitetura (X1 resolvida) |
| D15 | Dirigentes | Opção C (Q8, 01/10/2026): nome do QSA + 6 dígitos do meio do CPF contra CEIS/CNEP (CSV oficial), TCU contas irregulares (trânsito em julgado nos últimos 8 anos), TCU inabilitados (vigentes) e TCE-SP Terceiro Setor (CPF reconstituído só em memória, nunca gravado nem exibido, garantido por teste). Sempre ALERTA; correspondência só por nome nunca gera achado; relatório avisa que o QSA costuma trazer só o presidente. CPF completo informado pelo usuário e CNIA por CPF ficam para o pós-MVP (com D9). | Decidido |
| D16 | Fonte do CEBAS | Saúde: lista pública do SisCEBAS Saúde (principal) + DOU como evidência. MDS e MEC: planilha oficial (corte 2024/2023) + atos do DOU posteriores ao corte; último ato vale. Tipos de ato ganham PRORROGACAO e ARQUIVAMENTO; reconsideração e "torna sem efeito" anulam o ato anterior; validade vencida sem ato novo = "possível renovação em análise". As nuances (defasagem, cobertura por ministério, ausência não prova nada) devem estar documentadas no spec e explicadas no relatório. | Decidido (01/10/2026); DOU desde 12/2023 (Q39), carga pendente (X17); bloco "Sobre o CEBAS" no spec 22.7 |
| D17 | Fonte cadastral | MVP: OpenCNPJ principal com conversor (natureza texto -> código; situação e matriz/filial texto -> número; "" -> null; natureza desconhecida = ALERTA), BrasilAPI fallback (timeout ~12 s, 5xx, retry-after). Base própria da Receita fica para o projeto pós-MVP, não para o MVP. | Decidido (01/10/2026) |
| D18 | Vigência das sanções x TCU (achado 01/10/2026) | A Consulta Consolidada do TCU devolve CEIS `CONSTAM_REGISTROS` também para sanções expiradas (testado: 03126200000183 fim 18/11/2021; 07408449000132 fim 07/04/2022); a `observacao` traz só a data de fim entre parênteses. Logo: vigência de CEIS/CNEP vem das datas (OpenCNPJ datasets ou CSV); `CONSTAM_REGISTROS` do TCU com todas as sanções expiradas não é divergência (D3 só se aplica depois de avaliar vigência). Exemplo positivo do `?datasets=` salvo em `fase0/brasilapi/respostas/extras/`. | Decidido (01/10/2026, Q7). D3 passa a valer só depois de avaliar a vigência. |
| D19 | Respostas da revisão (`revisao_pre_codigo.md`, 01/10/2026) | Q1: consultar e mostrar sanções mesmo de entidade já INAPTA (status segue INAPTA). Q2: alfanumérico = INCONCLUSIVA com mensagem própria. Q3: DV/formato inválido = status próprio CNPJ_INVALIDO (erro de digitação), não INAPTA. Q4: filial não ativa com matriz ativa = ALERTA. Q5: verificação não eliminatória indisponível não muda o status, mas o usuário é avisado de forma explícita (aviso em destaque, não só lista). Q6: idade máxima CEIS/CNEP 3 dias, CEPIM e SisCEBAS 7, DOU 75; espelho cadastral > 60 dias = ALERTA. Q7: D18 aprovado. Q9: link da consulta aberto; nomes de dirigentes só para operador. Q10: interface simples, HTML + CSS + JS simples servidos pelo app. Q11: CSS de impressão (sem PDF no servidor). Q12: demonstração local, túnel se necessário. Q13: repositório privado até a aprovação. Q8 em aberto. | Decidido; aplicado no spec 1.2, na arquitetura e nos casos (01/10/2026) |
| D20 | Decisões técnicas da revisão (Q25 a Q44) | Fechadas pela recomendação de `revisao_pre_codigo.md`, seção 2.3, com autorização do dono. Principais: catálogo de 15 ids com o número do spec como atributo (Q25); CNPJ não encontrado = `situacao` INDISPONIVEL com motivo NAO_ENCONTRADO, sem fan-out (Q26); matriz só por `matriz_filial` (Q27); Mapa pela matriz e CEBAS pela matriz e pelo consultado (Q28); vigência inclusive no último dia (Q30); registro só no TCU pelas datas da `observacao` (Q35); OpenCNPJ datasets como observação adicional com TTL 24 h (Q36); intervalo por host só para TCU e Mapa (Q37); 5 seções do Mapa (Q38); DOU desde 12/2023 (Q39); `situacao` própria nas informativas (Q40); contrato `Coleta[T]` e resultado da arquitetura no spec (Q41); lista de inidôneos da Plataforma de Certidões como segunda observação (Q34). Detalhe de cada uma na revisão. | Decidido (01/10/2026) |
| D21 | Escolhas de produto restantes (01/10/2026) | B13: bruto com CPF completo só em disco local, fora do git e do banco, apagado na carga seguinte. B17: sem canal de contestação no MVP; relatório orienta conferir a fonte oficial. B21: data de referência sempre a da consulta. Repositório: git local apenas (sem remoto) por enquanto. | Decidido |
| D22 | Achados da fatia 1 (01/10/2026) | (1) OpenCNPJ `?datasets=` devolve só as chaves pedidas, sem o cadastro: cadastro e sanções exigem duas chamadas (corrige spec 18A/Q36 e arquitetura T5b/T7b; a fatia 3 trata como fonte separada com TTL próprio). (2) `data_base` do OpenCNPJ vem de `/info` (`last_updated` em UTC convertido para Brasília). (3) Natureza: tabela oficial da Receita (dados abertos do CNPJ, 89 códigos); 2330 Cooperativas de Consumo entrou como REVISAO_MANUAL [ORIENTADOR Q14]. (4) A recarga automática do uvicorn trava no Windows com log redirecionado: no desenvolvimento local, subir sem `--recarregar`. (5) Prazo global da consulta mantido em 20 s (`VOSC_PRAZO_CONSULTA_S`), ajustável. | Registrado |
| D23 | Achados da fatia 2 (01/10/2026) | (1) BrasilAPI devolve 200 para CNPJ alfanumérico real (00000000E08G12); o 404 da Fase 0 era do exemplo fictício. Nada muda no MVP (D4 mantém alfanumérico fora das consultas). (2) BrasilAPI e OpenCNPJ dão o mesmo cadastro para os 9 CNPJs comparados, exceto a ordem do QSA. (3) BrasilAPI com 1 tentativa só (reserva, T6b); OpenCNPJ com 3. (4) Matriz identificada só pelo campo matriz/filial do cadastro de raiz+0001; se não for matriz ou não existir, ALERTA pedindo o CNPJ da matriz (Q27). | Registrado |
| D24 | Fatia 3, decisões técnicas (02/10/2026) | (1) OpenCNPJ `?datasets=` fora do MVP: o CSV oficial da CGU é a observação principal das sanções e o TCU o cruzamento; uma chamada a mais por consulta sem dado novo (ajusta D14 e T5b). (2) Retenção das bases locais: linhas só da carga ativa e da anterior; metadados de toda carga (data, sha256, status) ficam para sempre. (3) Sanidade da carga: queda de linhas acima de 50% em relação à ativa = FALHOU (T5c dizia 80%). (4) CPFs completos achados em campos de texto livre do CEIS são mascarados na ingestão; o banco recusa documento de 11 dígitos (CHECK). (5) Registro só no TCU: histórico apenas se houver uma data legível por registro e todas passadas (Q35); a observação pode juntar vários registros. (6) Parâmetros do orientador em `dados/regras_orientador.json` e idades em `dados/limites.json`, ambos na `versao_regras`. | Decidido |
| D25 | Fatia 7, mensagens e relatório (05/10/2026) | (1) Mensagens ficam no código de cada verificação (um módulo por regra, cobertas pelos testes), em vez de um `mensagens.json` (B1): no MVP o texto muda junto com a regra e o JSON só duplicaria a lógica. Revisitar se houver tradução ou edição por não programadores. (2) B8: cada verificação traz `consulta_manual` com o link oficial para conferência. (3) B18: o relatório lista as fontes consultadas com a data da base e o link. (4) B16: a ordem de exibição segue o catálogo (cadastrais, sanções, TCU/CNJ, dirigentes, Mapa, CEBAS). (5) B9 e B20 já estavam na página. | Decidido |
| D12 | Pedidos LAI do CEBAS | Não bloqueante. Fazer depois do MVP pronto, para medir cobertura da fonte do CEBAS. | Adiado |

## Pendências

### Com o dono do projeto (manual)

| # | Pendência | Depende de | Status |
|---|---|---|---|
| P1 | Chave da API do Portal obtida e guardada no `.env` (nunca ler/expor). Uso só para teste/documentação (D14). | - | Feito |
| P2 | Testes do Portal T1 a T8 com chave. Resultado: API tem a mesma data de referência do CSV diário, busca só exata (sem raiz), página de 15, nome parcial e amplo. Confirma D14: sem chave em produção. Ver `fase0/portal/ficha.md`. | P1 | Feito (01/10/2026) |
| P3 | (Opcional) DevTools na Consulta Consolidada do TCU para conferir headers do navegador; conseguir CNPJ com ocorrência no CNIA (CNJ). Passo a passo em `fase0/tcu/ficha.md`. | - | CNIA com ocorrência obtido (C35, C36, C39, C46); resta só a conferência opcional de headers |
| P4 | (Opcional) Mapa das OSCs: conferir no DevTools as chamadas da página da OSC; achar um certificado autodeclarado real; e-mail a mapaosc@gmail.com sobre limite de uso e periodicidade da carga de CEBAS. | - | Opcional |
| P5 | (Opcional) Cadastro no INLABS para XML diário do DOU (passo a passo na seção 10 de `fase0/cebas_dou/ficha.md`). O XML mensal sem login basta para o MVP. Retestar `siscebas2.mec.gov.br` (sem DNS em 30/09/2026). | - | Opcional |
| P6 | Dirigentes: pesquisa feita (`fase0/dirigentes/ficha.md`). Proposta de ampliar D15 com TCU contas irregulares (8 anos), TCU inabilitados e TCE-SP Terceiro Setor, sempre ALERTA; CNIA só com CPF completo (pós-MVP); incisos III e § 2º sem cobertura. Sugestão extra: lista de PJ condenadas do TCU para a própria OSC (inciso VI). | Pesquisa | Resolvida: dono decidiu o Q8 pela opção C em 01/10/2026 (ver D15), aplicada no spec 1.2.1 (cap. 13), na arquitetura e nos casos; inciso VI aplicado como provisório [ORIENTADOR Q21] |

### Com o orientador

| # | Pendência | Status |
|---|---|---|
| O1 | Validar tabela de natureza jurídica (cap. 6.3): revisão manual de 214-3, 330-1, 320-4; exclusão de 307-7. | Reenviar (mensagem anterior não chegou); unificada com Q14-Q24; vale como provisória [ORIENTADOR Q14] |
| O2 | Validar os 8 pontos marcados em `fase0/cnae/proposta.md` (ex.: 94.93 em ALTA, saúde 86 inteira em ALTA, esporte em MEDIA, maçonaria no alerta religioso). | Reenviar (mensagem anterior não chegou); unificada com Q14-Q24; vale como provisória [ORIENTADOR Q15] |
| O3 | Informar que o score saiu do MVP (D8). | Reenviar (mensagem anterior não chegou); unificada com Q14-Q24 |

### Agentes em execução (Fase 0)

| # | Pendência | Saída | Status |
|---|---|---|---|
| A1 | BrasilAPI repassa para a Minha Receita (mesmos campos; caem juntas: 5xx após ~10 s, 77 respostas 503 em 2 h). OpenCNPJ estável (mediana 74 ms), dados de 15/09/2026, já tem alfanumérico real, mas natureza/situação/matriz-filial só em texto. Filial: raiz+0001 devolve a matriz; data de início e situação são da própria filial; QSA igual. `?datasets=ceis,cepim,cnep` do OpenCNPJ traz sanções do Portal (confirmado com Santa Casa de Pacaembu). CNPJs de referência em `fase0/brasilapi/ficha.md`. Pendentes: T3 e T5r na BrasilAPI (`retentar_pendentes.sh`). | `fase0/brasilapi/` | Feito |
| A2 | Downloads diários CEPIM/CEIS/CNEP sem chave (CSV ISO-8859-1, `;`). OpenAPI do Portal baixado sem chave; filtro por nome existe nas 3 rotas. API JSON aberta de inidôneos do TCU (`contas.tcu.gov.br/ords/condenacao/consulta/inidoneos`, filtro com CNPJ formatado). 13 CNPJs de referência com restrição em `fase0/portal/referencia_cnpjs.md`. Cruzamento IMDC e Santa Casa de Pacaembu com a Consulta Consolidada do TCU bateu. | `fase0/portal/` | Feito; fonte alternativa de inidôneos = Plataforma de Certidões, não o ORDS (Q34, X16 resolvida) |
| A3 | Mapa das OSCs: API REST pública do Ipea sem token (`mapaosc.ipea.gov.br/api/api/`). `busca/cnpj/{cnpj}` dá `id_osc` (busca por prefixo: filtrar igualdade; CNPJ sem zeros à esquerda); perfil em `osc/{secao}/{id_osc}`. Preenchido pela OSC = valor não vazio com `ft_* == "Representante de OSC"` ou `bo_oficial == false`. Certificados incluem CEBAS oficial, mas defasado. Base CSV 344 MB e 3 planilhas oficiais de CEBAS (MEC/MS/MDS, 2024) baixadas. Não usar a rota `representantes/...` (dados pessoais). | `fase0/mapa_osc/` | Feito |
| A4 | CEBAS: DOU viável (CNPJ em 99,7% dos atos, parser 20/20 correto, ~110 atos/mês, XML mensal sem login, defasagem 2 a 6 semanas). SisCEBAS Saúde tem lista pública XLS viva (4.458 CNPJs, 1.642 com CEBAS, cobriu 287/287 do DOU). MDS e MEC: só planilhas oficiais de 2023/2024 (via Mapa OSC); sem base viva. | `fase0/cebas_dou/` | Feito |
| A5 | TCU: endpoint oficial achado, sem CAPTCHA. `GET certidoes-apf.apps.tcu.gov.br/api/rest/publico/certidoes/{cnpj}?seEmitirPDF=false` devolve Inidôneos TCU, CNIA, CEIS e CNEP. APEX de inidôneos foi desativado; substituto: certidoes.apps.tcu.gov.br (CSV completo). | `fase0/tcu/` | Feito |

### Arquitetura (`arquitetura.md`, T1 a T18)

| # | Pendência | Status |
|---|---|---|
| R1 | Dono decidir os 8 itens [DECIDIR]: T10 interface, T16 PDF, T14c onde demonstrar, T15a repositório público/privado e licença, T5d idade máxima das bases locais, T3h consultar sanções de quem já é INAPTA, T3c ALERTA indisponível, T3e filial baixada com matriz ativa. | Resolvida (D19: Q10, Q11, Q12, Q13, Q6, Q1, Q5, Q4); arquitetura sem [DECIDIR] abertos; T5d completado com as bases do Q8 (listas do TCU 7 dias, TCE-SP 45 dias) |
| R2 | Revisão cruzada feita e aplicada (`revisao_pre_codigo.md`, seção 6). Q1-Q13 respondidas (D19, D15 para Q8); Q14-Q24 aguardam orientador como regras provisórias; Q25-Q44 adotadas (D20). | Feito |

### Depois da Fase 0

| # | Pendência | Depende de |
|---|---|---|
| F1 | Conjunto de referência: 49 casos + 11 variantes, reconsultados em 01/10/2026, esperado das 12 verificações por caso (`fase0/casos_referencia.md`/`.json`, gerado por `fase0/casos/montar_casos.py`). 17 ambiguidades de regra (A01 a A17). Faltaram: OSC ativa ausente do Mapa isolada, OSC ativa inidônea TCU, dirigente sancionado em entidade limpa, situação NULA, CEBAS MEC, certificado autodeclarado; INDISPONIVEL só por simulação. | Feito; gerado de novo em 01/10/2026 com os 15 ids (Q25) e as decisões D19/D20, A01 a A17 marcadas como resolvidas ou provisórias; casos de CEBAS MDS/MEC a gerar de novo depois da carga do DOU (X17) |
| F2 | Atualizar o spec com as decisões D2 a D11 e os retornos reais das fontes. | Feito (spec 1.1 e 1.2) |
| F3 | Codar o motor: adapters, cache, agregação, API FastAPI. | Tudo acima |
| F4 | Pedidos LAI do CEBAS (D12). | MVP pronto |
| F5 | LGPD (D9). | Aprovação do projeto |

### Dependem de terceiros

- Disponibilidade do orientador (O1 a O3 e Q14 a Q24).

- Resposta da LAI, até 30 dias (após F4).
- Teste da chamada ao TCU a partir do IP do servidor (bloqueio de datacenter?), quando houver servidor.
- Publicação de base aberta oficial do CEBAS pelos ministérios (sendo verificada em A4).
