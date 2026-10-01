# Validador de OSC

Triagem automatizada de CNPJ para parcerias conforme o Marco Regulatório das Organizações da Sociedade Civil (Lei 13.019/2014).

## Documentos

- `validador_osc_especificacao_mvp.md`: especificação funcional.
- `arquitetura.md`: decisões técnicas.
- `decisoes.md`: registro de decisões e pendências.
- `fase0/`: descoberta e testes das fontes de dados.

## Desenvolvimento

Pré-requisitos: [uv](https://docs.astral.sh/uv/) e Docker.

```
uv sync
uv run pre-commit install
docker compose up -d db
uv run alembic upgrade head
uv run validador-osc servir
```

Qualidade:

```
uv run ruff check
uv run ruff format --check
uv run mypy
uv run lint-imports
uv run pytest
```
