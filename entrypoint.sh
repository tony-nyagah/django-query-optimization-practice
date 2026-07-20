#!/bin/sh
set -e

uv run manage.py migrate --noinput
uv run manage.py seed_all

exec uv run -- gunicorn core.wsgi:application --bind 0.0.0.0:1759 --workers 2 --timeout 120 --capture-output --log-level debug
