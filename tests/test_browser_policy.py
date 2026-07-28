from __future__ import annotations

from pathlib import Path

import pytest

from coworker.connectors.browser_policy import (
    BrowserPolicyError,
    resolve_workspace_path,
    validate_public_url,
)


def _resolve_to(address: str):
    def resolver(_host: str, port: int):
        return [(2, 1, 6, "", (address, port))]

    return resolver


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://localhost/admin",
        "http://service.local/private",
        "http://127.0.0.1:8080",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.8/",
        "https://user:secret@example.com/",
    ],
)
def test_public_url_policy_blocks_unsafe_destinations(url):
    with pytest.raises(BrowserPolicyError):
        validate_public_url(url, resolver=_resolve_to("93.184.216.34"))


def test_public_url_policy_blocks_hostname_resolving_to_private_address():
    with pytest.raises(BrowserPolicyError):
        validate_public_url(
            "https://internal.example.test/",
            resolver=_resolve_to("192.168.1.25"),
        )


def test_public_url_policy_accepts_public_https_address():
    assert (
        validate_public_url(
            "https://example.com/docs", resolver=_resolve_to("93.184.216.34")
        )
        == "https://example.com/docs"
    )


def test_workspace_path_cannot_escape_granted_root(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    inside = workspace / "brief.txt"
    inside.write_text("safe", encoding="utf-8")
    outside = tmp_path / "secret.txt"
    outside.write_text("private", encoding="utf-8")

    assert resolve_workspace_path(inside, [workspace], must_exist=True) == inside
    with pytest.raises(BrowserPolicyError):
        resolve_workspace_path(outside, [workspace], must_exist=True)


def test_browser_upload_rejects_files_outside_workspace_without_opening_browser(
    tmp_path,
):
    from coworker.connectors.browser_automation import make_browser_automation_tools

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "private.txt"
    outside.write_text("private", encoding="utf-8")
    tools = {
        tool.__name__: tool
        for tool in make_browser_automation_tools(roots=[Path(workspace)])
    }

    result = tools["browser_upload_file"]("input[type=file]", str(outside))
    assert result["error"] == "The file must be inside a granted workspace."


def test_browser_controllers_are_isolated_by_session():
    from coworker.connectors.browser_automation import (
        _browser_for,
        browser_close_session,
    )

    first = _browser_for("session-a")
    second = _browser_for("session-b")
    assert first is not second
    assert _browser_for("session-a") is first

    assert browser_close_session("session-a") == {"ok": True}
    assert _browser_for("session-b") is second
    assert _browser_for("session-a") is first


def test_native_browser_does_not_open_an_external_window():
    from coworker.connectors.browser_automation import BROWSER_LAUNCH_OPTIONS

    assert BROWSER_LAUNCH_OPTIONS["headless"] is True


def test_closing_browser_preserves_last_preview():
    from coworker.connectors.browser_automation import _BrowserController

    controller = _BrowserController()
    controller._touch(screenshot_data_url="data:image/png;base64,preview")

    assert controller.close() == {"ok": True}
    assert controller.state()["screenshot_data_url"].endswith("preview")


def test_browser_session_policy_normalizes_domains_and_limits_navigation():
    from coworker.connectors.browser_automation import _BrowserController

    controller = _BrowserController()
    result = controller.set_policy(
        always_allow_reads=False,
        allowed_domains=["https://Docs.Example.com/path", "example.org", "example.org"],
    )

    assert result == {
        "ok": True,
        "always_allow_reads": False,
        "allowed_domains": ["docs.example.com", "example.org"],
    }
    assert controller._navigation_allowed("https://docs.example.com/guide") is True
    assert controller._navigation_allowed("https://cdn.docs.example.com/file") is True
    assert controller._navigation_allowed("https://example.net/") is False


def test_browser_history_and_evidence_are_session_scoped():
    from coworker.connectors.browser_automation import _BrowserController

    class Page:
        url = "https://example.com/docs"

        @staticmethod
        def title():
            return "Example docs"

    controller = _BrowserController()
    controller._page = Page()
    controller._touch(screenshot_data_url="data:image/png;base64,evidence")
    controller._record_evidence("open_url")

    state = controller._state
    assert state["history"][0]["url"] == "https://example.com/docs"
    assert state["evidence"][0]["action"] == "open_url"
    assert len(state["evidence"][0]["screenshot_sha256"]) == 64


def test_snapshot_discovers_direct_media_variants():
    from coworker.connectors.browser_automation import _snapshot

    class Page:
        @staticmethod
        def evaluate(_script):
            return {
                "title": "Media",
                "url": "https://example.com/watch",
                "text": "Watch",
                "controls": [],
                "media": [
                    {
                        "id": "video-0-0",
                        "kind": "video",
                        "url": "https://cdn.example.com/movie.mp4",
                        "mime_type": "video/mp4",
                        "resolution": "1080p",
                        "width": 1920,
                        "height": 1080,
                    }
                ],
            }

    result = _snapshot(Page(), 100)
    assert result["media"][0]["resolution"] == "1080p"
