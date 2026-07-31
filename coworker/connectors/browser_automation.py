"""Playwright-backed browser automation tools for Cowork.

The dependency is optional. If Playwright or its browser binaries are not installed, the
tools return a clear setup error instead of breaking engine construction.
"""

from __future__ import annotations

import re
import tempfile
import threading
import time
import base64
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlsplit

import aisuite as ai

from .browser_policy import BrowserPolicyError, resolve_workspace_path, validate_public_url


BROWSER_LAUNCH_OPTIONS = {"headless": True}


def _prepare_packaged_browsers() -> None:
    """Extract the signed packaged browser tree once and point Playwright at it."""

    import playwright

    archive = (
        Path(playwright.__file__).resolve().parent
        / "driver"
        / "package"
        / "playwright-browsers.tar.gz"
    )
    if not archive.is_file():
        return
    checksum = hashlib.sha256()
    with archive.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    digest = checksum.hexdigest()[:16]
    cache_root = (
        Path.home()
        / "Library"
        / "Caches"
        / "OpenWorker"
        / "secure-browser"
        / digest
    )
    marker = cache_root / ".ready"
    if not marker.is_file():
        cache_root.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f"{digest}-", dir=cache_root.parent))
        try:
            try:
                with tarfile.open(archive, "r:gz") as bundle:
                    bundle.extractall(staging, filter="data")
            except (OSError, tarfile.TarError, zlib.error):
                system_tar = shutil.which("tar")
                if not system_tar:
                    raise
                subprocess.run(
                    [system_tar, "-xzf", str(archive), "-C", str(staging)],
                    check=True,
                    capture_output=True,
                )
            (staging / ".ready").write_text(digest, encoding="utf-8")
            if cache_root.exists():
                shutil.rmtree(cache_root)
            staging.replace(cache_root)
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(cache_root)


def _meta(
    name: str, *, approval: bool = False, capabilities: Optional[list[str]] = None
):
    return ai.ToolMetadata(
        name=name,
        category="connector",
        risk_level="medium" if approval else "low",
        capabilities=capabilities or ["browser"],
        requires_approval=approval,
    )


def _schema(
    name: str, description: str, properties: dict[str, Any], required: list[str]
) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def _attach(fn: Callable[..., Any], schema: dict[str, Any], *, approval: bool = True):
    from .tool_defs import approval_for_tool

    name = schema["function"]["name"]
    # §36: the tool registry's read/write kind wins for registered tools — reads never gate.
    approval = approval_for_tool(name, default=approval)
    fn.__coworker_schema__ = schema
    fn.__aisuite_tool_metadata__ = _meta(name, approval=approval)
    fn.__doc__ = schema["function"]["description"]
    return fn


