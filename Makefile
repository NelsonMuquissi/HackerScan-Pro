.PHONY: dev dev-local test migrate makemigrations shell logs clean install build

# ─── Run full stack in Docker (API + DB + Redis + RabbitMQ + MinIO) ─────────
dev:
	docker-compose up --build

dev-detach:
	docker-compose up --build -d

# ─── Run Django runserver locally (requires DB + Redis already up) ──────────
dev-local:
	docker-compose up -d db redis
	cd apps/api && \
	  DJANGO_SETTINGS_MODULE=config.settings.development \
	  python manage.py runserver

# ─── Database migrations ─────────────────────────────────────────────────────
migrate:
	docker-compose run --rm api python manage.py migrate

makemigrations:
	docker-compose run --rm api python manage.py makemigrations

makemigrations-local:
	cd apps/api && python manage.py makemigrations

migrate-local:
	cd apps/api && python manage.py migrate

# ─── Tests ───────────────────────────────────────────────────────────────────
test:
	docker-compose run --rm api pytest

test-local:
	cd apps/api && pytest

# ─── Django shell ────────────────────────────────────────────────────────────
shell:
	docker-compose run --rm api python manage.py shell

# ─── Logs ────────────────────────────────────────────────────────────────────
logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

# ─── Build image only ────────────────────────────────────────────────────────
build:
	docker-compose build api

# ─── Install local dependencies ──────────────────────────────────────────────
install:
	pip install -r requirements/dev.txt
	npm install

# ─── Cleanup ─────────────────────────────────────────────────────────────────
clean:
	docker-compose down -v
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

