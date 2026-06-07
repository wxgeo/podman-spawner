import re
import shutil
import sys
from pathlib import Path

import fire
from colored_messages import print_error, print_info, print_success, print_warning

from pod.config import (
    ASSETS_DIR,
    COPY_PATH,
    IMG_NAME,
    POD_BUILD_DIRNAME,
    PORT,
    PREFIX,
    SAE_ID,
)
from pod.tools import (
    State,
    container_name,
    containers_states,
    format,
    get_state,
    get_state2,
    group_version,
    host_port,
    podman,
)


# pod info
def info(group: str, version: str) -> None:
    """Give some information on a container."""
    group, version = format(group, version)
    print("Container name:", container_name(group, version))
    print("State:", get_state2(group, version).name)
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
        f"name=^{PREFIX}",
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
def build_image(user: str = "tester") -> None:
    """
    Build the image.

    Arguments:
        - user: the username that will be used in the container.
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
    if not re.fullmatch("^[a-zA-Z_][a-zA-Z0-9_]*$", user):
        print_error(f"Invalid user name: {user!r}.")
        sys.exit(1)
    podman_args = [
        "build",
        "-t",
        IMG_NAME,
        "--build-arg",
        f"USER={user}",
        str(cwd),
    ]
    if podman(*podman_args):
        print_success(f"Image {IMG_NAME} build.")
    else:
        print_error("Build process failed. (See details above).")


def _run_container(name: str, port: int) -> bool:
    match get_state(name):
        case State.UP:
            return True
        case State.EXITED:
            return podman("start", name)
        case State.CREATED:
            return podman("start", name)
        case State.NOT_FOUND:
            print(f"Port forwarding: {port}->{PORT}")
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
                f"{port}:{PORT}",
                IMG_NAME,
            )
        case _:
            raise NotImplementedError


# pod test
def test_image():
    _run_container(f"{PREFIX}-test", 9999)


def run_container(group: str, version: str) -> None:
    """Start a new container for this group/version if needed.

    If a container already exist, print a warning and do nothing
    (use manually `pod reset` if needed).
    """
    group, version = format(group, version)
    name = container_name(group, version)
    port = host_port(group, version)
    _run_container(name, port)
    podman("cp", f"{COPY_PATH / version / group}/.", f"{name}:/usr/src/app")
    # podman(
    #     "cp",
    #     f"{SCRIPTS_PATH / 'webpagesaver'}",
    #     f"{name}:/usr/src/app/webpagesaver/webpagesaver",
    # )
    podman(
        "exec",
        "-d",
        name,
        "chmod",
        "u+x",
        "/usr/src/app/compile_all",
        "/usr/src/app/run",
    )
    podman("exec", "-d", name, "bash", "/usr/local/bin/compile_all")
    podman("exec", name, "sh", "-c", f"echo {name} >> /usr/src/.about")
    podman("exec", name, "bash", "/usr/local/bin/_welcome_", name)


# pod go
def attach_container(group: str, version: str) -> None:
    """Show the container for this group/version.

    Start or create it if needed.
    """
    group, version = format(group, version)
    name = container_name(group, version)
    if get_state2(group, version) == State.NOT_FOUND:
        run_container(group, version)
    elif get_state2(group, version) == State.EXITED:
        podman("start", name)
    podman("attach", name)


def _remove_container(name: str, force: bool = False) -> bool:
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


# pod rm
def remove_container(group: str, version: str, force: bool = False) -> None:
    """
    Remove definitively a container.

    The `--force` argument must be last one, due to a limitation
    in the python-fire library.
    """
    print(repr(group), repr(version))
    group, version = format(group, version)
    _remove_container(container_name(group, version), force=force)


# pode purge
def purge_containers(version: str, force: bool = False) -> None:
    """Remove all containers for a given version."""
    print("Removing containers:")
    _, version = format("_", version)
    count = 0
    for name in containers_states():
        assert name.startswith(PREFIX)
        gp, vers = group_version(name)
        if vers == version:
            count += 1
            if get_state2(gp, vers) == State.UP:
                print_warning(
                    f"Container {name} is still running. Use pod go {gp} {vers} to show it."
                )
            remove_container(gp, vers, force=force)
    if count == 0:
        print_warning(f"No container found for version {version}.")


# pod purge-all
def purge_all_containers(force: bool = False) -> None:
    """Remove all containers."""
    print("Removing containers:")
    _remove_container(f"{PREFIX}-test", force=force)
    count = 0
    containers = containers_states()
    for name, state in containers.items():
        assert name.startswith(PREFIX)
        if state == State.UP:
            gp, vers = group_version(name)
            print_warning(
                f"Container {name} is still running. Use `pod go {gp} {vers}` to show it."
            )
        _remove_container(name, force=force)
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
