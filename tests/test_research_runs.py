import json

import pytest

from coworker.research_runs import ResearchRunStore


def test_research_run_persists_across_store_restart(tmp_path):
    path = tmp_path / "research-runs.json"
    store = ResearchRunStore(path)
    created = store.create(
        session_id="session-a",
        question="Which model should we use?",
        depth="deep",
        plan=["Find primary evaluations", "Compare cost and quality"],
    )

    restored = ResearchRunStore(path).list("session-a")

    assert len(restored) == 1
    assert restored[0].run_id == created.run_id
    assert restored[0].status == "planned"
    assert restored[0].source_limit == 20
    assert restored[0].plan == [
        "Find primary evaluations",
        "Compare cost and quality",
    ]


def test_research_runs_are_session_scoped_and_updatable(tmp_path):
    store = ResearchRunStore(tmp_path / "research-runs.json")
    first = store.create(
        session_id="session-a",
        question="Question A",
        depth="quick",
        plan=["Research A"],
    )
    store.create(
        session_id="session-b",
        question="Question B",
        depth="standard",
        plan=["Research B"],
    )

    updated = store.update(first.run_id, status="researching", sources_found=3)

    assert updated is not None
    assert updated.status == "researching"
    assert updated.sources_found == 3
    assert [run.question for run in store.list("session-a")] == ["Question A"]


def test_research_run_persists_telemetry_baselines(tmp_path):
    path = tmp_path / "research-runs.json"
    store = ResearchRunStore(path)
    created = store.create(
        session_id="session-a",
        question="Track this research",
        depth="standard",
        plan=["Research"],
        artifact_paths_at_start=["existing.md"],
        browser_history_count_at_start=2,
        browser_evidence_count_at_start=3,
    )

    restored = ResearchRunStore(path).list("session-a")[0]

    assert restored.run_id == created.run_id
    assert restored.artifact_paths_at_start == ["existing.md"]
    assert restored.browser_history_count_at_start == 2
    assert restored.browser_evidence_count_at_start == 3


def test_planned_research_project_can_be_edited_and_reopened(tmp_path):
    path = tmp_path / "research-runs.json"
    store = ResearchRunStore(path)
    created = store.create(
        session_id="session-a",
        question="Initial question",
        depth="quick",
        plan=["Initial step"],
    )

    updated = store.update(
        created.run_id,
        question="Updated question",
        depth="deep",
        plan=["Find primary sources", "", "Compare evidence"],
    )
    restored = ResearchRunStore(path).list("session-a")[0]

    assert updated is not None
    assert restored.question == "Updated question"
    assert restored.depth == "deep"
    assert restored.source_limit == 20
    assert restored.plan == ["Find primary sources", "Compare evidence"]


def test_unknown_research_fields_survive_round_trip(tmp_path):
    path = tmp_path / "research-runs.json"
    path.write_text(
        """{
  "version": 1,
  "runs": [{
    "run_id": "research-existing",
    "session_id": "session-a",
    "question": "Existing",
    "depth": "quick",
    "plan": ["Research"],
    "future_field": {"keep": true}
  }]
}""",
        encoding="utf-8",
    )

    store = ResearchRunStore(path)
    store.update("research-existing", question="Edited")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["runs"][0]["future_field"] == {"keep": True}


def test_research_evidence_is_deduplicated_and_persists(tmp_path):
    path = tmp_path / "research-runs.json"
    store = ResearchRunStore(path)
    run = store.create(
        session_id="session-a",
        question="Evidence",
        depth="quick",
        plan=["Collect evidence"],
    )
    captured = {
        "url": "https://example.com/report",
        "title": "Primary report",
        "action": "open_url",
        "captured_at": "2026-07-27T00:00:00Z",
        "screenshot_sha256": "abc123",
    }

    store.merge_evidence(run.run_id, [captured, dict(captured)])
    restored = ResearchRunStore(path).list("session-a")[0]

    assert len(restored.evidence) == 1
    assert restored.evidence[0]["status"] == "collected"
    assert restored.evidence[0]["title"] == "Primary report"


def test_research_evidence_status_and_note_are_validated(tmp_path):
    store = ResearchRunStore(tmp_path / "research-runs.json")
    run = store.create(
        session_id="session-a",
        question="Evidence",
        depth="quick",
        plan=["Collect evidence"],
    )
    store.merge_evidence(
        run.run_id,
        [{"url": "https://example.com", "title": "Example"}],
    )
    evidence_id = run.evidence[0]["evidence_id"]

    updated = store.update_evidence(
        run.run_id,
        evidence_id,
        status="verified",
        note="Confirmed by the primary source.",
    )

    assert updated["status"] == "verified"
    assert updated["note"] == "Confirmed by the primary source."
    with pytest.raises(ValueError, match="Invalid evidence status"):
        store.update_evidence(
            run.run_id,
            evidence_id,
            status="trusted",
        )
    with pytest.raises(ValueError, match="2,000 characters"):
        store.update_evidence(
            run.run_id,
            evidence_id,
            note="x" * 2001,
        )


def test_invalid_persisted_evidence_collection_is_safely_normalized(tmp_path):
    path = tmp_path / "research-runs.json"
    path.write_text(
        """{
  "version": 1,
  "runs": [{
    "run_id": "research-existing",
    "session_id": "session-a",
    "question": "Existing",
    "depth": "quick",
    "plan": ["Research"],
    "evidence": "corrupt"
  }]
}""",
        encoding="utf-8",
    )

    restored = ResearchRunStore(path).list("session-a")[0]

    assert restored.evidence == []
