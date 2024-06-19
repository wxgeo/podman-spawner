from enum import Enum
from subprocess import run

import fire

from pod.config import IMG_NAME, PORT


# def cmd(command: str):


class State(Enum):
    UP = 0
    CREATED = 2
    EXITED = 3
    NOT_FOUND = 4


def _name(group: str, version: str) -> str:
    return f"{group}-{version}"


def state(group: str, version: str) -> str:
    completed_process = run(["podman", "ps", "-a"], encoding="utf8")
    lines = completed_process.stdout.split("\n")
    print(repr(lines))
    return


def print_sate(group, version):
    return print(state(group, version))


def host_port(group: str, version: str) -> int:
    if version.startswith("v"):
        version = version[1:].strip()
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


def build_image():
    """Build the image."""
    run(["podman", "build", "-t", IMG_NAME])


def test_image():
    """Create a temporary container to test the image."""
    run(
        [
            "podman",
            "run",
            "--interactive",
            "--rm",
            "--env='DISPLAY'",
            "--net=host",
            IMG_NAME,
        ]
    )


def run_container(group, version):
    """Start a new container for this group/version if needed.

    If a container already exist, print a warning and do nothing
    (use manually `pod reset` if needed).
    """
    port = host_port(group, version)
    run(
        [
            "podman",
            "run",
            "--name",
            _name(group, version),
            "--env=DISPLAY",
            "--publish",
            f"{port}:{PORT}",
            IMG_NAME,
        ]
    )
    print(f"Port forwarding: {port}->{PORT}")


def attach_container(group, version):
    """Show the container for this group/version.

    Start it if needed.
    """
    run(["podman", "attach", _name(group, version)])


def reset_container(group, version, force=True):
    """Reset the container for this group/version.

    To force the reset of a running container:

        pod reset <group> <version> --force

    The `--force` argument must be last one, due to a limitation
    in the python-fire library.
    """
    if not isinstance(force, bool):
        raise ValueError(f"Invalid argument: {force}.")
    run(["podman", "rm", _name(group, version)])


def exit_container(group, version):
    """Exit"""


def main():
    fire.Fire(
        {
            "build": build_image,
            "test": test_image,
            "new": run_container,
            "show": attach_container,
            "reset": reset_container,
            "port": host_port,
            "exit": exit_container,
            "state": print_state,
        }
    )


if __name__ == "__main__":
    main()
