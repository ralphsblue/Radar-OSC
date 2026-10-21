# Validador de OSC: leitura guiada do projeto

Este documento existe para que quem avalia o projeto consiga entender o que foi feito, por que foi feito dessa forma, e como as partes se encaixam, sem precisar ler o código.
Ele complementa o `README.md` (visão rápida, como rodar) e os documentos em `docs/`, que entram em mais detalhe técnico e de produto.

## 1. O que o sistema faz, em uma frase

O Validador de OSC recebe o CNPJ de uma organização e diz, em segundos, se ela parece apta a firmar parceria com a administração pública segundo a Lei 13.019/2014 (o Marco Regulatório das Organizações da Sociedade Civil), cruzando 16 verificações contra cadastros públicos (Receita Federal, CGU, TCU, CNJ, TCE-SP e Ipea) e mostrando a fonte e a data de cada dado usado.

## 2. O que foi feito

### 2.1 Motor de triagem (núcleo do MVP, já existia antes desta rodada)

- 16 verificações automatizadas, cobrindo situação cadastral, natureza jurídica, CNAE, organização religiosa, tempo de existência, filial, CEPIM, CEIS, CNEP, licitantes inidôneos, improbidade (CNJ), contas irregulares do TCU, dirigentes do quadro de sócios e presença no Mapa das OSCs.
- Cinco fontes públicas diferentes integradas: Receita Federal (via OpenCNPJ, com reserva na BrasilAPI), arquivos diários da CGU, TCU (consulta em tempo real e listas baixadas), CNJ (via TCU) e Mapa das OSCs do Ipea.
- Um motor de regras isolado, que nunca conclui "apto" quando uma fonte essencial não respondeu: o resultado vira inconclusivo, nunca aprovado por omissão.
- Toda resposta de fonte é guardada com hash SHA-256, como evidência, ligada à consulta.
- Mais de 1.300 testes automatizados, incluindo testes de contrato com respostas reais gravadas e testes de ponta a ponta sem acesso à rede.

### 2.2 O que foi adicionado nesta rodada (produto e interface)

Esta etapa do projeto trabalhou a parte de produto e interface do sistema, para além da parte técnica já existente. Veja `docs/produto_interface.md` para o raciocínio completo por trás de cada decisão.

- **Contas de usuário**: o ente público (prefeitura, estado ou União) agora pode se cadastrar (e-mail e senha) e entrar no sistema. A sessão usa um token JWT guardado num cookie.
- **Consulta em lote**: em vez de digitar um CNPJ por vez, o ente público cola até 20 CNPJs de uma vez (separados por `;`) e o sistema processa todos.
- **Fila de processamento assíncrono**: o lote não trava a página esperando. Cada CNPJ vira uma tarefa numa fila (Redis + RQ), e um processo separado (o "worker") consome essa fila e processa um CNPJ de cada vez, reaproveitando exatamente a mesma lógica da consulta individual.
- **Tela de resultado em lote**: mostra o status de cada CNPJ processado, com filtro por status e exportação em CSV.
- **Painel do usuário**: histórico de lotes já processados e métricas agregadas (total de CNPJs avaliados, distribuição de status, impedimentos encontrados por tipo).
- **Nova identidade visual**: paleta de cores e tipografia novas (Public Sans para texto, IBM Plex Mono para números e CNPJs), pensadas para clareza e para um público que toma decisão com peso legal a partir do resultado.

## 3. O que ainda não foi feito (fica para versões futuras)

