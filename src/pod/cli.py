import re
import shutil
import sys
from pathlib import Path

import fire  # type: ignore
from colored_messages import print_error, print_info, print_success, print_warning

from pod.config import (
    ASSETS_DIR,
    POD_BUILD_DIRNAME,
    TEST,
)
from pod.port import port_from_name
from pod.tools import (
    State,
    config,
    containers_states,
    get_state,
    podman,
)


# pod info
def info(name: str) -> None:
    """Give some information on a container."""
    print("Container name:", name)
    print("State:", get_state(name).name)
    print("Port forwarding:")
    podman("port", name)


# pod list
def list_containers():
    """List the current containers."""
    podman(
        "ps",
        "-a",
        "--format",
        "table {{.Names}}\t{{.Status}}\t{{.Ports}}",
        "--filter",
        f"name=^{config().prefix}",
    )


def initialize_directory(force: bool = False, update: str | Path | None = None) -> None:
    """
    Initialize the directory, creating the expected files for the build to work.

    If the current directory is named `pod-build`, then it will be used,
    else a `pod-build` subdirectory is created.
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
    """
    Build the image.
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
    """Start a new container with this name.

    If a container already exist, print a warning and do nothing
    (use manually `pod reset` if needed).
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
def test_image():
    attach_container(f"{config().prefix}-{TEST}")


# pod go
def attach_container(name: str) -> None:
    """Show the container for this group/version.

    Start or create it if needed.
    """
    state = get_state(name)
    if state == State.NOT_FOUND:
        run_container(name)
    elif state == State.EXITED:
        podman("start", name)
    podman("attach", name)


# pod rm
def remove_container(name: str, force: bool = False) -> bool:
    """Remove definitively a container.

    The `--force` argument must be the last one, due to a limitation
    in the python-fire library.
    """
    if not isinstance(force, bool):
        print_error(f"Invalid argument for --force: {force!r}.")
        sys.exit(1)
    if force:
        return podman("rm", "-f", name)
    else:
        return podman("rm", name)


# pode purge
def purge_containers(regex: str, force: bool = False) -> None:
    """Remove all containers matching the given regex."""
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
    """Remove all containers."""
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
