# Validador de OSC

Triagem automatizada de CNPJ para parcerias conforme o Marco Regulatório das Organizações da Sociedade Civil (Lei 13.019/2014).
O sistema consulta cadastros públicos e devolve um status (apta, apta com ressalvas, inconclusiva ou inapta), com a explicação de cada verificação e a fonte de cada dado.
É uma triagem: não substitui as certidões oficiais.

## O que é verificado

| Verificação | Fonte |
|---|---|
| Dígito verificador, situação cadastral, natureza jurídica, CNAE, organização religiosa, tempo de existência, filial e matriz | Receita Federal, via OpenCNPJ (reserva: BrasilAPI) |
| CEPIM, CEIS, CNEP | Arquivos diários oficiais da CGU, baixados para o banco |
| Licitantes inidôneos e improbidade (CNJ) | Consulta Consolidada do TCU e relação de inidôneos |
| Contas julgadas irregulares da própria OSC | TCU |
| Dirigentes do quadro de sócios | CEIS, CNEP, TCU (contas irregulares e inabilitados) e TCE-SP |
| Presença e perfil no Mapa das OSCs | Ipea |

As regras e decisões estão em `validador_osc_especificacao_mvp.md`, `arquitetura.md` e `decisoes.md`.

## Como rodar

Pré-requisitos: [uv](https://docs.astral.sh/uv/) e Docker Desktop aberto.

```
uv sync
docker compose up -d --wait db
uv run alembic upgrade head
uv run validador-osc atualizar-bases
uv run validador-osc servir
```

A aplicação fica em http://127.0.0.1:8000.
O banco local usa a porta 15432, fora das faixas que o Windows costuma reservar.
No Windows, não use `--recarregar` com o log redirecionado: o recarregamento automático trava nesse cenário.

## Bases locais

`validador-osc atualizar-bases` baixa as bases oficiais (CGU, TCU e TCE-SP), confere a integridade e troca a versão ativa de uma vez só.
Cada base tem idade máxima (em `validador_osc/dados/limites.json`); depois dela, a verificação fica indisponível e o resultado vira inconclusivo, nunca aprovado.
O estado de cada base aparece em http://127.0.0.1:8000/fontes.

Para agendar a atualização diária no Windows (executar uma vez, no PowerShell):

```
.\scripts\agendar_atualizacao.ps1 -Horario 06:00
```

Em Linux, use o cron com `uv run --no-sync validador-osc atualizar-bases`.

## Configuração

Variáveis com prefixo `VOSC_`, documentadas em `.env.example`.
`VOSC_TOKEN_OPERADOR` libera, no header `X-Token-Operador`, os nomes de dirigentes com possível correspondência e as evidências brutas em `/api/v1/evidencias/{id}`.
`VOSC_LIMITE_CONSULTAS_POR_MINUTO` limita consultas por endereço IP (0 desliga).

## API

Documentação interativa em http://127.0.0.1:8000/docs.

- `POST /api/v1/consultas` com `{"cnpj": "...", "esfera": "municipio|estado|uniao", "atualizar": false}`.
- `GET /api/v1/consultas/{id}`: resultado gravado (link permanente).
- `GET /api/v1/fontes`: estado das fontes online e das bases locais.

## Qualidade

```
uv run ruff check
uv run ruff format --check
uv run mypy
uv run lint-imports
uv run pytest
```

Os testes de integração e de ponta a ponta usam o banco `validador_teste`, criado automaticamente, e respostas gravadas das fontes (sem rede).

## Demonstração

Roteiro em `docs/roteiro_demonstracao.md`.
