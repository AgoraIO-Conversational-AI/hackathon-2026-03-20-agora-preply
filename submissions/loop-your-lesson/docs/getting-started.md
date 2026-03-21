# Getting started

Local setup for Loop Your Lesson. From zero to running in 5 minutes.

For architecture context, see [architecture.md](architecture.md).
For the AI chat system, see [conversational-ux.md](conversational-ux.md).

## Prerequisites

Install these four tools:

```bash
brew install uv bun mprocs
# Docker Desktop must be installed and running
```

| Tool | Purpose |
|------|---------|
| [uv](https://docs.astral.sh/uv/) | Python package manager, virtual environments |
| [bun](https://bun.sh/) | Frontend package manager and runtime |
| [mprocs](https://github.com/pvolok/mprocs) | Runs all services in a single terminal |
| [Docker](https://www.docker.com/products/docker-desktop/) | Redis, Temporal, PostgreSQL containers |

Optional: `brew install temporal` if you want the faster local Temporal CLI mode.

## Quick start

```bash
git clone git@github.com:vasyl-stanislavchuk/prepy-loop-your-lesson.git
cd prepy-loop-your-lesson
make setup    # install deps, start Redis, run migrations
make dev      # start everything
```

Open http://localhost:3006 (frontend) or http://localhost:8006 (backend API).

`make dev` launches a mprocs dashboard showing all processes. Press `q` to quit.

## Two dev modes

### Docker Temporal (default)

```bash
make dev
```

Runs Redis + Temporal + Temporal UI in Docker, plus backend, worker, and frontend natively. Good for most setups.

### Temporal CLI (faster on Apple Silicon)

```bash
brew install temporal   # one-time
make dev-local
```

Runs Temporal server natively via CLI instead of Docker. Faster startup, less memory. Redis still runs in Docker.

Both modes use [mprocs](https://github.com/pvolok/mprocs) to orchestrate processes. Config files are `bin/mprocs.yaml` (Docker) and `bin/mprocs-local.yaml` (CLI).

## Database setup

You have two options for PostgreSQL. Pick one.

### Option A: Docker PostgreSQL (default)

No extra setup needed. `docker-compose.yml` starts Postgres 16 on port 5432 and creates the `loop_dev` database automatically.

```bash
# .env (already configured for Docker)
DATABASE_URL=postgres://dev:pass@localhost:5432/loop_dev
```

If you previously used Postgres.app and want to switch to Docker, remove the override file:

```bash
rm docker-compose.override.yml
```

### Option B: Postgres.app (macOS)

If you prefer [Postgres.app](https://postgresapp.com/) over Docker for Postgres:

1. Install and start Postgres.app
2. Create the database:

```bash
createdb loop_dev
```

3. Update `.env` to use the Unix socket connection:

```bash
DATABASE_URL=postgres:///loop_dev
```

The repo ships with `docker-compose.override.yml` that disables Docker Postgres and points Temporal to your host database. Keep this file if using Postgres.app.

### After either option

Run migrations to create tables:

```bash
make migrate
```

Seed demo data (teacher, students, lessons):

```bash
cd backend && uv run python manage.py seed_demo
```

## Ports

All configurable via environment variables. Defaults:

| Service | Port | Override |
|---------|------|----------|
| Backend (Django) | 8006 | `BACKEND_PORT` |
| Frontend (Vite) | 3006 | `FRONTEND_PORT` |
| Temporal server | 7235 | `TEMPORAL_PORT` |
| Temporal UI | 8089 | `TEMPORAL_UI_PORT` |
| Redis | 6381 | via `REDIS_URL` |
| PostgreSQL | 5432 | via `DATABASE_URL` |

## Makefile commands

| Command | What it does |
|---------|-------------|
| `make setup` | First-time setup: sync deps, start Redis, migrate |
| `make dev` | Start all services (Docker Temporal) |
| `make dev-local` | Start all services (Temporal CLI) |
| `make server` | Django dev server only |
| `make worker` | Temporal worker only |
| `make check` | Django system check + import validation |
| `make migrate` | Run database migrations |
| `make migrations` | Create new migration files |
| `make shell` | Django interactive shell |
| `make test` | Run backend tests (pytest) |
| `make lint` | Check linting (ruff + eslint + tsc) |
| `make lint-fix` | Auto-fix linting issues |
| `make clean` | Stop containers, remove Docker volumes |

## Environment variables

The `.env` file is pre-configured for local development. Key variables:

| Variable | Notes |
|----------|-------|
| `DATABASE_URL` | Postgres connection string |
| `REDIS_URL` | Redis connection (port 6381 locally) |
| `ANTHROPIC_API_KEY` | Required for AI chat |
| `CLASSTIME_ADMIN_TOKEN` | Classtime API access |
| `CLASSTIME_ORG_ID` | Preply org on Classtime |
| `CLASSTIME_SCHOOL_ID` | School ID for practice sessions |
| `TEMPORAL_HOST` | `localhost` for local dev |
| `TEMPORAL_PORT` | `7235` for local dev |

API keys are pre-filled for hackathon development. Rotate before any production use.

## Project structure

```
backend/                 Django REST Framework
  apps/                  8 Django apps (accounts, lessons, conversations, ...)
  config/                Settings, URLs, views
  services/              Cross-app services (pipeline, Temporal client)
  stream/                Redis SSE streaming (events, writer, SSE conversion)
  workflows/             Temporal workflow definitions
  templates/             SPA template (spa.html)
frontend/                React + Vite + TypeScript + Tailwind
  src/pages/             Landing, Chat, Lessons, Students pages
  src/components/        UI components, chat widgets, layout
  src/api/               API hooks, SSE streaming client
  src/lib/               Modes, types, utilities
docs/                    Architecture, skills, conversational UX
terraform/               AWS infrastructure (ECS, RDS, Redis, ALB)
scripts/                 deploy.sh, setup-ssm.sh
bin/                     mprocs configs, start script
```

## Deployment

The app runs on AWS ECS Fargate at https://loopyourlesson.com/.

```bash
# Infrastructure (one-time)
cd terraform
terraform workspace select dev
terraform apply

# Deploy code
./scripts/deploy.sh      # build Docker image, push to ECR, redeploy ECS

# Seed demo data
aws ecs run-task \
  --cluster preply-loop-dev-cluster \
  --task-definition preply-loop-dev-backend \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<subnet>],securityGroups=[<sg>],assignPublicIp=ENABLED}" \
  --overrides '{"containerOverrides":[{"name":"preply-backend","command":["uv","run","python","manage.py","seed_demo"]}]}' \
  --region us-east-1
```

SSM parameters store secrets (API keys, DB credentials). See `scripts/setup-ssm.sh`.

## Troubleshooting

**Port already in use**
```bash
lsof -i :8006    # find what's using the port
kill -9 <pid>
```

**Database doesn't exist**
```bash
make migrate                  # Docker Postgres
createdb loop_dev && make migrate   # Postgres.app
```

**Python deps out of sync**

The `bin/start` script auto-syncs if `.venv` is missing or `uv.lock` is newer than `.venv`. To force:
```bash
cd backend && uv sync --dev
```

**Frontend can't reach backend**

Both servers must be running. The Vite config proxies API requests to `localhost:8006`.

**Temporal worker won't start**

The worker waits for Temporal to be healthy before starting. Check Temporal is running:
```bash
nc -z localhost 7235 && echo "Temporal up" || echo "Temporal down"
```

**Docker Postgres conflicts with Postgres.app**

Both use port 5432. Either remove `docker-compose.override.yml` (use Docker) or keep it (use Postgres.app). Don't run both.
