FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/venv

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into /venv
RUN uv sync --frozen --no-dev

# Copy project
COPY . .

# Collect static files
RUN uv run manage.py collectstatic --noinput

EXPOSE 1759

CMD ["uv", "run", "--", "gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:1759", "--workers", "2", "--timeout", "120"]
