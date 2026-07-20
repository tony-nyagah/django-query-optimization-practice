FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/venv

WORKDIR /app

# Install uv and PostgreSQL client
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into /venv
RUN uv sync --frozen --no-dev

# Copy project
COPY . .

# Collect static files
RUN uv run manage.py collectstatic --noinput

# Ensure SQLite data directory exists
RUN mkdir -p /app/data

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 1759

ENTRYPOINT ["/app/entrypoint.sh"]
