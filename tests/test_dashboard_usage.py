from datetime import datetime
from types import SimpleNamespace

from coworker.conversations import ConversationStore
from coworker.server.dashboard import _dashboard_data
from coworker.sessions import SessionRecord


def test_dashboard_uses_provider_reported_usage_per_session_model_and_day(tmp_path):
    store = ConversationStore(tmp_path / "state")
    timestamp = datetime.now().astimezone().replace(hour=12, minute=0, second=0).timestamp()
    store.save(
        SessionRecord(
            session_id="usage-session",
            workspace=str(tmp_path),
            model="gpt-5.6-sol",
            mode="interactive",
            title="Measured chat",
            messages=[
                {"role": "user", "content": "hello", "ts": timestamp - 1},
                {
                    "role": "assistant",
                    "content": "hi",
                    "ts": timestamp,
                    "_usage": {
                        "input_tokens": 1_000,
                        "output_tokens": 200,
                        "total_tokens": 1_200,
                        "model": "gpt-5.6-sol",
                    },
                },
            ],
        )
    )

    data = _dashboard_data(SimpleNamespace(session_store=store, model="gpt-5.6-sol"))
    session = data["sessions"][0]
    today = datetime.fromtimestamp(timestamp).astimezone().date().isoformat()

    assert session["measurement"] == "reported"
    assert session["model_calls"] == 1
    assert session["input_tokens"] == 1_000
    assert session["output_tokens"] == 200
    assert session["cost_usd"] == 0.011
    assert data["aggregates"]["daily"][today]["cost"] == 0.011
    assert data["aggregates"]["daily"][today]["sessions"] == 1
    assert data["aggregates"]["by_model"]["gpt-5.6-sol"]["tokens"] == 1_200


def test_dashboard_labels_legacy_session_estimates(tmp_path):
    store = ConversationStore(tmp_path / "state")
    store.save(
        SessionRecord(
            session_id="legacy-session",
            workspace=str(tmp_path),
            model="deepseek:deepseek-v4-flash",
            mode="interactive",
            messages=[
                {"role": "user", "content": "A" * 400},
                {"role": "assistant", "content": "B" * 80},
            ],
        )
    )

    session = _dashboard_data(
        SimpleNamespace(
            session_store=store, model="deepseek:deepseek-v4-flash"
        )
    )["sessions"][0]

    assert session["measurement"] == "estimated"
    assert session["input_tokens"] == 100
    assert session["output_tokens"] == 20