class _BrowserController:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._error: Optional[str] = None
        self._sensitive_targets: set[str] = set()
        self._workspace_roots: list[Any] = []
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="coworker-browser"
        )
        self._state: dict[str, Any] = {
            "open": False,
            "url": "",
            "title": "",
            "status": "closed",
            "last_action": "",
            "last_result": "",
            "last_error": "",
            "screenshot_data_url": "",
            "updated_at": None,
            "controls": [],
            "always_allow_reads": True,
            "allowed_domains": [],
            "history": [],
            "evidence": [],
            "media": [],
            "streaming_media": [],
            "streaming_media_status": "idle",
            "streaming_media_error": "",
            "streaming_media_progress": {},
            "pending_action": {},
            "control_owner": "agent",
            "control_changed_at": None,
        }

    def set_workspace_roots(self, roots: list[Any]) -> None:
        with self._lock:
            self._workspace_roots = list(roots)

    def _touch(self, **changes: Any) -> None:
        self._state.update(changes)
        self._state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _refresh_page_state(self) -> None:
        if self._page is None:
            self._touch(
                open=False,
                status="closed",
                url="",
                title="",
                controls=[],
                media=[],
            )
            return
        try:
            snap = _snapshot(self._page, 2000)
            self._touch(
                open=True,
                status="open",
                url=self._page.url,
                title=self._page.title(),
                controls=snap.get("controls", [])[:30],
                media=snap.get("media", []),
            )
        except Exception as exc:
            self._touch(open=True, status="error", last_error=str(exc))

    def _capture_preview(self) -> None:
        if self._page is None:
            return
        masks = []
        for target in sorted(self._sensitive_targets):
            try:
                locator = _target_locator(self._page, target, first=False)
                if locator.count() == 1:
                    masks.append(locator.first)
            except Exception:
                continue
        try:
            png = self._page.screenshot(
                full_page=False,
                **({"mask": masks, "mask_color": "#6b7280"} if masks else {}),
            )
        except Exception:
            # Never fall back to an unmasked screenshot after a sensitive field was used.
            if masks:
                self._touch(screenshot_data_url="")
                return
            raise
        data_url = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
        self._touch(screenshot_data_url=data_url)

    def _record_evidence(self, action: str) -> None:
        if self._page is None:
            return
        url = self._page.url
        if not url or url == "about:blank":
            return
        captured_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        screenshot = str(self._state.get("screenshot_data_url") or "")
        item = {
            "action": action,
            "url": url,
            "title": self._page.title(),
            "captured_at": captured_at,
            "screenshot_sha256": (
                hashlib.sha256(screenshot.encode("utf-8")).hexdigest()
                if screenshot
                else ""
            ),
        }
        history = list(self._state.get("history") or [])
        if not history or history[-1].get("url") != url:
            history.append(
                {
                    "url": url,
                    "title": item["title"],
                    "visited_at": captured_at,
                }
            )
        evidence = list(self._state.get("evidence") or [])
        evidence.append(item)
        self._touch(history=history[-100:], evidence=evidence[-100:])

    def set_policy(
        self, *, always_allow_reads: bool, allowed_domains: list[str]
    ) -> dict[str, Any]:
        normalized: list[str] = []
        for value in allowed_domains:
            domain = str(value or "").strip().lower().rstrip(".")
            if "://" in domain:
                domain = (urlsplit(domain).hostname or "").lower().rstrip(".")
            if domain and domain not in normalized:
                normalized.append(domain)
        with self._lock:
            self._touch(
                always_allow_reads=bool(always_allow_reads),
                allowed_domains=normalized,
            )
            return {
                "ok": True,
                "always_allow_reads": self._state["always_allow_reads"],
                "allowed_domains": list(self._state["allowed_domains"]),
            }

    def _navigation_allowed(self, url: str) -> bool:
        if self._state.get("always_allow_reads", True):
            return True
        hostname = (urlsplit(url).hostname or "").lower().rstrip(".")
        return any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in self._state.get("allowed_domains", [])
        )

    def media_source(self, media_id: str) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            with self._lock:
                match = next(
                    (
                        item
                        for item in self._state.get("media", [])
                        if item.get("id") == media_id
                    ),
                    None,
                )
                if not match:
                    return {"error": "The selected media is no longer available."}
                return {
                    "ok": True,
                    "media": dict(match),
                    "page_url": self._state.get("url", ""),
                    "cookies": (
                        self._context.cookies() if self._context is not None else []
                    ),
                }

        return self._submit(run)

    def media_context(self) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            with self._lock:
                if not self._state.get("url"):
                    return {"error": "Open a page before analyzing streaming media."}
                return {
                    "ok": True,
                    "url": self._state["url"],
                    "user_agent": (
                        self._page.evaluate("navigator.userAgent")
                        if self._page is not None
                        else ""
                    ),
                    "cookies": (
                        self._context.cookies() if self._context is not None else []
                    ),
                }

        return self._submit(run)

    def set_streaming_media(
        self,
        *,
        media: Optional[list[dict[str, Any]]] = None,
        status: str,
        error: str = "",
        progress: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        with self._lock:
            changes: dict[str, Any] = {
                "streaming_media_status": status,
                "streaming_media_error": error,
            }
            if media is not None:
                changes["streaming_media"] = list(media)
            if progress is not None:
                changes["streaming_media_progress"] = dict(progress)
            self._touch(**changes)
            return dict(self._state)

    def _setup_error(self, exc: Exception) -> dict[str, str]:
        return {
            "error": (
                "The Secure Browser runtime is not available in this build. "
                "Reinstall OpenWorker or run the browser setup for a source checkout."
            ),
            "details": str(exc),
        }

    def page(self):
        with self._lock:
            if self._error:
                return None, {"error": self._error}
            if self._page is not None:
                return self._page, None
            try:
                _prepare_packaged_browsers()
                from playwright.sync_api import sync_playwright

                self._playwright = sync_playwright().start()
                self._browser = self._playwright.chromium.launch(
                    **BROWSER_LAUNCH_OPTIONS
                )
                self._context = self._browser.new_context(
                    viewport={"width": 1280, "height": 900},
                    accept_downloads=False,
                )
                self._context.route("**/*", self._guard_request)
                self._page = self._context.new_page()
                self._touch(
                    open=True, status="open", last_action="open browser", last_error=""
                )
                return self._page, None
            except Exception as exc:
                self._touch(open=False, status="error", last_error=str(exc))
                return None, self._setup_error(exc)

    def _guard_request(self, route) -> None:
        url = route.request.url
        if url.startswith(("data:", "blob:", "about:")):
            route.continue_()
            return
        try:
            validate_public_url(url)
        except BrowserPolicyError:
            route.abort("blockedbyclient")
            return
        if route.request.is_navigation_request() and not self._navigation_allowed(url):
            route.abort("blockedbyclient")
            return
        route.continue_()

    def _submit(self, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        return self._executor.submit(fn).result()

    def close(self) -> dict[str, Any]:
        return self._submit(self._close_locked)

    def _close_locked(self) -> dict[str, Any]:
        with self._lock:
            try:
                if self._context is not None:
                    self._context.close()
                if self._browser is not None:
                    self._browser.close()
                if self._playwright is not None:
                    self._playwright.stop()
            except Exception as exc:
                return {"error": str(exc)}
            finally:
                self._playwright = None
                self._browser = None
                self._context = None
                self._page = None
                self._sensitive_targets.clear()
                self._touch(
                    open=False,
                    status="closed",
                    url="",
                    title="",
                    controls=[],
                    media=[],
                    pending_action={},
                    control_owner="agent",
                    control_changed_at=None,
                )
            return {"ok": True}

    def state(self) -> dict[str, Any]:
        return self._submit(self._state_locked)

    def _state_locked(self) -> dict[str, Any]:
        with self._lock:
            self._refresh_page_state()
            state = dict(self._state)
            state["pending_action"] = _public_action(
                dict(self._state.get("pending_action") or {})
            )
            return state

    def screenshot(self) -> dict[str, Any]:
        return self._submit(self._screenshot_locked)

    def _screenshot_locked(self) -> dict[str, Any]:
        with self._lock:
            page, err = self.page()
            if err:
                return err
            try:
                self._capture_preview()
                self._touch(
                    last_action="screenshot",
                    last_result="ok",
                    last_error="",
                )
                self._refresh_page_state()
                return {"ok": True, **dict(self._state)}
            except Exception as exc:
                self._touch(
                    last_action="screenshot", last_result="error", last_error=str(exc)
                )
                return {"error": str(exc)}

    def call(self, action: str, fn: Callable[[Any], dict[str, Any]]) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            with self._lock:
                if self._state.get("control_owner") == "user":
                    return {
                        "error": (
                            "The user is controlling Secure Browser. Wait until they "
                            "return control to the agent."
                        )
                    }
                page, err = self.page()
                if err:
                    return err
                previous_url = str(self._state.get("url") or "")
                self._touch(last_action=action, last_result="running", last_error="")
                try:
                    out = fn(page)
                except Exception as exc:
                    out = {"error": str(exc)}
                if "error" in out:
                    self._touch(
                        last_action=action,
                        last_result="error",
                        last_error=str(out["error"]),
                    )
                else:
                    self._refresh_page_state()
                    if previous_url and self._page.url != previous_url:
                        self._sensitive_targets.clear()
                        self._touch(
                            streaming_media=[],
                            streaming_media_status="idle",
                            streaming_media_error="",
                            streaming_media_progress={},
                        )
                    self._capture_preview()
                    self._record_evidence(action)
                    self._touch(last_action=action, last_result="ok", last_error="")
                return out

        return self._submit(run)

    def set_control_owner(self, owner: str) -> dict[str, Any]:
        normalized = str(owner or "").strip().lower()
        if normalized not in {"agent", "user"}:
            return {"error": "control_owner must be agent or user"}

        def run() -> dict[str, Any]:
            with self._lock:
                if normalized == "user" and self._page is None:
                    return {"error": "Open a page before taking control."}
                if normalized == "user" and self._state.get("pending_action"):
                    return {
                        "error": (
                            "Resolve the pending browser approval before taking control."
                        )
                    }
                changed_at = time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                )
                self._touch(
                    control_owner=normalized,
                    control_changed_at=changed_at,
                    last_action=(
                        "user_take_control"
                        if normalized == "user"
                        else "return_control_to_agent"
                    ),
                    last_result="ok",
                    last_error="",
                )
                return {
                    "ok": True,
                    "control_owner": normalized,
                    "control_changed_at": changed_at,
                }

        return self._submit(run)

    def human_action(self, action: str, **arguments: Any) -> dict[str, Any]:
        allowed = {
            "click",
            "scroll",
            "type",
            "key",
            "back",
            "forward",
            "reload",
            "open_url",
        }
        if action not in allowed:
            return {"error": "Unsupported browser control action."}

        def run() -> dict[str, Any]:
            with self._lock:
                if self._state.get("control_owner") != "user":
                    return {"error": "Take control before interacting with the page."}
                page, err = self.page()
                if err:
                    return err
                previous_url = page.url
                try:
                    if action == "click":
                        x = max(0.0, min(float(arguments.get("x", 0)), 1280.0))
                        y = max(0.0, min(float(arguments.get("y", 0)), 900.0))
                        page.mouse.click(x, y)
                    elif action == "scroll":
                        page.mouse.wheel(0, max(-4000, min(int(arguments.get("delta_y", 0)), 4000)))
                    elif action == "type":
                        text = str(arguments.get("text") or "")
                        if len(text) > 10000:
                            return {"error": "Text is too long."}
                        page.keyboard.type(text)
                    elif action == "key":
                        key = str(arguments.get("key") or "")
                        if key not in {"Enter", "Tab", "Escape", "Backspace", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"}:
                            return {"error": "That key is not supported."}
                        page.keyboard.press(key)
                    elif action == "back":
                        page.go_back(wait_until="domcontentloaded", timeout=30000)
                    elif action == "forward":
                        page.go_forward(wait_until="domcontentloaded", timeout=30000)
                    elif action == "reload":
                        page.reload(wait_until="domcontentloaded", timeout=30000)
                    elif action == "open_url":
                        safe_url = validate_public_url(str(arguments.get("url") or ""))
                        if not self._navigation_allowed(safe_url):
                            return {"error": "That domain is not allowed for this session."}
                        page.goto(safe_url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(150)
                    self._refresh_page_state()
                    if previous_url != page.url:
                        self._sensitive_targets.clear()
                    self._capture_preview()
                    self._record_evidence(f"human_{action}")
                    self._touch(
                        last_action=f"human_{action}",
                        last_result="ok",
                        last_error="",
                    )
                    return {"ok": True, **self._state_locked()}
                except Exception as exc:
                    self._touch(
                        last_action=f"human_{action}",
                        last_result="error",
                        last_error=str(exc),
                    )
                    return {"error": str(exc)}

        return self._submit(run)

    def propose_action(
        self,
        *,
        tool_call_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Freeze the exact visible target shown to the user before approval."""

        def run() -> dict[str, Any]:
            with self._lock:
                if self._state.get("control_owner") == "user":
                    return {
                        "error": (
                            "The user is controlling Secure Browser. Wait until they "
                            "return control to the agent."
                        )
                    }
                existing = dict(self._state.get("pending_action") or {})
                if tool_call_id and existing.get("tool_call_id") == tool_call_id:
                    return _public_action(existing)
                page, err = self.page()
                if err:
                    return err
                is_scroll = tool_name == "browser_scroll"
                target = str(arguments.get("target") or "").strip()
                scroll_target = target or "Main page"
                scroll_delta = int(arguments.get("delta_y") or 0) if is_scroll else 0
                inspected = (
                    _inspect_scroll_target(page, target)
                    if is_scroll
                    else _inspect_target(page, target)
                )
                is_type = tool_name == "browser_type"
                is_select = tool_name == "browser_select"
                is_upload = tool_name == "browser_upload_file"
                sensitive = bool(inspected.get("sensitive")) or (
                    is_type
                    and _looks_sensitive_value(str(arguments.get("text") or ""))
                )
                option_label = ""
                option_value = ""
                select_error = ""
                requested_value = str(arguments.get("value") or "")
                if is_select and not inspected.get("error"):
                    matches = [
                        option
                        for option in inspected.get("_options", [])
                        if requested_value
                        in {str(option.get("value") or ""), str(option.get("label") or "")}
                    ]
                    if len(matches) != 1:
                        select_error = (
                            "The selected option is ambiguous."
                            if matches
                            else "The selected option is no longer available."
                        )
                    elif matches[0].get("disabled"):
                        select_error = "The selected option is disabled."
                    else:
                        option_label = (
                            str(matches[0].get("label") or "")
                            or str(matches[0].get("value") or "")
                        )
                        option_value = str(matches[0].get("value") or "")
                upload_path = str(arguments.get("path") or "")
                upload_name = Path(upload_path).name
                upload_error = ""
                upload_resolved_path = ""
                upload_size = 0
                upload_mtime_ns = 0
                if is_upload and self._workspace_roots:
                    try:
                        resolved_upload = resolve_workspace_path(
                            upload_path, self._workspace_roots, must_exist=True
                        )
                        upload_resolved_path = str(resolved_upload)
                        upload_stat = resolved_upload.stat()
                        upload_size = int(upload_stat.st_size)
                        upload_mtime_ns = int(upload_stat.st_mtime_ns)
                    except (BrowserPolicyError, OSError) as exc:
                        upload_error = str(exc)
                action_name = (
                    "Scroll"
                    if is_scroll
                    else (
                        "Upload"
                        if is_upload
                        else (
                            "Select"
                            if is_select
                            else ("Type" if is_type else "Click")
                        )
                    )
                )
                risk = (
                    "Page navigation"
                    if is_scroll
                    else (
                        "File disclosure"
                        if is_upload
                        else (
                            "Sensitive input"
                            if sensitive
                            else (
                                "Form selection"
                                if is_select
                                else (
                                    "Form input" if is_type else "Page interaction"
                                )
                            )
                        )
                    )
                )
                if is_scroll:
                    direction = "Down" if scroll_delta > 0 else "Up"
                    distance = abs(scroll_delta)
                    expected_result = (
                        f"Content about {distance} px {direction.lower()} in "
                        f"{scroll_target} becomes visible."
                    )
                    content_summary = (
                        f"{direction} · {distance} px · {scroll_target}"
                    )
                elif is_upload:
                    expected_result = (
                        f'“{upload_name or "The selected file"}” is attached to '
                        "this field."
                    )
                    content_summary = (
                        (
                            f"File: {upload_name} "
                            f"({_format_file_size(upload_size)})"
                        )
                        if upload_size
                        else f"File: {upload_name}"
                    )
                elif is_select:
                    expected_result = (
                        f'The dropdown changes to “{option_label}”.'
                        if option_label
                        else "The chosen dropdown option is selected."
                    )
                    content_summary = (
                        f"Selected option: {option_label}" if option_label else ""
                    )
                elif is_type:
                    expected_result = (
                        "The field is replaced with the approved content."
                        if bool(arguments.get("clear", True))
                        else "The approved content is appended to the field."
                    )
                    content_summary = "Content hidden for privacy."
                else:
                    expected_result = "The selected page element is activated."
                    content_summary = ""
                proposal = {
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "action": action_name,
                    "target": target,
                    "domain": urlsplit(page.url).hostname or "",
                    "risk": risk,
                    "expected_result": expected_result,
                    "content_summary": content_summary,
                    "sensitive": sensitive,
                    "direction": (
                        ("Down" if scroll_delta > 0 else "Up") if is_scroll else ""
                    ),
                    "distance": f"{abs(scroll_delta)} px" if is_scroll else "",
                    "area": scroll_target if is_scroll else "",
                    "_scroll_delta_y": scroll_delta if is_scroll else 0,
                    "_requested_value": requested_value if is_select else "",
                    "_option_value": option_value if is_select else "",
                    "_upload_path": upload_path if is_upload else "",
                    "_upload_resolved_path": (
                        upload_resolved_path if is_upload else ""
                    ),
                    "_upload_size": upload_size if is_upload else 0,
                    "_upload_mtime_ns": upload_mtime_ns if is_upload else 0,
                    "status": "pending",
                    "created_at": time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                    ),
                    **inspected,
                }
                if select_error:
                    proposal["error"] = select_error
                if is_upload and (
                    inspected.get("_tag") != "input"
                    or inspected.get("_type") != "file"
                ):
                    proposal["error"] = (
                        "The proposed upload target is not a file input."
                    )
                if upload_error:
                    proposal["error"] = upload_error
                if is_scroll and (scroll_delta == 0 or abs(scroll_delta) > 5000):
                    proposal["error"] = (
                        "Scroll distance must be between 1 and 5000 pixels."
                    )
                self._capture_preview()
                self._touch(pending_action=proposal)
                return _public_action(proposal)

        return self._submit(run)

    def resolve_action(self, tool_call_id: str, resolution: str) -> dict[str, Any]:
        with self._lock:
            proposal = dict(self._state.get("pending_action") or {})
            if not proposal or proposal.get("tool_call_id") != tool_call_id:
                return {"ok": True}
            if resolution in {
                "allow",
                "once",
                "always",
                "always_tool",
                "always_command",
                "always_task",
            }:
                proposal["status"] = "approved"
                proposal["resolved_at"] = time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                )
                self._touch(pending_action=proposal)
            else:
                self._touch(pending_action={})
            return {"ok": True}

    def validate_action(
        self, tool_name: str, target: str, action_value: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
        """Reject an approved action when its page element changed before execution."""

        def run() -> Optional[dict[str, Any]]:
            with self._lock:
                proposal = dict(self._state.get("pending_action") or {})
                if not proposal:
                    return {
                        "error": (
                            "This browser action has no inspected approval. "
                            "Review and approve it before execution."
                        )
                    }
                if (
                    proposal.get("tool_name") != tool_name
                    or proposal.get("target") != target
                ):
                    return {
                        "error": (
                            "This browser action differs from the inspected approval. "
                            "Review and approve it again."
                        )
                    }
                if proposal.get("status") != "approved":
                    return {"error": "The browser action has not been approved."}
                if proposal.get("error"):
                    return {"error": str(proposal["error"])}
                if (
                    tool_name == "browser_select"
                    and str(proposal.get("_requested_value") or "")
                    != str(action_value or "")
                ):
                    return {
                        "error": (
                            "The selected option differs from the approved proposal. "
                            "Review and approve it again."
                        )
                    }
                if (
                    tool_name == "browser_upload_file"
                    and str(proposal.get("_upload_path") or "")
                    != str(action_value or "")
                ):
                    return {
                        "error": (
                            "The file differs from the approved proposal. "
                            "Review and approve it again."
                        )
                    }
                if (
                    tool_name == "browser_scroll"
                    and int(proposal.get("_scroll_delta_y") or 0)
                    != int(action_value or 0)
                ):
                    return {
                        "error": (
                            "The scroll distance differs from the approved proposal. "
                            "Review and approve it again."
                        )
                    }
                if tool_name == "browser_upload_file":
                    resolved_path = str(proposal.get("_upload_resolved_path") or "")
                    if resolved_path:
                        try:
                            current_stat = Path(resolved_path).stat()
                        except OSError:
                            current_stat = None
                        if (
                            current_stat is None
                            or int(current_stat.st_size)
                            != int(proposal.get("_upload_size") or 0)
                            or int(current_stat.st_mtime_ns)
                            != int(proposal.get("_upload_mtime_ns") or 0)
                        ):
                            proposal["status"] = "stale"
                            proposal["error"] = (
                                "The file changed before upload. Review and approve "
                                "it again."
                            )
                            self._touch(pending_action=proposal)
                            return {"error": proposal["error"]}
                page, err = self.page()
                if err:
                    return err
                current = (
                    _inspect_scroll_target(page, target)
                    if tool_name == "browser_scroll"
                    else _inspect_target(page, target)
                )
                if current.get("error") or current.get("fingerprint") != proposal.get(
                    "fingerprint"
                ):
                    proposal["status"] = "stale"
                    proposal["error"] = (
                        "The page changed before the action ran. Review the new target "
                        "and approve it again."
                    )
                    self._touch(pending_action=proposal)
                    return {"error": proposal["error"]}
                return None

        return self._executor.submit(run).result()

    def protect_action_value(self, tool_name: str, target: str) -> None:
        """Keep sensitive typed content out of every later preview screenshot."""
        with self._lock:
            proposal = dict(self._state.get("pending_action") or {})
            if (
                proposal.get("tool_name") == tool_name
                and proposal.get("target") == target
                and proposal.get("sensitive")
            ):
                self._sensitive_targets.add(target)

    def approved_select_value(self, target: str, requested_value: str) -> str:
        """Resolve an approved option label to the exact frozen HTML option value."""
        with self._lock:
            proposal = dict(self._state.get("pending_action") or {})
            if (
                proposal.get("tool_name") == "browser_select"
                and proposal.get("target") == target
                and str(proposal.get("_requested_value") or "") == requested_value
            ):
                return str(proposal.get("_option_value") or requested_value)
            return requested_value

    def finish_action(self, tool_name: str, target: str, *, succeeded: bool) -> None:
        with self._lock:
            proposal = dict(self._state.get("pending_action") or {})
            if (
                proposal.get("tool_name") == tool_name
                and proposal.get("target") == target
                and (succeeded or proposal.get("status") != "stale")
            ):
                self._touch(pending_action={})


_BROWSERS_LOCK = threading.RLock()
_BROWSERS: dict[str, _BrowserController] = {}


def _browser_for(session_id: str = "") -> _BrowserController:
    key = session_id or "__default__"
    with _BROWSERS_LOCK:
        controller = _BROWSERS.get(key)
        if controller is None:
            controller = _BrowserController()
            _BROWSERS[key] = controller
        return controller


def browser_state(session_id: str = "") -> dict[str, Any]:
    return _browser_for(session_id).state()


def browser_take_screenshot(session_id: str = "") -> dict[str, Any]:
    return _browser_for(session_id).screenshot()


def browser_close_session(session_id: str = "") -> dict[str, Any]:
    with _BROWSERS_LOCK:
        controller = _BROWSERS.get(session_id or "__default__")
    return controller.close() if controller is not None else {"ok": True}


def browser_set_control_owner(session_id: str, owner: str) -> dict[str, Any]:
    return _browser_for(session_id).set_control_owner(owner)


def browser_human_action(
    session_id: str, action: str, **arguments: Any
) -> dict[str, Any]:
    return _browser_for(session_id).human_action(action, **arguments)


def browser_set_policy(
    session_id: str = "",
    *,
    always_allow_reads: bool = True,
    allowed_domains: Optional[list[str]] = None,
) -> dict[str, Any]:
    return _browser_for(session_id).set_policy(
        always_allow_reads=always_allow_reads,
        allowed_domains=list(allowed_domains or []),
    )


def browser_media_source(session_id: str, media_id: str) -> dict[str, Any]:
    return _browser_for(session_id).media_source(media_id)


def browser_media_context(session_id: str) -> dict[str, Any]:
    return _browser_for(session_id).media_context()


def browser_set_streaming_media(
    session_id: str,
    *,
    media: Optional[list[dict[str, Any]]] = None,
    status: str,
    error: str = "",
    progress: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return _browser_for(session_id).set_streaming_media(
        media=media,
        status=status,
        error=error,
        progress=progress,
    )


def browser_propose_action(
    session_id: str,
    *,
    tool_call_id: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    if tool_name not in {
        "browser_click",
        "browser_scroll",
        "browser_type",
        "browser_select",
        "browser_upload_file",
    }:
        return {}
    return _browser_for(session_id).propose_action(
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        arguments=arguments,
    )


def browser_resolve_action(
    session_id: str, *, tool_call_id: str, resolution: str
) -> dict[str, Any]:
    return _browser_for(session_id).resolve_action(tool_call_id, resolution)


def _cap(value: int, default: int = 20000, upper: int = 100000) -> int:
    try:
        return max(1, min(int(value or default), upper))
    except Exception:
        return default


def _format_file_size(size: int) -> str:
    value = float(max(0, size))
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{int(value)} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{int(size)} B"


def _target_locator(page, target: str, *, first: bool = True):
    target = target.strip()
    if target.startswith("text="):
        locator = page.get_by_text(target[5:], exact=False)
    elif target.startswith("role="):
        role_name = target[5:]
        role, _, name = role_name.partition(":")
        locator = page.get_by_role(role.strip(), name=name.strip() or None)
    else:
        try:
            locator = page.locator(target)
        except Exception:
            locator = page.get_by_text(target, exact=False)
    return locator.first if first else locator


_TARGET_DESCRIPTOR_JS = """
(el) => {
  const rect = el.getBoundingClientRect();
  const tag = el.tagName.toLowerCase();
  const formField = tag === 'input' || tag === 'textarea' || el.isContentEditable;
  const label =
    el.getAttribute('aria-label') ||
    (el.labels && el.labels.length ? Array.from(el.labels).map(x => x.innerText.trim()).join(' ') : '') ||
    el.getAttribute('placeholder') ||
    el.getAttribute('name') ||
    el.getAttribute('id') ||
    (el.innerText || '').trim();
  return {
    tag,
    type: el.getAttribute('type') || '',
    id: el.getAttribute('id') || '',
    name: el.getAttribute('name') || '',
    role: el.getAttribute('role') || '',
    href: el.getAttribute('href') || '',
    autocomplete: el.getAttribute('autocomplete') || '',
    placeholder: el.getAttribute('placeholder') || '',
    label: label.slice(0, 160),
    text: formField ? '' : (el.innerText || el.value || '').trim().slice(0, 160),
    currentValue: (formField || tag === 'select') ? (el.value || el.innerText || '') : '',
    options: tag === 'select'
      ? Array.from(el.options).map(option => ({
          value: option.value,
          label: option.label || option.textContent || option.value,
          disabled: !!option.disabled
        }))
      : [],
    selectedValues: tag === 'select'
      ? Array.from(el.selectedOptions).map(option => option.value)
      : [],
    disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true',
    visible: rect.width > 0 && rect.height > 0,
    box: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
    viewport: { width: window.innerWidth, height: window.innerHeight }
  };
}
"""


_SENSITIVE_FIELD_HINTS = (
    "password",
    "passwd",
    "passcode",
    "pin",
    "token",
    "secret",
    "api key",
    "api_key",
    "credit card",
    "card number",
    "cvv",
    "cvc",
    "one-time",
    "otp",
)


def _looks_sensitive_value(value: str) -> bool:
    stripped = value.strip()
    lowered = stripped.lower()
    return bool(
        re.search(
            r"\b(?:bearer\s+\S+|sk-[a-z0-9_-]{12,}|"
            r"AIza[0-9A-Za-z_-]{20,}|gh[pousr]_[A-Za-z0-9_]{20,})\b",
            stripped,
            re.IGNORECASE,
        )
        or (stripped.count(".") == 2 and len(stripped) > 40)
        or any(hint in lowered for hint in ("api_key=", "token=", "password="))
    )


def _inspect_target(page, target: str) -> dict[str, Any]:
    if not target:
        return {"error": "The browser action does not identify a target."}
    try:
        candidates = _target_locator(page, target, first=False)
        count = candidates.count()
        if count != 1:
            return {
                "error": (
                    "The proposed browser target is no longer unique."
                    if count
                    else "The proposed browser target is no longer available."
                ),
                "match_count": count,
            }
        descriptor = candidates.first.evaluate(_TARGET_DESCRIPTOR_JS)
    except Exception as exc:
        return {"error": str(exc)}
    if not descriptor.get("visible") or descriptor.get("disabled"):
        return {"error": "The proposed browser target is not actionable."}
    current_value = str(descriptor.pop("currentValue", "") or "")
    options = list(descriptor.pop("options", []) or [])
    selected_values = list(descriptor.pop("selectedValues", []) or [])
    field_haystack = " ".join(
        str(descriptor.get(key) or "")
        for key in ("type", "id", "name", "autocomplete", "placeholder", "label")
    ).lower()
    sensitive = descriptor.get("type") == "password" or any(
        hint in field_haystack for hint in _SENSITIVE_FIELD_HINTS
    )
    identity = {
        "url": page.url,
        "target": target,
        "current_value_sha256": hashlib.sha256(
            current_value.encode("utf-8")
        ).hexdigest(),
        "options": options,
        "selected_values": selected_values,
        **{
            key: descriptor.get(key)
            for key in (
                "tag",
                "type",
                "id",
                "name",
                "role",
                "href",
                "autocomplete",
                "placeholder",
                "label",
                "text",
            )
        },
    }
    fingerprint = hashlib.sha256(
        json.dumps(identity, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return {
        "label": descriptor.get("label") or descriptor.get("text") or target,
        "box": descriptor.get("box") or {},
        "viewport": descriptor.get("viewport") or {},
        "fingerprint": fingerprint,
        "match_count": 1,
        "sensitive": sensitive,
        "_options": options,
        "_selected_values": selected_values,
        "_tag": descriptor.get("tag") or "",
        "_type": descriptor.get("type") or "",
    }


def _inspect_scroll_target(page, target: str) -> dict[str, Any]:
    """Freeze the page or scroll container before an approved scroll."""
    if target:
        inspected = _inspect_target(page, target)
        if inspected.get("error"):
            return inspected
        try:
            scroll_state = _target_locator(page, target).evaluate(
                """(el) => ({
                    scrollTop: el.scrollTop,
                    scrollHeight: el.scrollHeight,
                    clientHeight: el.clientHeight
                })"""
            )
        except Exception as exc:
            return {"error": str(exc)}
        if int(scroll_state.get("scrollHeight") or 0) <= int(
            scroll_state.get("clientHeight") or 0
        ):
            return {"error": "The proposed area is not scrollable."}
        identity = {
            "url": page.url,
            "target": target,
            **scroll_state,
            "fingerprint": inspected.get("fingerprint"),
        }
        inspected["fingerprint"] = hashlib.sha256(
            json.dumps(identity, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return inspected
    try:
        state = page.evaluate(
            """() => ({
                scrollY: window.scrollY,
                scrollHeight: document.documentElement.scrollHeight,
                clientHeight: window.innerHeight
            })"""
        )
    except Exception as exc:
        return {"error": str(exc)}
    identity = {"url": page.url, **state}
    return {
        "label": "Main page",
        "fingerprint": hashlib.sha256(
            json.dumps(identity, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "match_count": 1,
        "sensitive": False,
        "viewport": {
            "width": 1280,
            "height": int(state.get("clientHeight") or 900),
        },
    }


def _public_action(action: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in action.items()
        if key != "fingerprint" and not str(key).startswith("_")
    }


def _safe_call(fn: Callable[[], Any]) -> dict[str, Any]:
    try:
        return fn()
    except Exception as exc:
        return {"error": str(exc)}


_SNAPSHOT_JS = """
() => {
  const visible = (el) => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style && style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
  };
  const labelFor = (el) => {
    if (el.labels && el.labels.length) return Array.from(el.labels).map(l => l.innerText.trim()).filter(Boolean).join(' ');
    const id = el.getAttribute('id');
    if (id) {
      const label = document.querySelector(`label[for="${CSS.escape(id)}"]`);
      if (label) return label.innerText.trim();
    }
    return '';
  };
  const sensitive = (el) => {
    const hint = [
      el.getAttribute('type'),
      el.getAttribute('id'),
      el.getAttribute('name'),
      el.getAttribute('autocomplete'),
      el.getAttribute('placeholder'),
      el.getAttribute('aria-label'),
      labelFor(el)
    ].filter(Boolean).join(' ').toLowerCase();
    return [
      'password', 'passwd', 'passcode', 'pin', 'token', 'secret',
      'api key', 'api_key', 'credit card', 'card number', 'cvv',
      'cvc', 'one-time', 'otp'
    ].some(value => hint.includes(value));
  };
  const describe = (el, i) => ({
    index: i,
    tag: el.tagName.toLowerCase(),
    type: el.getAttribute('type') || '',
    id: el.getAttribute('id') || '',
    name: el.getAttribute('name') || '',
    role: el.getAttribute('role') || '',
    aria: el.getAttribute('aria-label') || '',
    label: labelFor(el),
    placeholder: el.getAttribute('placeholder') || '',
    text: sensitive(el)
      ? '[redacted]'
      : (el.innerText || el.value || '').trim().slice(0, 200),
    href: el.getAttribute('href') || '',
    selectorHint: el.getAttribute('id') ? `#${CSS.escape(el.getAttribute('id'))}` : (el.getAttribute('name') ? `[name="${el.getAttribute('name')}"]` : '')
  });
  const controls = Array.from(document.querySelectorAll('a,button,input,textarea,select,[role="button"],[contenteditable="true"]'))
    .filter(visible)
    .slice(0, 120)
    .map(describe);
  const media = [];
  const seen = new Set();
  document.querySelectorAll('video,audio').forEach((element, elementIndex) => {
    const candidates = [];
    if (element.currentSrc || element.src) {
      candidates.push({
        src: element.currentSrc || element.src,
        type: element.getAttribute('type') || '',
        label: element.getAttribute('data-quality') || element.getAttribute('data-res') || ''
      });
    }
    element.querySelectorAll('source').forEach(source => candidates.push({
      src: source.src,
      type: source.type || '',
      label: source.getAttribute('label') || source.getAttribute('data-quality') ||
        source.getAttribute('data-res') || source.getAttribute('media') || ''
    }));
    candidates.forEach((source, sourceIndex) => {
      if (!source.src || !/^https?:/i.test(source.src) || seen.has(source.src)) return;
      seen.add(source.src);
      const kind = element.tagName.toLowerCase() === 'audio' ? 'audio' : 'video';
      const width = Number(element.videoWidth || element.getAttribute('width') || 0);
      const height = Number(element.videoHeight || element.getAttribute('height') || 0);
      media.push({
        id: `${kind}-${elementIndex}-${sourceIndex}`,
        kind,
        url: source.src,
        mime_type: source.type || '',
        resolution: source.label || (height ? `${height}p` : (kind === 'audio' ? 'Audio' : 'Original')),
        width,
        height
      });
    });
  });
  return {
    title: document.title,
    url: location.href,
    text: document.body ? document.body.innerText : '',
    controls,
    media
  };
}
"""


def _snapshot(page, max_chars: int) -> dict[str, Any]:
    data = page.evaluate(_SNAPSHOT_JS)
    text = re.sub(r"\n{3,}", "\n\n", str(data.get("text") or ""))
    cap = _cap(max_chars)
    return {
        "title": data.get("title"),
        "url": data.get("url"),
        "text": text[:cap],
        "truncated": len(text) > cap,
        "controls": data.get("controls") or [],
        "media": data.get("media") or [],
    }


def make_browser_automation_tools(
    *, roots: Optional[list[str | Path]] = None, session_id: str = ""
) -> list[Callable[..., Any]]:
    tools: list[Callable[..., Any]] = []
    workspace_roots = list(roots or [])
    controller = _browser_for(session_id)
    controller.set_workspace_roots(workspace_roots)

    def browser_open_url(
        url: str, wait_until: str = "domcontentloaded"
    ) -> dict[str, Any]:
        try:
            safe_url = validate_public_url(url)
        except BrowserPolicyError as exc:
            return {"error": str(exc)}
        if not controller._navigation_allowed(safe_url):
            hostname = urlsplit(safe_url).hostname or safe_url
            return {
                "error": (
                    f"Navigation to {hostname} is not allowed for this session. "
                    "Add the domain in Secure Browser permissions or allow reads "
                    "from any public domain."
                )
            }
        return controller.call(
            "open_url",
            lambda page: (
                page.goto(safe_url, wait_until=wait_until, timeout=30000),
                {"ok": True, "url": page.url},
            )[1],
        )

    browser_open_url.__name__ = "browser_open_url"
    tools.append(
        _attach(
            browser_open_url,
            _schema(
                "browser_open_url",
                "Open a URL in the local Playwright browser session.",
                {"url": {"type": "string"}, "wait_until": {"type": "string"}},
                ["url"],
            ),
            approval=True,
        )
    )

    def browser_snapshot(max_chars: int = 20000) -> dict[str, Any]:
        return controller.call("snapshot", lambda page: _snapshot(page, max_chars))

    browser_snapshot.__name__ = "browser_snapshot"
    tools.append(
        _attach(
            browser_snapshot,
            _schema(
                "browser_snapshot",
                "Return the current page text plus visible controls and selector hints.",
                {"max_chars": {"type": "integer"}},
                [],
            ),
            approval=True,
        )
    )

    def browser_get_text(max_chars: int = 20000) -> dict[str, Any]:
        def run(page):
            text = re.sub(
                r"\n{3,}", "\n\n", page.locator("body").inner_text(timeout=5000)
            )
            cap = _cap(max_chars)
            return {
                "url": page.url,
                "title": page.title(),
                "text": text[:cap],
                "truncated": len(text) > cap,
            }

        return controller.call("get_text", run)

    browser_get_text.__name__ = "browser_get_text"
    tools.append(
        _attach(
            browser_get_text,
            _schema(
                "browser_get_text",
                "Read visible text from the current browser page.",
                {"max_chars": {"type": "integer"}},
                [],
            ),
            approval=True,
        )
    )

    def browser_click(target: str) -> dict[str, Any]:
        validation_error = controller.validate_action("browser_click", target)
        if validation_error:
            return validation_error
        result = controller.call(
            "click",
            lambda page: (
                _target_locator(page, target).click(timeout=10000),
                {"ok": True, "url": page.url},
            )[1],
        )
        controller.finish_action(
            "browser_click", target, succeeded="error" not in result
        )
        return result

    browser_click.__name__ = "browser_click"
    tools.append(
        _attach(
            browser_click,
            _schema(
                "browser_click",
                "Click a visible page element by CSS selector, text=label, role=button:Name, or text fallback. Requires approval.",
                {"target": {"type": "string"}},
                ["target"],
            ),
            approval=True,
        )
    )

    def browser_scroll(delta_y: int, target: str = "") -> dict[str, Any]:
        normalized_delta = int(delta_y or 0)
        validation_error = controller.validate_action(
            "browser_scroll", target, action_value=str(normalized_delta)
        )
        if validation_error:
            return validation_error

        def run(page):
            if target:
                _target_locator(page, target).evaluate(
                    "(el, delta) => el.scrollBy(0, delta)", normalized_delta
                )
            else:
                page.evaluate("(delta) => window.scrollBy(0, delta)", normalized_delta)
            page.wait_for_timeout(150)
            return {"ok": True, "url": page.url, "delta_y": normalized_delta}

        result = controller.call("scroll", run)
        controller.finish_action(
            "browser_scroll", target, succeeded="error" not in result
        )
        return result

    browser_scroll.__name__ = "browser_scroll"
    tools.append(
        _attach(
            browser_scroll,
            _schema(
                "browser_scroll",
                "Scroll the main page or a specific scrollable element by an exact pixel distance. Positive values move down; negative values move up. Requires approval.",
                {
                    "delta_y": {
                        "type": "integer",
                        "minimum": -5000,
                        "maximum": 5000,
                    },
                    "target": {"type": "string"},
                },
                ["delta_y"],
            ),
            approval=True,
        )
    )

    def browser_type(target: str, text: str, clear: bool = True) -> dict[str, Any]:
        validation_error = controller.validate_action("browser_type", target)
        if validation_error:
            return validation_error
        controller.protect_action_value("browser_type", target)

        def run(page):
            loc = _target_locator(page, target)
            if clear:
                loc.fill(text, timeout=10000)
            else:
                loc.type(text, timeout=10000)
            return {"ok": True, "url": page.url}

        result = controller.call("type", run)
        controller.finish_action(
            "browser_type", target, succeeded="error" not in result
        )
        return result

    browser_type.__name__ = "browser_type"
    tools.append(
        _attach(
            browser_type,
            _schema(
                "browser_type",
                "Fill or type into an input, textarea, or editable element. Requires approval.",
                {
                    "target": {"type": "string"},
                    "text": {"type": "string"},
                    "clear": {"type": "boolean"},
                },
                ["target", "text"],
            ),
            approval=True,
        )
    )

    def browser_select(target: str, value: str) -> dict[str, Any]:
        validation_error = controller.validate_action(
            "browser_select", target, action_value=value
        )
        if validation_error:
            return validation_error
        approved_value = controller.approved_select_value(target, value)
        result = controller.call(
            "select",
            lambda page: (
                _target_locator(page, target).select_option(
                    approved_value, timeout=10000
                ),
                {"ok": True, "url": page.url},
            )[1],
        )
        controller.finish_action(
            "browser_select", target, succeeded="error" not in result
        )
        return result

    browser_select.__name__ = "browser_select"
    tools.append(
        _attach(
            browser_select,
            _schema(
                "browser_select",
                "Select an option in a dropdown by selector and option value/label. Requires approval.",
                {"target": {"type": "string"}, "value": {"type": "string"}},
                ["target", "value"],
            ),
            approval=True,
        )
    )

    def browser_upload_file(target: str, path: str) -> dict[str, Any]:
        try:
            file_path = resolve_workspace_path(
                path, workspace_roots, must_exist=True
            )
        except BrowserPolicyError as exc:
            return {"error": str(exc)}
        validation_error = controller.validate_action(
            "browser_upload_file", target, action_value=path
        )
        if validation_error:
            return validation_error
        result = controller.call(
            "upload_file",
            lambda page: (
                _target_locator(page, target).set_input_files(
                    str(file_path), timeout=10000
                ),
                {"ok": True, "path": str(file_path)},
            )[1],
        )
        controller.finish_action(
            "browser_upload_file", target, succeeded="error" not in result
        )
        return result

    browser_upload_file.__name__ = "browser_upload_file"
    tools.append(
        _attach(
            browser_upload_file,
            _schema(
                "browser_upload_file",
                "Upload a local file through a file input. Requires approval.",
                {"target": {"type": "string"}, "path": {"type": "string"}},
                ["target", "path"],
            ),
            approval=True,
        )
    )

    def browser_wait(milliseconds: int = 1000, target: str = "") -> dict[str, Any]:
        def run(page):
            if target:
                _target_locator(page, target).wait_for(
                    timeout=max(1, int(milliseconds or 1000))
                )
            else:
                page.wait_for_timeout(max(1, min(int(milliseconds or 1000), 30000)))
            return {"ok": True, "url": page.url}

        return controller.call("wait", run)

    browser_wait.__name__ = "browser_wait"
    tools.append(
        _attach(
            browser_wait,
            _schema(
                "browser_wait",
                "Wait for a duration or for a target element to appear.",
                {"milliseconds": {"type": "integer"}, "target": {"type": "string"}},
                [],
            ),
            approval=True,
        )
    )

    def browser_screenshot(path: str = "") -> dict[str, Any]:
        def run(page):
            if path:
                try:
                    out = resolve_workspace_path(path, workspace_roots)
                except BrowserPolicyError as exc:
                    return {"error": str(exc)}
            else:
                out = (
                    Path(tempfile.gettempdir())
                    / "openworker"
                    / "browser-screenshot.png"
                ).resolve()
            out.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out), full_page=True)
            return {"ok": True, "path": str(out), "url": page.url}

        return controller.call("screenshot", run)

    browser_screenshot.__name__ = "browser_screenshot"
    tools.append(
        _attach(
            browser_screenshot,
            _schema(
                "browser_screenshot",
                "Save a full-page screenshot of the current browser page and return the local path.",
                {"path": {"type": "string"}},
                [],
            ),
            approval=True,
        )
    )

    def browser_close() -> dict[str, Any]:
        return browser_close_session(session_id)

    browser_close.__name__ = "browser_close"
    tools.append(
        _attach(
            browser_close,
            _schema(
                "browser_close",
                "Close the local Playwright browser session.",
                {},
                [],
            ),
            approval=True,
        )
    )

    return tools
