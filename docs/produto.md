# Validador de OSC: documento de produto

Este documento descreve o produto por inteiro, para quem nunca viu o projeto: contexto, problema, usuários, o que o sistema faz, como decide, o que não faz, o que está pendente e as perguntas em aberto.
Ele não exige ler código.
Para a parte técnica, veja `docs/arquitetura.md`; para a especificação detalhada de cada regra, `docs/especificacao.md`; para o histórico de decisões, `docs/decisoes.md`.

## 1. Resumo

O Validador de OSC recebe o CNPJ de uma organização e diz, em segundos, se ela parece apta a firmar parceria com a administração pública segundo a Lei 13.019/2014.
Ele consulta cadastros públicos (Receita Federal, CGU, TCU, CNJ, TCE-SP e Ipea), aplica 16 verificações e devolve um status com a explicação e a fonte de cada dado.
É uma triagem: aponta impedimentos registrados em bases públicas, mas não substitui as certidões e a análise documental exigidas no edital.
É o MVP de um projeto de extensão do IFSP, feito para demonstrar a viabilidade e ser aprovado na disciplina.

## 2. Contexto

### 2.1 O que é uma OSC e por que isso importa

OSC (Organização da Sociedade Civil) é o nome que a Lei 13.019/2014, o Marco Regulatório das Organizações da Sociedade Civil (MROSC), dá às entidades que podem receber recursos ou firmar parcerias com o poder público.
As parcerias são o termo de colaboração, o termo de fomento e o acordo de cooperação.
Para a lei, OSC é (art. 2º, I):

- entidade privada sem fins lucrativos (associação ou fundação privada, na prática);
- certos tipos de cooperativa (sociais, de combate à pobreza, de trabalhadores rurais, entre outras);
- organização religiosa que tenha atividades de interesse público distintas das exclusivamente religiosas.

Além de ser OSC, a entidade não pode estar impedida (art. 39): estar suspensa, declarada inidônea, com contas rejeitadas ou julgadas irregulares, ou ter dirigentes em situações vedadas.
E precisa ter tempo mínimo de existência com cadastro ativo (art. 33, V, a): 1 ano para parcerias com municípios, 2 com estados e Distrito Federal, 3 com a União.

### 2.2 O problema

Hoje essa checagem é manual.
Alguém consulta a Receita, abre o Portal da Transparência, emite certidão no TCU, procura certificações em outros sites e junta tudo.
É lento, sujeito a erro e cada pessoa faz de um jeito.
Além disso, várias fontes são instáveis, defasadas ou têm formatos ruins, o que torna fácil concluir "nada consta" quando, na verdade, a fonte não respondeu.

### 2.3 A proposta

Automatizar a parte que está em cadastros públicos, em uma consulta só, com três compromissos:

1. Mostrar de onde veio cada informação e de quando ela é.
2. Nunca aprovar quando uma fonte essencial não respondeu ou está desatualizada.
3. Deixar claro o que o sistema não verifica.

## 3. Usuários

| Usuário | O que quer | Como usa |
|---|---|---|
| A própria OSC | Saber se está apta antes de concorrer a um edital, e corrigir pendências | Consulta o próprio CNPJ e envia o link do resultado à prefeitura |
| Ente público (prefeitura, estado, União) | Triar as organizações candidatas com rapidez e critério uniforme | Consulta os CNPJs e escolhe a esfera da parceria |
| Público em geral | Transparência sobre organizações que recebem recursos públicos | Consulta qualquer CNPJ |
| Operador do sistema | Auditar um resultado e ver os nomes de dirigentes com possível correspondência | Usa um token de operador na API |

Os três primeiros usam a mesma interface (decisão D10).
A principal diferença entre eles é a esfera da parceria, que muda o tempo mínimo de existência exigido.
Nenhum usuário real foi entrevistado ainda; esses perfis vêm da proposta do projeto.

## 4. Como o produto funciona para o usuário

1. Na página inicial, o usuário digita o CNPJ, com ou sem pontuação, e escolhe a esfera da parceria (município, estado ou DF, União, ou "não informar").
2. Em até 20 segundos, recebe a página de resultado: o status final, o motivo, um resumo por estado e as 16 verificações com mensagem, fonte, data da base e link para conferir na fonte oficial.
3. O resultado tem um link permanente, que pode ser copiado e enviado, e pode ser impresso ou salvo em PDF pelo navegador.
4. A página "Fontes de dados" mostra a data e a idade de cada base, e a saúde das fontes consultadas na hora.

Comportamentos importantes:

