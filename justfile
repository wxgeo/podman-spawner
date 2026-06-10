install:
	uv tool  install -e .
test:
    uv run ruff check --fix .
    uv run mypy src