| Pendência | Por quê ficou de fora |
|---|---|
| CEBAS (16ª verificação) | Fontes de dados frágeis e defasadas (SisCEBAS, planilhas do MEC/MDS/MS, Diário Oficial); exige um trabalho de ingestão separado, ainda não feito |
| LGPD (retenção de dados, base legal, exibição de nomes de dirigentes) | Adiado para depois da aprovação do projeto na disciplina, por decisão registrada em `docs/decisoes.md` (D9) |
| Tema escuro adaptado à paleta nova | A paleta nova foi desenhada só para o tema claro; o bloco de cores escuras continua no CSS, pronto, mas sem ninguém ligando nele ainda |
| Aumentar o limite de 20 CNPJs por lote e aceitar mais separadores (vírgula, quebra de linha) | Decisão deliberada de escopo mínimo para esta primeira versão do lote |
| Exportar o lote em outros formatos (hoje só CSV) | Mesma lógica: começar pelo mais simples |
| Painel administrativo interno (saúde das fontes, taxa de inconclusiva, latência) | Fora do escopo desta rodada; ficaria numa rota separada, só para quem administra o sistema |
| Filtro de impedimento cruzando todos os lotes de um usuário no painel | Avaliado como não trivial de encaixar sem adicionar infraestrutura nova; adiado |
| Recuperação de item de lote preso (se o worker cair no meio do processamento) | Gap conhecido e aceito: hoje, se o processo do worker morrer no meio de um item, esse item fica "processando" para sempre. O conserto (uma varredura periódica) não foi implementado |
| CNPJ alfanumérico (novo formato da Receita) nas consultas | O dígito verificador já aceita o formato novo, mas as fontes externas ainda não foram testadas com ele nas consultas de verdade |
| Implantação em servidor público | O sistema roda localmente hoje; falta decidir onde hospedar e testar se o TCU bloqueia o IP de um datacenter (ver seção 5 abaixo, achado real durante os testes) |
| Pedidos de acesso à informação (LAI) sobre CEBAS | Depende da aprovação do projeto primeiro |

## 4. Stack escolhida para o MVP, e por quê

A escolha de tecnologia privilegiou simplicidade, robustez e previsibilidade em vez de "o que é mais rápido de escrever agora" — ver `docs/decisoes.md`, decisão D1.

| Tecnologia | Por que foi escolhida |
|---|---|
| **Python 3.14** | Linguagem única do projeto, tipagem forte com `mypy --strict`, facilita manter um motor de regras legível e testável |
| **FastAPI** | Framework web assíncrono, gera documentação interativa automática (`/docs`), valida entrada e saída com Pydantic sem código extra |
| **SQLAlchemy 2 (assíncrono) + PostgreSQL** | Banco relacional maduro, SQLAlchemy assíncrono encaixa com o FastAPI sem bloquear o processo enquanto espera o banco |
| **Alembic** | Controle de versão do schema do banco, para que cada mudança de tabela seja rastreável e reversível |
| **httpx** | Cliente HTTP assíncrono, usado para consultar as fontes públicas sem travar o servidor numa consulta lenta |
| **Jinja2 + HTML/CSS/JS simples** | Interface sem framework de frontend: decisão deliberada para manter o projeto pequeno e de fácil manutenção, já que o volume de tela é pequeno e não exige um SPA |
| **RQ + Redis** | Fila de processamento assíncrono para o lote de CNPJs, escolhida por ser mais simples que Celery (menos conceitos, API pequena) para um caso de uso de até 20 itens por vez |
| **PyJWT + bcrypt** | Autenticação mínima: token assinado (JWT) e hash de senha (bcrypt), sem a complexidade de um provedor de identidade externo, adequado para um MVP acadêmico |
| **structlog** | Logs estruturados (campo=valor), mais fáceis de filtrar e depurar do que texto solto |
| **uv** | Gerenciador de dependências e ambiente Python, mais rápido e com lockfile reprodutível |
| **Docker Compose** | Sobe PostgreSQL e Redis localmente de forma idêntica para qualquer pessoa que rode o projeto, sem precisar instalar banco na máquina |
| **ruff, mypy estrito, import-linter, pre-commit, GitHub Actions** | Disciplina de qualidade: formatação, tipagem e arquitetura são checadas automaticamente a cada mudança, não dependem de revisão manual |

## 5. Arquitetura, explicada em detalhe

### 5.1 A ideia central

O sistema separa claramente **quem coleta dado** de **quem decide**.
Os adaptadores de fonte só respondem uma de três coisas: "achei o dado", "não encontrei" ou "a fonte falhou". Eles nunca decidem se uma entidade está apta ou não.
Quem decide é o motor de regras, um pedaço de código que não sabe o que é HTTP, não abre conexão de banco e não conhece a internet. Ele só recebe fatos já coletados e aplica a lei.
Essa separação é o que permite testar o motor de regras com milhares de casos em milissegundos (sem rede, sem banco) e trocar uma fonte de dado sem arriscar mudar uma regra de negócio sem querer.

