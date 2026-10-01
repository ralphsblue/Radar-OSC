# Arquitetura do MVP - Validador de OSC

Arquitetura e decisões técnicas do MVP, antes de qualquer código de produção.
Data: 01/10/2026 (revisada no mesmo dia com a revisão cruzada `revisao_pre_codigo.md`).
Base: `validador_osc_especificacao_mvp.md` (spec v1.2), `decisoes.md` (D1 a D20, com D14 a D19 decididas e D20 resumindo as decisões técnicas Q25 a Q44), fichas da Fase 0 e o código existente.

## Como ler

Cada decisão tem um número (T1 a T18), as opções consideradas, a recomendação e o motivo.
Sub-decisões aparecem como T3a, T3b etc., para que cada uma possa ser aprovada ou recusada separadamente.
As escolhas que eram do dono do projeto (produto, prazo, exposição pública, política) tinham o selo [DECIDIR]; todas foram respondidas em D19 e o texto de cada uma traz agora o selo **[DECIDIDO Qxx]** com a resposta.
Itens sem selo são decisões técnicas, fechadas pela recomendação da revisão (D20).
Regras de interpretação da lei que ainda dependem do orientador aparecem como `[ORIENTADOR Qxx]` e são parâmetros versionados, não código; a ampliação de dirigentes aparece como `[PENDENTE Q8]`.
No fim há uma tabela-resumo de todas as decisões e a lista das decisões do dono.

## Estado atual verificado (01/10/2026)

| Item | Situação |
|---|---|
| Python | 3.14.3 instalado; `.venv` com httpx, lxml, openpyxl, xlrd, pytest, ruff, mypy. |
| uv | Não instalado. |
| Docker | CLI 29.2.1 e Compose v5.0.2 instalados (Docker Desktop), mas o daemon não estava rodando no momento da checagem. |
| PostgreSQL | Não há instalação local (`psql` ausente). |
| Git | 2.53 instalado; a pasta ainda não é um repositório. |
| Código | `validador_osc/cnpj.py` (DV, 36 testes, ruff e mypy strict limpos); `pyproject.toml` só com configuração do pytest. |
| Fase 0 | Scripts e fichas das 6 frentes; `fase0/cebas_dou/downloads` tem 1,2 GB e `fase0/portal/downloads` 39 MB. |
| Casos de referência | `fase0/casos_referencia.json` e `.md` existem: 49 casos e 11 variantes, gerados por `fase0/casos/montar_casos.py` com o catálogo de 15 ids (Q25) e as regras da spec v1.2. |

## Princípios que guiam as escolhas

1. O motor de regras é puro: recebe dados normalizados e uma data de referência e devolve o resultado, sem rede, banco ou relógio.
2. Adapters coletam e normalizam fatos; eles não decidem conformidade.
3. Toda conclusão é rastreável até uma evidência guardada com hash (resposta bruta ou arquivo de carga).
4. Nunca "aprovado por omissão": falta de dado em verificação eliminatória leva a INCONCLUSIVA.
5. Poucas peças móveis: um processo de aplicação, um banco, nenhum broker, nenhum cache externo.
6. Tabelas de regras que o orientador precisa revisar (natureza, CNAE) ficam em arquivos versionados e legíveis, não no banco.

---

# T1 - Visão de componentes

## Opções consideradas

| Opção | Descrição | Avaliação |
|---|---|---|
| A. Monólito modular | Um processo FastAPI com módulos bem separados; ingestão por comandos de linha de comando no mesmo pacote; Postgres. | Simples de rodar, testar e implantar; fronteiras garantidas por regras de import. |
| B. Serviços separados | API, worker de coleta, worker de ingestão, Redis e fila. | Escala melhor para lote, mas multiplica operação e falhas sem necessidade no MVP (D1 já diz: fila só com lote). |
| C. Funções serverless | Cada fonte numa função. | Cold start, limite de tempo e banco remoto complicam; o TCU leva cerca de 6 s. |

## Recomendação

Opção A: monólito modular, com o mesmo pacote servindo a API e os comandos de ingestão.

## Diagrama

```
                         Usuário (navegador)          Cliente HTTP / Swagger
                                 |                              |
                                 v                              v
 +--------------------------------------------------------------------------------+
 |  api/  (FastAPI)                                                               |
 |   páginas HTML (Jinja2)        rotas JSON /api/v1/...        /health           |
 +-------------------------------------+------------------------------------------+
                                       |
                                       v
 +--------------------------------------------------------------------------------+
 |  servico/consulta.py  (orquestrador, único lugar que junta I/O e regras)       |
 |   1. DV (puro)  2. cadastro  3. fan-out  4. motor  5. persistir resultado      |
 +------+-----------------------+--------------------------+----------------------+
        |                       |                          |
        v                       v                          v
 +--------------+   +--------------------------+   +---------------------------+
 | regras/      |   | fontes/  (adapters HTTP) |   | bases_locais/  (consulta) |
 | motor puro   |   |  opencnpj  (+datasets)   |   |  sanções CSV (CGU)        |
 | verificações |   |  brasilapi (fallback)    |   |  listas TCU (inidôneos,   |
 | agregação    |   |  tcu_consolidada         |   |   contas irregulares)     |
 | tabelas      |   |  mapa_osc                |   |  CEBAS: SisCEBAS Saúde,   |
 |              |   |                          |   |   planilhas MDS/MEC, DOU  |
 |              |   |                          |   +-------------+-------------+
 | dados/*.json |   |  cliente HTTP comum:     |                 |
 +--------------+   |  timeout, retry, limite  |                 |
        ^           |  por host, evidência     |                 |
        |           +------------+-------------+                 |
   dominio/ (tipos              |                                |
   compartilhados)              v                                v
                    +----------------------------------------------------------+
                    |  persistencia/  (SQLAlchemy 2 + psycopg 3)                |
                    |   resposta_fonte  = cache + evidência (bytes + sha256)    |
                    |   consulta, consulta_evidencia                            |
                    |   carga + tabelas carregadas (sancao_registro, cebas_*)   |
                    +-----------------------------+----------------------------+
                                                  |
                                                  v
                                           PostgreSQL 17
                                                  ^
                                                  |
 +------------------------------------------------+-------------------------------+
 |  bases_locais/ingestao  (CLI: python -m validador_osc ingerir <fonte>)          |
 |   baixa arquivo -> guarda bruto (var/arquivos/<sha256>) -> parse -> carga       |
 |   disparado manualmente no MVP; agendador externo no deploy (T5)                |
 +--------------------------------------------------------------------------------+
```

## Motivo

A consulta de um CNPJ é uma operação curta (poucos segundos), de baixo volume e sem estado compartilhado entre usuários além do cache.
Um processo só atende com folga e é o mais fácil de demonstrar, depurar e manter.
O cache fica no próprio Postgres (T7), então não há Redis.
A separação que importa para qualidade (motor puro, adapters isolados) é feita por módulos e verificada por ferramenta (T2), não por rede.
Se um dia houver lote, entra um worker que reutiliza o mesmo `servico/consulta.py`, sem reescrever nada.

---

# T2 - Estrutura de pastas, módulos e fronteiras

## Opções consideradas

| Opção | Avaliação |
|---|---|
| A. Camadas por tipo técnico (`models/`, `services/`, `routers/`) | Comum em tutoriais, mas espalha uma verificação por várias pastas e não protege o motor de I/O. |
| B. Núcleo de domínio + anéis (hexagonal leve) | Domínio e regras no centro, adapters e API na borda, dependências só para dentro. |
| C. Um pacote por fonte com regra junto | Junta coleta e decisão, o que impede testar regras sem HTTP e dificulta a regra de divergência (D3). |

## Recomendação

Opção B, com esta árvore:

```
atv-ext/
  pyproject.toml            dependências, ruff, mypy, pytest, import-linter
  uv.lock
  .python-version           3.14
  .env.example              variáveis documentadas (sem segredos)
  compose.yaml              postgres (+ app no perfil "completo")
  Dockerfile
  alembic.ini
  migrations/               Alembic
  validador_osc/
    __init__.py
    __main__.py             CLI (ingerir, atualizar-bases, consultar, verificar-fontes)
    config.py               pydantic-settings
    logs.py                 configuração do structlog
    cnpj.py                 existente (DV); passa a ser importado por dominio/regras
    dominio/                tipos puros e enums compartilhados (sem dependências externas)
      tipos.py              Cadastro, Dirigente, Sancao, CertidaoTcu, PerfilMapa, AtoCebas, SituacaoCebas
      coleta.py             Coleta[T] = Obtido | NaoEncontrado | Falha; Observacao[T]
      resultado.py          Estado, TipoVerificacao, StatusFinal, ResultadoVerificacao, ResultadoConsulta
    regras/                 MOTOR PURO (só importa dominio, cnpj e stdlib)
      motor.py              avaliar(dados, contexto, tabelas) -> ResultadoConsulta
      agregacao.py          status final, motivos e avisos
      tabelas.py            carga e validação dos arquivos de dados/ (lidos uma vez, passados como objeto)
      verificacoes/
        dv.py  cadastro.py (situação, estabelecimento, natureza, tempo)  cnae.py (cnae + religiosa)
        sancoes.py (CEPIM, CEIS, CNEP)  tcu.py (inidôneos, CNIA, contas irregulares)  dirigentes.py
        mapa.py  cebas.py
    dados/                  arquivos de regra versionados (package data)
      natureza_juridica.json   código, descrição oficial, sinônimos, regra, justificativa (B12)
      regras_cnae.json         movido de fase0/cnae
      ibge_cnae_subclasses.json
      regras_orientador.json   parâmetros das regras [ORIENTADOR Q16 a Q24] (mesmos nomes de REGRAS_ORIENTADOR)
      mensagens.json           catálogo de mensagens por (verificação, estado, situação) (B1)
      limites.json             idade máxima das bases, limite do espelho, janela de 8 anos (Q6)
    fontes/                 ADAPTERS ONLINE (I/O)
      http.py               cliente httpx comum: timeout, retry, limite por host, gravação de evidência
      opencnpj.py  brasilapi.py  tcu.py  mapa_osc.py
      normalizacao/         funções puras bruto -> dominio, uma por fonte (testadas com fixtures)
    bases_locais/           ARQUIVOS INGERIDOS
      carga.py              ciclo de vida de uma carga (baixar, hash, gravar, ativar)
      sancoes_cgu.py        CEPIM, CEIS, CNEP (CSV; observação principal, D14)
      listas_tcu.py         inidôneos (Q34) e contas irregulares [ORIENTADOR Q21] da Plataforma de Certidões
      siscebas_saude.py     XLS diário
      cebas_planilhas.py    MDS 2024 e MEC 2023
      dou.py                parser do XML mensal (porta de fase0/cebas_dou/parser_cebas.py)
      consultas.py          leituras por CNPJ usadas pelo orquestrador
    persistencia/
      banco.py              engine, sessão
      modelos.py            tabelas SQLAlchemy
      repositorios.py       evidência/cache, consulta, cargas
    servico/
      consulta.py           orquestrador
    api/
      app.py                criação do app, middlewares, erros
      rotas_json.py  rotas_paginas.py  esquemas.py (DTOs pydantic)
      templates/  static/
  tests/
    unit/                   motor, normalizadores, DV, cliente HTTP com MockTransport
    contrato/               adapters com respostas gravadas
    integracao/             Postgres real (marcador db)
    e2e/                    casos de referência pela API e pela página
    vivo/                   fontes reais (marcador vivo, fora do CI padrão)
    fixtures/               respostas curadas copiadas da Fase 0, com LEIAME de origem
  fase0/                    material de descoberta (versionado parcialmente, ver T15)
  var/                      dados de execução (arquivos baixados), fora do git
```

