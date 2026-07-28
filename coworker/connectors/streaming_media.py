"""Safe yt-dlp integration for page-level streaming media analysis and downloads."""

from __future__ import annotations

import hashlib
import re
import threading
from pathlib import Path
from typing import Any, Callable, Optional

from .browser_download import MAX_MEDIA_BYTES
from .browser_policy import BrowserPolicyError, validate_public_url


_LOCK = threading.RLock()
_SELECTIONS: dict[str, dict[str, dict[str, Any]]] = {}
_FORMAT_ID = re.compile(r"^[A-Za-z0-9._-]+$")


class _QuietLogger:
    def debug(self, _message: str) -> None:
        pass

    def warning(self, _message: str) -> None:
        pass

    def error(self, _message: str) -> None:
        pass


def _youtube_dl_factory(options: dict[str, Any]):
    import yt_dlp

    return yt_dlp.YoutubeDL(options)


def _size(item: dict[str, Any]) -> int:
    return int(item.get("filesize") or item.get("filesize_approx") or 0)


def _label(item: dict[str, Any], kind: str) -> str:
    ext = str(item.get("ext") or "").upper()
    if kind == "audio":
        abr = int(item.get("abr") or item.get("tbr") or 0)
        return f"Audio · {ext or 'Original'}" + (f" · {abr} kbps" if abr else "")
    height = int(item.get("height") or 0)
    fps = int(item.get("fps") or 0)
    dynamic_range = str(item.get("dynamic_range") or "")
    quality = f"{height}p" if height else str(item.get("format_note") or "Original")
    if fps > 30:
        quality += f"{fps}"
    if dynamic_range and dynamic_range != "SDR":
        quality += f" {dynamic_range}"
    return f"Video · {quality} · {ext or 'Original'}"


def _normalized_formats(
    session_id: str, source_url: str, info: dict[str, Any]
) -> list[dict[str, Any]]:
    selections: dict[str, dict[str, Any]] = {}
    output: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    formats = [
        item
        for item in info.get("formats", [])
        if not item.get("has_drm") and item.get("url")
    ]
    formats.sort(
        key=lambda item: (
            item.get("vcodec") != "none",
            int(item.get("height") or 0),
            float(item.get("tbr") or 0),
        ),
        reverse=True,
    )
    for item in formats:
        format_id = str(item.get("format_id") or "")
        if not _FORMAT_ID.fullmatch(format_id):
            continue
        is_audio = item.get("vcodec") == "none" and item.get("acodec") != "none"
        is_video = item.get("vcodec") != "none"
        if not (is_audio or is_video):
            continue
        kind = "audio" if is_audio else "video"
        key = (
            kind,
            int(item.get("height") or 0),
            str(item.get("ext") or ""),
            int(item.get("fps") or 0),
            str(item.get("dynamic_range") or ""),
            round(float(item.get("abr") or 0)),
            item.get("acodec") != "none",
        )
        if key in seen:
            continue
        seen.add(key)
        selection_id = hashlib.sha256(
            f"{session_id}|{source_url}|{kind}|{format_id}".encode()
        ).hexdigest()[:20]
        selector = format_id
        if kind == "video" and item.get("acodec") == "none":
            selector = (
                f"{format_id}+bestaudio[ext=m4a]/"
                f"{format_id}+bestaudio/{format_id}"
            )
        selections[selection_id] = {
            "url": source_url,
            "format": selector,
            "kind": kind,
            "label": _label(item, kind),
            "resolution": (
                f"{int(item.get('height') or 0)}p"
                if item.get("height")
                else "Audio"
            ),
        }
        output.append(
            {
                "id": selection_id,
                "kind": kind,
                "label": selections[selection_id]["label"],
                "resolution": selections[selection_id]["resolution"],
                "ext": str(item.get("ext") or ""),
                "filesize": _size(item),
                "fps": int(item.get("fps") or 0),
                "audio_included": item.get("acodec") != "none",
            }
        )
        if len(output) >= 40:
            break
    with _LOCK:
        _SELECTIONS[session_id] = selections
    return output


