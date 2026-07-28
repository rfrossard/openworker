from __future__ import annotations

import httpx

from coworker.connectors import browser_download


def test_downloads_discovered_media_to_workspace_without_overwriting(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(browser_download, "validate_public_url", lambda url: url)
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={"content-type": "video/mp4"},
                content=b"video-bytes",
                request=request,
            )
        )
    )
    source = {
        "url": "https://media.example/movie.mp4",
        "page_url": "https://example.com/watch",
        "kind": "video",
        "resolution": "1080p",
    }

    first = browser_download.download_media(source, tmp_path, client=client)
    second = browser_download.download_media(source, tmp_path, client=client)

    assert first["ok"] is True
    assert first["path"].endswith("movie-1080p.mp4")
    assert second["path"].endswith("movie-1080p-2.mp4")
    assert (tmp_path / "movie-1080p.mp4").read_bytes() == b"video-bytes"


def test_rejects_non_media_response(tmp_path, monkeypatch):
    monkeypatch.setattr(browser_download, "validate_public_url", lambda url: url)
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={"content-type": "text/html"},
                content=b"<html>not media</html>",
                request=request,
            )
        )
    )

    result = browser_download.download_media(
        {"url": "https://example.com/watch", "resolution": "Original"},
        tmp_path,
        client=client,
    )

    assert result["error"] == "The selected source did not return an audio or video file."
    assert not list(tmp_path.iterdir())


def test_validates_every_media_redirect(tmp_path, monkeypatch):
    checked: list[str] = []

    def validate(url: str) -> str:
        checked.append(url)
        if "private.example" in url:
            raise browser_download.BrowserPolicyError("blocked")
        return url

    monkeypatch.setattr(browser_download, "validate_public_url", validate)
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                302,
                headers={"location": "http://private.example/media.mp4"},
                request=request,
            )
        )
    )

    result = browser_download.download_media(
        {"url": "https://example.com/media.mp4"},
        tmp_path,
        client=client,
    )

    assert result == {"error": "blocked"}
    assert checked == [
        "https://example.com/media.mp4",
        "http://private.example/media.mp4",
    ]