## Fronteiras e dependências permitidas

| Módulo | Pode importar | Não pode importar |
|---|---|---|
| `dominio` | stdlib | qualquer outro módulo do pacote |
| `regras` | `dominio`, `cnpj`, stdlib | `fontes`, `bases_locais`, `persistencia`, `servico`, `api`, httpx, sqlalchemy |
| `fontes` | `dominio`, `cnpj`, `config`, httpx, pydantic | `regras`, `persistencia` (grava evidência por uma interface recebida no construtor), `api` |
| `bases_locais` | `dominio`, `persistencia`, `config`, lxml, xlrd, openpyxl | `regras`, `api` |
| `persistencia` | `dominio`, sqlalchemy | `regras`, `fontes`, `api` |
| `servico` | todos acima | `api` |
| `api` | `servico`, `dominio`, `config` | `fontes`, `bases_locais` diretamente |

Essas regras viram contratos do **import-linter** no `pyproject.toml` e rodam no CI e no pre-commit.
Assim a pureza do motor não depende de disciplina: um `import httpx` em `regras/` quebra o build.

## Motivo

O motor é a parte que o orientador vai discutir e que mais vai mudar (Q14 a Q24), então precisa ser lido e testado isoladamente.
Separar "normalização" (pura) de "transporte" (HTTP) dentro de `fontes/` permite testar o parse de cada fonte com as respostas reais da Fase 0 sem rede.
O código de `fase0/cnae/classificar_cnae.py` e o parser do DOU já são quase puros e migram com pouca mudança.
Nomes em português seguem o código existente e o vocabulário do spec.

---

# T3 - Desenho do motor de regras

## T3a - Forma das verificações

### Opções

| Opção | Avaliação |
|---|---|
| A. Funções puras registradas numa lista ordenada, cada uma com metadados (id, referência no spec, nome, tipo, base legal) | Simples, explícito, fácil de testar uma a uma. |
| B. Classes com herança (`class Verificacao(ABC)`) | Mais cerimônia sem ganho: não há estado. |
| C. Motor de regras declarativo (JSON/DSL, bibliotecas como `business-rules`) | Flexível demais para 14 regras, difícil de tipar e depurar. |

### Recomendação

Opção A.
Cada verificação é uma função `(DadosConsulta, Contexto, Tabelas) -> ResultadoVerificacao`, decorada ou registrada com seus metadados.
A tabela de natureza e as regras CNAE continuam declarativas (JSON validado na carga), porque são dados que o orientador revisa; a lógica fica em Python.

Esboço ilustrativo:

```python
@dataclass(frozen=True, slots=True)
class Contexto:
    data_referencia: date          # sempre injetada; o motor nunca chama date.today()
    esfera: Esfera | None          # D6

@dataclass(frozen=True, slots=True)
class ResultadoVerificacao:
    id: str                        # "situacao", "cepim", ...
    estado: Estado
    mensagem: str
    achados: tuple[Achado, ...]    # registros relevantes (sanção, ato CEBAS, etc.)
    fontes: tuple[RefFonte, ...]   # fonte, data da base, id da evidência, de_cache
```

## T3b - Tipos, estados e catálogo de verificações (Q25)

Tipos e estados seguem o spec (2.1 e 2.4).
Invariante verificada em teste: verificação de tipo ALERTA ou INFORMATIVA nunca devolve RESTRICAO (no máximo ALERTA).
Este é o contrato da API e dos casos de referência (spec 2.6); o número do spec é atributo.

| id | Spec | Nome | Tipo | Dados (primeira = observação principal) |
|---|---|---|---|---|
| `dv` | 1 | Dígito verificador | ELIMINATORIA (falha = status CNPJ_INVALIDO, Q3) | `cnpj.validar` |
| `situacao` | 2 | Situação cadastral da entidade | ELIMINATORIA | cadastro da matriz (D5); idade do espelho (Q6) |
| `natureza` | 3 | Natureza jurídica | ELIMINATORIA (ALERTA para revisão manual e natureza desconhecida, D17) | cadastro da matriz + `natureza_juridica.json` [ORIENTADOR Q14] |
| `cnae` | 4 | CNAE de relevância social | ALERTA | cadastro (filial e matriz) + regras CNAE (D7) [ORIENTADOR Q15] |
| `religiosa` | 4 | Organização religiosa, art. 2º, I, c | ALERTA | natureza + CNAEs [ORIENTADOR Q15] |
| `tempo` | 5 | Tempo de existência | ALERTA | data de início da matriz + esfera (D6, Q29) [ORIENTADOR Q23] |
| `estabelecimento` | 2 | Estabelecimento consultado | INFORMATIVA (ALERTA para filial não ativa, Q4, e matriz não identificada, Q27) | cadastro do consultado e da matriz |
| `cepim` | 6 | CEPIM | ELIMINATORIA | CSV local (exato e raiz) + OpenCNPJ datasets [ORIENTADOR Q18, Q20] |
| `ceis` | 7 | CEIS | ELIMINATORIA | CSV local (exato e raiz) + OpenCNPJ datasets + TCU [ORIENTADOR Q17, Q20] |
| `cnep` | 8 | CNEP | ELIMINATORIA | CSV local (exato e raiz) + OpenCNPJ datasets + TCU [ORIENTADOR Q16, Q17, Q20] |
| `tcu_inidoneos` | 9 | Licitantes inidôneos TCU | ELIMINATORIA | TCU consolidada + lista local de inidôneos (Q34) |
| `cnj_cnia` | 9 | Improbidade CNJ (CNIA) | ELIMINATORIA | TCU consolidada + CEIS de origem CNJ pelo processo [ORIENTADOR Q19] |
| `tcu_contas_irregulares` | 9 | Contas julgadas irregulares (art. 39, VI) | ALERTA [ORIENTADOR Q21] | lista local de contas irregulares do TCU |
| `dirigentes` | 10 | Dirigentes (QSA) | ALERTA | QSA + pessoas físicas do CEIS/CNEP locais (D15) [ORIENTADOR Q22] [PENDENTE Q8] |
| `mapa_osc` | 11 | Mapa das OSCs | INFORMATIVA (ausente = ALERTA, D2) | API do Ipea, pela matriz (Q28, Q38) |
| `cebas` | 12 | CEBAS | INFORMATIVA | bases locais (D16), pela matriz e pelo consultado (Q28) |

Separar a verificação 9 em `tcu_inidoneos` e `cnj_cnia` deixa claro qual cadastro falhou ou ficou indisponível (o CNIA não aceita alfanumérico, por exemplo).
O `id` textual é estável na API; a coluna "Spec" mantém a ligação com a numeração do documento.
`tcu_contas_irregulares` só existe enquanto `regras_orientador.json` mantiver o Q21 em "alerta" ou "restricao"; com "nao_usar" ela sai do catálogo.
As verificações informativas têm também um campo `situacao` com rótulo próprio (Q40): `ATIVO`, `EM_RENOVACAO`, `NAO_VIGENTE`, `PEDIDO_EM_ANALISE`, `NAO_ENCONTRADO` no CEBAS; `PREENCHIDO`, `AUTOMATICO`, `AUSENTE` no Mapa.

Fontes de `dirigentes` [PENDENTE Q8]: hoje só CEIS e CNEP; a proposta C acrescenta as listas do TCU (contas irregulares, inabilitados) e do TCE-SP como bases locais em `bases_locais/listas_tcu.py` e `bases_locais/tcesp.py`, com o mesmo casamento por nome normalizado + 6 dígitos.

## T3c - Agregação do status final

Regra do spec 2.5, escrita de forma que não haja ambiguidade:

```python
def status_final(vs: Sequence[ResultadoVerificacao]) -> StatusFinal:
    if dv(vs).estado is RESTRICAO:
        return CNPJ_INVALIDO                      # Q3
    elim = [v for v in vs if v.tipo is ELIMINATORIA]
    if any(v.estado is RESTRICAO for v in elim):
        return INAPTA
    if any(v.estado in (INDISPONIVEL, NAO_VERIFICADO) for v in elim):
        return INCONCLUSIVA
    if any(v.estado is ALERTA for v in vs):
        return APTA_COM_RESSALVAS
    return APTA
```

O resultado também traz `motivos`: a lista de ids que determinaram o status (todas as RESTRICAO, ou todas as eliminatórias sem resposta, ou todos os ALERTA).
Score não existe (D8).

**[DECIDIDO Q5]** Verificação não eliminatória que fica INDISPONIVEL (exemplo: dirigentes sem base local) não muda o status.
O usuário é avisado de forma explícita: o resultado traz a lista `avisos` com esses ids, e a página mostra um aviso em destaque junto do status, não só na lista de verificações.
Base local de dirigentes vencida segue a mesma regra.

## T3d - Várias observações para a mesma verificação (D3 reescrito pelo D18)

CEIS e CNEP têm até três observações (CSV local, que é a principal, OpenCNPJ datasets e TCU consolidada), o CEPIM duas (CSV local e OpenCNPJ datasets) e `tcu_inidoneos` duas (TCU consolidada e lista local).
Regra única de combinação, aplicada por verificação, com a vigência avaliada antes da divergência:

1. Os registros com datas (CSV local e OpenCNPJ) são casados pelo código da sanção e agrupados por conteúdo (Q32); cada registro é vigente se não tem data final ou se a data final é igual ou posterior à data de referência (Q30).
2. O estado de cada registro vigente sai da regra da verificação (RESTRICAO, ou ALERTA pelas regras provisórias Q16, Q17 e Q20).
3. `CONSTAM_REGISTROS` do TCU para CEIS ou CNEP não decide sozinho (D18): com registros locais todos expirados, é OK com histórico.
4. Registro só no TCU (nenhuma base local nem o OpenCNPJ têm registro para o CNPJ, Q35): o normalizador extrai as datas entre parênteses da `observacao`; todas passadas = OK com histórico e aviso "registro só no TCU"; alguma futura ou ilegível = RESTRICAO.

| Situação das observações | Estado da verificação |
|---|---|
| Algum registro vigente, em qualquer observação | O pior estado entre os registros vigentes (RESTRICAO vence ALERTA), com todas as respostas no relatório |
| Nenhum registro vigente e pelo menos uma observação válida | OK, com o histórico e a lista de fontes que responderam e que falharam |
| Nenhuma observação válida | INDISPONIVEL |

Divergência explícita depois da vigência (uma fonte com registro vigente, outra com "nada consta") gera o achado "fontes divergem" no texto, sem mudar o estado.
Observação de base local vencida (T5d) conta como "não respondeu".
A regra está implementada em `fase0/casos/montar_casos.py` (`avaliar_sancao_datada`), que serve de referência executável para o motor.

## T3e - Filial (D5)

O orquestrador detecta filial pelo primeiro cadastro, monta `cnpj_da_matriz` e busca a matriz em paralelo com o fan-out.
O motor recebe `Entidade(consultado: Cadastro, matriz: Coleta[Cadastro] | None)`.