def analyze_streaming_media(
    session_id: str,
    url: str,
    *,
    ydl_factory: Callable[[dict[str, Any]], Any] = _youtube_dl_factory,
) -> dict[str, Any]:
    try:
        source_url = validate_public_url(url)
    except BrowserPolicyError as exc:
        return {"error": str(exc)}
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "playlist_items": "1",
        "cachedir": False,
        "logger": _QuietLogger(),
        "extractor_retries": 2,
        "fragment_retries": 2,
        "socket_timeout": 20,
    }
    try:
        with ydl_factory(options) as ydl:
            info = ydl.extract_info(source_url, download=False)
    except Exception as exc:
        return {"error": f"Could not analyze this stream: {exc}"}
    if not isinstance(info, dict):
        return {"error": "The stream analyzer returned no media information."}
    if info.get("_type") in {"playlist", "multi_video"} or info.get("entries"):
        return {"error": "Playlists and multi-video downloads are not supported."}
    if info.get("is_live"):
        return {"error": "Live recording will be added in a later streaming phase."}
    formats = _normalized_formats(session_id, source_url, info)
    if not formats:
        if any(item.get("has_drm") for item in info.get("formats", [])):
            return {"error": "This media is protected by DRM and cannot be downloaded."}
        return {"error": "No downloadable audio or video formats were found."}
    return {
        "ok": True,
        "title": str(info.get("title") or ""),
        "duration": int(info.get("duration") or 0),
        "formats": formats,
    }


def _ffmpeg_path() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def download_streaming_media(
    session_id: str,
    selection_id: str,
    workspace: str | Path,
    *,
    ydl_factory: Callable[[dict[str, Any]], Any] = _youtube_dl_factory,
    ffmpeg_path: Optional[str] = None,
) -> dict[str, Any]:
    with _LOCK:
        selection = dict(_SELECTIONS.get(session_id, {}).get(selection_id, {}))
    if not selection:
        return {"error": "Analyze the current page again before downloading."}
    try:
        source_url = validate_public_url(selection["url"])
    except BrowserPolicyError as exc:
        return {"error": str(exc)}

    destination = Path(workspace).expanduser().resolve() / "OpenWorker Downloads"
    destination.mkdir(parents=True, exist_ok=True)
    before = {path.resolve() for path in destination.iterdir()}

    def progress(data: dict[str, Any]) -> None:
        downloaded = int(data.get("downloaded_bytes") or 0)
        total = int(data.get("total_bytes") or data.get("total_bytes_estimate") or 0)
        if downloaded > MAX_MEDIA_BYTES or total > MAX_MEDIA_BYTES:
            raise RuntimeError("The media file exceeds the 1 GB safety limit.")

    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "cachedir": False,
        "logger": _QuietLogger(),
        "format": selection["format"],
        "paths": {"home": str(destination), "temp": str(destination)},
        "outtmpl": {"default": "%(title).120B-%(height)sp.%(ext)s"},
        "restrictfilenames": True,
        "windowsfilenames": True,
        "overwrites": False,
        "continuedl": True,
        "merge_output_format": "mp4",
        "ffmpeg_location": ffmpeg_path or _ffmpeg_path(),
        "progress_hooks": [progress],
        "extractor_retries": 2,
        "fragment_retries": 3,
        "socket_timeout": 30,
    }
    try:
        with ydl_factory(options) as ydl:
            ydl.extract_info(source_url, download=True)
    except Exception as exc:
        for path in destination.iterdir():
            if path.resolve() not in before and path.suffix in {".part", ".ytdl"}:
                path.unlink(missing_ok=True)
        return {"error": f"Download failed: {exc}"}

    created = [
        path
        for path in destination.iterdir()
        if path.resolve() not in before
        and path.is_file()
        and path.suffix not in {".part", ".ytdl"}
    ]
    if not created:
        return {"error": "The downloader completed without producing a media file."}
    output = max(created, key=lambda path: path.stat().st_mtime)
    size = output.stat().st_size
    if size > MAX_MEDIA_BYTES:
        output.unlink(missing_ok=True)
        return {"error": "The completed media file exceeded the 1 GB safety limit."}
    return {
        "ok": True,
        "path": str(output),
        "bytes": size,
        "kind": selection["kind"],
        "resolution": selection["resolution"],
    }
