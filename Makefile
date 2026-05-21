.PHONY: check lint format typecheck test test-all install clean

check: lint format-check typecheck test ## run all CI checks (lint + format + types + unit tests)

install: ## sync the dev environment
	uv sync

lint: ## ruff lint (includes isort)
	uv run ruff check .

format: ## auto-format with ruff
	uv run ruff format .

format-check: ## check formatting without writing
	uv run ruff format --check .

typecheck: ## pyright type check
	uv run pyright src/ tests/

test: ## fast unit tests (no Detoxify download)
	uv run pytest -m 'not integration' -q

test-all: ## full suite including integration (downloads ~500MB on first run)
	uv run pytest -q

clean: ## remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist build *.egg-info
