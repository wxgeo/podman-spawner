import re
import shutil
from pathlib import Path
from typing import Annotated, Optional

import typer
from colored_messages import print_error, print_info, print_success, print_warning

from podman_spawner.config import ASSETS_DIR, POD_BUILD_DIRNAME, TEST
from podman_spawner.port import port_from_name
from podman_spawner.tools import State, config, containers_states, get_state, podman

app = typer.Typer(help="Manage Podman containers.")


# ---------------------------------------------------------------------------
# Internal helpers (not exposed as CLI commands)
# ---------------------------------------------------------------------------

def _run_container(name: str, host_port: int) -> bool:
    """Ensure the named container is running, creating it if necessary.

    Behaviour by current container state:

    - **UP** — nothing to do, returns ``True`` immediately.
    - **EXITED / CREATED** — attempts ``podman start``.  If that fails (e.g.
      the port stored in the container's config is already in use), the stale
      container is removed and the function recurses once to recreate it via
      the NOT_FOUND branch.
    - **NOT_FOUND** — creates a new detached container with ``podman run``,
      forwarding ``host_port`` on the host to the guest port defined in
      ``config.toml``.

    Returns ``True`` on success, ``False`` if the underlying podman command
    failed.
    """
    guest_port = config().port
    match get_state(name):
        case State.UP:
            return True
        case State.EXITED | State.CREATED:
            if podman("start", name):
                return True
            print_warning(
                f"Could not restart {name!r}; recreating with current port mapping."
            )
            podman("rm", "-f", name)
            return _run_container(name, host_port)
        case State.NOT_FOUND:
            print(f"Port forwarding: {host_port}->{guest_port}")
            return podman(
                "run", "-d", "-t",
                "--name", name,
                "--env=DISPLAY",
                "-v", "/tmp/.X11-unix:/tmp/.X11-unix",
                "--hostname", name,
                "--env", "TERM=xterm-256color",
                "--publish", f"{host_port}:{guest_port}",
                config().image_name,
            )
        case _:
            raise NotImplementedError


def run_container(
    name: str,
    host_port: int | None = None,
    copy: str | Path | None = None,
    script: str | Path | None = None,
) -> None:
    """Start a container, optionally copying files or running a script inside it.

    If the container does not exist it is created.  If it already exists but
    is stopped it is restarted (with automatic recreation if the port binding
    is stale — see :func:`_run_container`).

    Args:
        name: Container name.
        host_port: Port to forward on the host side.  Derived deterministically
            from ``name`` via :func:`port_from_name` when omitted.
        copy: Local directory whose *contents* are copied into the container's
            home directory (equivalent to ``podman cp <copy>/. <name>:<home>``).
        script: Local script file to copy into the container's home directory
            and execute there in a detached bash session.
    """
    if host_port is None:
        host_port = port_from_name(name)
    _run_container(name, host_port)
    home = Path(f"/home/{config().user}/")
    if copy is not None:
        # Docker documentation specifies to add "/." at the end of the source
        # path, so as to copy the folder content (and not the folder itself).
        podman("cp", f"{copy}/.", f"{name}:{home}")
    if script is not None:
        script = Path(script)
        podman("cp", str(script), f"{name}:{home / script.name}")
        podman("exec", "-d", name, "bash", str(home / script.name))


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

@app.command("info")
def info(name: str) -> None:
    """Print state and port-forwarding information for a container."""
    print("Container name:", name)
    print("State:", get_state(name).name)
    print("Port forwarding:")
    podman("port", name)


@app.command("list")
def list_containers() -> None:
    """List all containers whose name starts with the configured prefix."""
    podman(
        "ps", "-a",
        "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}",
        "--filter", f"name=^{config().prefix}",
    )


@app.command("init")
def initialize_directory(
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing pod-build directory.")] = False,
    update: Annotated[Optional[str], typer.Option("--update", help="Refresh only this file or subdirectory.")] = None,
) -> None:
    """Initialize (or update) the pod-build directory.

    Without --update, copies the full default skeleton into the target
    directory.  If the current working directory is named pod-build it is
    used directly; otherwise a pod-build/ subdirectory is created.  The
    operation is refused if the target already exists and is non-empty, unless
    --force is passed.

    With --update PATH, only the single file or subdirectory at PATH (relative
    to the skeleton root) is refreshed, leaving the rest of the directory
    untouched.
    """
    cwd = Path.cwd()
    dst = cwd if cwd.name == POD_BUILD_DIRNAME else cwd / POD_BUILD_DIRNAME
    dst = dst.absolute()
    if update is None:
        if dst.exists() and any(dst.iterdir()) and not force:
            print_error(f"Path already exists: '{dst}'.")
            print_info("Use `pod init --force` to overwrite it.")
            raise typer.Exit(code=1)
        shutil.copytree(ASSETS_DIR / "defaults/pod-build", dst, dirs_exist_ok=True)
        print_success(f"The directory `{dst.name}` was successfully initialized.")
    else:
        src = ASSETS_DIR / "defaults/pod-build" / update
        if not src.exists():
            print_error(f"Path does not exist: '{src}'.")
            raise typer.Exit(code=1)
        dst = dst / update
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        elif src.is_file():
            shutil.copy(src, dst)
        print_success(f"File or directory updated: `{Path(update).name}`.")


