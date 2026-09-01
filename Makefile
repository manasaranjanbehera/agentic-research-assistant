.PHONY: install lint test run clean help

help:
	@echo "Targets:"
	@echo "  install  Sync dependencies with uv"
	@echo "  lint     Run Ruff linter"
	@echo "  test     Run the test suite"
	@echo "  run      Run the pipeline (TOPIC=... required)"
	@echo "  clean    Remove local caches and virtualenv"

install:
	uv sync

lint:
	uv run ruff check src tests

test:
	uv run pytest -v

run:
	@test -n "$(TOPIC)" || (echo "Usage: make run TOPIC=\"your question here\"" && exit 1)
	uv run python -m src.main "$(TOPIC)" -v

clean:
	rm -rf .venv .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
