from datetime import datetime
import json
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


def test_dashboard_counts_image_generation_once_by_session_day_and_provider(tmp_path):
    store = ConversationStore(tmp_path / "state")
    timestamp = datetime.now().astimezone().replace(hour=13, minute=0, second=0).timestamp()
    store.save(
        SessionRecord(
            session_id="image-session",
            workspace=str(tmp_path),
            model="deepseek:deepseek-v4-flash",
            mode="interactive",
            messages=[
                {"role": "user", "content": "Create a deck", "ts": timestamp - 2},
                {
                    "role": "assistant",
                    "content": "",
                    "ts": timestamp - 1,
                    "_usage": {
                        "input_tokens": 100,
                        "output_tokens": 20,
                        "model": "deepseek:deepseek-v4-flash",
                    },
                },
                {
                    "role": "tool",
                    "tool_call_id": "image-1",
                    "ts": timestamp,
                    "content": json.dumps(
                        {
                            "ok": True,
                            "operation_usage": {
                                "type": "image",
                                "provider": "OpenAI",
                                "model": "gpt-image-1.5",
                                "input_tokens": 12,
                                "output_tokens": 34,
                                "units": 1,
                                "estimated_cost_usd": 0.05,
                                "measurement": "estimated",
                            },
                        }
                    ),
                },
            ],
        )
    )

    data = _dashboard_data(
        SimpleNamespace(session_store=store, model="deepseek:deepseek-v4-flash")
    )
    session = data["sessions"][0]
    today = datetime.fromtimestamp(timestamp).astimezone().date().isoformat()

    assert session["model_calls"] == 1
    assert session["operations"] == {"image": 1}
    assert data["aggregates"]["operations"]["image"] == {
        "units": 1,
        "cost": 0.05,
    }
    assert data["aggregates"]["by_provider"]["OpenAI"]["cost"] == 0.05
    assert data["aggregates"]["daily"][today]["sessions"] == 1
