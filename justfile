project := "podman-spawner"
uv := "env -u VIRTUAL_ENV uv"

test:
    uv run ruff check --fix .
    uv run mypy src
    uv run pytest tests

install:
	uv tool  install -e .

_check-clean:
    @git diff --exit-code || (printf "\e[1;97;43m[Warning]\e[0m Uncommitted changes in {{project}}! \n" && exit 1)
    @git diff --cached --exit-code || (printf "\e[1;97;43m[Warning]\e[0m Staged changes in {{project}}! \n" && exit 1)

_check-branch branch="main":
    @git rev-parse --abbrev-ref HEAD | grep -qx {{branch}} || (echo "\e[1;97;43m[Warning]\e[0m {{project}} is not on {{branch}} branch!" && exit 1)

release: _check-clean _check-branch test
    rm -rf dist/
    {{uv}} publish
