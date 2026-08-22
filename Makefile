.PHONY: nothing venv up down logs shell manage migrate migrations fix check test db-backup db-restore db-restore-latest

DOCKER_ENV ?= .env.docker
DOCKER = DJANGO_ENV_FILE=$(DOCKER_ENV) docker compose --env-file $(DOCKER_ENV)

nothing:
	@echo "Please specify a target"

venv:
	uv sync --frozen

up:
	$(DOCKER) up --build

down:
	$(DOCKER) down

logs:
	$(DOCKER) logs -f

shell:
	$(DOCKER) run --rm web sh

manage:
	$(DOCKER) run --rm web python manage.py $(filter-out $@,$(MAKECMDGOALS))

migrate:
	$(DOCKER) run --rm web python manage.py migrate

migrations:
	$(DOCKER) run --rm web python manage.py makemigrations

fix:
	uv run ruff check --fix
	uv run ruff format

check:
	uv lock --check
	uv run ruff format --check
	uv run ruff check
	$(DOCKER) run --rm web pyright
	$(DOCKER) run --rm web mypy --pretty .

test:
	$(DOCKER) run --rm web pytest -v \
		--cov-branch \
		--cov-report=term-missing:skip-covered

db-backup:
	DOCKER_ENV=$(DOCKER_ENV) scripts/db.sh backup $(BACKUP)

db-restore:
	DOCKER_ENV=$(DOCKER_ENV) CONFIRM_RESTORE=$(CONFIRM_RESTORE) scripts/db.sh restore $(BACKUP)

db-restore-latest:
	DOCKER_ENV=$(DOCKER_ENV) CONFIRM_RESTORE=$(CONFIRM_RESTORE) scripts/db.sh restore-latest

%:
	@:
