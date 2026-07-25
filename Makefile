.PHONY: nothing lint pyright mypy typecheck check test fix clean venv

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
