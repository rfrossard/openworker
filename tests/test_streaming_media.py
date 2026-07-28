from __future__ import annotations

from pathlib import Path

from coworker.connectors import streaming_media


class FakeYDL:
    def __init__(self, options, info, on_download=None):
        self.options = options
        self.info = info
        self.on_download = on_download

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def extract_info(self, _url, download=False):
        if download and self.on_download:
            self.on_download(self.options)
        return self.info


def _video_info():
    return {
        "title": "Example video",
        "duration": 120,
        "subtitles": {"en": [{"ext": "vtt"}]},
        "automatic_captions": {
            "pt-BR": [{"ext": "vtt"}],
            "es-419": [{"ext": "vtt"}],
        },
        "formats": [
            {
                "format_id": "137",
                "url": "https://cdn.example/video",
                "ext": "mp4",
                "height": 1080,
                "width": 1920,
                "fps": 30,
                "vcodec": "avc1",
                "acodec": "none",
                "filesize_approx": 50_000_000,
            },
            {
                "format_id": "18",
                "url": "https://cdn.example/combined",
                "ext": "mp4",
                "height": 360,
                "width": 640,
                "fps": 30,
                "vcodec": "avc1",
                "acodec": "mp4a",
                "filesize": 10_000_000,
            },
            {
                "format_id": "140",
                "url": "https://cdn.example/audio",
                "ext": "m4a",
                "vcodec": "none",
                "acodec": "mp4a",
                "abr": 129,
            },
        ],
    }


def test_analyzes_video_and_audio_formats_without_downloading(monkeypatch):
    monkeypatch.setattr(streaming_media, "validate_public_url", lambda url: url)
    captured = {}

    def factory(options):
        captured.update(options)
        return FakeYDL(options, _video_info())

    result = streaming_media.analyze_streaming_media(
        "session-a",
        "https://example.com/watch",
        ydl_factory=factory,
    )

    assert result["ok"] is True
    assert [item["kind"] for item in result["formats"]] == ["video", "video", "audio"]
    assert result["formats"][0]["resolution"] == "1080p"
    assert captured["skip_download"] is True
    assert captured["noplaylist"] is True


def test_blocks_drm_only_media(monkeypatch):
    monkeypatch.setattr(streaming_media, "validate_public_url", lambda url: url)
    info = {
        "formats": [
            {
                "format_id": "drm",
                "url": "https://cdn.example/protected",
                "vcodec": "avc1",
                "acodec": "mp4a",
                "has_drm": True,
            }
        ]
    }
    result = streaming_media.analyze_streaming_media(
        "session-drm",
        "https://example.com/watch",
        ydl_factory=lambda options: FakeYDL(options, info),
    )
    assert result["error"] == "This media is protected by DRM and cannot be downloaded."


def test_download_uses_server_owned_selection_and_controlled_output(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(streaming_media, "validate_public_url", lambda url: url)
    analyzed = streaming_media.analyze_streaming_media(
        "session-download",
        "https://example.com/watch",
        ydl_factory=lambda options: FakeYDL(options, _video_info()),
    )
    selection = analyzed["formats"][0]

    def create_output(options):
        destination = Path(options["paths"]["home"])
        (destination / "Example_video-1080p.mp4").write_bytes(b"downloaded")

    result = streaming_media.download_streaming_media(
        "session-download",
        selection["id"],
        tmp_path,
        ydl_factory=lambda options: FakeYDL(
            options, _video_info(), on_download=create_output
        ),
        ffmpeg_path="/safe/ffmpeg",
    )

    assert result["ok"] is True
    assert result["path"].endswith("Example_video-1080p.mp4")
    assert Path(result["path"]).read_bytes() == b"downloaded"


def test_rejects_unknown_or_stale_selection(tmp_path):
    result = streaming_media.download_streaming_media(
        "unknown-session", "user-controlled-format", tmp_path
    )
    assert result["error"] == "Analyze the current page again before downloading."


def test_video_download_embeds_requested_supported_subtitle(tmp_path, monkeypatch):
    monkeypatch.setattr(streaming_media, "validate_public_url", lambda url: url)
    analyzed = streaming_media.analyze_streaming_media(
        "session-subs",
        "https://example.com/watch",
        ydl_factory=lambda options: FakeYDL(options, _video_info()),
    )
    selection = analyzed["formats"][0]
    captured = {}

    def create_output(options):
        captured.update(options)
        (tmp_path / "Example_video-1080p.mp4").write_bytes(b"subtitled")

    result = streaming_media.download_streaming_media(
        "session-subs",
        selection["id"],
        tmp_path,
        subtitle_language="pt",
        ydl_factory=lambda options: FakeYDL(
            options, _video_info(), on_download=create_output
        ),
        ffmpeg_path="/safe/ffmpeg",
    )

    assert result["ok"] is True
    assert captured["writesubtitles"] is True
    assert captured["writeautomaticsub"] is True
    assert captured["embedsubtitles"] is True
    assert captured["subtitleslangs"] == ["pt-BR"]
    assert captured["postprocessors"] == [
        {"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False}
    ]


def test_rejects_unsupported_subtitle_language(tmp_path, monkeypatch):
    monkeypatch.setattr(streaming_media, "validate_public_url", lambda url: url)
    analyzed = streaming_media.analyze_streaming_media(
        "session-bad-subs",
        "https://example.com/watch",
        ydl_factory=lambda options: FakeYDL(options, _video_info()),
    )
    result = streaming_media.download_streaming_media(
        "session-bad-subs",
        analyzed["formats"][0]["id"],
        tmp_path,
        subtitle_language="fr",
    )
    assert result["error"] == (
        "Subtitle language must be English, Portuguese, or Spanish."
    )


def test_download_recognizes_an_existing_file_reported_by_downloader(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(streaming_media, "validate_public_url", lambda url: url)
    analyzed = streaming_media.analyze_streaming_media(
        "session-existing",
        "https://example.com/watch",
        ydl_factory=lambda options: FakeYDL(options, _video_info()),
    )
    selection = analyzed["formats"][1]
    destination = tmp_path
    existing = destination / "Example_video-360p.mp4"
    existing.write_bytes(b"already downloaded")

    def report_existing(options):
        options["progress_hooks"][0](
            {
                "status": "finished",
                "filename": str(existing),
                "downloaded_bytes": existing.stat().st_size,
            }
        )

    result = streaming_media.download_streaming_media(
        "session-existing",
        selection["id"],
        tmp_path,
        ydl_factory=lambda options: FakeYDL(
            options, _video_info(), on_download=report_existing
        ),
        ffmpeg_path="/safe/ffmpeg",
    )

    assert result["ok"] is True
    assert result["path"] == str(existing)
