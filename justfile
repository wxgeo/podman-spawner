test:
    uv run ruff check --fix .
    uv run mypy src
install:
	uv tool  install -e .