| Verificação | Regra com filial |
|---|---|
| `situacao` | Avalia a entidade: matriz não ativa = RESTRICAO; matriz ativa = OK. Matriz INDISPONIVEL = INDISPONIVEL, e natureza e QSA vêm da filial, tempo pela data da filial com aviso (Q44). |
| `estabelecimento` | Filial ativa = OK informativo "consulta partiu de filial". **[DECIDIDO Q4]** Filial BAIXADA, INAPTA ou SUSPENSA com matriz ATIVA = ALERTA ("o estabelecimento informado não está ativo; a entidade está"). Raiz + 0001 que não volta como matriz = ALERTA pedindo o CNPJ da matriz, e as demais verificações usam o estabelecimento consultado (Q27). |
| `natureza`, `tempo`, `dirigentes` | Avaliados sobre a matriz. |
| `cnae`, `religiosa` | Unem CNAEs da filial e da matriz. |
| Sanções | Consulta o CNPJ informado e a matriz em todas as fontes; nas bases locais, também todos os estabelecimentos da raiz. [ORIENTADOR Q20] Registro em outro estabelecimento da raiz = RESTRICAO, com o estabelecimento no texto (alternativa: ALERTA). O T4 do Portal confirmou que a API só busca exato; a busca por raiz é feita no CSV local. |
| `mapa_osc` | Pela matriz (Q28). |
| `cebas` | Pela matriz e pelo consultado; vale o mais informativo (Q28). |

A matriz é detectada só por `matriz_filial`, nunca pela ordem (Q27).

## T3f - Esfera (D6)

`Contexto.esfera` vem do parâmetro opcional da API.
A verificação `tempo` calcula anos completos entre a data de início da matriz e `data_referencia`, com o aniversário contando e 29/02 fazendo aniversário em 28/02 (Q29), e aplica D6 literalmente.
Os três cenários (município, estado, União) sempre aparecem nos achados, para o relatório mostrar a tabela mesmo quando a esfera foi informada.

## T3g - CNPJ inexistente e TCU (D13, Q26, Q33)

CNPJ não encontrado (Q26): OpenCNPJ e BrasilAPI devolvem `NaoEncontrado` (a BrasilAPI é chamada também no 404, T6c); `situacao` fica INDISPONIVEL com motivo `NAO_ENCONTRADO` e o texto "não encontrado no espelho de DD/MM/AAAA"; o fan-out não roda e as demais verificações ficam NAO_VERIFICADO; o status é INCONCLUSIVA.
Sem cadastro não há QSA nem raiz para as sanções, e o TCU daria um "nada consta" enganoso.

Condição de OK do TCU (Q33): como o fan-out só roda com o cadastro confirmado, `tcu_inidoneos` e `cnj_cnia` concluem OK com NADA_CONSTA do TCU; `seCnpjEncontradoNaBaseTcu: false` com cadastro confirmado vira um achado informativo e não muda o estado, porque um CNPJ recém-criado pode existir na Receita e ainda não no TCU.

## T3h - Curto-circuito e ordem **[DECIDIDO Q1]**

| Opção | Avaliação |
|---|---|
| A. Spec 1.1: DV inválido para tudo; cadastro com RESTRICAO (baixada, natureza não elegível) pula o fan-out | Economiza chamadas, mas esconde sanções de 7 dos 13 CNPJs sancionados de referência. |
| B. Sempre fazer o fan-out depois do DV, quando o cadastro existe | Relatório completo (mostra sanções de uma entidade baixada ou de uma LTDA), custo de 2 a 4 chamadas a mais. |

Decisão do dono (D19, Q1): B.
Há só dois cortes: DV inválido (CNPJ_INVALIDO, nada é consultado) e cadastro não encontrado (Q26, fan-out não roda).
Fora isso, todas as verificações são avaliadas; o status continua INAPTA quando a cadastral reprova, e `motivos` lista todas as RESTRICAO.
Não existe `precisa_fanout`: o motor fica mais simples, e os casos de referência não têm mais `estado_sem_parada`.

## T3i - Data de referência e reprodutibilidade

`data_referencia` é a data corrente em `America/Sao_Paulo`, calculada no orquestrador e gravada na consulta junto com o instante (`iniciada_em`, com fuso).
Como o motor é puro e as evidências ficam guardadas, qualquer consulta pode ser reavaliada ("replay") com a mesma entrada e a mesma versão das regras.
Isso dá testes determinísticos (caso CEIS que vence em 22/11/2026, por exemplo) e auditoria de mudanças de regra.

Fuso e datas (B3): toda comparação de vigência é entre datas, sem hora, no fuso de Brasília.
Datas que chegam em UTC (OpenCNPJ `last_updated`, ORDS, `dataHoraGeracaoInMillis` do TCU) são convertidas para America/Sao_Paulo antes de truncar para data.
Numa consulta perto da meia-noite servida pelo cache, vale a `data_referencia` da consulta nova, não a da evidência; a idade da evidência aparece no texto.
A idade das bases locais (T5d) é medida contra o instante da consulta.
O usuário não escolhe a data de referência no MVP (B21); o campo existe só nos testes e no replay.

Formatos (B2): cada normalizador tem o seu parser de data, testado com os casos reais (`"0"` do GRPCOM, `""`, "Sem informação", data final ausente do C33, DD/MM/AAAA da CGU, ISO do OpenCNPJ, ISO em UTC do ORDS) e o de número com vírgula decimal; o domínio só vê `date`, `Decimal` e `None`.
A API devolve ISO 8601; a página formata `DD/MM/AAAA` e `R$ 1.234,56`.

---

# T4 - Contrato dos adapters e modelo de dados normalizado

## Revisão do 24.2 do spec (adotada no spec v1.2, Q41)

O 24.2 da spec 1.1 fazia o adapter devolver `estado` (OK, RESTRICAO...).
Isso coloca regra de negócio dentro da coleta e impede aplicar D3, D5 e D13, que precisam ver dados de mais de uma fonte ao mesmo tempo.

Recomendação: o adapter devolve fatos normalizados ou uma falha tipada; quem decide estado é o motor.

```python
@dataclass(frozen=True, slots=True)
class Obtido(Generic[T]):
    dados: T
    evidencia: RefEvidencia        # id + sha256 + recebida_em + de_cache

@dataclass(frozen=True, slots=True)
class NaoEncontrado:
    evidencia: RefEvidencia

@dataclass(frozen=True, slots=True)
class Falha:
    motivo: MotivoFalha            # TIMEOUT, HTTP_5XX, HTTP_4XX, FORMATO_INESPERADO, NAO_SUPORTADO, BASE_VENCIDA
    detalhe: str
    evidencia: RefEvidencia | None

type Coleta[T] = Obtido[T] | NaoEncontrado | Falha
```

```python
class FonteCadastral(Protocol):
    nome: str
    aceita_alfanumerico: bool
    async def consultar(self, cnpj: str) -> Coleta[CadastroComDatasets]: ...
```

Cada fonte tem seu protocolo pequeno (cadastral, certidões TCU, perfil Mapa) em vez de uma interface genérica com `dict`.
O TTL sai do adapter e vai para a configuração do cache (T7), porque é política e não comportamento da fonte.
`verificacoes: list[int]` sai do adapter: quem sabe que dado alimenta qual verificação é o motor.

## Modelo de dados normalizado (domínio)

| Tipo | Campos principais | Observações |
|---|---|---|
| `Cadastro` | cnpj, razao_social, nome_fantasia, situacao (enum 1 a 8), situacao_data, motivo_codigo, motivo_descricao, matriz (bool), natureza_codigo (int ou None), natureza_descricao, cnae_principal (str 7), cnaes_secundarios (tuple), data_inicio, uf, municipio, qsa (tuple[Dirigente]), fonte, data_base | Modelo sugerido na ficha da BrasilAPI. `natureza_codigo` None quando a descrição do OpenCNPJ não estiver no mapeamento (D17: vira ALERTA, nunca NÃO ELEGÍVEL). |
| `Dirigente` | nome, qualificacao, data_entrada, documento_mascarado, pessoa_fisica (bool) | Dado pessoal; não sai na API pública (T9). |
| `Sancao` | cadastro (CEPIM, CEIS, CNEP), documento, raiz, nome, categoria, data_inicio, data_fim (None = sem fim), orgao, esfera, uf, abrangencia, fundamentacao, processo, valor_multa, codigo_sancao, origem_informacoes, fontes | Mesmo tipo para CSV local e OpenCNPJ datasets, que têm os mesmos campos e o mesmo `codigo_sancao` (spec 18A.3). CEPIM sem datas. |
| `CertidaoTcu` | tipo (INIDONEOS, CNIA, CEIS, CNEP), situacao (NADA_CONSTA, CONSTAM_REGISTROS, INDISPONIVEL, NAO_SUPORTADO), observacao, datas_observacao (datas entre parênteses, Q35), processos (números do CNIA, Q19), link_manual | `RespostaTcu` agrega as 4 certidões + `cnpj_encontrado` + razão social. |
| `RegistroListaTcu` | lista (INIDONEOS, CONTAS_IRREGULARES), documento, raiz, nome, processo, acordao, data_acordao, data_transito, data_final | Linhas das listas da Plataforma de Certidões (Q34, Q21). |
>>>>

| `PerfilMapa` | id_osc, situacao, preenchido_pela_osc (bool), indice_preenchimento, certificados (tuple) | Regra de "preenchido pela OSC" da ficha do Mapa, aplicada no normalizador. |
| `AtoCebas` | cnpj, area, tipo_ato (CONCESSAO, RENOVACAO, INDEFERIMENTO, CANCELAMENTO, RECONSIDERACAO, PRORROGACAO, ARQUIVAMENTO, OUTRO), deferido, vigencia_inicio, vigencia_fim, data_publicacao, ref_ato, torna_sem_efeito, trecho, url_pdf | D16 e ficha do DOU. |
| `SituacaoCebas` | fonte (SISCEBAS_SAUDE, PLANILHA_MDS_2024, PLANILHA_MEC_2023), area, cebas, situacao_texto, vigencia_inicio, vigencia_fim, portaria, data_base | Linha de retrato oficial. |

## Dataclasses ou pydantic

| Opção | Avaliação |
|---|---|
| A. Pydantic em tudo | Validação grátis, mas acopla o domínio a uma biblioteca e deixa o motor mais pesado para ler e testar. |
| B. Dataclasses `frozen, slots` no domínio e no motor; pydantic só nas bordas (API, configuração e validação do JSON bruto dentro de cada normalizador) | Domínio sem dependências, imutável, rápido; validação forte onde entra dado externo. |
| C. msgspec / attrs | Bons, mas é mais uma biblioteca para aprender sem ganho relevante aqui. |

Recomendação: B, coerente com `cnpj.py` (que já usa `@dataclass(frozen=True, slots=True)`).
Os normalizadores podem declarar modelos pydantic privados para o formato bruto de cada fonte: se a fonte mudar o contrato, o erro aparece como `Falha(FORMATO_INESPERADO)` com a mensagem de validação, em vez de um `KeyError` perdido.

---

# T5 - Fontes online e bases locais

## T5a - Divisão online x local

