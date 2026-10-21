# Decisões de produto: usuário, fluxo, métricas e interface

Registro das decisões de produto discutidas em 21/10/2026, antes do design visual.
Complementa `docs/produto.md` (visão geral do produto) e `docs/decisoes.md` (decisões técnicas e de engenharia).
Aqui ainda não há decisão de engenharia, apenas de produto e de interface.

## 1. Usuário principal

O ente público (prefeitura, estado ou União) é o usuário principal.
Ele é quem decide a parceria, quem repete o uso a cada edital e quem tem motivo de confiar no sistema como ferramenta de triagem.
A OSC e o público em geral continuam usando a mesma interface (D10 em `docs/decisoes.md`), mas como consequência do produto, não como foco principal.
A OSC usa o sistema de forma pontual, para autoavaliação antes de concorrer a um edital.
O público em geral usa para transparência, sem tomar nenhuma decisão a partir do resultado.

## 2. Fluxo (a implementar depois)

O fluxo atual do MVP é unitário: um CNPJ por consulta.
Isso não representa bem o uso real do ente público, que tria várias organizações candidatas de um mesmo edital de uma vez.

Fluxo proposto, a validar e implementar depois desta rodada de produto:

1. Abrir um lote (ou "edital"): informar a esfera da parceria uma vez, não por CNPJ.
2. Inserir a lista de CNPJs do lote (colar vários ou enviar um CSV), em vez de um por um.
3. Ver o resultado em lista: status de cada CNPJ (apta, apta com ressalvas, inconclusiva, inapta, CNPJ inválido), filtrável e ordenável por status e por tipo de impedimento.
4. Abrir o detalhe de uma organização específica quando for preciso justificar a decisão; aqui entra a tela de resultado individual que já existe hoje.
5. Exportar o resultado do lote (CSV ou PDF), para anexar ao processo administrativo.

A consulta unitária continua existindo; o lote é uma opção adicional, não uma substituição.

## 3. Métricas

Duas métricas diferentes, em dois painéis diferentes, com acesso diferente.

### 3.1 Painel do usuário (ente público)

Rota própria (por exemplo `/painel` ou `/dashboard`), acessível a quem usa o sistema.
Mostra dados sobre o uso do próprio usuário, organizados em dois níveis:

- **Por edital ou lote**: já é a própria tela de resultado em lista (item 2.3 do fluxo); não precisa duplicar como métrica separada.
- **Agregado histórico**, cobrindo todos os lotes já processados por aquele usuário:
  - Total de editais ou lotes já processados.
  - Total de CNPJs avaliados (contando cada CNPJ uma vez, mesmo se reconsultado).
  - Distribuição geral de status (percentual de apta, ressalva, inconclusiva, inapta e inválido).
  - Impedimentos detectados por tipo, somados em todo o histórico (CEPIM, CEIS, CNEP, TCU inidôneos, CNJ/improbidade e demais verificações eliminatórias).
  Esse número é o que prova valor do sistema: quantos impedimentos o sistema encontrou que teriam que ser achados manualmente.
  - Lista dos lotes anteriores, com data, esfera, quantidade de CNPJs, resumo do status e link para reabrir o resultado completo.
  - Possível extra: destacar CNPJ que aparece em mais de um edital (organização reincidente).

O tempo poupado em relação à triagem manual **não entra** no painel do usuário nesta fase.
Não há dado real de quanto tempo a triagem manual levava antes do sistema, e mostrar uma estimativa sem medição vai contra o princípio de honestidade do produto (`docs/produto.md`, seção 9).
Essa métrica fica pendente até haver dado real de uso (entrevista ou medição com usuário real).

### 3.2 Painel administrativo (interno, só o dono do projeto)

Rota separada e autenticada, fora do alcance do usuário comum (ex.: futura rota `/admin`).
Mostra a saúde do sistema, não o uso de um usuário específico:

- Taxa de inconclusiva por fonte (sinaliza fonte instável ou fora do ar).
- Latência e erros de cada fonte externa.
- Volume de pesquisas nos últimos X dias (uso agregado de todo o sistema).

## 4. Tela de resultado individual: melhorar a localização do impedimento

Problema identificado: a lista de 16 verificações, hoje exibida de forma linear, obriga o usuário a escanear tudo para achar o que realmente importa (a restrição ou o alerta).

Decisões para resolver isso:

