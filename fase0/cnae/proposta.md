# Proposta: classificação CNAE de relevância social (Verificação 4)

Este documento substitui a tabela 7.3 do spec por uma classificação completa e sem ambiguidade de todas as 1.332 subclasses da CNAE 2.3.
Os pontos que precisam do aval do orientador estão marcados com **[DECISÃO DO ORIENTADOR]**.

## 1. Problemas da tabela 7.3 atual

A tabela lista divisões e classes soltas e não diz o que acontece com as demais subclasses.
A subclasse 94.91-0 (organizações religiosas) aparece como MÉDIA e, ao mesmo tempo, "com alerta", misturando faixa de aderência com a regra do art. 2º, I, c.
Não há regra de desempate quando uma divisão é ALTA e uma subclasse dela claramente não é (ex.: autoescola dentro de 85, educação).

## 2. Arquivos

| Arquivo | Conteúdo |
|---|---|
| `baixar_cnae.py` | Baixa seções, divisões, grupos, classes e subclasses da API v2 do IBGE. |
| `ibge_cnae_subclasses.json` | Estrutura completa: 21 seções, 87 divisões, 285 grupos, 673 classes, 1.332 subclasses (contagens oficiais da CNAE 2.3). |
| `regras_cnae.json` | Lista de regras `{prefixo, nivel, faixa, justificativa}` e a faixa padrão. |
| `classificar_cnae.py` | Aplica as regras, gera `cnae_classificado.csv` e expõe `classificar()` e `avaliar_entidade()` para o motor. |
| `cnae_classificado.csv` | Subclasse, descrição, faixa e regra aplicada para as 1.332 subclasses. |
| `test_classificar_cnae.py` | 22 testes (CNAEs de referência, normalização, regra religiosa). |

Para reproduzir: `.venv/Scripts/python fase0/cnae/baixar_cnae.py`, depois `.venv/Scripts/python fase0/cnae/classificar_cnae.py` e `.venv/Scripts/python -m pytest fase0/cnae -q`.

## 3. Como as regras funcionam

Cada regra tem um prefixo de 2 (divisão), 3 (grupo), 5 (classe) ou 7 dígitos (subclasse).
Para cada subclasse vence a regra de prefixo mais longo que casar, ou seja, a mais específica.
Se nenhuma regra casar, vale o padrão BAIXA.
O script valida as regras ao carregar: o prefixo precisa existir no nível declarado da CNAE do IBGE, não pode haver prefixo repetido e toda regra precisa de justificativa.
A entrada aceita qualquer formato (`9430800`, `94.30-8-00`, `9430-8/00`) e também o inteiro da BrasilAPI sem o zero à esquerda das divisões 01 a 09 (`111301` vira `0111301`).

Premissa importante: a faixa CNAE só é avaliada depois do filtro de natureza jurídica (cap. 6).
Uma subclasse como "coleta de resíduos" em MÉDIA não favorece empresas, porque uma LTDA já foi reprovada antes.
A pergunta que a faixa responde é: "para uma associação, fundação ou organização religiosa, este CNAE sinaliza atividade de relevância pública e social?".

Critério das faixas:

- **ALTA**: a atividade corresponde diretamente a uma finalidade do art. 84-C da Lei 13.019/2014 ou a uma área central do Mapa das OSCs (assistência social, saúde, educação e pesquisa, cultura, meio ambiente, defesa de direitos).
- **MEDIA**: a atividade é compatível com uma finalidade social, mas o CNAE sozinho não distingue o uso social do uso comercial ou de interesse particular (ex.: esporte, associativas genéricas, reciclagem, rádio).
- **BAIXA**: atividade econômica comum, de interesse de categoria, estatal ou vedada (padrão).

## 4. Regras propostas

### 4.1 ALTA

