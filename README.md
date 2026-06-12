# Podman Spawner — a Podman interface for container management

`pod` automates the creation and lifecycle management of [Podman](https://podman.io/)
containers, easing the creation of temporary podman images.

It was originally developed to review students projects, enabling to create containers on the fly for each student group
and submission version.

## Table of contents

- [Prerequisites](#prerequisites)
- [Using `pod`](#using-pod)

---

## Prerequisites

`pod` is a thin wrapper around Podman (a rootless Docker alternative).
Install it before anything else:

```sh
sudo apt install podman containers-storage
```

`containers-storage` is not strictly required, but it switches the storage
driver from `vfs` to `overlay`, which makes image builds significantly faster.
Verify it worked:

```sh
podman info | grep graphDriverName   # should print: overlay
```

To pull images from Docker Hub, register it as an unqualified search registry:

```sh
mkdir -p ~/.config/containers/
echo 'unqualified-search-registries = ["docker.io"]' >> ~/.config/containers/registries.conf
```

For a small Podman introduction, see [podman-intro.md](podman-intro.md).

---

## Using `pod`

### Installation

Install [uv](https://docs.astral.sh/uv/) if you do not have it already:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then, from the root of the `pod` repository:

```sh
uv tool install -e .
```

The `pod` command is now available for the current user.

### Configuration

Every `pod` command reads `config.toml` from the **current working directory**.
A default file is created by `pod init` (see below); its keys are:

| Key      | Default  | Description                                          |
|----------|----------|------------------------------------------------------|
| `prefix` | `POD`    | Prefix prepended to every container name.            |
| `port`   | `2026`   | Guest port exposed by the container.                 |
| `user`   | `tester` | Username created inside the container at build time. |

### Workflow overview

```
pod init        # create the pod-build/ scaffold
  ↓ (edit Dockerfile, home-dir/, on_build.bash as needed)
pod build       # build the Podman image
pod test        # smoke-test the image interactively
  ↓
pod go <name>   # open a container for a group / version
```

### Commands

#### `pod init`

Creates a `pod-build/` directory in the current directory (or uses the current
directory itself if it is already named `pod-build`), populated with a default
`Dockerfile`, `config.toml`, `on_build.bash`, and `home-dir/`.

```sh
pod init                      # create pod-build/ (fails if it already exists)
pod init --force              # overwrite an existing pod-build/
pod init --update Dockerfile  # refresh only one file, keeping local changes
```

#### `pod build`

Builds the Podman image from the `pod-build/` directory.
Must be run from inside `pod-build/` (or a directory that contains it).

```sh
pod build
```

The image is tagged `<prefix>:latest` (lower-cased), e.g. `pod:latest`.

#### `pod test`

Starts the dedicated test container (`<prefix>-test-0.0`) and attaches to it
interactively. Use this to verify that a freshly built image behaves correctly
before deploying it to students. The container is created if it does not exist.

```sh
pod test
```

#### `pod go <name>`

Attaches to a container, creating or restarting it as needed.

```sh
pod go GROUP-1.0
```

The host port is derived deterministically from the container name, so the
same container always gets the same port across restarts.

#### `pod list`

Lists all containers belonging to this project (filtered by prefix).

```sh
pod list
```

#### `pod info <name>`

Prints the state and port-forwarding details of a container.

```sh
pod info GROUP-1.0
```

#### `pod rm <name>`

Removes a container permanently.

```sh
pod rm GROUP-1.0           # fails if the container is still running
pod rm GROUP-1.0 --force   # stops and removes unconditionally
```

> **Note:** due to a limitation in python-fire, `--force` must come *after*
> the container name.

#### `pod purge <regex>`

Removes all containers whose full name matches `regex`
(matched with `re.fullmatch`, i.e. the pattern must cover the entire name
including the prefix).

```sh
pod purge 'POD-GROUP-1.*'           # remove all versions for GROUP-1
pod purge 'POD-GROUP-1.*' --force   # also remove running containers
```

#### `pod purge-all`

Removes every container belonging to this project, including the test container.

```sh
pod purge-all
pod purge-all --force
```