- O card de status final e motivo, no topo da página, passa a linkar (âncora) direto para a verificação detalhada correspondente.
  Ao clicar no motivo, o usuário é levado direto ao detalhe daquela verificação, sem precisar procurar na lista.
- As verificações são agrupadas em cards por estado (OK, RESTRIÇÃO, ALERTA, e os demais estados quando houver).
- Ordem fixa de exibição dos cards: **OK sempre em primeiro lugar, mas fechado, mostrando só a contagem** (por exemplo "12 verificações OK"); depois o card de RESTRIÇÃO, aberto; depois o card de ALERTA, aberto.
  Essa ordem concilia duas ideias discutidas: priorizar o que precisa de atenção (RESTRIÇÃO e ALERTA já abertos, sem clique extra) e manter o OK em primeiro lugar na posição, só que recolhido.

## 5. Design visual: tipografia e paleta

Direção geral: seguir heurísticas de Nielsen relevantes para um sistema de triagem com peso legal (visibilidade do status, correspondência com o mundo real, reconhecimento em vez de lembrança, prevenção de erro, consistência, design minimalista).
Site claro, fundo branco como base; nenhuma cor escura como destaque.
Cor é usada só como acento (ações e links) e como semáforo de status, nunca como cor de fundo dominante.

### 5.1 Tipografia

- **Texto geral: Public Sans.** Família usada pelo padrão de serviços digitais do governo dos EUA (USWDS), desenhada para legibilidade em interface institucional, gratuita, boa em tamanhos pequenos, com bom suporte a acentuação em português.
- **Números e códigos (CNPJ, datas, valores): IBM Plex Mono.** Alinha dígitos e reduz erro de leitura, importante quando um dígito errado de CNPJ muda tudo.

### 5.2 Paleta

Valores fechados em 21/10/2026 (opção C entre três propostas), todos com contraste AA sobre fundo branco.
Vale só para o tema claro; o tema escuro é pendência futura (ver seção 7).

| Papel | Cor | Hex |
|---|---|---|
| Fundo | branco | `#FFFFFF` |
| Texto principal | quase preto | `#17181C` |
| Texto secundário | cinza médio | `#63666E` |
| Borda / divisor | cinza claro | `#DFE1E6` |
| Acento de marca (links, botão primário, foco) | azul-marinho | `#2F5BAE` |
| Status OK | verde | `#1E8A4C` |
| Status ALERTA | âmbar | `#C27803` |
| Status RESTRIÇÃO | vermelho | `#B3261E` |
| Status INDISPONÍVEL | cinza-azulado | `#5C6B7A` |
| Status NÃO VERIFICADO | cinza bem claro | `#E1E3E8` |

O acento de marca nunca é usado em nenhum estado de verificação, para não ser confundido com status.
Cor nunca é o único sinal de estado: todo estado também tem ícone e rótulo de texto, para acessibilidade e para reforçar reconhecimento em vez de lembrança.

### 5.3 Componentes

Sem biblioteca de componentes (ex.: shadcn) e sem React: o projeto mantém a stack atual, HTML/CSS/JS simples servido por Jinja2 (D1 em `docs/decisoes.md`).
A linguagem visual (cantos arredondados, bordas sutis, sombra leve, espaçamento generoso) é copiada em CSS puro, sem adotar o framework.

## 6. Disposição por tela

Discutido tela por tela, nessa ordem de prioridade.
Todas as telas compartilham o mesmo padrão visual de estado (cor + ícone + rótulo de texto, nunca cor isolada) e a mesma tipografia (seção 5.1), para manter consistência (heurística de Nielsen).

### 6.1 Página inicial

- Header fino: nome do produto à esquerda; link discreto para "Fontes de dados" à direita.
- Card central branco, com borda e sombra leves: campo de CNPJ com máscara automática (dígitos em mono), seletor de esfera (município, estado, União ou não informar) e texto de ajuda curto explicando o que a esfera muda (prazo do art. 33).
- Botão primário (cor de acento) para consultar.
- Ação secundária discreta abaixo do botão: link para a consulta em lote, sem disputar atenção com a ação principal.
- Rodapé fixo: bloco "o que esta triagem não verifica" e link para licença/sobre.
- Heurísticas aplicadas: prevenção de erro (máscara e validação do DV antes de enviar, com feedback inline), visibilidade do sistema (texto de ajuda da esfera), design minimalista (uma ação primária só).

