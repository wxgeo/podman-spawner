# Small introduction to Podman

Podman is used almost identically to Docker, but runs without root privileges.

## Building an image

Images are built from a `Dockerfile`. The default one shipped with `pod` starts
from a minimal Debian (bitnami/minideb:trixie) and installs a Java development
environment. To build manually, go to the directory containing the `Dockerfile`:

```sh
podman build -t sae:latest .
```

To test the image interactively (with X11 forwarding for graphical apps):

```sh
podman run -it --rm --env="DISPLAY" --net=host sae:latest
```

`podman images` lists all local images, including the intermediate layer images
created during the build. To find a specific one:

```sh
podman images | grep localhost/sae
```

## Starting a container

Run a container in the background from an image:

```sh
podman run -d -t --name HELLO localhost/sae:latest
```

List running containers:

```sh
podman ps
podman ps -a            # include stopped containers
podman ps | grep sae    # filter by image name
```

Restart a stopped container:

```sh
podman start HELLO
podman attach HELLO     # re-attach to its terminal
```

## Copying files

Copy a local directory into a running container:

```sh
podman cp ./submissions/group-1/. HELLO:/home/tester/
```

The trailing `/.` copies the *contents* of the directory rather than the
directory itself (Docker/Podman convention).

## Stopping and removing containers

```sh
podman stop HELLO       # graceful stop
podman kill HELLO       # immediate stop
podman rm HELLO         # remove a stopped container
podman rm -f HELLO      # stop and remove in one step
```

Remove all stopped containers at once:

```sh
podman container prune
```

## Port forwarding

To expose a port from the container on the host:

```sh
podman run -d -t --publish 8080:2026 --name HELLO localhost/sae:latest
```

This maps port `2026` inside the container to port `8080` on the host.
Inspect active port mappings with:

```sh
podman port HELLO
```