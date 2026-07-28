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
