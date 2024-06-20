from pathlib import Path

import fire

from pod.config import IMG_NAME, PORT, COPY_PATH
from pod.tools import _name, state, host_port, _format, State, podman, containers_states


# pod info
def info(group: object, version: object) -> None:
    """Give some information on a container."""
    group, version = _format(group, version)
    print("Container name:", _name(group, version))
    print("State:", state(group, version).name)
    port = host_port(group, version)
    print(f"Port forwarding: {port}->{PORT}")


# pod list
def list_containers():
    """List the current containers."""
    podman(
        "ps",
        "-a",
        "--format",
        "table {{.Names}}\t{{.Status}}\t{{.Ports}}",
        "--filter",
        "name=^SAE-",
    )


# pod build
def build_image() -> None:
    """Build the image."""
    podman("build", "-t", IMG_NAME, str(Path(__file__).parent.parent))


# pod test
def test_image() -> None:
    """Create a temporary container to test the image."""
    podman(
        "run",
        "--interactive",
        "--tty",  # `--tty` or `-t` is mandatory here!
        "--rm",
        "--env='DISPLAY'",
        "--net=host",
        "--env color_prompt=yes",
        IMG_NAME,
    )


# (pod new)
def run_container(group: object, version: object) -> None:
    """Start a new container for this group/version if needed.

    If a container already exist, print a warning and do nothing
    (use manually `pod reset` if needed).
    """
    group, version = _format(group, version)
    name = _name(group, version)
    port = host_port(group, version)
    match state(group, version):
        case State.UP:
            pass
        case State.EXITED:
            podman("start", name)
        case State.CREATED:
            podman("start", name)
        case State.NOT_FOUND:
            podman(
                "run",
                "-d",
                "-t",
                "--name",
                name,
                "--env=DISPLAY",
                "--publish",
                f"{port}:{PORT}",
                IMG_NAME,
            )
            print(f"Port forwarding: {port}->{PORT}")
    podman("cp", f"{COPY_PATH / version / group}/.", f"{name}:/usr/src/app")
    podman("exec", "-d", name, "chmod", "u+x", "/usr/src/app/compile_all")
    podman("exec", "-d", name, "bash", "/usr/src/app/compile_all")


# pod go
def attach_container(group: object, version: object) -> None:
    """Show the container for this group/version.

    Start or create it if needed.
    """
    group, version = _format(group, version)
    name = _name(group, version)
    if state(group, version) == State.NOT_FOUND:
        run_container(group, version)
    elif state(group, version) == State.EXITED:
        podman("start", name)
    podman("attach", name)


# (pod reset)
def reset_container(group: object, version: object, force=False) -> None:
    """Reset the container for this group/version.

    To force the reset of a running container:

        pod reset <group> <version> --force

    The `--force` argument must be last one, due to a limitation
    in the python-fire library.
    """
    group, version = _format(group, version)
    if not isinstance(force, bool):
        raise ValueError(f"Invalid argument: {force}.")
    remove_container(group, version, force=force)
    run_container(group, version)


# pod rm
def remove_container(group, version, force=False) -> None:
    """Remove definitively a container.

    The `--force` argument must be last one, due to a limitation
    in the python-fire library.
    """
    group, version = _format(group, version)
    if not isinstance(force, bool):
        raise ValueError(f"Invalid argument: {force}.")
    if force:
        podman("rm", "-f", _name(group, version))
    else:
        podman("rm", _name(group, version))


def _purge_containers(version: object = None, force=False) -> None:
    """Remove all containers for a given version."""
    if version is not None:
        _, version = _format("A", version)
    count = 0
    for container in containers_states():
        assert container.startswith("SAE-")
        assert "-" in container[4:]
        gp, vers = container[4:].split("-")
        if vers == version or version is None:
            count += 1
            if state(gp, vers) == State.UP:
                name = _name(gp, vers)
                print(f"Warning: {name} is running. Use pod go {gp} {vers} to show it.")
            remove_container(gp, vers, force=force)
    if count == 0:
        print(
            (
                f"No container found"
                + ("" if version is None else f" for version {version}")
                + "."
            ),
        )


# pode purge
def purge_containers(version: object, force=False) -> None:
    """Remove all containers for a given version."""
    _purge_containers(version, force=force)


# pod armaggedon
def purge_all_containers(force=False) -> None:
    """Remove all containers."""
    _purge_containers(force=force)


def main():
    fire.Fire(
        {
            "build": build_image,
            "test": test_image,
            # "new": run_container,
            "go": attach_container,
            # "reset": reset_container,
            "rm": remove_container,
            "purge": purge_containers,
            "armaggedon": purge_all_containers,
            "info": info,
            "list": list_containers,
        }
    )


if __name__ == "__main__":
    main()
