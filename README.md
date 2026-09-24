# To-Do App (Django)

The application half of the ECS Fargate + RDS Proxy + ElastiCache lab. Infrastructure lives in two
separate repos: **md6-bootstrap-repo** (S3 bucket, GitHub OIDC roles, ECR) and **md6-infra-repo** (the
actual application infra).

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
  groups **and** the ECS task definition's own container-level `healthCheck` both check (see
  `ecs/taskdef.json`; without it, Fargate always reports task health as `UNKNOWN` in the console,
  regardless of the Dockerfile's own `HEALTHCHECK`).

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

Local-only — `build-and-push.yml` doesn't run these (see "CI/CD" below):

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

`.github/workflows/build-and-push.yml` has a single job, `build-and-push` — no test/lint step, and no
lookup of any live infra value:
1. Assume an IAM role via GitHub OIDC (no long-lived credentials), log in to ECR, **build** the image
   (not pushed yet).
2. **Upload the deploy template**: zip `ecs/taskdef.json` + `ecs/appspec.yaml` (flat, no `ecs/` prefix
   inside the zip) and `aws s3 cp` it to the infra repo's pipeline artifact bucket at
   `source/appspec-taskdef.zip`. Done *before* the image push, deliberately — CodePipeline's S3 source
   action reads this object, and the object must already be in place by the time the push below fires
   the EventBridge rule that starts the pipeline.
3. **Push** the image tagged **only** `sha-<git sha>` — no `latest`. The ECR repository is
   `ImageTagMutability: IMMUTABLE`; the infra's EventBridge rule fires on *any* successful push (no tag
   filter) and pins the deployment pipeline to the exact digest just pushed.

CodePipeline never talks to GitHub directly — no CodeConnections handshake needed for this repo. See
`md6-infra-repo`'s `09-cicd-pipeline.yaml` for the full rationale.

Only the one value that's actually sensitive (the role ARN CI assumes) is a **secret**; everything else
the workflow needs is a plain **repository variable** (Settings → Secrets and variables → Actions,
*Variables* tab, not *Secrets*) — set once the other two repos are deployed:
- Secret: `AWS_ROLE_ARN` ← `md6-bootstrap-repo`'s `GitHubActionsRoleArn` output.
- Variables: `AWS_REGION` (`us-east-1`), `ECR_REPOSITORY` (`md6-todo-dev-app`, from
  `md6-bootstrap-repo`'s `EcrRepositoryName` output), `ARTIFACT_BUCKET` ← `md6-infra-repo`'s root stack
  `PipelineArtifactBucketName` output, `ARTIFACT_KEY` (`source/appspec-taskdef.zip`, must match the S3
  key `09-cicd-pipeline.yaml`'s `TaskDefTemplateSource` action reads).

`ecs/taskdef.json` is committed as a **static, final file** — not rendered by CI. Every value that can
change independently of a code change (DB proxy endpoint, Redis endpoint, DB credentials, Django
`SECRET_KEY`) is a `secrets[].valueFrom` reference to a fixed-name SSM parameter or Secrets Manager
secret (published by `md6-infra-repo`'s `03-database.yaml`/`04-cache.yaml`), referenced without the
Secrets Manager random suffix so it never needs updating when a secret rotates. Only the account ID
and role names would need editing by hand if this were redeployed into a different AWS account.
