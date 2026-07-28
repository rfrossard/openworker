"""Persistent state for Deep Research runs.

Research execution will grow into a multi-agent workflow. This store deliberately keeps the
first schema small and explicit so the UI, future workers, and recovery logic share one durable
source of truth instead of inferring state from chat messages.
"""

from __future__ import annotations

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
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ResearchRun":
        fields = cls.__dataclass_fields__
        return cls(**{key: value[key] for key in fields if key in value})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
                setattr(run, key, value)
            run.updated_at = _now()
            self._save()
            return run