| Prefixo | Nível | Atividade | Base |
|---|---|---|---|
| 85 | divisão | Educação (exceções em 4.2 e 4.3) | art. 84-C, III |
| 86 | divisão | Atenção à saúde humana | art. 84-C, IV |
| 87 | divisão | Saúde integrada com assistência social em residências (exceção 8711-5/05) | art. 84-C, I e IV |
| 88 | divisão | Assistência social sem alojamento | art. 84-C, I |
| 90 | divisão | Artes, criação e espetáculos (exceções 9001-9/05 e 9001-9/06) | art. 84-C, II |
| 91 | divisão | Bibliotecas, museus, patrimônio, jardins botânicos, reservas ecológicas | art. 84-C, II e VI |
| 94.30-8 | classe | Defesa de direitos sociais (direitos humanos, meio ambiente, minorias) | art. 84-C, VI, X e XI |
| 94.93-6 | classe | Associações ligadas à cultura e à arte | art. 84-C, II |
| 72.20-7 | classe | P&D em ciências sociais e humanas | art. 84-C, XIII |
| 0220-9/06 | subclasse | Conservação de florestas nativas | art. 84-C, VI |
| 6499-9/05 | subclasse | Concessão de crédito pelas OSCIP (microcrédito) | art. 84-C, VIII e IX |

### 4.2 MEDIA

| Prefixo | Nível | Atividade | Motivo de não ser ALTA |
|---|---|---|---|
| 94.99-5 | classe | Associativas não especificadas | Abrange de associação comunitária e proteção animal a fã-clube e fraternidade. |
| 94.91-0 | classe | Organizações religiosas ou filosóficas | Pode ser OSC (art. 2º, I, c), mas o culto em si não é atividade social; ver seção 5. |
| 93.1 | grupo | Atividades esportivas (exceção 93.13-1) | Área do Mapa das OSCs, mas fora do art. 84-C; inclui clubes recreativos de sócios. |
| 38.11-4 e 38.3 | classe e grupo | Coleta de resíduos não perigosos e reciclagem | Típico de associações de catadores, mas também serviço comum. |
| 59.11-1 e 59.14-6 | classe | Produção e exibição audiovisual (exceção 5911-1/02) | Projeto cultural ou indústria comercial. |
| 60.10-1 | classe | Rádio | Rádios comunitárias são associações por lei (Lei 9.612/1998). |
| 72.10-0 | classe | P&D em ciências físicas e naturais | Também comum em P&D empresarial. |
| 7490-1/03 | subclasse | Agronomia e consultoria agropecuária | Inclui ATER para agricultura familiar. |
| 75.00-1 | classe | Atividades veterinárias | OSC de proteção animal costumam declarar clínica social e castração. |
| 85.93-7 | classe | Ensino de idiomas | Predominantemente comercial. |
| 8599-6/03, /04, /05 | subclasse | Informática, treinamento profissional, cursinhos | Inclusão digital e cursinho popular, mas em geral comercial. |
| 8711-5/05 | subclasse | Condomínios residenciais para idosos | Moradia com serviços, frequentemente comercial; diferente da ILPI (8711-5/02). |
| 9001-9/05 | subclasse | Rodeios e vaquejadas | Manifestação cultural (EC 96/2017), mas comercial e controversa. |

### 4.3 BAIXA explícita (documenta decisões; o padrão já seria BAIXA)

| Prefixo | Nível | Atividade | Motivo |
|---|---|---|---|
| 94.1 | grupo | Patronais, empresariais, profissionais e conselhos de fiscalização | Interesse de categoria, não público (spec 7.3). |
| 94.2 | grupo | Sindicatos | Interesse de categoria, regime próprio (spec 7.3). |
| 94.92-8 | classe | Organizações políticas | Art. 84-C, parágrafo único veda atuação político-partidária. |
| 84 | divisão | Administração pública | Atividade estatal. |
| 99 | divisão | Organismos internacionais | Não é OSC nacional. |
| 92 | divisão | Jogos de azar e apostas | Sem relação social. |
| 93.13-1 e 93.2 | classe e grupo | Academias, parques de diversão, danceterias | Entretenimento comercial. |
| 96.09-2 | classe | Serviços pessoais diversos (inclui hotel e banho e tosa de animais) | Comercial. |
| 8599-6/01 e 8599-6/02 | subclasse | Autoescola e cursos de pilotagem | Comercial. |
| 9001-9/06 | subclasse | Sonorização e iluminação | Serviço técnico, não produção cultural. |
| 5911-1/02 | subclasse | Filmes para publicidade | Comercial. |

## 5. Regra de alerta para organizações religiosas (art. 2º, I, c)

A faixa e o alerta passam a ser coisas separadas.
A faixa de 94.91-0 é sempre MEDIA e não carrega alerta nenhum.
O alerta do art. 2º, I, c vem de uma regra própria, avaliada sobre a entidade inteira:

