.PHONY: help setup dev dev-local server worker test lint lint-fix check migrate migrations shell clean

help:
	@echo "Loop Your Lesson"
	@echo ""
	@echo "Quick start:"
	@echo "  make setup     First time setup"
	@echo "  make dev       Start everything (Docker Temporal)"
	@echo "  make dev-local Start everything (Temporal CLI, no Docker)"
	@echo ""
	@echo "Development:"
	@echo "  make server    Django dev server only"
	@echo "  make worker    Temporal worker only"
	@echo "  make check     Django system check + import validation"
	@echo ""
	@echo "Database:"
	@echo "  make migrate     Run migrations"
	@echo "  make migrations  Create new migrations"
	@echo "  make shell       Django shell"
	@echo ""
	@echo "Quality:"
	@echo "  make test      Run backend tests"
	@echo "  make lint      Check linting (ruff + eslint + tsc)"
	@echo "  make lint-fix  Auto-fix linting issues"
	@echo ""
	@echo "Other:"
	@echo "  make clean     Stop containers, remove volumes"

# --- Setup ---

setup:
	cd backend && uv sync --dev
	cd frontend && bun install
	docker compose up -d redis
	@echo "Waiting for services..."
	@sleep 2
	cd backend && uv run python manage.py migrate
	@echo ""
	@echo "Setup complete! Run 'make dev' to start."
	@echo "Visit http://localhost:$${BACKEND_PORT:-8006} for the app."

# --- Development ---

dev:
	./bin/start

dev-local:
	./bin/start --local

server:
	cd backend && uv run python manage.py runserver 0.0.0.0:$${BACKEND_PORT:-8006}

worker:
	cd backend && uv run python manage.py run_temporal_worker

check:
	cd backend && uv run python manage.py check
	@cd backend && uv run python -c "\
	import os, django; \
	os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'; \
	django.setup(); \
	from apps.lessons import services; \
	from apps.skill_results import services; \
	from apps.daily_briefings import services; \
	from apps.classtime_sessions.services import client, auth, questions, sessions, results; \
	from apps.conversations.services import agent, tools, modes, context; \
	from apps.conversations.services.query_tools import query_lesson_errors; \
	from services import pipeline, exceptions; \
	from stream import events, sse; \
	print('All imports OK')"

# --- Database ---

migrate:
	cd backend && uv run python manage.py migrate

migrations:
	cd backend && uv run python manage.py makemigrations

shell:
	cd backend && uv run python manage.py shell

# --- Quality ---

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check .
	cd backend && uv run ruff format --check .
	cd frontend && bun run lint
	cd frontend && bun run tsc --noEmit

lint-fix:
	cd backend && uv run ruff check --fix .
	cd backend && uv run ruff format .

# --- Cleanup ---

clean:
	docker compose down -v
	@echo "Cleaned up Docker volumes."
