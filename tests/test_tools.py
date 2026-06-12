import json
from pathlib import Path

import pytest

from podman_spawner import tools
from podman_spawner.tools import Config, State, config, containers_states, get_state


@pytest.fixture(autouse=True)
def _clear_config_cache() -> None:
    """`config()` is cached with @cache; clear it before each test."""
    config.cache_clear()


# --- config() -------------------------------------------------------------


def test_config_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "config.toml").write_text(
        'prefix = "POD"\nport = 2026\nuser = "tester"\n'
    )
    monkeypatch.chdir(tmp_path)

    cfg = config()

    assert cfg == Config(prefix="POD", port=2026, user="tester")
    assert cfg.image_name == "pod:latest"


def test_config_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit):
        config()


def test_config_missing_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "config.toml").write_text('prefix = "POD"\nport = 2026\n')  # no `user`
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit):
        config()


def test_config_unexpected_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "config.toml").write_text(
        'prefix = "POD"\nport = 2026\nuser = "tester"\nextra = "oops"\n'
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit):
        config()


# --- containers_states() / get_state() -------------------------------------


PODMAN_PS_OUTPUT = json.dumps(
    [
        {"Names": ["POD-GROUP-1.0"], "State": "running"},
        {"Names": ["POD-GROUP-2.0"], "State": "exited"},
        {"Names": ["POD-GROUP-3.0"], "State": "created"},
        {"Names": ["unrelated-container"], "State": "running"},
    ]
)


class _FakeCompletedProcess:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout


def _set_config(monkeypatch: pytest.MonkeyPatch, prefix: str = "POD") -> None:
    monkeypatch.setattr(
        tools, "config", lambda: Config(prefix=prefix, port=2026, user="tester")
    )


def test_containers_states_filters_by_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_config(monkeypatch)
    monkeypatch.setattr(
        tools, "run", lambda *a, **kw: _FakeCompletedProcess(PODMAN_PS_OUTPUT)
    )

    states = containers_states()

    assert states == {
        "POD-GROUP-1.0": State.UP,
        "POD-GROUP-2.0": State.EXITED,
        "POD-GROUP-3.0": State.CREATED,
    }
    assert "unrelated-container" not in states


def test_containers_states_empty_output(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_config(monkeypatch)
    monkeypatch.setattr(tools, "run", lambda *a, **kw: _FakeCompletedProcess(""))

    assert containers_states() == {}


def test_containers_states_unknown_state_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_config(monkeypatch)
    output = json.dumps([{"Names": ["POD-WEIRD"], "State": "paused"}])
    monkeypatch.setattr(tools, "run", lambda *a, **kw: _FakeCompletedProcess(output))

    with pytest.raises(NotImplementedError):
        containers_states()


def test_get_state_known_container(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_config(monkeypatch)
    monkeypatch.setattr(
        tools, "run", lambda *a, **kw: _FakeCompletedProcess(PODMAN_PS_OUTPUT)
    )

    assert get_state("POD-GROUP-1.0") == State.UP


def test_get_state_unknown_container(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_config(monkeypatch)
    monkeypatch.setattr(
        tools, "run", lambda *a, **kw: _FakeCompletedProcess(PODMAN_PS_OUTPUT)
    )

    assert get_state("POD-DOES-NOT-EXIST") == State.NOT_FOUND
