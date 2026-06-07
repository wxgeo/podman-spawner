import datetime
from enum import Enum
from subprocess import run
from typing import Any


class State(Enum):
    UP = 0
    CREATED = 2
    EXITED = 3
    NOT_FOUND = 4


def format(group: str, version: str) -> tuple[str, str]:
    if isinstance(version, str) and version.startswith("v"):
        version = version[1:].strip()
    try:
        float(version)
    except ValueError:
        raise ValueError(f"Unsupported version number: {version}.")
    return str(group).lower(), str(float(version))


def container_name(group: str, version: str) -> str:
    from pod.config import PREFIX

    return f"{PREFIX}-{group}-{version}"


def group_version(name: str) -> tuple[str, str]:
    from pod.config import PREFIX

    try:
        group, version = name[len(PREFIX) + 1 :].split("-")
    except ValueError:
        raise ValueError(f"Invalid image name format: {name!r}.")
    return group, version


def _extract_state(podman_output: str) -> State:
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
    from pod.config import PREFIX

    completed_process = run(
        ["podman", "ps", "-a"], encoding="utf8", capture_output=True
    )
    header, *rows = completed_process.stdout.strip().split("\n")
    status_position = header.find("STATUS")
    names_position = header.find("NAMES")
    return {
        name: _extract_state(row[status_position:].split()[0])
        for row in rows
        if (name := row[names_position:].strip()).startswith(PREFIX)
    }


def get_state(name: str) -> State:
    return containers_states().get(name, State.NOT_FOUND)


def get_state2(group: str, version: str) -> State:
    return get_state(container_name(group, version))


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


def podman(*args: str, **kw: Any) -> bool:
    """Return True if the process was successful, False else."""
    print(" ".join(["podman", *args]))
    return run(["podman", *args], **kw).returncode == 0


def academic_year() -> tuple[int, int]:
    """
    Returns the current academic year as a tuple of two-digit years (start, end).
    The academic year shifts on September 1st.
    """
    today = datetime.date.today()
    current_year = today.year

    # If we are in September or later, the academic year started this year.
    # Otherwise, it started the previous year.
    if today.month >= 9:
        start_year = current_year
    else:
        start_year = current_year - 1

    end_year = start_year + 1

    # Extract the last two digits of the years
    return start_year % 100, end_year % 100
