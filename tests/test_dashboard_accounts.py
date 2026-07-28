from datetime import datetime

from coworker.server import dashboard


class _Secrets:
    def __init__(self, values):
        self.values = values

    def get(self, key):
        return self.values.get(key)


class _Manager:
    def __init__(self, values):
        self.secrets = _Secrets(values)


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "is_available": True,
            "balance_infos": [
                {
                    "currency": "USD",
                    "total_balance": "12.34",
                    "granted_balance": "1.00",
                    "topped_up_balance": "11.34",
                }
            ],
        }


def test_official_balance_includes_provider_update_timestamp(monkeypatch):
    manager = _Manager({"provider:deepseek": {"api_key": "test-key"}})
    monkeypatch.setattr(dashboard.httpx, "get", lambda *args, **kwargs: _Response())

    result = dashboard._account_summary(manager)
    account = result["accounts"]["DeepSeek"]

    assert account["balances"][0]["total"] == 12.34
    assert account["updated_at"]
    assert datetime.fromisoformat(account["updated_at"]).tzinfo is not None
    assert datetime.fromisoformat(result["updated_at"]).tzinfo is not None


def test_failed_balance_check_still_reports_last_attempt_timestamp(monkeypatch):
    manager = _Manager({"provider:deepseek": {"api_key": "test-key"}})

    def fail(*args, **kwargs):
        raise TimeoutError("offline")

    monkeypatch.setattr(dashboard.httpx, "get", fail)

    account = dashboard._account_summary(manager)["accounts"]["DeepSeek"]

    assert account["status"] == "error"
    assert account["balances"] == []
    assert datetime.fromisoformat(account["updated_at"]).tzinfo is not None


def test_configured_gemini_is_visible_without_inventing_a_balance():
    manager = _Manager({"provider:gemini": {"api_key": "test-key"}})

    account = dashboard._account_summary(manager)["accounts"][
        "Google · Gemini Nano Banana 2 Lite"
    ]

    assert account["status"] == "local_estimate"
    assert account["balances"] == []
    assert account["local_spend"] == 0
    assert account["units"] == 0
    assert "No successful paid image generations" in account["message"]


def test_unconfigured_gemini_still_explains_why_usage_is_absent():
    manager = _Manager({})

    account = dashboard._account_summary(manager)["accounts"][
        "Google · Gemini Nano Banana 2 Lite"
    ]

    assert account["configured"] is False
    assert account["status"] == "not_configured"
    assert account["balances"] == []
    assert account["units"] == 0
    assert "Add a Gemini API key" in account["message"]


def test_gemini_card_uses_dynamic_locally_recorded_image_usage(monkeypatch):
    manager = _Manager({"provider:gemini": {"api_key": "test-key"}})
    monkeypatch.setattr(
        dashboard,
        "_dashboard_data",
        lambda _manager: {
            "aggregates": {
                "operation_models": {
                    "Gemini Nano Banana 2 Lite": {
                        "units": 3,
                        "cost": 0.1008,
                        "measurement": "estimated",
                    }
                }
            }
        },
    )

    account = dashboard._account_summary(manager)["accounts"][
        "Google · Gemini Nano Banana 2 Lite"
    ]

    assert account["local_spend"] == 0.1008
    assert account["units"] == 3
