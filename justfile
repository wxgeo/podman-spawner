test:
    uv run ruff check --fix .
    uv run mypy src
    uv run pytest tests
install:
	uv tool  install -e .