- **Filial:** se o CNPJ é de uma filial, a entidade é avaliada pela matriz, e o resultado diz isso.
- **CNPJ com dígito errado:** é tratado como erro de digitação (status próprio), sem consultar nada e sem rotular a entidade como inapta.
- **Sem esfera:** o tempo de existência mostra os três cenários (município, estado, União).
- **Consulta repetida:** a mesma consulta nos últimos 10 segundos devolve o mesmo resultado, para evitar duplicidade.
- **Dirigentes:** quando um dirigente pode ter sanção, o público vê "Dirigente 1, 2..."; o nome só aparece para o operador.
- **API:** tudo o que a página faz também existe em JSON, para integração com outros sistemas.

## 5. Como o resultado é decidido

### 5.1 Tipos de verificação

| Tipo | Efeito |
|---|---|
| Eliminatória | Uma restrição impede a parceria (status INAPTA). Se não puder ser feita, o resultado é INCONCLUSIVA. |
| Alerta | Não impede, mas exige atenção (status APTA COM RESSALVAS). |
| Informativa | Contexto para quem analisa; um alerta aqui também gera ressalva. |

### 5.2 Estado de cada verificação

| Estado | Significado |
|---|---|
| OK | Conferido, nada impede. |
| RESTRIÇÃO | Encontrado um impedimento. |
| ALERTA | Encontrado algo que precisa de análise humana. |
| INDISPONÍVEL | A fonte não respondeu ou está fora da validade. |
| NÃO VERIFICADO | O sistema não faz essa verificação neste caso (por exemplo, CNPJ alfanumérico ou CEBAS). |

### 5.3 Status final

A regra é aplicada nesta ordem, e a primeira que se aplica vence:

| Ordem | Condição | Status | Mensagem ao usuário |
|---|---|---|---|
| 1 | Dígito verificador errado | CNPJ INVÁLIDO | Erro de digitação; nada foi consultado |
| 2 | Alguma eliminatória com RESTRIÇÃO | INAPTA | Não pode firmar parceria no estado atual |
| 3 | Alguma eliminatória INDISPONÍVEL ou NÃO VERIFICADA | INCONCLUSIVA | Não é possível dizer se está apta; tentar de novo ou conferir na fonte |
| 4 | Algum ALERTA, em qualquer verificação | APTA COM RESSALVAS | Pode firmar, mas há pontos a analisar |
| 5 | Nenhuma das anteriores | APTA | Nada impede nas bases consultadas |

Verificação não eliminatória que ficou indisponível não muda o status, mas gera um aviso em destaque ("Resultado incompleto").

## 6. As 16 verificações

| # | Verificação | Tipo | Base legal | Fonte | Quando gera restrição ou alerta |
|---|---|---|---|---|---|
| 1 | Dígito verificador | Eliminatória | - | Cálculo local | DV errado: CNPJ INVÁLIDO |
| 2 | Situação cadastral | Eliminatória | Art. 2º | Receita (OpenCNPJ; reserva BrasilAPI) | Matriz não ativa: restrição. Base da Receita com mais de 60 dias: alerta |
| 3 | Estabelecimento consultado | Informativa | - | Receita | Filial não ativa com matriz ativa: alerta. Não foi possível achar a matriz: alerta |
| 4 | Natureza jurídica | Eliminatória | Art. 2º, I | Receita + tabela própria | Natureza não elegível (ex.: empresa): restrição. Cooperativa e casos de revisão manual: alerta |
| 5 | CNAE de relevância social | Alerta | Art. 2º, I | Receita + classificação própria | Atividades de baixa relevância social: alerta |
| 6 | Organização religiosa | Alerta | Art. 2º, I, c | Receita | Natureza ou CNAE religioso sem atividade social clara: alerta |
| 7 | Tempo de existência | Alerta | Art. 33, V, a | Receita | Menos que o prazo da esfera: alerta (a lei permite reduzir o prazo) |
| 8 | CEPIM | Eliminatória | Art. 39 | Arquivo diário da CGU | Qualquer registro: restrição |
| 9 | CEIS | Eliminatória | Art. 39, V | Arquivo diário da CGU + TCU | Sanção vigente: restrição. Encerrada: histórico, sem efeito |
| 10 | CNEP | Eliminatória | Art. 39, V | Arquivo diário da CGU + TCU | Sanção vigente: restrição. Só multa: alerta |
| 11 | Licitantes inidôneos | Eliminatória | Art. 39, V | TCU (consulta e lista) | Inidoneidade vigente: restrição |
| 12 | Improbidade (CNIA) | Eliminatória | Art. 39, VII | CNJ via TCU | Proibição de contratar vigente: restrição. Encerrada ou sem data: alerta |
| 13 | Contas julgadas irregulares | Alerta | Art. 39, VI | Lista do TCU | Julgamento nos últimos 8 anos: alerta |
| 14 | Dirigentes | Alerta | Art. 39 (dirigentes) | CEIS, CNEP, TCU e TCE-SP | Possível correspondência de dirigente com sanção: sempre alerta |
| 15 | Mapa das OSCs | Informativa | - | Ipea | Entidade ausente do Mapa: alerta. Presente: mostra o perfil |
| 16 | CEBAS | Informativa | - | Ainda não implementada | Sempre "não verificado" nesta versão |

