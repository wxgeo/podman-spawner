"""Deterministic port allocation.

Derives a stable host port from a container name so that the same container
always gets the same port across restarts, while avoiding collisions with
ports already in use on the host.
"""

import hashlib
import socket


def port_from_name(name: str, start: int = 1024, end: int = 65535) -> int:
    """Derive a free host port from ``name``.

    Uses SHA-256 to map ``name`` to a deterministic starting point in
    ``[start, end)``, then scans forward (wrapping around) until a port that
    is free on both TCP and UDP is found.

    The determinism guarantee means the same container name always resolves to
    the same base port, making port assignments stable and predictable for
    operators and students alike.

    Raises:
        RuntimeError: If every port in the range is occupied.
    """
    if not isinstance(name, str):
        raise ValueError(f"Name must be a string, not {type(name)}.")
    hash_int = int(hashlib.sha256(name.encode()).hexdigest(), 16)
    base_port = start + (hash_int % (end - start) if end - start else 0)

    for offset in range(end - start):
        port = start + (base_port - start + offset) % (end - start)
        if _is_port_free(port):
            return port

    raise RuntimeError("No free port found in range")


def _is_port_free(port: int) -> bool:
    """Return ``True`` if ``port`` is available on both TCP and UDP."""
    for kind in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
        with socket.socket(socket.AF_INET, kind) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("", port))
            except OSError:
                return False
    return True


if __name__ == "__main__":
    for _name in ("my-service", "postgres", "redis"):
        _port = port_from_name(_name)
        print(f"{_name!r:20} → port {_port}")
