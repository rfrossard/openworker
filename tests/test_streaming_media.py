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

    def process_ie_result(self, info, download=False):
        self.info = info
        if download and self.on_download:
            self.on_download(self.options)
        return info


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


def test_analysis_forwards_ephemeral_browser_cookies_and_user_agent(monkeypatch):
    monkeypatch.setattr(streaming_media, "validate_public_url", lambda url: url)
    captured = {}

    def factory(options):
        captured.update(options)
        cookiefile = Path(options["cookiefile"])
        assert cookiefile.exists()
        assert "\tSID\tbrowser-cookie" in cookiefile.read_text()
        return FakeYDL(options, _video_info())

    result = streaming_media.analyze_streaming_media(
        "session-browser-auth",
        "https://example.com/watch",
        cookies=[
            {
                "domain": ".example.com",
                "path": "/",
                "secure": True,
                "expires": 0,
                "name": "SID",
                "value": "browser-cookie",
            }
        ],
        user_agent="OpenWorker Browser Test",
        ydl_factory=factory,
    )

    assert result["ok"] is True
    assert captured["http_headers"]["User-Agent"] == "OpenWorker Browser Test"
    assert not Path(captured["cookiefile"]).exists()


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


def test_missing_portuguese_track_uses_youtube_auto_translation(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(streaming_media, "validate_public_url", lambda url: url)
    info = _video_info()
    info["automatic_captions"] = {
        "en": [
            {
                "ext": "vtt",
                "url": "https://captions.example/timedtext?lang=en&fmt=vtt",
            }
        ]
    }
    analyzed = streaming_media.analyze_streaming_media(
        "session-translated-subs",
        "https://example.com/watch",
        ydl_factory=lambda options: FakeYDL(options, info),
    )
    monkeypatch.setattr(
        streaming_media,
        "_download_original_caption",
        lambda *_args: "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nHello\n",
    )
    monkeypatch.setattr(
        streaming_media,
        "_translate_vtt_locally",
        lambda _vtt, _language: (
            "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nOlá\n"
        ),
    )
    embedded = {}

    def embed(media, subtitle, language, _ffmpeg):
        embedded.update(
            {
                "media": media,
                "subtitle": subtitle.read_text(),
                "language": language,
            }
        )

    monkeypatch.setattr(streaming_media, "_embed_local_subtitle", embed)

    def create_output(_options):
        (tmp_path / "Example_video-1080p.mp4").write_bytes(b"translated")

    result = streaming_media.download_streaming_media(
        "session-translated-subs",
        analyzed["formats"][0]["id"],
        tmp_path,
        subtitle_language="pt",
        ydl_factory=lambda options: FakeYDL(
            options, info, on_download=create_output
        ),
        ffmpeg_path="/safe/ffmpeg",
    )

    assert result["ok"] is True
    assert embedded["language"] == "pt"
    assert "Olá" in embedded["subtitle"]


def test_selected_chat_model_is_preferred_for_subtitle_translation(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(streaming_media, "validate_public_url", lambda url: url)
    info = _video_info()
    info["automatic_captions"] = {
        "en": [
            {
                "ext": "vtt",
                "url": "https://captions.example/timedtext?lang=en&fmt=vtt",
            }
        ]
    }
    analyzed = streaming_media.analyze_streaming_media(
        "session-primary-translator",
        "https://example.com/watch",
        ydl_factory=lambda options: FakeYDL(options, info),
    )
    monkeypatch.setattr(
        streaming_media,
        "_download_original_caption",
        lambda *_args: "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nHello\n",
    )
    called = []

    def selected_model(batch, target):
        called.append((batch, target))
        return ["Olá pelo modelo selecionado"]

    monkeypatch.setattr(streaming_media, "_embed_local_subtitle", lambda *_args: None)

    def create_output(_options):
        (tmp_path / "Example_video-1080p.mp4").write_bytes(b"translated")

    result = streaming_media.download_streaming_media(
        "session-primary-translator",
        analyzed["formats"][0]["id"],
        tmp_path,
        subtitle_language="pt",
        subtitle_translator=selected_model,
        ydl_factory=lambda options: FakeYDL(
            options, info, on_download=create_output
        ),
        ffmpeg_path="/safe/ffmpeg",
    )

    assert result["ok"] is True
    assert called == [(["Hello"], "Brazilian Portuguese")]


def test_ollama_fallback_is_used_when_selected_model_fails(monkeypatch):
    class FakeClient:
        def get(self, *_args, **_kwargs):
            return FakeResponse({"models": [{"name": "qwen3:latest"}]})

        def post(self, *_args, **_kwargs):
            return FakeResponse(
                {"message": {"content": '{"translations":["Tradução local"]}'}}
            )

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    def unavailable_model(_batch, _target):
        raise RuntimeError("provider unavailable")

    translated = streaming_media._translate_vtt_locally(
        "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nHello\n",
        "pt",
        client=FakeClient(),
        primary_translator=unavailable_model,
    )

    assert "Tradução local" in translated


def test_subtitle_rate_limit_returns_login_and_retry_guidance(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(streaming_media, "validate_public_url", lambda url: url)
    analyzed = streaming_media.analyze_streaming_media(
        "session-rate-limit",
        "https://example.com/watch",
        ydl_factory=lambda options: FakeYDL(options, _video_info()),
    )

    class RateLimitedYDL(FakeYDL):
        def extract_info(self, _url, download=False):
            raise RuntimeError("HTTP Error 429: Too Many Requests")

    result = streaming_media.download_streaming_media(
        "session-rate-limit",
        analyzed["formats"][0]["id"],
        tmp_path,
        subtitle_language="pt",
        ydl_factory=lambda options: RateLimitedYDL(options, _video_info()),
        ffmpeg_path="/safe/ffmpeg",
    )

    assert result["error"] == (
        "YouTube temporarily rate-limited subtitle downloads. "
        "Sign in inside Secure Browser, analyze the page again, and retry."
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
