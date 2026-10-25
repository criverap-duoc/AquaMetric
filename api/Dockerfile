# syntax=docker/dockerfile:1

# --- Builder: resolve the lockfile with uv and install runtime dependencies only -----------
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

# Dependencies first, so the layer is reused while pyproject.toml and uv.lock stay unchanged.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# --- Runtime: no uv, no compilers, no dev dependencies ------------------------------------
FROM python:3.13-slim AS runtime

# curl serves the HEALTHCHECK below; nothing else is installed in the final image.
RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/app ./app
COPY --from=builder /app/alembic ./alembic
COPY --from=builder /app/alembic.ini ./

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Never root: the process only needs to read the code and talk to Postgres.
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