| Dado | Origem | Como | Motivo |
|---|---|---|---|
| Cadastro (verificações `situacao` a `tempo`, QSA) | OpenCNPJ, fallback BrasilAPI | Online por consulta, com cache | D17; base de 73 milhões de CNPJs não compensa ingerir no MVP (fica para o pós-MVP). |
| CEPIM, CEIS, CNEP (CGU) | CSV diário oficial | Local, ingestão diária, **observação principal** com busca exata e por raiz | D14; ver T5b. |
| CEPIM, CEIS, CNEP (OpenCNPJ) | OpenCNPJ `?datasets=cepim,ceis,cnep` | Online, **na mesma chamada do cadastro** (zero requisição extra), observação adicional | D14, Q36. |
| Inidôneos TCU, CNIA, CEIS, CNEP | TCU Consulta Consolidada | Online por consulta, com cache | D13, D14. |
| Lista de inidôneos TCU (CSV) | Plataforma de Certidões (certidoes.apps.tcu.gov.br) | Local, ingestão diária (35 KB), segunda observação de `tcu_inidoneos` | Q34. |
| Lista de contas irregulares TCU (CSV) | Plataforma de Certidões | Local, ingestão diária (11 MB) | [ORIENTADOR Q21]; também fonte de dirigentes se Q8 aceitar. |
| Listas de dirigentes (TCU inabilitados, TCE-SP) | Plataforma de Certidões e TCE-SP | Local, diária (TCU) e mensal (TCE-SP) | [PENDENTE Q8]. |
| Mapa das OSCs | API do Ipea | Online, cache de 30 dias, 5 chamadas por consulta (Q38) | Base CSV de 344 MB não traz certificados nem perfil. |
| CEBAS Saúde | SisCEBAS Saúde XLS | Local, ingestão diária | D16; 24 s para gerar, inviável por consulta. |
| CEBAS MDS e MEC | Planilhas oficiais (2024 e 2023) | Local, carga única com hash fixado | D16; retrato estático. |
| CEBAS atos | DOU XML mensal | Local, carga desde 12/2023 (corte do MEC) + mensal | D16, Q39; cerca de 22 meses de XML, imagens descartadas na carga. |
| Natureza jurídica, CNAE, regras do orientador, mensagens, limites | Arquivos JSON do repositório | Embutidos no pacote, versionados | Revisão do orientador por diff; nada a ingerir. |
| API do Portal com chave | - | Fora do motor e da configuração | D14: ferramenta manual de conferência (spec 19.4). |

## T5b - CEPIM, CEIS e CNEP: CSV local como principal (D14)

Decisão (D14): o CSV diário oficial da CGU é a observação principal de CEPIM, CEIS e CNEP desde a primeira fatia de sanções; o OpenCNPJ `?datasets=` e o TCU são observações adicionais.
Motivos: D15 (dirigentes) já exige ingerir os CSVs de CEIS e CNEP, porque só eles têm o CPF completo; o CSV do CEPIM tem 640 KB; o CSV permite busca por raiz (a API do Portal não permite, T4 de 01/10/2026); e se o OpenCNPJ cair e o fallback for a BrasilAPI, não há datasets, e o CEPIM, que é a verificação mais importante para OSC, ficaria INDISPONIVEL.
O OpenCNPJ datasets vem de graça na chamada cadastral e cobre o CSV local vencido ou com falha de carga (Q36).
As duas observações são combinadas pela regra do T3d, casando os registros pelo código da sanção (os campos são os mesmos, spec 18A.3).
A resposta real de `?datasets=` com sanção já existe (49 casos, `fase0/casos/respostas/`; exemplo da Santa Casa de Pacaembu em `fase0/brasilapi/respostas/extras/`).

## T5c - Como ingerir e versionar

Cada ingestão é um comando idempotente: `python -m validador_osc ingerir <fonte>`.
Ciclo de vida de uma carga:

1. Cria registro `carga` (EM_ANDAMENTO) com fonte, URL e data da fonte (do nome do arquivo ou da coluna DATA ATUALIZAÇÃO).
2. Baixa para `var/arquivos/<fonte>/<sha256>.<ext>` (endereçado por conteúdo); se o hash já existe numa carga concluída, encerra como "sem mudança".
3. Faz o parse em streaming e insere as linhas com `carga_id`, numa transação.
4. Valida sanidade; se falhar, marca FALHOU e a carga anterior continua ativa. Limites por fonte na configuração (B19): colunas esperadas exatamente iguais às do cabeçalho conhecido; quantidade mínima de linhas de 80% da carga ativa anterior (na primeira carga, um piso fixo por fonte, por exemplo 20.000 no CEIS, 1.500 no CNEP, 3.000 no CEPIM, 100 nos inidôneos); proporção de documentos de 14 dígitos com DV válido acima de 99%; data da fonte não anterior à da carga ativa. Esses limites são o teste de contrato das bases locais.
5. Marca a nova carga como ativa (índice único parcial: uma ativa por fonte) na mesma transação.

Cargas antigas ficam guardadas (com limite configurável) porque consultas passadas apontam para elas.
O DOU é cumulativo: cada ZIP mensal é uma carga, e os atos são únicos por `ref_ato` (`idMateria#n`); o ZIP pode ser apagado depois do parse (só o hash e a URL ficam), porque 95% dele são imagens.

## T5d - Agendamento e validade das bases

| Opção | Avaliação |
|---|---|
| A. Comando manual | Zero infraestrutura; depende de lembrar. |
| B. APScheduler dentro do processo da API | Dispara duplicado com mais de um worker, mistura carga longa com atendimento, morre junto com a API. |
| C. Agendador externo chamando o mesmo comando (Agendador de Tarefas do Windows local, cron do host ou serviço `agendador` no Compose com supercronic) | Separação limpa, mesmo comando testado; uma peça a mais só no deploy. |
| D. Celery beat / RQ scheduler | Exige broker; D1 reserva fila para lote. |

Recomendação: A no desenvolvimento e na demonstração local, C no deploy.
O comando `atualizar-bases` roda todas as ingestões devidas, em ordem, e é o único ponto de entrada para qualquer agendador.

Para nunca usar base velha em silêncio, cada fonte local tem uma idade máxima configurável (`dados/limites.json`); acima dela a observação vira `Falha(BASE_VENCIDA)`.
**[DECIDIDO Q6]** Valores: CEIS e CNEP 3 dias, CEPIM 7 dias (já chega com 2 dias de atraso), SisCEBAS Saúde 7 dias, DOU 75 dias (defasagem natural de até 6 semanas), planilhas MDS/MEC sem limite (retrato declarado com data de corte na mensagem).
Bases acrescentadas pela revisão: lista de inidôneos do TCU 3 dias (Q34), lista de contas irregulares do TCU 7 dias [ORIENTADOR Q21]; se Q8 aceitar, TCU inabilitados 7 dias e TCE-SP 45 dias.
Espelho cadastral (Q6, B6): o OpenCNPJ com mais de 60 dias (data do `/info`) gera ALERTA em `situacao` com a data dos dados; não é base local, mas segue a mesma ideia de nunca usar dado velho em silêncio.

Base vencida ou ausente (B5): a mensagem ao usuário diz "base de [fonte] de DD/MM/AAAA, mais velha que o limite de N dias" (ou "base ainda não carregada" no primeiro uso); a página `/fontes` mostra a base em destaque e o log registra nível de erro; todo texto de verificação baseada em base local diz "consultado na base de DD/MM/AAAA".
A página e a rota `/api/v1/fontes` mostram, para cada base, a data da carga ativa e se está dentro da validade.

---

# T6 - Resiliência

## T6a - Timeouts e prazo global

| Fonte | Timeout por tentativa | Base |
|---|---|---|
| OpenCNPJ | 5 s | Mediana 74 ms, máximo 432 ms. |
| BrasilAPI | 12 s | Falha típica em cerca de 10,2 s (ficha). |
| TCU consolidada | 30 s | Cerca de 5,5 s sem cache no servidor. |
| Mapa das OSCs | 10 s | Pico isolado de 15,9 s; informativa. |

Cada consulta tem um prazo global de 45 s; ao estourar, o que não respondeu vira `Falha(TIMEOUT)` e o resultado sai mesmo assim.
Timeouts usam `httpx.Timeout(connect=..., read=..., write=..., pool=...)` separados, para distinguir "não conectou" de "conectou e travou".

Orçamento por fase (B10), porque os timeouts por tentativa somados passam do prazo global:

| Fase | Orçamento | O que cabe |
|---|---|---|
| Cadastro (E1) | até 20 s | OpenCNPJ do consultado (5 s, 1 retry só se couber) e, se filial, da matriz em paralelo; BrasilAPI (12 s) só no que sobrar. |
| Fan-out (E2) | até 25 s | TCU com uma tentativa longa (até 25 s, sem retry quando o primeiro timeout já gastou o orçamento); Mapa com 5 chamadas de até 4 s, 1 s entre elas; bases locais em milissegundos. |

O retry só acontece se o tempo restante da fase couber a próxima tentativa inteira; senão vira `Falha(TIMEOUT)`.
O pior caso fica dentro de 45 s, e o caso comum (cache frio, fontes no ar) em cerca de 6 a 10 s.

## T6b - Retry e backoff

| Opção | Avaliação |
|---|---|
| A. `tenacity` | Madura, mas genérica; tratar `Retry-After` e não repetir 4xx exige configuração cuidadosa. |
| B. `stamina` | Boa API, mais uma dependência. |
| C. Função própria de cerca de 40 linhas no `fontes/http.py`, testada com relógio falso | Regras explícitas e poucas: só GET idempotente; repete timeout de conexão, 502, 503, 504 e 429; respeita `Retry-After` até um teto; backoff exponencial com jitter. |

Recomendação: C, porque as regras por fonte são diferentes e precisam estar visíveis.
Política por fonte: OpenCNPJ até 2 tentativas; BrasilAPI 1 tentativa (a ficha mostra que repetir não ajuda e o `retry-after` é de 120 s); TCU 1 tentativa longa e uma segunda só se couber no orçamento (B10); Mapa 2 tentativas por chamada, dentro do orçamento.

## T6c - Fallback cadastral

OpenCNPJ é consultado primeiro.
BrasilAPI é chamada quando o OpenCNPJ devolve `Falha` ou `NaoEncontrado` (o 404 pode ser espelho desatualizado, e uma segunda base aumenta a confiança).
Os dois `NaoEncontrado` levam a `situacao` INDISPONIVEL com motivo `NAO_ENCONTRADO` e a mensagem do spec 5.4 ("CNPJ não encontrado no espelho de DD/MM/AAAA; pode ser recém-criado ou inexistente"), e o fan-out não roda (Q26).
Minha Receita não é chamada (é a mesma origem da BrasilAPI).
Quando o cadastro vier da BrasilAPI, não há datasets: CEPIM, CEIS e CNEP dependem do CSV local (principal) e do TCU (T5b).

## T6d - Circuit breaker

Não no MVP.
Com uma consulta por vez e prazo global, um breaker só economiza alguns segundos em pane de fonte, e acrescenta estado compartilhado difícil de testar.
O lugar para ele fica reservado no `fontes/http.py` se houver lote.

## T6e - Limite por host e cortesia

Um `httpx.AsyncClient` por host, criado na inicialização do app, com `Limits` de conexões.
Regra decidida (Q37, spec 23): intervalo mínimo por host para chamadas em sequência de uma mesma consulta e em lote, de 1 s para TCU e Mapa; APIs servidas por CDN (OpenCNPJ, BrasilAPI) só com limite de concorrência (semáforo de 4); downloads de bases locais no máximo 1 por dia por arquivo.
User-Agent do projeto em todas as chamadas, vindo da configuração.
O limite é por processo, suficiente para um processo; se houver vários, vira um limitador no Postgres (advisory lock), não Redis.

Concorrência entre usuários (B15): chamadas iguais em andamento (mesma fonte e mesma chave) são coalescidas dentro do processo; a segunda consulta espera o mesmo `Future` em vez de abrir outra chamada ao TCU.
Duas consultas ao mesmo CNPJ em sequência usam o cache (T7).

## T6f - Comportamento INDISPONIVEL

