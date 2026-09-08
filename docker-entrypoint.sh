#!/bin/sh
set -e

# Migrations run only when explicitly enabled; ECS uses the pipeline's
# Migrate stage instead.
if [ "${RUN_MIGRATIONS_ON_STARTUP:-false}" = "true" ]; then
  echo "Running database migrations..."
  python manage.py migrate --noinput
fi

exec "$@"
