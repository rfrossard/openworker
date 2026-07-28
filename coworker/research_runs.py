"""Persistent state for Deep Research runs.

Research execution will grow into a multi-agent workflow. This store deliberately keeps the
first schema small and explicit so the UI, future workers, and recovery logic share one durable
source of truth instead of inferring state from chat messages.
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


RESEARCH_DEPTHS = {"quick", "standard", "deep"}
RESEARCH_STATUSES = {
    "planned",
    "researching",
    "synthesizing",
    "completed",
    "failed",
    "cancelled",
}
SOURCE_LIMITS = {"quick": 5, "standard": 10, "deep": 20}
EVIDENCE_STATUSES = {"collected", "verified", "conflicting", "discarded"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ResearchRun:
    run_id: str
    session_id: str
    question: str
    depth: str
    plan: list[str]
    status: str = "planned"
    source_limit: int = 10
    agent_limit: int = 1
    sources_found: int = 0
    artifact_path: Optional[str] = None
    error: Optional[str] = None
    artifact_paths_at_start: list[str] = field(default_factory=list)
    browser_history_count_at_start: int = 0
    browser_evidence_count_at_start: int = 0
    evidence: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    extra_fields: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ResearchRun":
        fields = cls.__dataclass_fields__
        known = {
            key: value[key]
            for key in fields
            if key in value and key != "extra_fields"
        }
        known["extra_fields"] = {
            key: item
            for key, item in value.items()
            if key not in fields
        }
        if not isinstance(known.get("evidence", []), list):
            known["evidence"] = []
        else:
            known["evidence"] = [
                dict(item)
                for item in known.get("evidence", [])
                if isinstance(item, dict)
            ]
        return cls(**known)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        extras = value.pop("extra_fields", {})
        return {**extras, **value}


class ResearchRunStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()
        self._runs: dict[str, ResearchRun] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            for value in payload.get("runs", []):
                run = ResearchRun.from_dict(value)
                self._runs[run.run_id] = run
        except (OSError, ValueError, TypeError):
            self._runs = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {"version": 1, "runs": [run.to_dict() for run in self._runs.values()]},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def create(
        self,
        *,
        session_id: str,
        question: str,
        depth: str,
        plan: list[str],
        artifact_paths_at_start: Optional[list[str]] = None,
        browser_history_count_at_start: int = 0,
        browser_evidence_count_at_start: int = 0,
    ) -> ResearchRun:
        depth = depth.strip().lower()
        if depth not in RESEARCH_DEPTHS:
            raise ValueError("Research depth must be quick, standard, or deep.")
        question = question.strip()
        if not question:
            raise ValueError("Research question is required.")
        clean_plan = [str(item).strip() for item in plan if str(item).strip()]
        if not clean_plan:
            raise ValueError("Research plan must contain at least one step.")
        run = ResearchRun(
            run_id=f"research-{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            question=question,
            depth=depth,
            plan=clean_plan,
            source_limit=SOURCE_LIMITS[depth],
            artifact_paths_at_start=list(artifact_paths_at_start or []),
            browser_history_count_at_start=max(0, browser_history_count_at_start),
            browser_evidence_count_at_start=max(0, browser_evidence_count_at_start),
        )
        with self._lock:
            self._runs[run.run_id] = run
            self._save()
        return run

    def list(self, session_id: str) -> list[ResearchRun]:
        with self._lock:
            runs = [
                run for run in self._runs.values() if run.session_id == session_id
            ]
        return sorted(runs, key=lambda run: run.created_at, reverse=True)

    def update(self, run_id: str, **changes: Any) -> Optional[ResearchRun]:
        allowed = {
            "question",
            "depth",
            "plan",
            "status",
            "sources_found",
            "artifact_path",
            "error",
            "agent_limit",
        }
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            for key, value in changes.items():
                if key not in allowed:
                    continue
                if key == "status" and value not in RESEARCH_STATUSES:
                    raise ValueError("Invalid research status.")
                if key == "question":
                    value = str(value).strip()
                    if not value:
                        raise ValueError("Research question is required.")
                if key == "depth":
                    value = str(value).strip().lower()
                    if value not in RESEARCH_DEPTHS:
                        raise ValueError(
                            "Research depth must be quick, standard, or deep."
                        )
                if key == "plan":
                    value = [
                        str(item).strip()
                        for item in (value or [])
                        if str(item).strip()
                    ]
                    if not value:
                        raise ValueError(
                            "Research plan must contain at least one step."
                        )
                setattr(run, key, value)
                if key == "depth":
                    run.source_limit = SOURCE_LIMITS[value]
            run.updated_at = _now()
            self._save()
            return run

    def merge_evidence(
        self, run_id: str, items: list[dict[str, Any]]
    ) -> Optional[ResearchRun]:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            existing = {
                str(item.get("fingerprint") or ""): item
                for item in run.evidence
                if item.get("fingerprint")
            }
            changed = False
            for raw in items:
                url = str(raw.get("url") or "").strip()
                if not url:
                    continue
                screenshot_sha256 = str(
                    raw.get("screenshot_sha256") or ""
                ).strip()
                fingerprint = hashlib.sha256(
                    f"{url}\n{screenshot_sha256 or raw.get('title') or ''}".encode(
                        "utf-8"
                    )
                ).hexdigest()
                if fingerprint in existing:
                    continue
                item = {
                    "evidence_id": f"evidence-{fingerprint[:12]}",
                    "fingerprint": fingerprint,
                    "url": url,
                    "title": str(raw.get("title") or "").strip(),
                    "action": str(raw.get("action") or "").strip(),
                    "captured_at": str(raw.get("captured_at") or _now()),
                    "screenshot_sha256": screenshot_sha256,
                    "status": "collected",
                    "note": "",
                }
                run.evidence.append(item)
                existing[fingerprint] = item
                changed = True
            if changed:
                run.updated_at = _now()
                self._save()
            return run

    def update_evidence(
        self,
        run_id: str,
        evidence_id: str,
        *,
        status: Any = None,
        note: Any = None,
    ) -> Optional[dict[str, Any]]:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            item = next(
                (
                    value
                    for value in run.evidence
                    if value.get("evidence_id") == evidence_id
                ),
                None,
            )
            if item is None:
                return None
            if status is not None:
                status = str(status).strip().lower()
                if status not in EVIDENCE_STATUSES:
                    raise ValueError("Invalid evidence status.")
                item["status"] = status
            if note is not None:
                note = str(note).strip()
                if len(note) > 2000:
                    raise ValueError(
                        "Evidence note must be 2,000 characters or fewer."
                    )
                item["note"] = note
            run.updated_at = _now()
            self._save()
            return dict(item)
