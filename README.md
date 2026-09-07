# To-Do App (Django)

The application half of the ECS Fargate + RDS Proxy + ElastiCache lab. Infrastructure lives in a
separate repo: **md6-infra-repo**.

## Layout

`config/` (settings/urls/wsgi/asgi) stays at the repo root as the outer management layer; the actual
application code lives under `src/todos/` (models, views, forms, templates, tests). `manage.py` puts
`src/` on `sys.path` itself; the Docker image sets `PYTHONPATH=/app/src` so gunicorn can import
`config.wsgi` directly.

Managed with **uv** (`pyproject.toml` + `uv.lock`), not pip/`requirements.txt`.

## What it does

A single-page to-do list: create, view, toggle done/undone, edit, and delete tasks.
- **Writes** go through the Django ORM to PostgreSQL — in ECS, `POSTGRES_HOST` is always the **RDS
  Proxy** endpoint, never the raw RDS instance.
- **Reads** (the task list) go through Redis first (`django-redis`); every write invalidates the cache
  key immediately, so the list page visibly shows whether it was served `from Redis cache` or
  `from database`.
- `GET /health/` is a bare `200 {"status": "ok"}` with no DB/cache dependency — what the ALB target
  groups check.

## Local development

```bash
cp .env.example .env
uv sync --group dev
docker compose up          # Postgres + Redis + this app, migrations run on startup (RUN_MIGRATIONS_ON_STARTUP=true)
```

Or without Docker, against your own Postgres/Redis (or none — falls back to LocMemCache if `REDIS_HOST`
is unset):

```bash
uv run manage.py migrate
uv run manage.py runserver
```

## Tests / lint

```bash
uv sync --group dev
uv run flake8 .
DJANGO_TESTING=true DJANGO_SECRET_KEY=ci uv run manage.py collectstatic --noinput
DJANGO_TESTING=true DJANGO_SECRET_KEY=ci uv run pytest -v
```

`DJANGO_TESTING=true` swaps the database to sqlite in-memory and the cache to LocMemCache, so none of
this needs a live Postgres/Redis.

## Why migrations aren't run in the container's entrypoint by default

`docker-entrypoint.sh` only runs `manage.py migrate` when `RUN_MIGRATIONS_ON_STARTUP=true` (set for local
`docker-compose` convenience). In ECS this is left unset (false): under blue/green, the old and new task
sets briefly run concurrently, so migrating at container startup risks running migrations twice at once
and makes rollback messier. Instead, the infra repo's CodePipeline has a dedicated CodeBuild "Migrate"
stage that runs `manage.py migrate` once, as a one-off Fargate task, before CodeDeploy ever shifts
traffic to the new task set.

## CI/CD

`.github/workflows/build-and-push.yml`:
1. `test` job — `uv sync --group dev`, `flake8`, `pytest` (against sqlite, no live AWS needed).
2. `build-and-push` job (gated on `test` passing) — assumes an IAM role via GitHub OIDC (no long-lived
   credentials), looks up live values from **md6-infra-repo**'s deployed root stack
   (`aws cloudformation describe-stacks --stack-name md6-todo-dev-root`), renders `ecs/taskdef.json`
   from `ecs/taskdef.template.json`, commits the rendered file, then builds and pushes the image tagged
   **only** `sha-<git sha>` — no `latest`. The ECR repository is `ImageTagMutability: IMMUTABLE`; the
   infra's EventBridge rule fires on *any* successful push (no tag filter) and pins the deployment
   pipeline to the exact digest just pushed. See `md6-infra-repo`'s `templates/stacks/05-ecr.yaml` and
   `09-cicd-pipeline.yaml` for the full rationale.

`AWS_ROLE_ARN` must be set as a repository secret once the infra repo's stacks are deployed (value = the
root stack's `GitHubActionsRoleArn` output) — it can't be hardcoded yet since no AWS account is attached
to this lab yet.

`ecs/taskdef.json` in this repo right now is a **placeholder** (`PENDING_FIRST_CI_RENDER` values) — the
first successful `build-and-push` run overwrites it with real values read from the deployed infra.