### 5.2 As camadas do código, uma por uma

O código em `validador_osc/` está dividido em pacotes, cada um com uma responsabilidade e uma regra clara sobre o que ele pode ou não importar de outro pacote:

| Pacote | O que é / o que faz | Pode depender de |
|---|---|---|
| `dominio/` | Os "substantivos" do sistema: o que é um CNPJ, uma sanção, um estado de verificação, uma evidência. São tipos de dado puros, sem lógica de coleta nem de decisão | Só a biblioteca padrão do Python |
| `regras/` | O motor de regras: as 16 verificações, a agregação do status final, os parâmetros jurídicos provisórios (em JSON, não em código, para poder mudar sem recompilar) | `dominio` |
| `fontes/` | Os clientes HTTP que conversam com as APIs públicas (OpenCNPJ, BrasilAPI, TCU, Mapa das OSCs) e traduzem a resposta bruta de cada uma para o vocabulário de `dominio` | `dominio` |
| `bases_locais/` | Baixa, lê e carrega diariamente os arquivos oficiais que não têm uma API boa (CEIS, CNEP, CEPIM da CGU; listas do TCU; planilha do TCE-SP) | `dominio`, `persistencia` |
| `persistencia/` | As tabelas do PostgreSQL e os repositórios que leem e escrevem nelas | `dominio`, SQLAlchemy |
| `servico/` | Os casos de uso: "consultar um CNPJ", "criar um lote", "autenticar um usuário". É aqui que tudo se junta: busca dado nas fontes, manda pro motor de regras, grava o resultado | `dominio`, `regras`, `persistencia` |
| `api/` | As rotas HTTP (FastAPI), as páginas HTML (Jinja2) e os arquivos estáticos (CSS, JS). Só conversa com `servico`, nunca direto com banco ou fonte externa | `servico` |
| `composicao.py` | O único lugar do sistema que monta tudo: cria a conexão com o banco, os clientes HTTP, a fila, e entrega pros serviços prontos para usar | Todos os pacotes acima |
| `cli.py` | Linha de comando: subir o servidor (`servir`), atualizar as bases diárias (`atualizar-bases`), processar a fila de lotes (`trabalhar`) | `composicao`, `bases_locais` |
| `trabalhador.py` | O worker que consome a fila de lotes: para cada CNPJ enfileirado, chama o mesmo caso de uso de consulta individual que a API usa | `composicao`, `servico` |
| `config.py` | Todas as variáveis de ambiente do sistema (prefixo `VOSC_`), num único lugar tipado | — |

### 5.3 Como as camadas se comunicam

A regra geral é: **uma camada nunca importa uma camada "acima" dela** (mais perto da interface com o mundo externo).
`api/` só fala com `servico/`. `servico/` nunca fala direto com `fontes/`, `bases_locais/`, `persistencia/` nem com o FastAPI — ele recebe tudo isso já pronto através do `composicao.py`, que é o único lugar que conhece as implementações concretas.
Essa regra não depende de disciplina de quem está programando: ela é verificada automaticamente por uma ferramenta chamada **import-linter**, que quebra o build (CI e pre-commit) se alguém importar algo proibido.
Na prática, isso significa que dá pra trocar o banco de dados, trocar uma fonte externa, ou até trocar o framework web, sem precisar reescrever o motor de regras ou os casos de uso.

### 5.4 O fluxo padrão de uma consulta individual

1. O usuário digita o CNPJ e a esfera da parceria (opcional) na página inicial, ou chama `POST /api/v1/consultas`.
2. O dígito verificador é conferido localmente, sem gastar nenhuma chamada de rede. Se estiver errado, a resposta é "CNPJ inválido" na hora, sem consultar nada.
3. O serviço consulta o cadastro da entidade (Receita Federal, via OpenCNPJ, com a BrasilAPI como reserva).
4. Em paralelo (ao mesmo tempo, não em sequência), o serviço consulta sanções (bases locais da CGU + TCU), o Mapa das OSCs e os dirigentes, dentro de um prazo máximo de 20 segundos.
5. Tudo o que cada fonte respondeu é mandado para o motor de regras, que decide o estado de cada uma das 16 verificações e o status final (apta, apta com ressalvas, inconclusiva ou inapta).
6. O resultado é gravado no banco (com link permanente) e devolvido ao usuário, em HTML ou em JSON.

