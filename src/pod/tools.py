import json
import tomllib
from dataclasses import dataclass
from enum import Enum
from functools import cache
from subprocess import run
from typing import Any


class State(Enum):
    UP = 0
    CREATED = 2
    EXITED = 3
    NOT_FOUND = 4


_PODMAN_STATE_MAP: dict[str, State] = {
    "running": State.UP,
    "created": State.CREATED,
    "exited": State.EXITED,
}


@dataclass
class Config:
    prefix: str
    port: int
    user: str

    @property
    def image_name(self):
        return f"{self.prefix}:latest".lower()


@cache
def config() -> Config:
    # Open the file in binary mode ('rb')
    with open("config.toml", "rb") as f:
        # Load the TOML content into a dictionary
        data = tomllib.load(f)
    return Config(**data)


def containers_states() -> dict[str, State]:
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
    return containers_states().get(name, State.NOT_FOUND)


def podman(*args: str, **kw: Any) -> bool:
    """Return True if the process was successful, False else."""
    print(" ".join(["podman", *args]))
    return run(["podman", *args], **kw).returncode == 0
