.PHONY: nothing lint pyright mypy typecheck check test fix clean venv docker-config docker-up docker-down docker-build docker-migrate docker-test docker-logs docker-shell docker-prod-config docker-prod-check docker-prod-static docker-prod-migrate docker-prod-up docker-prod-down docker-prod-logs

DOCKER_DEV_ENV ?= .env.docker
DOCKER_PROD_ENV ?= .env.prod
DOCKER_DEV = DJANGO_ENV_FILE=$(DOCKER_DEV_ENV) docker compose --env-file $(DOCKER_DEV_ENV)
DOCKER_PROD = DJANGO_ENV_FILE=$(DOCKER_PROD_ENV) docker compose -f compose.yml -f compose.prod.yml --env-file $(DOCKER_PROD_ENV)

nothing:
	@echo "Please specify a target"

venv:
	uv sync --frozen

lint:
	uv lock --check
	uv run ruff format --check
	uv run ruff check

pyright:
	uv run --frozen --all-groups pyright

mypy:
	uv run --frozen --all-groups mypy --pretty .

typecheck: pyright mypy

check: lint typecheck

test:
	uv run --frozen --only-group dev pytest -v \
		--cov-branch \
		--cov-report=term-missing:skip-covered

fix:
	uv run ruff check --fix
	uv run ruff format

clean:
	find . -type d -name __pycache__ | xargs -n1 rm -rf
	rm -rf \
		.venv \
		.pytest_cache \
		.ruff_cache \
		.mypy_cache \
		.coverage* \
		coverage.xml \
		.hypothesis \
		.testmondata

upgrade:
	uv lock --upgrade
	uv sync

docker-config:
	$(DOCKER_DEV) config --quiet

docker-build:
	$(DOCKER_DEV) build

docker-up:
	$(DOCKER_DEV) up --build

docker-down:
	$(DOCKER_DEV) down

docker-migrate:
	$(DOCKER_DEV) run --rm web python manage.py migrate

docker-test:
	$(DOCKER_DEV) run --rm web pytest -v

docker-logs:
	$(DOCKER_DEV) logs -f

docker-shell:
	$(DOCKER_DEV) run --rm web sh

docker-prod-config:
	$(DOCKER_PROD) config --quiet

docker-prod-check:
	$(DOCKER_PROD) run --rm web python manage.py check --deploy

docker-prod-static:
	$(DOCKER_PROD) run --rm web python manage.py collectstatic --noinput

docker-prod-migrate:
	$(DOCKER_PROD) run --rm web python manage.py migrate --noinput

docker-prod-up:
	$(DOCKER_PROD) up --build -d

docker-prod-down:
	$(DOCKER_PROD) down

docker-prod-logs:
	$(DOCKER_PROD) logs -f
