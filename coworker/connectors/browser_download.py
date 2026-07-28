"""Controlled downloads for direct audio/video sources found by Secure Browser."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote, urljoin, urlsplit

import httpx

from .browser_policy import BrowserPolicyError, validate_public_url


MAX_MEDIA_BYTES = 1024 * 1024 * 1024
MEDIA_EXTENSIONS = {
    ".aac",
    ".flac",
    ".m4a",
    ".m4v",
    ".mov",
    ".mp3",
    ".mp4",
    ".ogg",
    ".opus",
    ".wav",
    ".webm",
}
MIME_EXTENSIONS = {
    "audio/aac": ".aac",
    "audio/flac": ".flac",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/webm": ".webm",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
}


def _safe_filename(url: str, content_type: str, resolution: str) -> str:
    name = unquote(Path(urlsplit(url).path).name) or "media"
    name = re.sub(r"[^A-Za-z0-9._ -]+", "-", name).strip(" .-") or "media"
    suffix = Path(name).suffix.lower()
    if suffix not in MEDIA_EXTENSIONS:
        name = Path(name).stem or "media"
        suffix = MIME_EXTENSIONS.get(content_type, ".mp4")
    quality = re.sub(r"[^A-Za-z0-9._-]+", "-", resolution).strip("-")
    return f"{Path(name).stem}-{quality}{suffix}" if quality else f"{Path(name).stem}{suffix}"


def _unused_path(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    stem, suffix = candidate.stem, candidate.suffix
    index = 2
    while candidate.exists():
        candidate = directory / f"{stem}-{index}{suffix}"
        index += 1
    return candidate


def download_media(
    source: dict[str, Any],
    destination_directory: str | Path,
    *,
    cookies: Optional[list[dict[str, Any]]] = None,
    client: Optional[httpx.Client] = None,
) -> dict[str, Any]:
    """Download one discovered direct media URL into a controlled user-selected folder."""

    url = str(source.get("url") or "")
    try:
        current = validate_public_url(url)
    except BrowserPolicyError as exc:
        return {"error": str(exc)}

    owned_client = client is None
    jar = httpx.Cookies()
    for cookie in cookies or []:
        if cookie.get("name") and cookie.get("value"):
            jar.set(
                str(cookie["name"]),
                str(cookie["value"]),
                domain=str(cookie.get("domain") or "") or None,
                path=str(cookie.get("path") or "/"),
            )
    active_client = client or httpx.Client(
        cookies=jar,
        timeout=httpx.Timeout(30.0, read=120.0),
        follow_redirects=False,
    )
    try:
        for _ in range(6):
            with active_client.stream(
                "GET",
                current,
                headers={"Referer": str(source.get("page_url") or "")},
            ) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location", "")
                    if not location:
                        return {"error": "The media server returned an invalid redirect."}
                    try:
                        current = validate_public_url(urljoin(current, location))
                    except BrowserPolicyError as exc:
                        return {"error": str(exc)}
                    continue
                if response.status_code >= 400:
                    return {"error": f"Media download failed with HTTP {response.status_code}."}

                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                suffix = Path(urlsplit(current).path).suffix.lower()
                if not (
                    content_type.startswith(("audio/", "video/"))
                    or (
                        content_type == "application/octet-stream"
                        and suffix in MEDIA_EXTENSIONS
                    )
                ):
                    return {"error": "The selected source did not return an audio or video file."}
                try:
                    length = int(response.headers.get("content-length") or 0)
                except ValueError:
                    length = 0
                if length > MAX_MEDIA_BYTES:
                    return {"error": "The media file is larger than the 1 GB safety limit."}

                destination = Path(destination_directory).expanduser().resolve()
                destination.mkdir(parents=True, exist_ok=True)
                output = _unused_path(
                    destination,
                    _safe_filename(
                        current,
                        content_type,
                        str(source.get("resolution") or ""),
                    ),
                )
                partial = output.with_suffix(output.suffix + ".part")
                total = 0
                try:
                    with partial.open("xb") as stream:
                        for chunk in response.iter_bytes():
                            total += len(chunk)
                            if total > MAX_MEDIA_BYTES:
                                raise ValueError("The media file exceeded the 1 GB safety limit.")
                            stream.write(chunk)
                    partial.replace(output)
                except Exception as exc:
                    partial.unlink(missing_ok=True)
                    return {"error": str(exc)}
                return {
                    "ok": True,
                    "path": str(output),
                    "bytes": total,
                    "kind": source.get("kind", "media"),
                    "resolution": source.get("resolution", "Original"),
                }
        return {"error": "The media server returned too many redirects."}
    finally:
        if owned_client:
            active_client.close()