### 5.5 O fluxo novo: consulta em lote

1. O ente público, logado, cola até 20 CNPJs (separados por `;`) e escolhe uma esfera para o lote inteiro.
2. O sistema cria um registro de lote e um registro por CNPJ (todos começam como "pendente"), e devolve a página na hora — sem esperar nenhum CNPJ ser processado.
3. Cada CNPJ do lote vira uma tarefa numa fila gerenciada pelo Redis (biblioteca RQ).
4. Um processo separado, o worker (`uv run validador-osc trabalhar`), fica consumindo essa fila. Para cada tarefa, ele chama exatamente o mesmo caso de uso da consulta individual (passo 5.4) — não existe nenhuma lógica de verificação duplicada entre a consulta avulsa e a consulta em lote.
5. Conforme cada CNPJ termina (com sucesso ou com erro), o item do lote é atualizado, e o status do lote inteiro é recalculado: fica "concluído" quando todos os itens terminaram, mesmo que algum tenha dado erro.
6. A página de resultado do lote atualiza sozinha enquanto o processamento ainda está rodando, e mostra o resultado final com filtro por status e exportação em CSV.

Essa separação entre "criar o lote" (rápido, dentro da requisição HTTP) e "processar cada item" (fora da requisição, na fila) é o que evita que a tela trave esperando 20 consultas, uma atrás da outra.

### 5.6 Achado real durante os testes desta rodada

Ao testar o sistema de ponta a ponta nesta etapa, foi identificado que o TCU bloqueia, pelo firewall de aplicação dele, chamadas automatizadas em alguns casos — a resposta volta com código HTTP 200 (sucesso), mas o corpo é uma página HTML de bloqueio, não o JSON esperado. Isso derruba a verificação de improbidade (CNJ) para "indisponível" mesmo quando o dado existe e pode ser consultado manualmente no site do TCU.
Esse é um risco que já estava documentado antes desta rodada (`docs/decisoes.md`, próximos passos: "testar o acesso ao TCU a partir do servidor, risco de bloqueio de datacenter") e segue como pendência de investigação, não como algo resolvido nesta etapa.

## 6. Glossário rápido das tecnologias

| Tecnologia | O que é, em uma frase |
|---|---|
| **uv** | Ferramenta que instala as dependências do projeto e gerencia o ambiente Python, de forma rápida e com um arquivo de trava (`uv.lock`) que garante que todo mundo rode exatamente as mesmas versões |
| **pyproject.toml** | Arquivo único que descreve o projeto: nome, dependências, e a configuração de todas as ferramentas de qualidade (ruff, mypy, pytest, import-linter) |
| **Alembic** | Ferramenta que versiona as mudanças de estrutura do banco de dados (criar uma tabela, adicionar uma coluna), uma "migração" por mudança, para poder aplicar ou desfazer de forma controlada |
| **SQLAlchemy** | Biblioteca que permite escrever e ler no banco de dados usando código Python em vez de SQL cru, com suporte a operações assíncronas |
| **Pydantic** | Biblioteca de validação de dados: garante que o que entra e sai da API tem o formato esperado, e converte automaticamente entre JSON e objetos Python tipados |
| **FastAPI** | Framework web usado para expor as rotas HTTP (JSON e páginas), construído sobre Pydantic e um servidor assíncrono (Uvicorn) |
| **Jinja2** | Motor de templates que gera HTML a partir de um "molde" com variáveis, usado para renderizar as páginas do site |
| **httpx** | Biblioteca para fazer chamadas HTTP a outras APIs (as fontes públicas), de forma assíncrona |
| **Redis** | Banco de dados em memória, usado aqui só como "quadro de tarefas" da fila de processamento de lotes |
| **RQ (Redis Queue)** | Biblioteca que organiza tarefas numa fila guardada no Redis, e permite que um processo separado (o worker) as consuma uma a uma |
| **PyJWT** | Biblioteca que cria e verifica tokens JWT (JSON Web Token), usados aqui para manter o usuário logado sem guardar a sessão inteira no servidor |
| **bcrypt** | Algoritmo de hash de senha: transforma a senha num valor que não pode ser revertido para o texto original, usado antes de guardar qualquer senha no banco |
| **structlog** | Biblioteca de logs estruturados: cada linha de log vira pares campo=valor, mais fáceis de filtrar do que uma frase solta |
| **Docker Compose** | Ferramenta que sobe vários serviços (aqui: PostgreSQL e Redis) de forma isolada e reprodutível, descritos num único arquivo (`compose.yaml`) |
| **ruff** | Ferramenta que confere formatação e estilo do código Python automaticamente |
| **mypy (modo estrito)** | Ferramenta que confere, antes de rodar o programa, se os tipos declarados no código realmente batem (evita uma classe inteira de erros) |
| **import-linter** | Ferramenta que garante que as regras de arquitetura (seção 5.3) não sejam quebradas por um import indevido |
| **pytest** | Framework de testes automatizados usado em todo o projeto |