Sanções são buscadas pela raiz do CNPJ, ou seja, alcançam todos os estabelecimentos da mesma entidade.
Dirigentes são comparados por nome normalizado e pelos 6 dígitos centrais do CPF, que é o que o cadastro público expõe; por isso o resultado é sempre "possível correspondência" e nunca reprova sozinho.

## 7. Fontes e atualização

| Fonte | Como é usada | Atualização | Idade máxima aceita |
|---|---|---|---|
| Receita Federal (OpenCNPJ, BrasilAPI de reserva) | Consulta na hora | Espelho mensal da Receita | 60 dias (depois disso, alerta) |
| CGU: CEIS e CNEP | Arquivo baixado | Diária | 3 dias |
| CGU: CEPIM | Arquivo baixado | Diária | 7 dias |
| TCU: inidôneos | Arquivo baixado + consulta na hora | Diária | 3 dias |
| TCU: contas irregulares e inabilitados | Arquivo baixado | Diária | 7 dias |
| TCE-SP: Terceiro Setor | Planilha baixada | Periódica | 45 dias |
| TCU Consulta Consolidada (inclui CNIA do CNJ) | Consulta na hora | Tempo real | - |
| Mapa das OSCs (Ipea) | Consulta na hora, cache de 30 dias | Variável | - |

Base mais velha que o limite deixa a verificação indisponível; o sistema nunca aprova com dado vencido.
As bases baixadas são atualizadas por um comando diário (`atualizar-bases`), que pode ser agendado.
Toda resposta de fonte é guardada com hash SHA-256, o que permite provar o que a fonte disse no momento da consulta.

## 8. O que o produto não faz

| Não verifica | Por quê |
|---|---|
| Certidões do art. 34 (fiscal, FGTS, trabalhista etc.) | São emitidas na hora, em sites com captcha ou login, e são apresentadas pela própria OSC |
| Dirigente que é agente político do ente parceiro (art. 39, III) | Exige a lista de agentes de cada ente; não existe base única |
| Ressarcimento do dano (art. 39, § 2º) | Não há fonte pública |
| Sanções estaduais e municipais fora do CEIS | Cada ente tem sua lista; são milhares de fontes |
| Tribunais de contas além do TCU e do TCE-SP | Não há lista aberta padronizada |
| Improbidade com suspensão de direitos políticos | Exige CPF completo, que o sistema nunca usa |
| Dirigentes fora do quadro de sócios | A Receita costuma listar só o presidente |
| Estatuto, experiência prévia e prestação de contas | São documentos, sem base estruturada |
| CEBAS | Planejado (fatia 6); as fontes são frágeis e defasadas |
| CNPJ alfanumérico | O dígito é validado, mas as fontes ainda não aceitam o formato |

Essa lista aparece na página inicial do produto.

## 9. Princípios de produto

1. **Honestidade antes de conveniência:** fonte fora do ar vira "inconclusiva", nunca "apta".
2. **Rastreabilidade:** cada informação mostra a fonte, a data da base e um link para conferir.
3. **Linguagem do usuário:** mensagens explicam o motivo em português simples e citam o artigo da lei.
4. **Não estigmatizar por engano:** erro de digitação não vira "inapta"; correspondência de dirigente é "possível", não "confirmada".
5. **Privacidade:** nenhum CPF completo é guardado, exibido ou registrado; nomes de dirigentes com possível sanção só aparecem para o operador.
6. **Regras como parâmetro:** as regras que dependem de interpretação jurídica ficam em arquivo de configuração, e mudam sem mexer no código.

## 10. Regras provisórias, aguardando o orientador

Algumas regras dependem de interpretação jurídica e foram definidas provisoriamente até a resposta do orientador do projeto.
Os valores atuais estão em `validador_osc/dados/regras_orientador.json`.

| Pergunta | Regra atual | Alternativas |
|---|---|---|
| Q14 | Tabela de naturezas jurídicas elegíveis, com revisão manual para cooperativas e alguns casos | Ajustar casos específicos |
| Q15 | Classificação de relevância social dos CNAEs em alta, média e baixa | Ajustar 8 pontos marcados |
| Q16 | Multa do CNEP gera alerta, não restrição | Restrição |
| Q17 | Sanção com abrangência limitada a um órgão ou esfera gera restrição | Alerta |
| Q18 | CEPIM impede em qualquer esfera | Só na União |
| Q19 | Improbidade no CNIA impede enquanto a proibição estiver vigente | Qualquer registro impede |
| Q20 | Sanção em outro estabelecimento da mesma raiz gera restrição | Alerta, ou só o CNPJ exato |
| Q21 | Contas irregulares no TCU geram alerta | Restrição, ou não usar |
| Q22 | Achado de dirigente é sempre alerta | Definir quais achados contam |
| Q23 | Tempo de existência contado desde a data de início de atividade, mesmo se a entidade foi reativada | Contar desde a última reativação |
| Q24 | CEBAS vencido sem ato novo aparece como "possível renovação em análise", sem limite de tempo e com a idade explícita | Limitar a N anos e depois mostrar "situação desconhecida" |