Toda `Falha` vira INDISPONIVEL (ou NAO_VERIFICADO quando o motivo é NAO_SUPORTADO) com a fonte, o motivo legível e o link de consulta manual quando houver (`linkConsultaManual` do TCU, URL do Mapa).
A resposta HTTP da API continua 201: indisponibilidade de fonte é resultado de negócio (INCONCLUSIVA), não erro do serviço.
Falhas são gravadas como evidência (sem corpo quando não houver) para diagnóstico, mas nunca servem de cache.

---

# T7 - Cache e evidências

## T7a - Uma tabela para cache e evidência

| Opção | Avaliação |
|---|---|
| A. Cache separado (Redis ou tabela) + evidências em outra tabela | Duas cópias do mesmo dado, duas políticas de expiração. |
| B. Tabela `resposta_fonte` única: toda resposta bruta é evidência; o cache é "a última resposta bem-sucedida da mesma fonte e chave dentro do TTL" | Uma fonte de verdade, evidência garantida para todo dado usado. |

Recomendação: B.
Uma consulta servida pelo cache aponta para a mesma evidência original (com `de_cache = true` e a data em que ela foi obtida), o que é exatamente o que o relatório precisa mostrar.

## T7b - TTL por fonte (spec 24.4 revisado)

| Fonte | TTL | Mudança em relação ao spec 1.1 |
|---|---|---|
| OpenCNPJ com datasets (chamada cadastral) | 24 horas | A chamada é uma só e traz sanções, então o TTL efetivo é 24 h (Q36, adotado no spec 1.2, 24.4). O espelho cadastral muda só a cada atualização do OpenCNPJ, então isso custa uma chamada de 100 ms por dia por CNPJ. |
| BrasilAPI | 7 dias | Mantido. |
| TCU consolidada | 24 horas | Mantido. |
| Mapa das OSCs | 30 dias | Mantido. |
| Não encontrado (404) | 6 horas | Novo: evita repetir 404 em sequência sem congelar um CNPJ recém-criado. |
| Bases locais | sem cache | Consulta direta à carga ativa, com idade máxima (T5d). |
| Falhas | nunca | Novo. |

Parâmetro `atualizar=true` na API ignora o cache (spec: "relatório de auditoria sem cache").

## T7c - Hash e armazenamento do bruto

O sha256 é calculado sobre os bytes exatos recebidos (corpo HTTP sem decodificação de conteúdo aplicada pelo cliente, ou seja, depois de descomprimir gzip, antes de qualquer parse).

| Opção | Avaliação |
|---|---|
| A. JSONB | Consultável, mas normaliza chaves e espaços: o hash deixa de bater com o que se guardou. Não serve para HTML ou XLS. |
| B. `bytea` no Postgres | Bytes exatos, hash verificável, backup junto com o resto; o Postgres comprime valores grandes automaticamente (TOAST). Respostas por consulta somam cerca de 10 a 20 KB. |
| C. Arquivos no disco com caminho no banco | Bom para arquivos grandes; para respostas pequenas complica backup e consistência transacional. |

Recomendação: B para respostas de fontes online e C (endereçado por sha256 em `var/arquivos/`) para os arquivos de ingestão (CSV de 34 MB, XLS, ZIP do DOU).
A API expõe a evidência por id com o `Content-Type` original e o hash num header, com o acesso restrito do T9e.

---

# T8 - PostgreSQL: esquema, migrações e acesso

## T8a - Acesso ao banco

| Opção | Avaliação |
|---|---|
| A. SQLAlchemy 2 (ORM tipado com `Mapped[]`) + driver psycopg 3 | Padrão de mercado, integra com Alembic, async e sync com o mesmo driver, COPY disponível para cargas. |
| B. SQLModel | Mistura modelo de banco com pydantic, o que conflita com o domínio em dataclasses (T4); menos maduro. |
| C. asyncpg puro com SQL escrito à mão | Rápido, mas sem migrações automáticas, sem tipos e só async (a ingestão ficaria mais trabalhosa). |
| D. SQLAlchemy com asyncpg | Funciona, mas exige outro driver para o Alembic e a ingestão síncrona. |

Recomendação: A.
A API usa a engine async (`postgresql+psycopg`), a CLI de ingestão e o Alembic usam a engine síncrona, ambas com o mesmo driver.
Os modelos ORM ficam só em `persistencia/`; os repositórios convertem para os tipos de domínio, então nenhuma entidade ORM vaza para o motor ou para a API.
Postgres 17 em contêiner (imagem oficial `postgres:17`).
Risco a checar na fatia 0: disponibilidade de wheels de `psycopg[binary]` para Python 3.14 no Windows (ver T17).

## T8b - Migrações

Alembic, com autogenerate como rascunho e revisão manual de cada migração.
Os testes de integração sobem um banco vazio e aplicam `alembic upgrade head`, garantindo que as migrações e os modelos não divergem.

## T8c - Tabelas principais

```
resposta_fonte            -- evidência e cache (T7)
  id              bigint identity PK
  fonte           text        -- opencnpj, brasilapi, tcu_consolidada, mapa_osc_busca, mapa_osc_perfil ...
  chave           text        -- ex.: "19131243000197?datasets=cepim,ceis,cnep"
  url             text
  resultado       text        -- OBTIDO | NAO_ENCONTRADO | FALHA
  motivo_falha    text null
  http_status     int null
  recebida_em     timestamptz
  duracao_ms      int
  tentativas      int
  content_type    text null
  corpo           bytea null
  sha256          char(64) null
  indice (fonte, chave, recebida_em desc) where resultado <> 'FALHA'

consulta
  id              uuid PK
  cnpj_informado  text
  cnpj            varchar(14)
  cnpj_matriz     varchar(14) null
  esfera          text null
  data_referencia date
  iniciada_em     timestamptz
  duracao_ms      int
  status          text        -- CNPJ_INVALIDO | INAPTA | INCONCLUSIVA | APTA_COM_RESSALVAS | APTA
  resultado       jsonb       -- documento completo devolvido pela API
  versao_app      text
  versao_regras   text        -- sha256 do conjunto de regras (B11), ver abaixo
  forcou_atualizacao bool
  chave_idempotencia text null -- header Idempotency-Key (B4)
  indices (cnpj, iniciada_em desc), unico (chave_idempotencia) where not null

consulta_evidencia
  consulta_id        uuid FK
  resposta_fonte_id  bigint FK null
  carga_id           bigint FK null
  papel              text     -- cadastro_consultado, cadastro_matriz, tcu, mapa_busca, cebas_saude ...
  de_cache           bool

carga
  id              bigint identity PK
  fonte           text        -- cgu_cepim, cgu_ceis, cgu_cnep, tcu_inidoneos, tcu_contas_irregulares,
                              -- siscebas_saude, cebas_mds_2024, cebas_mec_2023, dou_s01
                              -- (+ tcu_inabilitados, tcesp_terceiro_setor se Q8 aceitar)
  status          text        -- EM_ANDAMENTO | CONCLUIDA | SEM_MUDANCA | FALHOU
  ativa           bool        -- índice único parcial (fonte) where ativa
  referencia      text null   -- ex.: "2026-08" para o DOU
  data_base       date        -- data dos dados segundo a fonte
  iniciada_em, concluida_em  timestamptz
  url             text
  arquivo_caminho text null
  arquivo_sha256  char(64)
  arquivo_bytes   bigint
  linhas          int
  erro            text null

sancao_registro           -- CSVs da CGU
  id, carga_id FK, cadastro (CEPIM|CEIS|CNEP), tipo_pessoa char(1) null,
  documento text null,        -- só PJ (14 dígitos); NULL para pessoa física (B13)
  raiz char(8) null, nome_normalizado text, cpf_meio char(6) null, cpf_dv_final char(2) null,
  nome, categoria, data_inicio date null, data_fim date null,
  orgao, esfera, uf, abrangencia, fundamentacao, processo, valor_multa numeric null,
  codigo_sancao text, origem_informacoes text,
  linha jsonb  -- linha original completa (evidência), com o CPF de PF já mascarado
  indices (carga_id, documento), (carga_id, raiz), (carga_id, nome_normalizado, cpf_meio)

lista_tcu_registro        -- inidôneos (Q34) e contas irregulares (Q21) da Plataforma de Certidões
  id, carga_id FK, lista (INIDONEOS|CONTAS_IRREGULARES|INABILITADOS), tipo_registro (CPF|CNPJ),
  documento text null,        -- só CNPJ; para CPF, as mesmas regras do B13
  raiz char(8) null, nome_normalizado text, cpf_meio char(6) null, cpf_dv_final char(2) null,
  nome, processo, acordao, data_acordao date null, data_transito date null, data_final date null,
  linha jsonb
  indices (carga_id, documento), (carga_id, raiz), (carga_id, nome_normalizado, cpf_meio)

cebas_ato                 -- DOU
  id, carga_id FK, ref_ato text unique, cnpj varchar(14), cnpj_dv_ok bool, entidade, municipio_uf,
  area, tipo_ato, deferido bool null, detalhe, validade_texto,
  vigencia_inicio date null, vigencia_fim date null, torna_sem_efeito_ref text null,
  data_publicacao date, data_ato date null, identificacao_ato, edicao, pagina, url_pdf, trecho
  indice (cnpj, data_publicacao)

cebas_situacao            -- SisCEBAS Saúde e planilhas MDS/MEC
  id, carga_id FK, fonte, area, cnpj varchar(14), entidade, cebas text, situacao_texto,
  vigencia_inicio date null, vigencia_fim date null, portaria, data_publicacao date null, linha jsonb
  indice (carga_id, cnpj)
```

As colunas `linha jsonb` guardam a linha original para evidência e para reprocessar se a regra mudar; aqui JSONB serve, porque o hash de integridade é o do arquivo inteiro.
`cnpj` usa `varchar(14)` e aceita alfanumérico.

Política de CPF no banco (B13): o casamento de dirigentes só usa nome normalizado + 6 dígitos do meio, então o banco não guarda CPF completo de pessoa física.
Para cada PF ficam o nome normalizado, os 6 dígitos do meio e os 2 dígitos finais (DV), que ajudam a desempatar sem reconstruir o CPF; a coluna `linha` guarda o CPF já mascarado (`***XXXXXX**`).
O arquivo bruto com CPF completo fica só em `var/arquivos/` (fora do git, acesso local do operador) para a prova de integridade pelo hash; ele é apagado quando a carga deixa de ser referenciada por consultas dentro do limite de retenção.
CPF nunca vai para log, fixture ou resposta da API.

Versão das regras (B11): `versao_regras` é o sha256 da concatenação ordenada de `natureza_juridica.json`, `regras_cnae.json`, `regras_orientador.json`, `mensagens.json` e `limites.json` (idades máximas, limite do espelho, janela de 8 anos) e da lista de fontes ativas; o replay de uma consulta usa a mesma versão.

---

# T9 - API HTTP

## T9a - Síncrona ou assíncrona

| Opção | Avaliação |
|---|---|
| A. Síncrona: a requisição espera o resultado (pior caso cerca de 6 a 10 s sem cache, cerca de 0,3 s com cache) | Simples para cliente e página; sem polling, sem estado intermediário. |
| B. Assíncrona: 202 + id + polling ou SSE | Necessária para lote ou consultas de minutos; complexidade sem ganho para uma consulta. |

Recomendação: A, com prazo global (T6a).
Lote, se vier, entra como recurso novo (`POST /api/v1/lotes`, 202), sem mudar a consulta unitária.

## T9b - Endpoints