### 6.2 Resultado individual

- Cabeçalho: razão social e CNPJ (mono); se a consulta partiu de filial, aviso imediatamente abaixo (B20) informando que a entidade avaliada é a matriz.
- Card de status final, maior destaque da página, com cor de fundo suave do próprio status (nunca a cor de acento de marca): status, frase-motivo e a lista de motivos como links-âncora que levam direto à verificação detalhada correspondente.
- Faixa de aviso em destaque, separada do card de status, quando o resultado estiver incompleto (fonte indisponível), nunca escondida dentro da lista de verificações.
- Verificações agrupadas em cards por estado, ordem fixa: OK fechado (só contagem) → RESTRIÇÃO aberto → ALERTA aberto → INDISPONÍVEL/NÃO VERIFICADO aberto quando houver. Cada item mostra ícone, cor e rótulo do estado, mensagem em português simples com o artigo da lei, fonte, data da base e link "consultar na fonte".
- Rodapé: bloco fixo "o que este relatório não verifica", lista de fontes consultadas com data e link (B18), botão discreto de impressão/PDF.
- Heurísticas aplicadas: visibilidade do status, controle do usuário (link para nova consulta sempre visível), ajuda a reconhecer e evitar erro (CNPJ_INVALIDO tratado como erro de digitação, nunca rotulado como entidade inapta).

### 6.3 Criação de lote

- Card central parecido com a página inicial; campo de texto grande para colar vários CNPJs (aceita quebra de linha, vírgula ou espaço) e opção de upload de CSV.
- Esfera escolhida uma única vez, para o lote inteiro.
- Contador ao vivo de CNPJs reconhecidos no texto colado, com aviso inline se algum já falha o DV antes de enviar.
- Botão primário "Processar lote".

### 6.4 Resultado em lote

- Barra de resumo no topo: total processado e contagem por status, em cards pequenos clicáveis que funcionam como filtro (clicar em "INAPTA (3)" filtra a lista).
- Filtro secundário por tipo de impedimento (CEPIM, CEIS, CNEP etc.).
- Tabela: CNPJ (mono), razão social, status (cor, ícone e rótulo, mesmo padrão da tela individual), impedimento principal, ação "ver detalhe".
- Tabela ordenável por coluna.
- Botão de exportar (CSV/PDF) fixo no topo da tabela, visível mesmo com scroll.
- Clicar numa linha abre o resultado individual (6.2) sem perder o contexto do lote (botão "voltar ao lote").

### 6.5 Painel do usuário (ente público)

- Topo: 3 a 4 cards de resumo agregado (total de lotes/editais, total de CNPJs avaliados, total de impedimentos detectados, distribuição geral de status).
- Bloco "impedimentos por tipo": gráfico de barra simples por tipo de impedimento (CEPIM, CEIS, CNEP, TCU inidôneos, CNJ/improbidade etc.); é o número que o usuário leva para justificar o uso do sistema para a própria chefia.
- Lista de lotes anteriores em tabela (data, esfera, quantidade de CNPJs, resumo de status, link "reabrir resultado"), cada linha abrindo o resultado daquele lote (6.4).
- Filtro por tipo de impedimento, cruzando todos os lotes do usuário.
- Sem métrica de tempo poupado (ver seção 3.1).

### 6.6 Fontes de dados (`/fontes`, já existe hoje)

- Ajustar para usar o mesmo código de cor e ícone de estado das demais telas (verde = fresca, âmbar = perto do limite, vermelho = vencida, cinza-azulado = indisponível agora).
- Barra de "frescor" visual por fonte (idade atual sobre idade máxima), para entender a situação sem precisar ler os números.
- Separar visualmente as fontes consultadas na hora (online) das bases locais baixadas diariamente, por serem conceitos diferentes para o usuário.
- Link de volta fácil para a consulta.

### 6.7 Painel administrativo (interno)

Fora do escopo detalhado desta rodada; fica a critério de quem implementar, descrito em alto nível na seção 3.2.

## 7. Pendente para a próxima rodada

- Design visual: cores, disposição e posição dos elementos das telas descritas acima.
- Validar com casos reais se a ordem e o agrupamento dos cards (item 4) realmente ajudam a achar o impedimento mais rápido.
- Detalhar a tela de criação de lote e o formato aceito de entrada (colar lista, CSV, limite de CNPJs por lote).
