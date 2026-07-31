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


class _ActionLocator:
    def __init__(self, page):
        self.page = page

    @property
    def first(self):
        return self

    def count(self):
        return self.page.match_count

    def evaluate(self, _script):
        return {
            "tag": self.page.tag,
            "type": self.page.input_type,
            "id": self.page.element_id,
            "name": self.page.name,
            "role": "",
            "href": "",
            "autocomplete": self.page.autocomplete,
            "placeholder": self.page.placeholder,
            "label": self.page.label,
            "text": self.page.label,
            "currentValue": self.page.current_value,
            "disabled": False,
            "visible": True,
            "box": {"x": 80, "y": 120, "width": 160, "height": 44},
            "viewport": {"width": 1280, "height": 900},
        }

    def click(self, timeout=0):
        self.page.clicked += 1

    def fill(self, text, timeout=0):
        self.page.current_value = text
        self.page.typed.append(("fill", text))

    def type(self, text, timeout=0):
        self.page.current_value += text
        self.page.typed.append(("type", text))


class _ActionPage:
    url = "https://example.com/form"

    def __init__(self):
        self.label = "Save draft"
        self.tag = "button"
        self.input_type = ""
        self.element_id = "save"
        self.name = ""
        self.autocomplete = ""
        self.placeholder = ""
        self.current_value = ""
        self.match_count = 1
        self.clicked = 0
        self.typed = []
        self.screenshot_masks = []

    def locator(self, _target):
        return _ActionLocator(self)

    def get_by_text(self, _target, exact=False):
        return _ActionLocator(self)

    def get_by_role(self, _role, name=None):
        return _ActionLocator(self)

    def screenshot(self, full_page=False, mask=None, mask_color=None):
        self.screenshot_masks.append(len(mask or []))
        return b"preview"

    def title(self):
        return "Example form"


def test_browser_click_rejects_a_target_that_changed_after_approval():
    from coworker.connectors.browser_automation import _BrowserController

    page = _ActionPage()
    controller = _BrowserController()
    controller._page = page

    proposal = controller.propose_action(
        tool_call_id="call-1",
        tool_name="browser_click",
        arguments={"target": "#save"},
    )
    assert proposal["label"] == "Save draft"
    assert proposal["box"] == {"x": 80, "y": 120, "width": 160, "height": 44}
    assert "fingerprint" not in proposal

    controller.resolve_action("call-1", "once")
    page.label = "Delete account"

    result = controller.validate_action("browser_click", "#save")

    assert result == {
        "error": (
            "The page changed before the action ran. Review the new target "
            "and approve it again."
        )
    }
    assert controller._state["pending_action"]["status"] == "stale"
    assert page.clicked == 0


def test_browser_action_proposal_rejects_an_ambiguous_target():
    from coworker.connectors.browser_automation import _BrowserController

    page = _ActionPage()
    page.match_count = 2
    controller = _BrowserController()
    controller._page = page

    proposal = controller.propose_action(
        tool_call_id="call-ambiguous",
        tool_name="browser_click",
        arguments={"target": "text=Continue"},
    )

    assert proposal["status"] == "pending"
    assert proposal["match_count"] == 2
    assert proposal["error"] == "The proposed browser target is no longer unique."


def test_browser_action_denial_clears_the_pending_target():
    from coworker.connectors.browser_automation import _BrowserController

    controller = _BrowserController()
    controller._page = _ActionPage()
    controller.propose_action(
        tool_call_id="call-denied",
        tool_name="browser_click",
        arguments={"target": "#save"},
    )

    controller.resolve_action("call-denied", "deny")

    assert controller._state["pending_action"] == {}


def test_browser_click_tool_fails_closed_without_clicking_a_stale_target():
    from coworker.connectors.browser_automation import (
        _browser_for,
        make_browser_automation_tools,
    )

    session_id = "stale-action-tool"
    page = _ActionPage()
    controller = _browser_for(session_id)
    controller._page = page
    controller.propose_action(
        tool_call_id="call-tool",
        tool_name="browser_click",
        arguments={"target": "#save"},
    )
    controller.resolve_action("call-tool", "once")
    page.label = "Delete account"
    tools = {
        tool.__name__: tool
        for tool in make_browser_automation_tools(session_id=session_id)
    }

    result = tools["browser_click"]("#save")

    assert result["error"].startswith("The page changed before the action ran.")
    assert page.clicked == 0


