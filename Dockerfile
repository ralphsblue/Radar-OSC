FROM python:3.14-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

COPY validador_osc ./validador_osc
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --locked --no-dev

RUN useradd --system --uid 10001 validador && mkdir -p /app/var && chown validador /app/var
USER validador
ENV PATH="/app/.venv/bin:$PATH" VOSC_LOG_FORMATO=json
EXPOSE 8000
CMD ["validador-osc", "servir", "--host", "0.0.0.0", "--porta", "8000"]
