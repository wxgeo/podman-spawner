from enum import Enum
from pathlib import Path
from subprocess import run

SCRIPTS_PATH = Path(__file__).parent.parent / "scripts"
assert SCRIPTS_PATH.resolve()
assert SCRIPTS_PATH.is_dir()


class State(Enum):
    UP = 0
    CREATED = 2
    EXITED = 3
    NOT_FOUND = 4


def _format(group: object, version: object) -> tuple[str, str]:
    if isinstance(version, str) and version.startswith("v"):
        version = version[1:].strip()
    try:
        float(version)
    except ValueError:
        raise ValueError(f"Unsupported version number: {version}.")
    return str(group).lower(), str(float(version))


def _name(group: str, version: str) -> str:
    return f"SAE-{group}-{version}"


def _get_state(podman_output: str) -> State:
    match podman_output:
        case "Up":
            return State.UP
        case "Created":
            return State.CREATED
        case "Exited":
            return State.EXITED
        case _ as e:
            raise NotImplementedError(e)


def containers_states() -> dict[str, State]:
    completed_process = run(
        ["podman", "ps", "-a"], encoding="utf8", capture_output=True
    )
    header, *rows = completed_process.stdout.strip().split("\n")
    status_position = header.find("STATUS")
    names_position = header.find("NAMES")
    return {
        name: _get_state(row[status_position:].split()[0])
        for row in rows
        if (name := row[names_position:].strip()).startswith("SAE-") and "-" in name[4:]
    }


def state(group: str, version: str) -> State:
    return containers_states().get(_name(group, version), State.NOT_FOUND)


def host_port(group: str, version: str) -> int:
    if len(group) > 1:
        raise NotImplementedError(
            "Le nom du groupe doit avoir un seule caractère (lettre/chiffre),"
            " ou être un nombre."
        )
    if group.isdigit():
        n = int(group)
    else:
        n = ord(group)
    return 9000 + int(100 * float(version)) + n


def podman(*args: str, **kw):
    run(["podman", *args], **kw)