def test_browser_type_proposal_redacts_sensitive_content_and_masks_preview():
    from coworker.connectors.browser_automation import (
        _browser_for,
        make_browser_automation_tools,
    )

    session_id = "sensitive-type-tool"
    secret = "example-sensitive-value-that-must-never-appear"
    page = _ActionPage()
    page.tag = "input"
    page.input_type = "password"
    page.element_id = "account-password"
    page.name = "password"
    page.autocomplete = "current-password"
    page.label = "Account password"
    controller = _browser_for(session_id)
    controller._page = page

    proposal = controller.propose_action(
        tool_call_id="call-type",
        tool_name="browser_type",
        arguments={"target": "#account-password", "text": secret, "clear": True},
    )

    assert proposal["action"] == "Type"
    assert proposal["risk"] == "Sensitive input"
    assert proposal["content_summary"] == "Content hidden for privacy."
    assert secret not in repr(proposal)
    assert secret not in repr(controller._state["pending_action"])

    controller.resolve_action("call-type", "once")
    tools = {
        tool.__name__: tool
        for tool in make_browser_automation_tools(session_id=session_id)
    }
    result = tools["browser_type"]("#account-password", secret)

    assert result["ok"] is True
    assert page.current_value == secret
    assert page.screenshot_masks[-1] == 1
    assert controller._state["pending_action"] == {}


def test_browser_type_rejects_when_existing_input_changed_after_approval():
    from coworker.connectors.browser_automation import _BrowserController

    page = _ActionPage()
    page.tag = "input"
    page.element_id = "search"
    page.label = "Search"
    page.current_value = "original"
    controller = _BrowserController()
    controller._page = page
    controller.propose_action(
        tool_call_id="call-input-change",
        tool_name="browser_type",
        arguments={"target": "#search", "text": "approved text", "clear": True},
    )
    controller.resolve_action("call-input-change", "once")
    page.current_value = "changed elsewhere"

    result = controller.validate_action("browser_type", "#search")

    assert result and result["error"].startswith(
        "The page changed before the action ran."
    )
    assert page.typed == []


def test_browser_type_arguments_are_redacted_for_ui_and_persistence():
    from coworker.audit import redact_tool_arguments
    from coworker.engine import PermissionRequest
    from coworker.server.manager import _approval_body

    secret = "do-not-render-this-value"
    request = PermissionRequest(
        tool_name="browser_type",
        arguments={"target": "#token", "text": secret, "clear": True},
        metadata=None,
        reason="requires approval",
        tool_call_id="call-redaction",
    )
    safe = redact_tool_arguments(request.tool_name, request.arguments)

    assert safe == {
        "target": "#token",
        "text": "[redacted input]",
        "clear": True,
    }
    assert secret not in _approval_body(request)


def test_browser_type_denial_and_two_sessions_remain_isolated():
    from coworker.connectors.browser_automation import (
        _browser_for,
        make_browser_automation_tools,
    )

    first = _browser_for("type-isolation-first")
    second = _browser_for("type-isolation-second")
    first_page = _ActionPage()
    second_page = _ActionPage()
    for page in (first_page, second_page):
        page.tag = "input"
        page.element_id = "note"
        page.label = "Private note"
    first._page = first_page
    second._page = second_page
    first.propose_action(
        tool_call_id="call-first",
        tool_name="browser_type",
        arguments={"target": "#note", "text": "first value"},
    )
    second.propose_action(
        tool_call_id="call-second",
        tool_name="browser_type",
        arguments={"target": "#note", "text": "second value"},
    )

    first.resolve_action("call-first", "deny")
    second.resolve_action("call-second", "once")
    second_tools = {
        tool.__name__: tool
        for tool in make_browser_automation_tools(session_id="type-isolation-second")
    }
    result = second_tools["browser_type"]("#note", "second value")

    assert result["ok"] is True
    assert first_page.current_value == ""
    assert second_page.current_value == "second value"
    assert first._state["pending_action"] == {}
    assert second._state["pending_action"] == {}
