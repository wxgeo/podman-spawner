import hashlib
import socket


def port_from_name(name: str, start: int = 1024, end: int = 65535) -> int:
    """
    Derive a port number from a name via hashing, then scan forward
    until a free port is found.
    """
    # Hash the name to get a deterministic starting port
    hash_int = int(hashlib.sha256(name.encode()).hexdigest(), 16)
    base_port = start + (hash_int % (end - start))

    # Scan forward from the base port until we find a free one
    for offset in range(end - start):
        port = start + (base_port - start + offset) % (end - start)
        if _is_port_free(port):
            return port

    raise RuntimeError("No free port found in range")


def _is_port_free(port: int) -> bool:
    """Return True if both TCP and UDP are free on the given port."""
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
