#!/bin/sh
set -e

# Migrations are NOT run unconditionally here: under ECS blue/green, old and
# new task sets briefly run concurrently, so migrating at container startup
# risks running migrate twice at once and complicates rollback. In ECS this
# stays unset/false - the infra's CodeBuild "Migrate" pipeline stage runs
# migrations once, before CodeDeploy ever shifts traffic. Set to "true" only
# for local docker-compose convenience.
if [ "${RUN_MIGRATIONS_ON_STARTUP:-false}" = "true" ]; then
  echo "Running database migrations..."
  python manage.py migrate --noinput
fi

exec "$@"