```
ALERTA_RELIGIOSA =
    (natureza_juridica == 3220  OU  cnae_principal == 9491-0/00)
    E nenhum CNAE (principal ou secundário) em faixa ALTA
```

Mensagem: "Organização religiosa sem atividade social de alta aderência no CNAE: a Lei 13.019/2014, art. 2º, I, c, exige atividades de interesse público e de cunho social distintas das exclusivamente religiosas; confira estatuto e plano de trabalho."

Justificativa de cada parte:

- **Natureza 322-0** cobre quem se declara organização religiosa.
- **CNAE principal 94.91-0** cobre igrejas registradas como associação privada (399-9), o que é comum porque a natureza 322-0 só existe desde a Lei 10.825/2003. O art. 2º, I, c trata da organização religiosa pelo que ela é, não só pela forma jurídica.
- **Só o CNAE principal** conta no segundo gatilho. Uma associação de assistência social que tem 94.91-0 como secundário não é uma organização religiosa e não deve receber o alerta.
- **Exigir ALTA, e não MÉDIA**, é o que torna a regra objetiva. Os códigos MÉDIA (94.99-5 associativa genérica, esporte, a própria 94.91-0) não demonstram atividade social distinta da religiosa. Um 88.00-6 (assistência social) ou 85.13-9 (ensino fundamental) demonstra.
- **A regra não reprova**, como toda a verificação CNAE. Ela só pede revisão do estatuto.

Interação com o alerta CNAE do cap. 7.4 (nenhum CNAE em ALTA ou MÉDIA):

| Natureza | CNAE principal | Secundários | Alerta CNAE | Alerta religiosa |
|---|---|---|---|---|
| 322-0 | 94.91-0 | nenhum | não (MEDIA) | **sim** |
| 322-0 | 94.91-0 | 94.99-5 | não | **sim** |
| 322-0 | 94.91-0 | 88.00-6 | não | não |
| 322-0 | 85.13-9 | 94.91-0 | não | não |
| 399-9 | 94.91-0 | 94.99-5 | não | **sim** |
| 399-9 | 94.99-5 | 94.91-0 | não | não |
| 322-0 | 47.11-3 | nenhum | **sim** | **sim** (os dois motivos são distintos) |

Cada caso desta tabela está coberto em `test_classificar_cnae.py`.

Sugestão de ajuste no spec: na tabela 6.3, trocar "alerta se CNAE só religioso" por "alerta pela regra ALERTA_RELIGIOSA (cap. 7)", e na tabela 7.3 retirar "com alerta" da linha de 94.91-0.

## 6. Contagens

| Faixa | Subclasses | % |
|---|---|---|
| ALTA | 86 | 6,5% |
| MEDIA | 25 | 1,9% |
| BAIXA | 1.221 | 91,7% |
| Total | 1.332 | 100% |

Das 86 em ALTA, 41 vêm da divisão 86 (saúde), 17 da 85 (educação), 10 da 87, 8 da 90, 4 da 91, 1 da 88 e 5 de regras pontuais (94.30-8, 94.93-6, 72.20-7, 0220-9/06, 6499-9/05).
Das 1.221 em BAIXA, 1.184 caem no padrão e 37 têm regra BAIXA explícita.

## 7. CNAEs de referência testados

| CNAE | Descrição | Faixa | Regra aplicada |
|---|---|---|---|
| 9430-8/00 | Associações de defesa de direitos sociais | ALTA | 94.30-8 (classe) |
| 8800-6/00 | Assistência social sem alojamento | ALTA | 88 (divisão) |
| 9499-5/00 | Associativas não especificadas | MEDIA | 94.99-5 (classe) |
| 9491-0/00 | Organizações religiosas ou filosóficas | MEDIA | 94.91-0 (classe) |
| 4711-3/02 | Supermercados | BAIXA | padrão |
| 9411-1/00 | Organizações patronais e empresariais | BAIXA | 94.1 (grupo) |
| 8711-5/05 | Condomínios residenciais para idosos | MEDIA | 8711-5/05 (subclasse) |
| 8513-9/00 | Ensino fundamental | ALTA | 85 (divisão) |
| 9001-9/01 | Produção teatral | ALTA | 90 (divisão) |

## 8. Pontos que precisam do aval do orientador