| Método e rota | Função |
|---|---|
| `POST /api/v1/consultas` | Corpo `{"cnpj": "...", "esfera": "municipio|estado|uniao" (opcional), "atualizar": false}`, header opcional `Idempotency-Key`. Executa e devolve 201 com o resultado e `Location: /api/v1/consultas/{id}`. |
| `GET /api/v1/consultas/{id}` | Resultado gravado (link permanente para auditoria e para a página). Aberto, com id não adivinhável (UUID v4); os nomes de dirigentes com possível correspondência só aparecem com token de operador (Q9). |
| `GET /api/v1/fontes` | Estado de cada fonte: online (última resposta, latência, falhas recentes) e local (carga ativa, data da base, validade). |
| `GET /api/v1/evidencias/{id}` | Bruto com o content-type original e header `X-Sha256` (acesso restrito, T9e). |
| `GET /health` e `GET /health/ready` | Processo vivo; banco acessível e migrações aplicadas. |
| `/docs` | Swagger gerado pelo FastAPI. |

POST em vez de `GET /consultas/{cnpj}` porque cada chamada cria um registro de consulta com evidências e pode acionar fontes externas; o GET fica reservado para ler o que já existe.
Prefixo `/api/v1` permite evoluir o formato sem quebrar a página.

Idempotência (B4): com `Idempotency-Key`, a mesma chave devolve a mesma consulta (200 com o resultado gravado).
Sem a chave, a mesma combinação (CNPJ normalizado, esfera, `atualizar=false`) em menos de 10 s devolve a consulta já feita; o formulário desabilita o botão enquanto espera.

## T9c - Formato da resposta (24.3 revisado, sem score; adotado no spec v1.2, Q41)

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

Mudanças em relação ao 24.3 da spec 1.1: sem `score` (D8); `alertas` vira `motivos` + `resumo` (os textos já estão em cada verificação); evidências ficam dentro de cada verificação (rastreio direto); entram `cnpj_avaliado`, `estabelecimento`, `data_referencia`, `esfera`, `versao`, `avisos` (Q5) e `situacao` nas informativas (Q40).
O QSA completo não aparece na resposta; a verificação `dirigentes` mostra só as possíveis correspondências, e os nomes só para o operador (Q9).

## T9d - Erros

Formato RFC 9457 (`application/problem+json`).
CNPJ com DV inválido, formato errado ou base repetida não é erro HTTP: é resultado de negócio com status `CNPJ_INVALIDO` pela verificação `dv` (201), sem chamada externa (Q3); a página mostra como erro de digitação no próprio formulário, com o DV esperado.
422 só para corpo inválido (campo ausente, texto com mais de 32 caracteres, esfera desconhecida).
404 para consulta ou evidência inexistente.
503 quando o banco está fora (sem banco não há evidência, e o serviço não responde sem evidência).
Falha de fonte externa nunca vira 5xx (T6f).

## T9e - Proteção mínima

Se houver qualquer exposição fora da máquina local: limite de consultas por IP (proposta: 10 por minuto, implementação simples em memória) para não fazer o projeto ser bloqueado pelo TCU ou pelo Ipea por abuso de terceiros.
`/api/v1/evidencias` só com token de operador (header configurado no `.env`), porque o bruto do cadastro contém o QSA (nomes de pessoas).
**[DECIDIDO Q9]** O link `/consultas/{id}` é aberto (é o que a OSC manda para a prefeitura), mas os nomes de dirigentes com possível correspondência só aparecem com o token de operador; o público vê "possível correspondência em N dirigente(s); consulte o operador".
Retenção limitada (90 dias e depois só o status) fica para quando a LGPD for tratada (D9).

---

# T10 - Interface para o usuário no MVP **[DECIDIDO Q10]**

| Opção | O que é | Prós | Contras |
|---|---|---|---|
| A. Só API + Swagger | `/docs` do FastAPI | Zero trabalho de interface. | Ruim para demonstrar a quem não é técnico; o resultado é um JSON longo. |
| B. Páginas HTML renderizadas no servidor (Jinja2), mesma aplicação, CSS próprio pequeno, JavaScript mínimo (indicador de "consultando" durante os segundos de espera) | Formulário (CNPJ + esfera) e página de resultado com link permanente `/consultas/{id}`, cartões por verificação, fontes e datas, versão para impressão. | Sem build, sem Node, mesmo deploy, testável com o cliente HTTP do FastAPI; a página de resultado com CSS de impressão já resolve o "PDF" (T16). | Interatividade limitada (suficiente aqui). |
| C. B + HTMX | Atualizações parciais sem recarregar | Experiência um pouco mais fluida. | Mais uma tecnologia sem necessidade real: a consulta é um formulário e uma página. |
| D. SPA (React, Vue) | Front separado | Interface rica. | Build, segundo projeto, CORS, duplicação de tipos; desproporcional para o MVP. |

Decisão do dono (D19, Q10): interface simples, com HTML + CSS + JavaScript simples servidos pelo próprio app, sem framework de frontend; é a opção B.
É o que melhor demonstra o projeto numa banca (digitar um CNPJ e ver o veredito com a explicação de cada verificação e de onde veio cada dado), sem criar um segundo projeto para manter.
Precisa de `jinja2` e `python-multipart` (formulário); o JavaScript fica num arquivo estático pequeno (indicador de espera e botão desabilitado durante a consulta, B4), sem build.
A página `/fontes` (estado e data de cada base) ajuda a mostrar a honestidade do sistema sobre o que verifica.
O aviso em destaque das verificações não eliminatórias indisponíveis (Q5) fica no topo do resultado, junto do status.

---

# T11 - Configuração, segredos, logs e observabilidade

## T11a - Configuração

`pydantic-settings` com prefixo `VOSC_`, lendo variáveis de ambiente e um `.env` local (fora do git); `.env.example` versionado documenta tudo.
Itens: `DATABASE_URL`, `USER_AGENT`, timeouts, orçamento por fase e TTLs por fonte, `DIR_ARQUIVOS`, `TOKEN_OPERADOR`, `LOG_FORMATO` (`console` ou `json`), `LOG_NIVEL`, `FUSO` (`America/Sao_Paulo`).
As idades máximas das bases e as regras do orientador ficam nos arquivos versionados de `dados/` (entram na `versao_regras`), não em variável de ambiente.
A chave da API do Portal não faz parte da configuração (D14): ela só é usada pelo script manual `fase0/portal/testar_api_com_chave.py`, que a lê do `.env` sem nunca gravá-la.
O objeto de configuração é criado uma vez e injetado (dependência do FastAPI e parâmetro da CLI), nunca lido como global dentro de `regras/`.
Segredos nunca em log: os campos usam `SecretStr`.

## T11b - Logs

| Opção | Avaliação |
|---|---|
| A. `logging` da stdlib com formatter JSON próprio | Sem dependência, mas contexto por requisição exige código. |
| B. `structlog` sobre a stdlib | Contexto por `contextvars` (id da consulta, CNPJ), saída legível no desenvolvimento e JSON no deploy, mesma API. |

Recomendação: B.
Eventos mínimos: requisição recebida e respondida (rota, status, ms, id da requisição); cada chamada de fonte (fonte, chave, status HTTP, ms, tentativa, de_cache, motivo de falha); conclusão da consulta (status, motivos, ms); cada carga (fonte, linhas, hash, duração, resultado).
CNPJ pode aparecer em log (dado público de pessoa jurídica); nomes de dirigentes não.

## T11c - Observabilidade

No MVP: logs estruturados + `/api/v1/fontes` + `/health/ready`.
Sem Prometheus, OpenTelemetry ou Sentry por enquanto; o volume não justifica e os logs JSON permitem ligar qualquer um deles depois.
Um teste "vivo" agendado (T13) faz o papel do "teste de contrato diário" do cap. 23.

---

# T12 - Dependências, ambiente e qualidade de código

## T12a - Gerenciador

| Opção | Avaliação |
|---|---|
| A. pip + venv + requirements.txt | Universal, mas sem lockfile com hashes de forma nativa e sem gestão da versão do Python. |
| B. Poetry | Bom, mas mais lento e com formato próprio em partes do `pyproject`. |
| C. uv | Lockfile multiplataforma (`uv.lock`), instala a versão do Python, muito rápido, segue os padrões do `pyproject` (PEP 621 e dependency groups). |

Recomendação: C (instalar com `winget install astral-sh.uv` ou pelo instalador oficial).
O lockfile garante que Windows (desenvolvimento) e Linux (CI e contêiner) instalam exatamente as mesmas versões.

## T12b - Versão do Python

3.14 (`requires-python = ">=3.14,<3.15"` e `.python-version`), que é o que está instalado e já roda o código existente.
Imagem Docker `python:3.14-slim`.

## T12c - Dependências propostas

| Grupo | Pacotes |
|---|---|
| Execução | fastapi, uvicorn, httpx, pydantic, pydantic-settings, sqlalchemy, psycopg[binary], alembic, jinja2, python-multipart, structlog, lxml (DOU), xlrd (SisCEBAS XLS), openpyxl (planilhas) |
| Desenvolvimento | pytest, anyio (plugin de testes async, já vem com httpx), ruff, mypy, import-linter, pre-commit |
| Opcional (E2E de navegador) | playwright |

Sem `respx`: o `httpx.MockTransport` nativo basta para simular fontes.

## T12d - Lint, formatação, tipos e pre-commit

ruff para lint e formatação (linha de 110, regras `E, F, W, I, UP, B, SIM, RUF, PL, PT, DTZ, ASYNC, S` com exceções justificadas; `DTZ` impede datetime sem fuso, importante para vigências).
mypy `--strict` em todo o pacote (o código atual já passa), com o plugin do pydantic.
import-linter com os contratos do T2.
pre-commit: ruff, ruff-format, mypy (hook local via `uv run`), import-linter, `check-added-large-files` (limite de 1 MB, essencial com os downloads da Fase 0), `detect-private-key`, fim de linha e espaços.
O CI roda os mesmos comandos, então o pre-commit é conveniência e o CI é a garantia.

---

# T13 - Estratégia de testes

| Camada | O que testa | Como | Onde roda |
|---|---|---|---|
| Unitários do motor | Cada verificação e a agregação, tabela de casos por regra (D3, D5, D6, D13, vigência na fronteira de datas, natureza desconhecida, religiosa) | Funções puras com `DadosConsulta` montados em código; `data_referencia` fixa; invariantes (não eliminatória nunca dá RESTRICAO) | Sempre, milissegundos |
| Unitários de tabelas | `natureza_juridica.json` e regras CNAE válidas | Validação na carga (como o `classificar_cnae.py` já faz) + os 22 testes existentes migrados | Sempre |
| Normalizadores (contrato) | Bruto real de cada fonte vira o domínio esperado | Fixtures copiadas da Fase 0 para `tests/fixtures/fontes/<fonte>/` (OK, RESTRICAO, 404, 412, 5xx, formatos estranhos como `cnae_fiscal` sem zero à esquerda) | Sempre |
| Cliente HTTP e adapters | Timeouts, retry, `Retry-After`, fallback OpenCNPJ para BrasilAPI, falha tipada | `httpx.MockTransport` e relógio falso | Sempre |
| Ingestores | Parse e sanidade de CSV CGU, XLS SisCEBAS, planilhas, XML do DOU | Amostras pequenas versionadas (as 10 linhas de `fase0/portal/amostras`, um XLS reduzido, os XMLs dos 20 atos conferidos no T2 do DOU) | Sempre |
| Integração com banco | Repositórios, cache por TTL, troca atômica de carga, migrações | Postgres real (serviço no CI, Compose local), banco recriado por sessão, transação revertida por teste | Sempre no CI; local com o banco no ar |
| E2E da API | Casos de referência ponta a ponta | `fase0/casos_referencia.json` (movido para `tests/e2e/casos_referencia.json` quando estabilizar) executado pela API com todas as fontes servidas por fixtures gravadas ("modo replay") e `data_referencia` fixa na data da gravação; afere status final e estado de cada verificação | Sempre |
| E2E de navegador | A página como o usuário usa: digitar CNPJ, esperar, ver o veredito, abrir link permanente, imprimir | Playwright contra o app em modo replay; poucos cenários (APTA, INAPTA, INCONCLUSIVA) | CI e local |
| Vivo | Contrato das fontes reais não mudou; latência; bloqueio de IP | Marcador `vivo`, excluído por padrão (`-m "not vivo"`); afere estrutura, não status (sanções expiram) | Manual e workflow agendado semanal |

