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