1. **[DECISÃO DO ORIENTADOR] 94.93-6 sobe de MÉDIA (spec) para ALTA.**
   As notas do IBGE descrevem associações culturais, escolas de samba e clubes literários.
   Manter MÉDIA criaria a incoerência de uma produtora teatral (90) valer mais que uma associação cultural.
2. **[DECISÃO DO ORIENTADOR] Saúde (86) inteira em ALTA.**
   O art. 3º, IV da Lei 13.019 exclui do MROSC os convênios e contratos do SUS complementar (CF, art. 199, § 1º).
   A entidade continua podendo ser OSC, mas parcerias de saúde via SUS seguem outro regime.
   Alternativa: manter ALTA e apenas registrar a ressalva no relatório.
3. **[DECISÃO DO ORIENTADOR] Esporte (93.1) em MÉDIA, incluindo clubes sociais (9312-3/00).**
   Esporte não está no art. 84-C, mas é área do Mapa das OSCs e tem fomento próprio.
   Clubes de sócios são associações legítimas, mas servem sobretudo aos próprios membros.
4. **[DECISÃO DO ORIENTADOR] Proteção animal.**
   Não existe CNAE específico: segundo as notas do IBGE, ela está em 94.99-5 (MÉDIA).
   Propomos 75.00-1 (veterinária) em MÉDIA por ser secundário comum dessas OSC.
   Se o orientador quiser proteção animal em ALTA, só é possível pelo estatuto, não pelo CNAE.
5. **[DECISÃO DO ORIENTADOR] Meio ambiente.**
   Fica em ALTA por 94.30-8 (as notas do IBGE incluem "ONG de defesa do meio ambiente"), 91.03-1 e 0220-9/06.
   Reciclagem e coleta (38.11-4, 38.3) ficam em MÉDIA para cobrir associações de catadores.
6. **[DECISÃO DO ORIENTADOR] Regra religiosa (seção 5).**
   Confirmar o gatilho por CNAE principal 94.91-0 também para natureza 399-9.
   Confirmar que organizações filosóficas (lojas maçônicas), que estão na mesma subclasse, recebem o mesmo alerta.
7. **[DECISÃO DO ORIENTADOR] Inclusões fora das divisões sociais clássicas.**
   Microcrédito de OSCIP (6499-9/05) em ALTA; rádio (60.10-1), ATER (7490-1/03) e audiovisual (59.11-1, 59.14-6) em MÉDIA.
8. **[DECISÃO DO ORIENTADOR] Exceções dentro de divisões ALTA.**
   Autoescola e pilotagem em BAIXA; idiomas, informática, treinamento gerencial e cursinhos em MÉDIA; condomínio para idosos e rodeios em MÉDIA; sonorização em BAIXA.

## 9. Exemplos limítrofes que ficaram em BAIXA (padrão)

Estes casos foram considerados e deixados em BAIXA; o alerta resultante só pede conferência do estatuto.

- **Água e esgoto (36, 37)**: existem associações comunitárias rurais de abastecimento, mas a atividade é serviço público concedido.
- **Habitação (41.10-7, 41.20-4)**: OSC de habitação social aparecem em 94.99-5 (as notas do IBGE citam "habitação de interesse social"), e construção é atividade empresarial.
- **Segurança alimentar (56.20)**: cozinhas comunitárias e bancos de alimentos costumam usar 88.00-6; fornecimento de refeições é comercial.
- **Albergues não assistenciais (5590-6/01)**: os assistenciais têm código próprio em ALTA (8730-1/02).
- **Serviços advocatícios (6911-7/01)**: assessoria jurídica gratuita é finalidade do art. 84-C, X, mas OSC desse tipo costumam usar 94.30-8.
- **Agropecuária (01)**: associações de produtores rurais costumam ter 94.99-5 ou 94.1 como principal; cooperativas rurais já caem em revisão manual pela natureza 214-3.
- **Viveiros florestais (0210-1/06)**: reflorestamento de nativas está em 0220-9/06 (ALTA); plantadas é atividade produtiva.
- **Salas de acesso à internet (8299-7/07)**: poderiam ser telecentros, mas são majoritariamente lan houses.
- **Cemitérios (96.03-3)**: muitas irmandades religiosas mantêm cemitérios, mas a atividade é serviço funerário.
