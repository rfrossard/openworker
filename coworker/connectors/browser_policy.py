"""Security boundaries shared by browser-based connector tools."""

from __future__ import annotations

import ipaddress
import socket
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import urlsplit


class BrowserPolicyError(ValueError):
    """Raised when a browser operation crosses a configured safety boundary."""


def _is_public_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError:
        return False
    return address.is_global


def validate_public_url(
    url: str,
    *,
    resolver: Callable[..., list[Any]] = socket.getaddrinfo,
) -> str:
    """Return a normalized public HTTP(S) URL or raise ``BrowserPolicyError``.

    Resolving before navigation blocks localhost aliases and hostnames that point at
    private, loopback, link-local, reserved, or metadata-service address space.
    """

    value = str(url or "").strip()
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise BrowserPolicyError("Only public http:// and https:// URLs are allowed.")
    if not parsed.hostname:
        raise BrowserPolicyError("The URL must include a public hostname.")
    if parsed.username or parsed.password:
        raise BrowserPolicyError("Credentials embedded in URLs are not allowed.")

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith((".localhost", ".local")):
        raise BrowserPolicyError("Local and private network addresses are blocked.")

    try:
        literal = ipaddress.ip_address(hostname.split("%", 1)[0])
    except ValueError:
        literal = None
    if literal is not None:
        if not literal.is_global:
            raise BrowserPolicyError("Local and private network addresses are blocked.")
        return value

    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        answers = resolver(hostname, port)
    except (OSError, socket.gaierror) as exc:
        raise BrowserPolicyError(f"Could not resolve the destination host: {hostname}") from exc
    addresses = {str(answer[4][0]) for answer in answers if len(answer) > 4 and answer[4]}
    if not addresses or any(not _is_public_address(address) for address in addresses):
        raise BrowserPolicyError("Local and private network addresses are blocked.")
    return value


def resolve_workspace_path(
    value: str | Path,
    roots: Iterable[str | Path],
    *,
    must_exist: bool = False,
) -> Path:
    """Resolve a file path and require it to stay inside one granted workspace root."""

    path = Path(value).expanduser().resolve()
    allowed = [
        Path(getattr(root, "path", root)).expanduser().resolve()
        for root in roots
        if root
    ]
    if not allowed or not any(path == root or path.is_relative_to(root) for root in allowed):
        raise BrowserPolicyError("The file must be inside a granted workspace.")
    if must_exist and not path.is_file():
        raise BrowserPolicyError(f"File not found: {path}")
    return path