## 11. Estado atual

| Item | Situação |
|---|---|
| Verificações 1 a 15 | Prontas e testadas com casos reais |
| CEBAS (16) | Não implementado |
| Interface web, API, link permanente, impressão | Prontos |
| Bases diárias e agendamento | Prontos |
| Testes | Mais de 1.200 automatizados, CI no GitHub |
| Implantação | Roda localmente; não há servidor público |
| Usuários reais | Nenhum ainda; não há métricas de uso |
| LGPD (retenção, acesso, exibição de nomes) | Adiado para depois da aprovação (D9) |

## 12. Próximos passos conhecidos

1. Receber as respostas do orientador (Q14 a Q24) e ajustar os parâmetros.
2. Implementar o CEBAS com SisCEBAS Saúde, planilhas do MDS e do MEC e atos do Diário Oficial.
3. Pedir aos ministérios, por Lei de Acesso à Informação, dados de CEBAS para medir a cobertura.
4. Definir onde o sistema vai rodar e testar o acesso ao TCU a partir do servidor (risco de bloqueio de datacenter).
5. Tratar LGPD: retenção das consultas, base legal e exibição de nomes.
6. Aceitar CNPJ alfanumérico quando as fontes aceitarem.

## 13. Perguntas de produto em aberto

Estas perguntas não foram decididas e são um bom ponto de partida para evoluir o produto.

- Qual dos usuários é o principal, e o produto deve ter fluxos diferentes para cada um?
- A prefeitura precisa consultar vários CNPJs de uma vez (lote) ou exportar o resultado?
- O link permanente deve mostrar quando o resultado ficou desatualizado e oferecer nova consulta?
- Vale avisar a OSC quando seu status mudar (por exemplo, sanção nova)?
- Como medir sucesso: tempo poupado por análise, número de consultas, erros evitados?
- Quem opera o sistema em produção, e quem atualiza as regras quando a interpretação jurídica mudar?
- O produto deve cobrir outros tribunais de contas estaduais, começando por quais?

## 14. Exemplos para demonstração

O roteiro em `docs/roteiro_demonstracao.md` tem CNPJs reais para cada situação: entidade apta, inapta por CEPIM, inapta por CEIS, natureza incompatível, sanção encerrada (histórico), multa como alerta, dirigente com sanção, filial e organização religiosa.

## 15. Glossário

| Termo | Significado |
|---|---|
| CNPJ | Cadastro Nacional da Pessoa Jurídica; os 8 primeiros dígitos (raiz) identificam a entidade, os 4 seguintes o estabelecimento |
| Matriz e filial | Estabelecimento principal e demais estabelecimentos da mesma entidade |
| OSC | Organização da Sociedade Civil, nos termos da Lei 13.019/2014 |
| MROSC | Marco Regulatório das Organizações da Sociedade Civil, a Lei 13.019/2014 |
| Esfera | Nível do ente que firma a parceria: município, estado ou DF, União |
| Natureza jurídica | Tipo legal da entidade na Receita (associação, fundação, empresa etc.) |
| CNAE | Classificação Nacional de Atividades Econômicas, a atividade declarada |
| QSA | Quadro de sócios e administradores, onde aparecem os dirigentes |
| CGU | Controladoria-Geral da União, que mantém CEIS, CNEP e CEPIM |
| CEIS | Cadastro de Empresas Inidôneas e Suspensas |
| CNEP | Cadastro Nacional de Empresas Punidas (Lei Anticorrupção) |
| CEPIM | Cadastro de Entidades Privadas sem Fins Lucrativos Impedidas |
| TCU | Tribunal de Contas da União |
| TCE-SP | Tribunal de Contas do Estado de São Paulo |
| CNJ e CNIA | Conselho Nacional de Justiça e seu Cadastro Nacional de Condenações por Improbidade Administrativa |
| CEBAS | Certificação de Entidade Beneficente de Assistência Social |
| Mapa das OSCs | Plataforma do Ipea com o perfil das organizações da sociedade civil |
| Evidência | Resposta bruta de uma fonte, guardada com hash SHA-256 |
| Operador | Pessoa com token que vê nomes de dirigentes e evidências brutas |
