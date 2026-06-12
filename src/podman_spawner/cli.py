import re
import shutil
import sys
from pathlib import Path

import fire  # type: ignore
from colored_messages import print_error, print_info, print_success, print_warning

from podman_spawner.config import (
    ASSETS_DIR,
    POD_BUILD_DIRNAME,
    TEST,
)
from podman_spawner.port import port_from_name
from podman_spawner.tools import (
    State,
    config,
    containers_states,
    get_state,
    podman,
)


# pod info
def info(name: str) -> None:
    """Print state and port-forwarding information for a container."""
    print("Container name:", name)
    print("State:", get_state(name).name)
    print("Port forwarding:")
    podman("port", name)


# pod list
def list_containers() -> None:
    """List all containers whose name starts with the configured prefix."""
    podman(
        "ps",
        "-a",
        "--format",
        "table {{.Names}}\t{{.Status}}\t{{.Ports}}",
        "--filter",
        f"name=^{config().prefix}",
    )


def initialize_directory(force: bool = False, update: str | Path | None = None) -> None:
    """Initialize (or update) the pod-build directory.

    Without ``--update``, copies the full default skeleton into the target
    directory.  If the current working directory is named ``pod-build`` it is
    used directly; otherwise a ``pod-build/`` subdirectory is created.  The
    operation is refused if the target already exists and is non-empty, unless
    ``--force`` is passed.

    With ``--update <path>``, only the single file or subdirectory at
    ``<path>`` (relative to the skeleton root) is refreshed, leaving the rest
    of the directory untouched.  This is useful for pulling in an updated
    ``Dockerfile`` or ``home-dir/`` without clobbering local changes.
    """
    cwd = Path.cwd()
    dst = cwd if cwd.name == POD_BUILD_DIRNAME else cwd / POD_BUILD_DIRNAME
    dst = Path(dst).absolute()
    if update is None:
        # If the directory exists and is not empty, it should not be overwritten, unless `force` is set to True.
        if dst.exists() and any(dst.iterdir()) and not force:
            print_error(f"Path already exists: '{dst}'.")
            print_info("Use `pod init --force` to overwrite it.")
            sys.exit(1)
        shutil.copytree(ASSETS_DIR / "defaults/pod-build", dst, dirs_exist_ok=True)
        print_success(f"The directory `{dst.name}` was successfully initialized.")
    else:
        src = ASSETS_DIR / "defaults/pod-build" / update
        if not src.exists():
            print_error(f"Path does not exist: '{src}'.")
            sys.exit(1)
        dst = dst / update
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        elif src.is_file():
            shutil.copy(src, dst)
        print_success(f"File or directory updated: `{dst.name}`.")


# pod build
def build_image() -> None:
    """Build the Podman image from the current pod-build directory.

    The current working directory must look like a valid build context:
    it must contain an ``on_build.bash`` file and a ``home-dir/``
    subdirectory.  Use ``pod init`` to create a conforming directory first.

    The username baked into the image is taken from ``config.toml``
    (``user`` key) and must match ``^[a-zA-Z_][a-zA-Z0-9_]*$``.
    """
    cwd = Path.cwd()
    invalid_dir = False
    # Test that the current directory looks like a correct build context.
    if not (script := cwd / "on_build.bash").is_file():
        invalid_dir = True
        print_error(f"File not found: '{script}'.")
    if not (home_dir := cwd / "home-dir").is_dir():
        print_error(f"Directory not found: '{home_dir}'.")
    if invalid_dir:
        print_info("Hint: use `pod init` to initialize a pod directory.")
        sys.exit(1)
    user = config().user
    if not re.fullmatch("^[a-zA-Z_][a-zA-Z0-9_]*$", user):
        print_error(f"Invalid user name: {user!r}.")
        sys.exit(1)
    image_name = config().image_name
    podman_args = [
        "build",
        "-t",
        image_name,
        "--build-arg",
        f"USER={user}",
        str(cwd),
    ]
    if podman(*podman_args):
        print_success(f"Image {image_name} built.")
    else:
        print_error("Build process failed. (See details above).")


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
                "run",
                "-d",
                "-t",
                "--name",
                name,
                "--env=DISPLAY",
                "-v",
                "/tmp/.X11-unix:/tmp/.X11-unix",
                "--hostname",
                name,
                "--env",
                "TERM=xterm-256color",
                "--publish",
                f"{host_port}:{guest_port}",
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
        podman("cp", f"{script}", f"{name}:{home / script.name}")
        podman(
            "exec",
            "-d",
            name,
            "bash",
            f"{home / script.name}",
        )


# pod test
def test_image() -> None:
    """Start and attach to the ephemeral test container.

    The test container is named ``<prefix>-<TEST>`` (e.g. ``POD-test-0.0``).
    It is created from the current image if it does not exist yet.  Use this
    command to verify that a freshly built image behaves as expected before
    deploying containers to students.
    """
    attach_container(f"{config().prefix}-{TEST}")


# pod go
def attach_container(name: str) -> None:
    """Attach to a container, starting or creating it first if needed.

    Delegates start/create logic to :func:`_run_container` so that stale port
    bindings are handled consistently: if ``podman start`` fails the container
    is automatically recreated with the current port mapping.
    """
    _run_container(name, port_from_name(name))
    podman("attach", name)


# pod rm
def remove_container(name: str, force: bool = False) -> bool:
    """Remove a container permanently.

    Pass ``--force`` to remove a running container without stopping it first.
    Note: due to a limitation in python-fire, ``--force`` must come *after*
    the container name on the command line.
    """
    if not isinstance(force, bool):
        print_error(f"Invalid argument for --force: {force!r}.")
        sys.exit(1)
    if force:
        return podman("rm", "-f", name)
    else:
        return podman("rm", name)


# pod purge
def purge_containers(regex: str, force: bool = False) -> None:
    """Remove all containers whose full name matches ``regex``.

    The regex is matched against the complete container name (including the
    configured prefix), using :func:`re.fullmatch`.  Running containers are
    flagged with a warning; pass ``--force`` to remove them without stopping
    first.
    """
    print("Removing containers:")
    count = 0
    for name in containers_states():
        assert name.startswith(config().prefix)
        if re.fullmatch(regex, name):
            count += 1
            if get_state(name) == State.UP:
                print_warning(
                    f"Container {name} is still running. Use pod go {name} to show it."
                )
            remove_container(name, force=force)
    if count == 0:
        print_warning(f"No matching container found for '{regex}'.")


# pod purge-all
def purge_all_containers(force: bool = False) -> None:
    """Remove all containers, including the test container.

    Running containers are flagged with a warning; pass ``--force`` to remove
    them without stopping first.
    """
    print("Removing containers:")
    prefix = config().prefix
    name = f"{prefix}-{TEST}"
    if get_state(name) != State.NOT_FOUND:
        remove_container(name, force=force)
    containers = containers_states()
    for name, state in containers.items():
        assert name.startswith(prefix)
        if state == State.UP:
            print_warning(
                f"Container {name} is still running. Use `pod go {name}` to show it."
            )
        remove_container(name, force=force)
    if len(containers) == 0:
        print_warning("No container found.")


def main() -> None:
    fire.Fire(
        {
            "init": initialize_directory,
            "build": build_image,
            "test": test_image,
            "go": attach_container,
            "rm": remove_container,
            "purge": purge_containers,
            "purge-all": purge_all_containers,
            "info": info,
            "list": list_containers,
        }
    )


if __name__ == "__main__":
    main()