Gravação das fixtures: um comando `python -m validador_osc gravar-fixtures <cnpj>` usa os adapters reais e salva o bruto no formato que o modo replay lê, para renovar fixtures sem editar à mão.
Meta de cobertura: 100% de ramos em `regras/` e nos normalizadores; o restante sem meta numérica, guiado pelos E2E.

---

# T14 - Execução local e deploy

## T14a - Execução local

Postgres em contêiner (`docker compose up -d db`); aplicação rodando nativamente com `uv run` e recarga automática, para depurar no PyCharm.
Perfil `completo` do Compose sobe app + banco como no deploy, para conferir a imagem antes de publicar.
Pré-requisito: abrir o Docker Desktop (o daemon não estava ativo na checagem).
Alternativa sem Docker: instalar o PostgreSQL 17 nativo no Windows; funciona, mas o ambiente local fica diferente do CI e do deploy, por isso não é a recomendação.

## T14b - Deploy

Uma imagem Docker (app) + Postgres, descritos no mesmo `compose.yaml`, servem para qualquer destino.

## T14c - Onde demonstrar **[DECIDIDO Q12]**

| Opção | Custo | IP visto pelo TCU | Observações |
|---|---|---|---|
| A. Só local (notebook na apresentação) | Zero | Residencial (já testado, funciona) | Mais seguro para a banca; depende do notebook e da rede do local. |
| B. Local + túnel público (Cloudflare Tunnel) | Zero | Residencial | Link público sem servidor; a máquina precisa estar ligada; exige T9e. |
| C. VM gratuita (por exemplo Oracle Cloud Always Free, região São Paulo) | Zero, com cadastro e cartão | Datacenter | Roda o Compose inteiro; conferir condições atuais do plano gratuito. |
| D. PaaS com plano gratuito (Render e similares) | Zero ou baixo | Datacenter | Costumam hibernar e ter Postgres gratuito temporário; conferir condições atuais. |
| E. VPS pequena paga | Poucos dólares por mês | Datacenter | Mais previsível. |
| F. Servidor do IFSP | Zero | Rede acadêmica | Depende de TI do campus. |

Decisão do dono (D19, Q12): A como plano principal da apresentação, e B (túnel) se for preciso um link para o orientador testar sozinho.
Antes de qualquer opção com IP de datacenter (C, D, E), rodar os testes `vivo` a partir do servidor candidato: o risco de bloqueio do TCU (e do WAF do Portal) só se resolve testando.
Se o TCU bloquear, a verificação fica INDISPONIVEL de forma honesta (INCONCLUSIVA), o que é aceitável para a demonstração mas não para uso real.
A decisão é sua porque envolve cadastro em serviços, cartão e quanto o projeto precisa estar "no ar".

---

# T15 - Git, versionamento da Fase 0 e CI

## T15a - Repositório

`git init` na raiz, branch `main`, commits pequenos por fatia (T18), mensagens em português.
Remoto no GitHub.
**[DECIDIDO Q13]** Repositório privado até a aprovação do projeto; público (MIT) depois de uma varredura de dados pessoais em `fase0/`.
Motivo: as respostas da Fase 0 incluem nomes do QSA (dado público da Receita, mas pessoal) e os downloads da CGU têm CPF completo, que nunca podem ir para o repositório; um erro de `.gitignore` num repositório público não tem volta.

## T15b - .gitignore e o que versionar da Fase 0

Ignorar: `.venv/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`, `.idea/`, `.env`, `var/`, `fase0/**/downloads/`, `fase0/brasilapi/respostas/falhas/` (centenas de arquivos que só provam instabilidade; o resumo está na ficha), `*.zip`, `*.xls`, `*.xlsx` fora das pastas de fixtures, e o PDF do spec se o `.md` for a fonte (a decidir junto com o spec).

Versionar: fichas, `proposta.md`, `decisoes.md`, spec, scripts da Fase 0 (documentam como cada fonte foi descoberta), respostas JSON pequenas que são exemplos oficiais, `portal-openapi.json`, `amostras/` (CPF mascarado), CSVs extraídos do DOU (pequenos) e `casos_referencia.json`.
Fixtures dos testes são cópias curadas dentro de `tests/fixtures/`, para que os testes não dependam de `fase0/`, que é material de descoberta e pode ser arquivado depois.
O `check-added-large-files` (T12d) impede que um download escape por engano.

## T15c - CI

GitHub Actions em todo push e pull request, Ubuntu, com `uv` e cache:

1. `ruff check` e `ruff format --check`.
2. `mypy --strict`.
3. `lint-imports` (import-linter).
4. `pytest -m "not vivo"` com serviço `postgres:17`, incluindo E2E em modo replay e Playwright.
5. Build da imagem Docker (sem publicar).

Workflow agendado separado (semanal, e manual) com `pytest -m vivo`: detecta mudança de contrato das fontes e responde de graça se o TCU bloqueia IP de datacenter (os runners do GitHub são datacenter).
Proteção da `main`: só entra com CI verde.

---

# T16 - Relatório PDF de auditoria **[DECIDIDO Q11]**

| Opção | Avaliação |
|---|---|
| A. Fora do MVP | Nada a fazer; o JSON e a página já contêm tudo. |
| B. Página de resultado com CSS de impressão (cabeçalho, data, hashes, aviso, quebra de página por seção); o usuário usa "Salvar como PDF" do navegador | Custo baixo, zero dependência, atende a demonstração; o PDF não é gerado nem assinado pelo servidor. |
| C. PDF no servidor com WeasyPrint | PDF idêntico para todos e arquivável com hash; no Windows depende de bibliotecas GTK/Pango (instalação chata), no contêiner é simples. |
| D. PDF no servidor com Playwright/Chromium | Fiel ao HTML; imagem Docker bem maior. |

Decisão do dono (D19, Q11): B no MVP, CSS de impressão sem PDF no servidor (sai junto com a página do T10); C depois, se o relatório precisar ser anexado a processos.
Um bônus barato para depois: anexar ao relatório o PDF oficial da certidão consolidada do TCU (`seEmitirPDF=true`), que já é um documento do próprio TCU.

---

# T17 - Riscos técnicos e mitigação

| # | Risco | Impacto | Mitigação |
|---|---|---|---|
| R1 | OpenCNPJ (comunitário, sem SLA) sai do ar ou muda o formato | Cadastro só pela BrasilAPI, que é instável e sem datasets | Fallback (T6c), CSV local de sanções (T5b), teste vivo semanal, dump no Postgres documentado para o pós-MVP (D17). |
| R2 | Descrição de natureza do OpenCNPJ fora do mapeamento | Natureza indefinida | D17: vira ALERTA; teste que percorre a tabela oficial; log de descrições desconhecidas. |
| R3 | TCU bloqueia IP de datacenter ou muda a API | Verificações 7, 8 e 9 indisponíveis | Teste vivo a partir do host antes do deploy (T14c); CEIS e CNEP também vêm de OpenCNPJ e CSV (T3d). |
| R4 | Semântica do `?datasets=` do OpenCNPJ não confirmada com caso positivo | CEPIM pode estar errado | Resolvido: os 49 casos têm `?datasets=` com registros e datas (spec 18A.3), e o CSV local é a observação principal (D14). |
| R5 | TCU lista CEIS ou CNEP `CONSTAM_REGISTROS` para sanção que as bases locais mostram como expirada | Falso INAPTA | D18: a vigência vem das datas; com todas as sanções expiradas é OK com histórico, e só depois se aplica D3. Registro só no TCU segue o Q35. |
| R6 | Link do SisCEBAS Saúde (tokens opacos, só HTTP) muda | CEBAS Saúde desatualizado | Sanidade na carga + idade máxima (T5d) + DOU como reserva; mensagem sempre com data da base. |
| R7 | DOU com defasagem de até 6 semanas; MDS e MEC só com retratos de 2023/2024 | CEBAS impreciso | Verificação informativa; mensagem cita fonte e data de corte (D16); INLABS (P5) depois. |
| R8 | Python 3.14 sem wheel de alguma dependência (psycopg binário, lxml) no Windows | Ambiente não sobe | Checar na fatia 0 antes de qualquer código; plano: driver `psycopg` com libpq do contêiner ou Python 3.13 só no contêiner. |
| R9 | Diferenças Windows (desenvolvimento) x Linux (CI e deploy): encoding latin-1 e cp1252 dos CSVs, caminhos, fim de linha | Bug só em um lado | Encoding sempre explícito no código; CI em Linux; testes de ingestão com os arquivos reais de amostra. |
| R10 | Agendador não roda e bases envelhecem | Resposta baseada em dado velho | Idade máxima vira INDISPONIVEL (T5d), visível em `/fontes`. |
| R11 | Casos de referência apodrecem (sanções vencem, entidades mudam) | Testes E2E quebram sem bug | Modo replay com `data_referencia` fixa; testes vivos aferem só estrutura. |
| R12 | Exposição de dados pessoais (QSA, CPF dos CSVs) numa demo pública | LGPD e credibilidade | QSA fora da resposta pública, evidências com token (T9e), CPF só no banco e nunca em log ou fixture. |
| R13 | Uso abusivo da demo pública leva ao bloqueio do projeto nas fontes | Fontes indisponíveis | Limite por IP (T9e), cache (T7). |
| R14 | Parser do DOU erra em formatos não vistos | Ato CEBAS errado | Testes com os 20 atos conferidos; CNPJ com DV inválido marcado; trecho do ato sempre exibido como evidência. |
| R15 | Escopo crescer antes da aprovação | MVP atrasa | Fatias verticais (T18) com ponto de demonstração em cada uma; itens pós-MVP explícitos. |

---

# T18 - Plano de implementação em fatias verticais

Cada fatia termina com: testes verdes no CI, E2E da API e da página passando nos casos da fatia, e uma demonstração manual na interface conferida com cuidado visual.
A ordem prioriza chegar cedo a uma consulta completa e demonstrável, e depois aumentar a cobertura de verificações.

