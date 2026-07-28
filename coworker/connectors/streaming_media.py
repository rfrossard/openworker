"""Safe yt-dlp integration for page-level streaming media analysis and downloads."""

from __future__ import annotations

import hashlib
import re
import threading
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .browser_download import MAX_MEDIA_BYTES, MEDIA_EXTENSIONS
from .browser_policy import BrowserPolicyError, validate_public_url


_LOCK = threading.RLock()
_SELECTIONS: dict[str, dict[str, dict[str, Any]]] = {}
_FORMAT_ID = re.compile(r"^[A-Za-z0-9._-]+$")
_SUBTITLE_LANGUAGES = {"en", "pt", "es"}


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


def _subtitle_choices(info: dict[str, Any]) -> dict[str, str]:
    """Choose one concrete manual/automatic subtitle track for each UI language."""
    tracks: list[str] = []
    for source in ("subtitles", "automatic_captions"):
        values = info.get(source)
        if isinstance(values, dict):
            tracks.extend(str(key) for key in values if str(key) not in tracks)
    choices: dict[str, str] = {}
    for language in _SUBTITLE_LANGUAGES:
        matches = [
            track
            for track in tracks
            if track.lower() == language
            or track.lower().startswith((f"{language}-", f"{language}_", f"{language}."))
        ]
        if matches:
            choices[language] = min(
                matches,
                key=lambda track: (
                    track.lower() != language,
                    track.lower().endswith("-orig") is False,
                    len(track),
                ),
            )
    return choices


def _translated_subtitles(
    info: dict[str, Any], choices: dict[str, str]
) -> dict[str, dict[str, Any]]:
    """Build yt-dlp caption records for YouTube's supported auto-translation fallback."""
    automatic = info.get("automatic_captions")
    if not isinstance(automatic, dict):
        return {}
    source_language = choices.get("en")
    source_formats = automatic.get(source_language) if source_language else None
    if not isinstance(source_formats, list):
        return {}
    source = next(
        (
            item
            for item in source_formats
            if isinstance(item, dict)
            and item.get("url")
            and str(item.get("ext") or "") == "vtt"
        ),
        None,
    )
    if not source:
        return {}
    translated: dict[str, dict[str, Any]] = {}
    for language in ("pt", "es"):
        if language in choices:
            continue
        parts = urlsplit(str(source["url"]))
        query = [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key != "tlang"
        ]
        query.append(("tlang", language))
        translated[language] = {
            **source,
            "url": urlunsplit(
                (
                    parts.scheme,
                    parts.netloc,
                    parts.path,
                    urlencode(query),
                    parts.fragment,
                )
            ),
            "ext": "vtt",
            "name": f"{language.upper()} (auto-translated)",
        }
    return translated


