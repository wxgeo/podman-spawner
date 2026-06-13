import json
import sys
import tomllib
from dataclasses import dataclass, fields
from enum import Enum
from functools import cache
from subprocess import run
from typing import Any

from colored_messages import print_error, print_info

from podman_spawner.config import CONFIG_FILE


class State(Enum):
    """Lifecycle state of a Podman container.

    Mirrors the subset of states returned by ``podman ps --format json``:

    - ``UP``        — container is running.
    - ``CREATED``   — container was created but never started.
    - ``EXITED``    — container ran and has stopped.
    - ``NOT_FOUND`` — no container with that name exists (local addition,
                      not a Podman state).
    """

    UP = 0
    CREATED = 2
    EXITED = 3
    NOT_FOUND = 4


# Maps the lowercase state strings from `podman ps --format json` to State.
_PODMAN_STATE_MAP: dict[str, State] = {
    "running": State.UP,
    "created": State.CREATED,
    "exited": State.EXITED,
}


@dataclass
class Config:
    f"""Runtime configuration loaded from ``{CONFIG_FILE}l``.

    Attributes:
        prefix: Prefix prepended to every container name (e.g. ``"POD"``).
        port:   Guest port exposed by every container.
        user:   Username created inside the container at build time.
    """

    prefix: str
    port: int
    user: str

    @property
    def image_name(self) -> str:
        """Fully-qualified image tag used by ``podman build`` and ``podman run``."""
        return f"{self.prefix}:latest".lower()


@cache
def config() -> Config:
    f"""Load and return the project configuration.

    Reads ``{CONFIG_FILE}` from the *current working directory* and returns a
    :class:`Config` instance.  The result is cached so the file is read only
    once per process; run ``pod`` from the directory that contains
    ``{CONFIG_FILE}``.
    """
    try:
        with open(CONFIG_FILE, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        print_error(f"File `{CONFIG_FILE}` was not found")
        print_info("Hint: use `pod init` to initialize a pod directory.")
        sys.exit(1)
    try:
        config_ = Config(**data)
    except TypeError:
        # Compare data keys and Config fields, to report a useful message.
        expected = {f.name for f in fields(Config)}
        actual = set(data.keys())
        missing = expected - actual
        unexpected = actual - expected
        if missing:
            print_error(
                f"Missing keys in `{CONFIG_FILE}`: {', '.join(sorted(missing))}"
            )
        if unexpected:
            print_error(
                f"Unknown keys in `{CONFIG_FILE}`: {', '.join(sorted(unexpected))}"
            )
        sys.exit(1)
    return config_


def containers_states() -> dict[str, State]:
    """Return the state of every container whose name matches the configured prefix.

    Calls ``podman ps -a --format json`` and filters by :attr:`Config.prefix`.
    Containers not belonging to this project are ignored.

    Raises:
        NotImplementedError: If Podman reports a state string not present in
            ``_PODMAN_STATE_MAP`` (i.e. a state this code does not yet handle).
    """
    completed_process = run(
        ["podman", "ps", "-a", "--format", "json"],
        encoding="utf8",
        capture_output=True,
    )
    entries = json.loads(completed_process.stdout or "[]")
    prefix = config().prefix
    result = {}
    for entry in entries:
        names = entry.get("Names") or []
        raw_state = entry.get("State", "").lower()
        state = _PODMAN_STATE_MAP.get(raw_state)
        if state is None:
            raise NotImplementedError(f"Unrecognised container state: {raw_state!r}")
        for name in names:
            if name.startswith(prefix):
                result[name] = state
    return result


def get_state(name: str) -> State:
    """Return the :class:`State` of a single container.

    Returns ``State.NOT_FOUND`` if no container with that name exists,
    rather than raising an exception.
    """
    return containers_states().get(name, State.NOT_FOUND)


def podman(*args: str, **kw: Any) -> bool:
    """Run a podman command and return ``True`` on success, ``False`` otherwise."""
    print(" ".join(["podman", *args]))
    return run(["podman", *args], **kw).returncode == 0