## 7. Decisões de produto desta rodada

Estas decisões foram tomadas antes de qualquer código ser escrito, numa conversa de produto registrada integralmente em `docs/produto_interface.md`. Resumo:

- **Usuário principal: o ente público**, não a OSC nem o público em geral. É quem decide a parceria, quem repete o uso a cada edital, e quem tem motivo de confiar no sistema como ferramenta de triagem oficial. A OSC e o público em geral continuam usando a mesma interface, como consequência, não como foco.
- **Contas**: autocadastro simples (e-mail e senha), sem etapa de aprovação manual, para permitir testar o fluxo completo agora. Login por JWT guardado num cookie.
- **Consulta em lote**: decidida como o fluxo certo para o ente público, que precisa triar várias organizações de um mesmo edital de uma vez, não uma por uma. Limite inicial de 20 CNPJs, separados só por `;` (decisão deliberada de escopo mínimo, com aumento planejado para depois).
- **Processamento assíncrono**: o lote não pode travar a tela do usuário esperando 20 consultas em sequência; daí a decisão de usar uma fila (RQ + Redis) com um processo worker separado.
- **Exportação**: a versão mais simples possível (CSV), com outros formatos ficando para depois.
- **Dois painéis de métrica, propositalmente separados**: um painel do usuário (uso próprio, público para quem está logado) e um painel administrativo interno (saúde do sistema, só para quem administra, fora do escopo desta rodada). A métrica "tempo poupado em relação à triagem manual" foi deliberadamente deixada de fora, por não haver dado real medido ainda; mostrar uma estimativa sem medição contrariaria o princípio de honestidade do produto.
- **Tela de resultado individual**: redesenhada para resolver um problema real de usabilidade encontrado durante a conversa de produto — a lista de 16 verificações, antes linear, obrigava o usuário a escanear tudo para achar o que importava. A solução: agrupar por estado, com as verificações "OK" sempre em primeiro lugar na posição mas fechadas (só com contagem), e as que precisam de atenção (restrição, alerta) já abertas.
- **Interface visual**: fundo branco, cor usada só como acento e como semáforo de status (nunca como cor de fundo dominante), seguindo heurísticas de usabilidade de Nielsen relevantes para um sistema de triagem com peso legal (visibilidade do status, prevenção de erro, reconhecimento em vez de lembrança, consistência). Tipografia Public Sans (texto) e IBM Plex Mono (números e CNPJs), ambas auto-hospedadas (sem CDN externo, mantendo a decisão já existente do projeto de não depender de serviços externos para a interface).
- **Sem framework de frontend nem biblioteca de componentes** (nada de React, shadcn etc.): decisão de manter a simplicidade arquitetural já estabelecida no projeto (HTML, CSS e JavaScript simples, servidos pelo próprio FastAPI).