| Fatia | Entrega | Verificações | Casos de referência que passam a valer |
|---|---|---|---|
| 0. Fundação | git, uv, `pyproject` completo, ruff, mypy, import-linter, pre-commit, CI, Compose com Postgres, configuração, logs, Alembic com migração inicial (`resposta_fonte`, `consulta`, `consulta_evidencia`), `/health`, esqueleto da página. Migração de `cnpj.py` e do classificador CNAE com seus testes. Checagem de wheels do Python 3.14 (R8). | `dv` | DV inválido, base repetida, alfanumérico (D4). |
| 1. Consulta cadastral ponta a ponta | Cliente HTTP comum, adapter e normalizador OpenCNPJ, `natureza_juridica.json`, motor com agregação, orquestrador, cache e evidência, `POST/GET /consultas`, página de formulário e resultado. | `situacao`, `natureza`, `cnae`, `religiosa`, `tempo` | OKBR, Banco do Brasil, associação baixada (T4), associação recente (E1), religiosa (E2), cooperativa (E3), inexistente (T3). |
| 2. Resiliência e filial | Fallback BrasilAPI e normalizador; retry, timeouts, prazo global; INDISPONIVEL; filial (D5) e esfera (D6) completos; `/fontes` (parte online). | `estabelecimento` + regras de filial | Filial ativa (T7), filial baixada com matriz ativa (T7b), cenários de pane simulados. |
| 3. TCU e sanções (um marco só) | Adapter e normalizador da Consulta Consolidada (D13, Q33, Q35); infraestrutura de carga (`carga`, CLI `ingerir`, `atualizar-bases`, idade máxima, sanidade B19); ingestão dos CSVs CEPIM, CEIS, CNEP (principal, D14) e das listas do TCU (inidôneos, contas irregulares); datasets do OpenCNPJ; combinação T3d com busca por raiz [ORIENTADOR Q20]. | `tcu_inidoneos`, `cnj_cnia`, `tcu_contas_irregulares`, `cepim`, `ceis`, `cnep` | C28 a C46 e C49 de `casos_referencia.json`: CEPIM, CEIS vigente, expirado e fronteira 22/11/2026, CNEP de multa, CNIA, Instituto Global e IDEAS (raiz), entidades INAPTAS com sanções (Q1). |
| 4. Mapa das OSCs | Adapter com as 5 seções do Q38, regra de perfil preenchido, D2, `situacao` (Q40). | `mapa_osc` | OKBR (só automático), Abrinq (preenchido), cooperativa e filial ausentes (C14, C24). |
| 5. Dirigentes | Casamento nome + 6 dígitos centrais do CPF contra pessoas físicas do CEIS/CNEP locais (D15) [ORIENTADOR Q22]; exibição dos nomes só para o operador (Q9). Fontes extras conforme Q8 [PENDENTE Q8]. | `dirigentes` | C36 e C39 (correspondência), os QSA dos demais casos (sem correspondência) e os casos do teste ponta a ponta de `fase0/dirigentes/ficha.md` se Q8 aceitar. |
| 6. CEBAS | Ingestão SisCEBAS Saúde, planilhas MDS/MEC, DOU desde 12/2023 (Q39) e mensal, parser migrado com vigência como data e novos tipos de ato (Q43); regra de status pura (D16) com `situacao` (Q40) e bloco "Sobre o CEBAS" (B7). | `cebas` | C16, C23, C25, C26, C27, C47, C48 (gerar de novo depois da carga do DOU, [PENDENTE X17]). |
| 7. Mensagens e relatório | Catálogo `mensagens.json` (B1) com teste de cobertura, blocos fixos (B8, B9), ordem de exibição (B16), rodapé de atribuição (B18), relatório de filial (B20). | todas | Conjunto completo, conferido na página. |
| 8. Pronto para apresentar | CSS de impressão (T16 B), página `/fontes` completa, limite por IP e token de evidências (T9e), workflow `vivo` agendado, deploy conforme T14c, roteiro de demonstração. | todas | Conjunto completo de `casos_referencia.json`. |

Depois da fatia 3 todas as eliminatórias estão cobertas e já existe um MVP demonstrável; a ingestão dos CSVs da CGU entra junto com o TCU porque o CSV é a observação principal (D14).
As fatias 4 a 7 são informativas, de alerta ou de texto e podem ser reordenadas conforme o que a banca valorizar; a 5 depende do Q8 só para as fontes extras, e a 6 depende da carga do DOU.

---

# Tabela-resumo das decisões

| # | Tema | Recomendação | Selo |
|---|---|---|---|
| T1 | Componentes | Monólito modular: FastAPI + CLI de ingestão no mesmo pacote + Postgres; sem Redis, sem fila. | |
| T2 | Estrutura | `dominio`, `regras` (puro), `fontes`, `bases_locais`, `persistencia`, `servico`, `api`; fronteiras verificadas por import-linter. | |
| T3a | Verificações | Funções puras registradas com metadados; tabelas de regra em JSON validado. | |
| T3b | Catálogo | 15 verificações com id textual estável e número do spec como atributo (Q25); verificação 9 dividida em TCU e CNIA; `religiosa` e `estabelecimento` próprias; `tcu_contas_irregulares` provisória [ORIENTADOR Q21]. | |
| T3c | Agregação | CNPJ_INVALIDO (Q3), INAPTA, INCONCLUSIVA (eliminatória INDISPONIVEL ou NAO_VERIFICADO, Q2), APTA COM RESSALVAS, APTA; `motivos` e `avisos` no resultado. | |
| T3c' | Verificação não eliminatória indisponível | Não muda o status; aviso explícito em destaque (`avisos`). | [DECIDIDO Q5] |
| T3d | Várias fontes | Vigência pelas datas primeiro (D18), divergência depois (D3); registro só no TCU pelo Q35; OK se ao menos uma respondeu; INDISPONIVEL se nenhuma. | |
| T3e | Filial | D5 com matriz consultada em paralelo; filial inativa com matriz ativa = ALERTA em `estabelecimento`; matriz pela `matriz_filial` (Q27); matriz sem resposta = INDISPONIVEL (Q44); Mapa e CEBAS pelo Q28; sanções da raiz [ORIENTADOR Q20]. | [DECIDIDO Q4] |
| T3f | Esfera | D6, sempre com os três cenários nos achados; anos completos (Q29). | |
| T3g | D13 | CNPJ não encontrado = `situacao` INDISPONIVEL (NAO_ENCONTRADO), sem fan-out (Q26); OK do TCU com o cadastro confirmado (Q33). | |
| T3h | Curto-circuito | Sem parada antecipada: com DV válido e cadastro encontrado, tudo é avaliado; sem `precisa_fanout`. | [DECIDIDO Q1] |
| T3i | Data de referência | Injetada no motor, gravada na consulta; replay possível; datas em Brasília (B3) e formatos (B2). | |
| T4 | Contrato e modelo | Adapter devolve `Coleta[T]` (fatos ou falha tipada), não estado (Q41); domínio em dataclasses, pydantic nas bordas. | |
| T5a | Online x local | Cadastro, TCU e Mapa online; CGU, listas do TCU, CEBAS e DOU locais; regras, mensagens e limites no repositório; API do Portal fora do motor. | |
| T5b | CEPIM, CEIS, CNEP | CSV local como observação principal desde a primeira fatia de sanções (D14); OpenCNPJ datasets e TCU como observações adicionais. | |
| T5c | Ingestão | Comando idempotente, arquivo endereçado por sha256, carga com troca atômica, histórico e sanidade por fonte (B19). | |
| T5d | Agendamento | Manual no desenvolvimento; agendador externo chamando `atualizar-bases` no deploy; idade máxima por base e limite do espelho. | [DECIDIDO Q6] |
| T6 | Resiliência | Timeouts por fonte, prazo global de 45 s com orçamento por fase (B10), retry só se couber, fallback OpenCNPJ para BrasilAPI também no 404, sem circuit breaker, limite por host (Q37), coalescência de chamadas iguais (B15). | |
| T7 | Cache e evidências | Tabela única `resposta_fonte` (bytes exatos em `bytea` + sha256); TTL do spec 24.4 v1.2 (Q36); arquivos de carga em disco por hash. | |
| T8 | Banco | Postgres 17, SQLAlchemy 2 + psycopg 3 (async na API, sync na CLI), Alembic, esquema do T8c com listas do TCU, política de CPF (B13) e versão das regras (B11). | |
| T9 | API | `POST /api/v1/consultas` síncrono (201) com idempotência (B4), `GET` por id com nomes de dirigentes só para operador (Q9), `/fontes`, `/evidencias` restrito; problem+json; DV inválido é resultado CNPJ_INVALIDO, não erro. | |
| T10 | Interface | HTML + CSS + JavaScript simples servidos pelo app (Jinja2), sem framework de frontend e sem build. | [DECIDIDO Q10] |
| T11 | Configuração e logs | pydantic-settings + `.env`; structlog (console e JSON); sem APM no MVP. | |
| T12 | Ambiente e qualidade | uv, Python 3.14, ruff, mypy strict, import-linter, pre-commit com bloqueio de arquivos grandes. | |
| T13 | Testes | Motor puro, normalizadores com fixtures reais, MockTransport, Postgres real, E2E em modo replay (API e navegador), testes vivos fora do CI padrão. | |
| T14a | Execução local | Postgres no Compose, app nativo com uv; perfil completo para paridade. | |
| T14c | Onde demonstrar | Local na apresentação; túnel se precisar de link; testar IP antes de qualquer nuvem. | [DECIDIDO Q12] |
| T15a | Repositório | GitHub privado até a aprovação; público com MIT depois da varredura de dados pessoais. | [DECIDIDO Q13] |
| T15b | Fase 0 no git | Fichas, scripts, exemplos pequenos e amostras mascaradas; downloads e falhas fora. | |
| T15c | CI | GitHub Actions (lint, tipos, imports, testes com Postgres, build) + workflow vivo semanal. | |
| T16 | PDF | CSS de impressão no MVP; PDF no servidor depois. | [DECIDIDO Q11] |
| T17 | Riscos | 15 riscos com mitigação; R4 resolvido e R5 reescrito pelo D18. | |
| T18 | Plano | 9 fatias verticais (0 a 8), com TCU e sanções da CGU no mesmo marco (fatia 3); eliminatórias completas e MVP demonstrável após a fatia 3. | |

# Decisões do dono (antes [DECIDIR], respondidas em D19)

1. **T10 - Interface do MVP (Q10):** HTML + CSS + JavaScript simples servidos pelo app, sem framework de frontend.
2. **T16 - PDF de auditoria (Q11):** CSS de impressão; sem PDF no servidor no MVP.
3. **T14c - Onde demonstrar (Q12):** local na apresentação; túnel público se necessário.
4. **T15a - Repositório (Q13):** privado até a aprovação do projeto.
5. **T5d - Idade máxima das bases locais (Q6):** CEIS e CNEP 3 dias, CEPIM e SisCEBAS 7, DOU 75, espelho cadastral com mais de 60 dias = ALERTA.
6. **T3h - Entidade já INAPTA pelo cadastro (Q1):** consultar e mostrar as sanções mesmo assim; o status segue INAPTA.
7. **T3c' - Verificação não eliminatória indisponível (Q5):** não muda o status, com aviso explícito em destaque.
8. **T3e - Filial inativa com matriz ativa (Q4):** ALERTA.

Também respondidas em D19: Q2 (alfanumérico = INCONCLUSIVA), Q3 (CNPJ_INVALIDO), Q7 (D18 aprovado) e Q9 (link aberto, nomes de dirigentes só para operador).

Ainda em aberto, sem bloquear o início:

- [PENDENTE Q8] Ampliação das fontes de dirigentes (antes da fatia 5 só para as fontes extras).
- [ORIENTADOR Q14 a Q24] Regras de interpretação da lei; até a resposta valem as recomendações da revisão como parâmetros de `dados/regras_orientador.json`, `natureza_juridica.json` e `regras_cnae.json`, sem mudar código.
- [PENDENTE X17] Carga do DOU desde 12/2023 (antes de fechar os casos da fatia 6).
>>>>