@app.command("build")
def build_image() -> None:
    """Build the Podman image from the current pod-build directory.

    The current working directory must contain a home-dir/ subdirectory with
    an on_build.bash file inside it.  Use `pod init` to create a conforming
    directory first.

    The username baked into the image is taken from config.toml (user key).
    """
    cwd = Path.cwd()
    invalid_dir = False
    if not (home_dir := cwd / "home-dir").is_dir():
        print_error(f"Directory not found: '{home_dir}'.")
        invalid_dir = True
    if not (script := cwd / "home-dir" / "on_build.bash").is_file():
        print_error(f"File not found: '{script}'.")
        invalid_dir = True
    if invalid_dir:
        print_info("Hint: use `pod init` to initialize a pod directory.")
        raise typer.Exit(code=1)
    user = config().user
    if not re.fullmatch("^[a-zA-Z_][a-zA-Z0-9_]*$", user):
        print_error(f"Invalid user name: {user!r}.")
        raise typer.Exit(code=1)
    image_name = config().image_name
    if podman("build", "-t", image_name, "--build-arg", f"USER={user}", str(cwd)):
        print_success(f"Image {image_name} built.")
    else:
        print_error("Build process failed. (See details above).")


@app.command("test")
def test_image() -> None:
    """Start and attach to the ephemeral test container.

    The test container is named <prefix>-<TEST> (e.g. POD-test-0.0).
    It is created from the current image if it does not exist yet.  Use this
    command to verify that a freshly built image behaves as expected before
    deploying containers to students.
    """
    attach_container(f"{config().prefix}-{TEST}")


@app.command("go")
def attach_container(name: str) -> None:
    """Attach to a container, starting or creating it first if needed.

    Delegates start/create logic to _run_container so that stale port
    bindings are handled consistently: if podman start fails the container
    is automatically recreated with the current port mapping.
    """
    _run_container(name, port_from_name(name))
    podman("attach", name)


@app.command("rm")
def remove_container(
    name: str,
    force: Annotated[bool, typer.Option("--force", help="Remove a running container without stopping it first.")] = False,
) -> None:
    """Remove a container permanently."""
    if force:
        podman("rm", "-f", name)
    else:
        podman("rm", name)


@app.command("purge")
def purge_containers(
    regex: str,
    force: Annotated[bool, typer.Option("--force", help="Also remove running containers.")] = False,
) -> None:
    """Remove all containers whose full name matches REGEX.

    The regex is matched against the complete container name (including the
    configured prefix) using re.fullmatch.  Running containers are flagged
    with a warning; pass --force to remove them without stopping first.
    """
    print("Removing containers:")
    count = 0
    for name in containers_states():
        assert name.startswith(config().prefix)
        if re.fullmatch(regex, name):
            count += 1
            if get_state(name) == State.UP:
                print_warning(
                    f"Container {name} is still running. Use `pod go {name}` to show it."
                )
            remove_container(name, force=force)
    if count == 0:
        print_warning(f"No matching container found for '{regex}'.")


@app.command("purge-all")
def purge_all_containers(
    force: Annotated[bool, typer.Option("--force", help="Also remove running containers.")] = False,
) -> None:
    """Remove all containers, including the test container.

    Running containers are flagged with a warning; pass --force to remove
    them without stopping first.
    """
    print("Removing containers:")
    prefix = config().prefix
    test_name = f"{prefix}-{TEST}"
    if get_state(test_name) != State.NOT_FOUND:
        remove_container(test_name, force=force)
    containers = containers_states()
    for name, state in containers.items():
        assert name.startswith(prefix)
        if state == State.UP:
            print_warning(
                f"Container {name} is still running. Use `pod go {name}` to show it."
            )
        remove_container(name, force=force)
    if not containers:
        print_warning("No container found.")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