def _normalized_formats(
    session_id: str, source_url: str, info: dict[str, Any]
) -> list[dict[str, Any]]:
    selections: dict[str, dict[str, Any]] = {}
    output: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    subtitle_choices = _subtitle_choices(info)
    translated_subtitles = _translated_subtitles(info, subtitle_choices)
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
            "subtitles": subtitle_choices,
            "translated_subtitles": translated_subtitles,
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
    destination_directory: str | Path,
    *,
    subtitle_language: str = "",
    ydl_factory: Callable[[dict[str, Any]], Any] = _youtube_dl_factory,
    ffmpeg_path: Optional[str] = None,
) -> dict[str, Any]:
    with _LOCK:
        selection = dict(_SELECTIONS.get(session_id, {}).get(selection_id, {}))
    if not selection:
        return {"error": "Analyze the current page again before downloading."}
    subtitle_language = (subtitle_language or "").strip().lower()
    if subtitle_language and subtitle_language not in _SUBTITLE_LANGUAGES:
        return {"error": "Subtitle language must be English, Portuguese, or Spanish."}
    if subtitle_language and selection.get("kind") != "video":
        return {"error": "Subtitles can only be embedded in video downloads."}
    subtitle_track = (
        dict(selection.get("subtitles") or {}).get(subtitle_language)
        if subtitle_language
        else ""
    )
    translated_subtitle = (
        dict(selection.get("translated_subtitles") or {}).get(subtitle_language)
        if subtitle_language
        else None
    )
    if subtitle_language and not subtitle_track and not translated_subtitle:
        return {
            "error": (
                "The selected subtitle language is not available for this video, "
                "including automatic captions."
            )
        }
    if translated_subtitle:
        try:
            translated_subtitle["url"] = validate_public_url(
                str(translated_subtitle.get("url") or "")
            )
        except BrowserPolicyError as exc:
            return {"error": str(exc)}
        subtitle_track = subtitle_language
    try:
        source_url = validate_public_url(selection["url"])
    except BrowserPolicyError as exc:
        return {"error": str(exc)}

    destination = Path(destination_directory).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    before = {path.resolve() for path in destination.iterdir()}
    reported_paths: set[Path] = set()

    def remember_path(value: Any) -> None:
        if not isinstance(value, (str, Path)) or not value:
            return
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = destination / candidate
        try:
            resolved = candidate.resolve()
            resolved.relative_to(destination)
        except (OSError, ValueError):
            return
        reported_paths.add(resolved)

    def progress(data: dict[str, Any]) -> None:
        remember_path(data.get("filename"))
        info = data.get("info_dict")
        if isinstance(info, dict):
            remember_path(info.get("filepath"))
            remember_path(info.get("_filename"))
        downloaded = int(data.get("downloaded_bytes") or 0)
        total = int(data.get("total_bytes") or data.get("total_bytes_estimate") or 0)
        if downloaded > MAX_MEDIA_BYTES or total > MAX_MEDIA_BYTES:
            raise RuntimeError("The media file exceeds the 1 GB safety limit.")

    def postprocessor(data: dict[str, Any]) -> None:
        info = data.get("info_dict")
        if isinstance(info, dict):
            remember_path(info.get("filepath"))
            remember_path(info.get("_filename"))

    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "cachedir": False,
        "logger": _QuietLogger(),
        "format": selection["format"],
        "paths": {"home": str(destination), "temp": str(destination)},
        "outtmpl": {
            "default": (
                f"%(title).120B-%(height)sp-{subtitle_language}.%(ext)s"
                if subtitle_language
                else "%(title).120B-%(height)sp.%(ext)s"
            )
        },
        "restrictfilenames": True,
        "windowsfilenames": True,
        "overwrites": False,
        "continuedl": True,
        "merge_output_format": "mp4",
        "ffmpeg_location": ffmpeg_path or _ffmpeg_path(),
        "progress_hooks": [progress],
        "postprocessor_hooks": [postprocessor],
        "extractor_retries": 2,
        "fragment_retries": 3,
        "socket_timeout": 30,
    }
    if subtitle_language:
        options.update(
            {
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": [subtitle_track],
                "subtitlesformat": "vtt/best",
                "embedsubtitles": True,
                "postprocessors": [
                    {
                        "key": "FFmpegEmbedSubtitle",
                        "already_have_subtitle": False,
                    }
                ],
            }
        )
    try:
        with ydl_factory(options) as ydl:
            if translated_subtitle:
                info = ydl.extract_info(source_url, download=False)
                if not isinstance(info, dict):
                    return {"error": "The stream analyzer returned no media information."}
                subtitles = dict(info.get("subtitles") or {})
                subtitles[subtitle_language] = [translated_subtitle]
                info["subtitles"] = subtitles
                info = ydl.process_ie_result(info, download=True)
            else:
                info = ydl.extract_info(source_url, download=True)
            if isinstance(info, dict):
                remember_path(info.get("filepath"))
                remember_path(info.get("_filename"))
                for item in info.get("requested_downloads") or []:
                    if isinstance(item, dict):
                        remember_path(item.get("filepath"))
                        remember_path(item.get("_filename"))
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
        and path.suffix.lower() in MEDIA_EXTENSIONS
    ]
    reported = [
        path
        for path in reported_paths
        if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS
    ]
    candidates = created or reported
    if not candidates:
        return {"error": "The downloader completed without producing a media file."}
    output = max(candidates, key=lambda path: path.stat().st_mtime)
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
