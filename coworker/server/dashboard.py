"""Read-only usage dashboard routes for the local OpenWorker conversation store."""

from __future__ import annotations

import json
import math
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI
import httpx


MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    "gpt-5.6-sol": {"provider": "OpenAI", "family": "GPT-5.6", "input_per_1m": 5.00, "output_per_1m": 30.00, "status": "active", "tested": True, "frontier": True, "context": "400K"},
    "gpt-5.6-terra": {"provider": "OpenAI", "family": "GPT-5.6", "input_per_1m": 2.50, "output_per_1m": 15.00, "status": "active", "tested": True, "frontier": False, "context": "400K"},
    "gpt-5.6-luna": {"provider": "OpenAI", "family": "GPT-5.6", "input_per_1m": 1.00, "output_per_1m": 6.00, "status": "active", "tested": True, "frontier": False, "context": "400K"},
    "gpt-5.5": {"provider": "OpenAI", "family": "GPT-5", "input_per_1m": 5.00, "output_per_1m": 30.00, "status": "active", "tested": True, "frontier": False, "context": "256K"},
    "gpt-5-mini": {"provider": "OpenAI", "family": "GPT-5", "input_per_1m": 0.25, "output_per_1m": 2.00, "status": "active", "tested": True, "frontier": False, "context": "128K"},
    "gpt-4o": {"provider": "OpenAI", "family": "GPT-4", "input_per_1m": 2.50, "output_per_1m": 10.00, "status": "active", "tested": True, "frontier": False, "context": "128K"},
    "claude-fable-5": {"provider": "Anthropic", "family": "Claude 5", "input_per_1m": 10.00, "output_per_1m": 50.00, "status": "active", "tested": True, "frontier": True, "context": "1M"},
    "claude-opus-4.8": {"provider": "Anthropic", "family": "Claude 4", "input_per_1m": 5.00, "output_per_1m": 25.00, "status": "active", "tested": True, "frontier": True, "context": "1M"},
    "claude-sonnet-4.6": {"provider": "Anthropic", "family": "Claude 4", "input_per_1m": 3.00, "output_per_1m": 15.00, "status": "active", "tested": True, "frontier": False, "context": "1M"},
    "claude-haiku-4.5": {"provider": "Anthropic", "family": "Claude 4", "input_per_1m": 1.00, "output_per_1m": 5.00, "status": "active", "tested": True, "frontier": False, "context": "200K"},
    "gemini-3.5-flash": {"provider": "Google", "family": "Gemini 3", "input_per_1m": 1.50, "output_per_1m": 9.00, "status": "active", "tested": True, "frontier": False, "context": "1M"},
    "gemini-3.1-pro": {"provider": "Google", "family": "Gemini 3", "input_per_1m": 2.00, "output_per_1m": 12.00, "status": "active", "tested": True, "frontier": True, "context": "2M"},
    "gemini-3-flash-lite": {"provider": "Google", "family": "Gemini 3", "input_per_1m": 0.20, "output_per_1m": 1.20, "status": "active", "tested": True, "frontier": False, "context": "1M"},
    "deepseek-v4": {"provider": "DeepSeek", "family": "DeepSeek V4", "input_per_1m": 0.50, "output_per_1m": 2.00, "status": "active", "tested": True, "frontier": False, "context": "256K"},
    "deepseek-v4-flash": {"provider": "DeepSeek", "family": "DeepSeek V4", "input_per_1m": 0.14, "output_per_1m": 0.28, "status": "active", "tested": True, "frontier": False, "context": "1M"},
    "deepseek-r1": {"provider": "DeepSeek", "family": "DeepSeek R1", "input_per_1m": 0.55, "output_per_1m": 2.19, "status": "active", "tested": True, "frontier": True, "context": "128K"},
    "grok-4.3": {"provider": "xAI", "family": "Grok 4", "input_per_1m": 1.25, "output_per_1m": 2.50, "status": "active", "tested": True, "frontier": True, "context": "256K"},
    "grok-4.3-fast": {"provider": "xAI", "family": "Grok 4", "input_per_1m": 0.50, "output_per_1m": 1.00, "status": "active", "tested": True, "frontier": False, "context": "256K"},
    "grok-code-2": {"provider": "xAI", "family": "Grok Code", "input_per_1m": 0.75, "output_per_1m": 3.00, "status": "active", "tested": True, "frontier": False, "context": "256K"},
    "mistral-large-3": {"provider": "Mistral", "family": "Mistral Large", "input_per_1m": 2.00, "output_per_1m": 6.00, "status": "active", "tested": True, "frontier": True, "context": "256K"},
    "mistral-medium-3.1": {"provider": "Mistral", "family": "Mistral Medium", "input_per_1m": 0.40, "output_per_1m": 2.00, "status": "active", "tested": True, "frontier": False, "context": "128K"},
    "codestral-3": {"provider": "Mistral", "family": "Codestral", "input_per_1m": 0.30, "output_per_1m": 0.90, "status": "active", "tested": True, "frontier": False, "context": "256K"},
    "qwen-max": {"provider": "Qwen", "family": "Qwen Max", "input_per_1m": 0.40, "output_per_1m": 1.20, "status": "active", "tested": True, "frontier": True, "context": "256K"},
    "qwen-plus": {"provider": "Qwen", "family": "Qwen Plus", "input_per_1m": 0.20, "output_per_1m": 0.60, "status": "active", "tested": True, "frontier": False, "context": "256K"},
    "qwen-coder": {"provider": "Qwen", "family": "Qwen Coder", "input_per_1m": 0.30, "output_per_1m": 1.20, "status": "active", "tested": True, "frontier": False, "context": "256K"},
    "llama-4-maverick": {"provider": "Meta", "family": "Llama 4", "input_per_1m": 0.27, "output_per_1m": 0.85, "status": "active", "tested": True, "frontier": True, "context": "1M"},
    "llama-4-scout": {"provider": "Meta", "family": "Llama 4", "input_per_1m": 0.18, "output_per_1m": 0.59, "status": "active", "tested": True, "frontier": False, "context": "10M"},
    "command-a": {"provider": "Cohere", "family": "Command", "input_per_1m": 2.50, "output_per_1m": 10.00, "status": "active", "tested": True, "frontier": True, "context": "256K"},
    "command-r7b": {"provider": "Cohere", "family": "Command", "input_per_1m": 0.04, "output_per_1m": 0.15, "status": "active", "tested": True, "frontier": False, "context": "128K"},
}

# Published results grouped by the exact evaluation name. Scores from different harnesses
# (for example SWE-bench Pro and SWE-bench Verified) deliberately remain separate.
# Ollama entries refer to the matching upstream checkpoint; local quantization can change
# the observed result slightly.
BENCHMARKS: dict[str, dict[str, float]] = {
    "gpt-5.6-sol": {"aa_coding": 80.0, "gpqa": 94.6, "toolathlon": 58.0, "mrcr": 91.5, "mmmu": 83.0},
    "gpt-5.6-terra": {"aa_coding": 77.4, "gpqa": 92.9, "toolathlon": 53.1, "mrcr": 89.6, "mmmu": 80.7},
    "gpt-5.6-luna": {"aa_coding": 74.6, "gpqa": 92.3, "toolathlon": 53.4, "mrcr": 41.3, "mmmu": 78.4},
    "gpt-5.5": {"aa_coding": 76.4, "gpqa": 93.6, "toolathlon": 55.6, "mrcr": 81.5, "mmmu": 81.2, "swe_pro": 58.6},
    "claude-fable-5": {"aa_coding": 77.2, "gpqa": 92.6, "toolathlon": 61.7},
    "claude-opus-4.8": {"aa_coding": 72.5, "gpqa": 92.0, "toolathlon": 59.9, "mrcr": 85.9, "swe_pro": 69.2},
    "gemini-3.1-pro": {"aa_coding": 42.7, "gpqa": 94.3, "toolathlon": 48.8, "mmmu": 80.5, "swe_pro": 54.2},
    "ollama:glm-5.2:cloud": {"gpqa": 91.2, "swe_pro": 62.1},
    "ollama:glm-4.7-flash:latest": {"gpqa": 75.2, "livecodebench": 64.0, "swe_verified": 59.2, "tau2": 79.5},
    "ollama:qwen3:latest": {"gpqa": 59.0},
    "ollama:gemma4:latest": {"gpqa": 58.6, "livecodebench": 52.0, "tau2": 42.2, "mmmu": 52.6, "mrcr": 25.4},
    "ollama:gemma4:31b": {"gpqa": 84.3, "livecodebench": 80.0, "tau2": 76.9, "mmmu": 76.9, "mrcr": 66.4},
    "ollama:gpt-oss:latest": {"gpqa": 71.5, "livecodebench": 61.0, "swe_verified": 60.7, "tau2": 47.7},
    "ollama:gpt-oss:20b": {"gpqa": 71.5, "livecodebench": 61.0, "swe_verified": 60.7, "tau2": 47.7},
    "ollama:deepseek-r1:70b": {"gpqa": 65.2, "livecodebench": 57.5},
}

BENCHMARK_META = {
    "gpqa": {"label": "Reasoning", "metric": "GPQA Diamond", "source": "official model cards"},
    "livecodebench": {"label": "Coding", "metric": "LiveCodeBench v6", "source": "official model cards"},
    "swe_verified": {"label": "Coding agent", "metric": "SWE-bench Verified", "source": "official model cards"},
    "swe_pro": {"label": "Software engineering", "metric": "SWE-bench Pro", "source": "official model cards"},
    "tau2": {"label": "Tool use", "metric": "Tau²-bench (average)", "source": "official model cards"},
    "mmmu": {"label": "Vision", "metric": "MMMU Pro (no tools)", "source": "official model cards"},
    "mrcr": {"label": "Long context", "metric": "MRCR 128K / 256K", "source": "official model cards"},
    "aa_coding": {"label": "Coding agent", "metric": "AA Coding Agent Index v1.1", "source": "OpenAI GPT-5.6"},
}

MEDIA_CAPACITY = [
    {"kind": "image", "provider": "OpenAI", "model": "GPT Image 1.5", "unit": "medium 1K image", "cost_per_unit": 0.034},
    {"kind": "image", "provider": "Google", "model": "Gemini 3.1 Flash Image", "unit": "1K image", "cost_per_unit": 0.067},
    {"kind": "audio", "provider": "Google", "model": "Gemini 3.1 Flash TTS", "unit": "audio minute", "cost_per_unit": 0.03},
]


def _provider_summary() -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for name, spec in MODEL_REGISTRY.items():
        grouped[spec["provider"]].append((name, spec))
    result = {}
    for provider, models in grouped.items():
        frontier_name, frontier = max(models, key=lambda item: item[1]["output_per_1m"])
        result[provider] = {
            "models": len(models),
            "avg_input_cost": sum(m["input_per_1m"] for _, m in models) / len(models),
            "avg_output_cost": sum(m["output_per_1m"] for _, m in models) / len(models),
            "frontier_model": frontier_name,
            "frontier_input": frontier["input_per_1m"],
            "frontier_output": frontier["output_per_1m"],
            "active_count": sum(m["status"] == "active" for _, m in models),
        }
    return result


def _dashboard_registry(manager: Any) -> dict[str, dict[str, Any]]:
    """Registry enriched with live configuration state and pulled Ollama models."""
    provider_ids = {
        "OpenAI": "openai", "Anthropic": "anthropic", "Google": "gemini",
        "DeepSeek": "deepseek", "xAI": "xai", "Mistral": "mistral",
        "Qwen": "qwen", "Meta": "meta", "Cohere": "cohere",
    }
    configured = {
        item["name"] for item in manager.get_providers() if item.get("configured")
    }
    registry = {
        name: {
            **spec,
            "configured": provider_ids.get(spec["provider"]) in configured,
            "local": False,
            "pricing_known": True,
        }
        for name, spec in MODEL_REGISTRY.items()
    }
    if manager._ollama_alive():
        for routed_name in manager._ollama_models():
            bare_name = routed_name.split(":", 1)[-1]
            registry[routed_name] = {
                "provider": "Ollama",
                "family": "Cloud via Ollama" if bare_name.endswith(":cloud") else "Local",
                "input_per_1m": 0.0, "output_per_1m": 0.0,
                "status": "active", "tested": True, "frontier": False,
                "context": "—", "configured": True,
                "local": not bare_name.endswith(":cloud"),
                "ollama": True, "pricing_known": not bare_name.endswith(":cloud"),
                "display_name": bare_name,
            }
    for routed_name, provider in _live_api_models(manager).items():
        canonical = routed_name.split(":", 1)[-1] if ":" in routed_name else routed_name
        existing_key = canonical if canonical in registry else routed_name
        if existing_key in registry:
            registry[existing_key]["configured"] = True
            registry[existing_key]["live_catalog"] = True
            continue
        registry[routed_name] = {
            "provider": provider, "family": "API catalog",
            "input_per_1m": 0.0, "output_per_1m": 0.0,
            "status": "active", "tested": False, "frontier": False,
            "context": "—", "configured": True, "local": False,
            "pricing_known": False, "live_catalog": True,
        }
    return registry


def _live_api_models(manager: Any) -> dict[str, str]:
    """Best-effort live catalogs for configured providers; cached for five minutes."""
    cached = getattr(manager, "_dashboard_model_catalog_cache", None)
    now = time.monotonic()
    if cached and now - cached[0] < 300:
        return cached[1]
    catalogs: dict[str, str] = {}
    targets = [
        ("openai", "OpenAI", "OPENAI_API_KEY", "https://api.openai.com/v1", ""),
        ("deepseek", "DeepSeek", "DEEPSEEK_API_KEY", "https://api.deepseek.com", "deepseek:"),
    ]
    for provider_id, label, env_name, default_base, prefix in targets:
        key, profile = _provider_key(manager, provider_id, env_name)
        if not key:
            continue
        base = str(profile.get("base_url") or default_base).rstrip("/")
        try:
            response = httpx.get(
                f"{base}/models",
                headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
                timeout=8,
            )
            response.raise_for_status()
            for item in response.json().get("data", []):
                model_id = item.get("id") if isinstance(item, dict) else None
                if model_id:
                    catalogs[f"{prefix}{model_id}"] = label
        except Exception:
            continue
    manager._dashboard_model_catalog_cache = (now, catalogs)
    return catalogs


def _content_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_content_text(item) for item in value)
    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return value["text"]
        return " ".join(_content_text(v) for k, v in value.items() if k not in {"image", "data"})
    return ""


def _estimate_tokens(value: Any) -> int:
    text = _content_text(value)
    return math.ceil(len(text) / 4) if text else 0


def _model_pricing(model: str) -> tuple[str, dict[str, Any]]:
    """Resolve the persisted ``provider:model`` form against the bare-name registry."""
    bare_name = model.split(":", 1)[-1] if ":" in model else model
    return bare_name, MODEL_REGISTRY.get(bare_name, {})


def _read_messages(store: Any, session_id: str) -> list[dict[str, Any]]:
    path = Path(store.conv_dir) / f"{session_id}.jsonl"
    if path.exists():
        messages = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                messages.append(item)
        return messages
    record = store.load(session_id)
    return record.messages if record else []


def _message_date(message: dict[str, Any], fallback: str) -> str:
    try:
        timestamp = float(message.get("ts") or 0)
        if timestamp > 0:
            return datetime.fromtimestamp(timestamp).astimezone().date().isoformat()
    except (TypeError, ValueError, OSError):
        pass
    return fallback or "Unknown"


def _session_usage_events(
    messages: list[dict[str, Any]], fallback_model: str, fallback_date: str
) -> list[dict[str, Any]]:
    """One billable model call per assistant message, exact when the provider reported it."""
    events: list[dict[str, Any]] = []
    for index, message in enumerate(messages):
        if message.get("role") != "assistant":
            continue
        usage = message.get("_usage")
        exact = isinstance(usage, dict) and (
            usage.get("input_tokens") is not None
            or usage.get("output_tokens") is not None
        )
        if exact:
            input_tokens = max(0, int(usage.get("input_tokens") or 0))
            output_tokens = max(0, int(usage.get("output_tokens") or 0))
            model = str(usage.get("model") or fallback_model)
        else:
            # Legacy/provider fallback: approximate the context sent for this call, not
            # merely the unique text stored in the conversation. Replayed context is billed.
            input_tokens = sum(
                _estimate_tokens(item.get("content"))
                for item in messages[:index]
                if item.get("role") != "assistant"
            )
            output_tokens = _estimate_tokens(message.get("content"))
            model = fallback_model
        _, spec = _model_pricing(model)
        cost = (
            input_tokens * float(spec.get("input_per_1m", 0))
            + output_tokens * float(spec.get("output_per_1m", 0))
        ) / 1_000_000
        events.append({
            "model": model,
            "provider": spec.get("provider", "Unknown"),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "date": _message_date(message, fallback_date),
            "exact": exact,
        })
    return events


def _dashboard_data(manager: Any) -> dict[str, Any]:
    sessions = []
    by_provider: dict[str, dict[str, Any]] = {}
    by_model: dict[str, dict[str, Any]] = {}
    daily: dict[str, dict[str, Any]] = {}
    daily_session_ids: dict[str, set[str]] = defaultdict(set)
    total_input = total_output = 0

    for record in manager.session_store.list():
        messages = _read_messages(manager.session_store, record.session_id)
        fallback_model = record.model or manager.model or "unknown"
        fallback_date = (record.updated_at or "")[:10] or "Unknown"
        events = _session_usage_events(messages, fallback_model, fallback_date)
        input_tokens = sum(event["input_tokens"] for event in events)
        output_tokens = sum(event["output_tokens"] for event in events)
        cost = sum(event["cost"] for event in events)
        used_models = list(dict.fromkeys(event["model"] for event in events))
        used_providers = list(dict.fromkeys(event["provider"] for event in events))
        model = used_models[-1] if len(used_models) == 1 else f"Multiple ({len(used_models)})"
        provider = used_providers[-1] if len(used_providers) == 1 else "Multiple"
        exact_count = sum(bool(event["exact"]) for event in events)
        measurement = (
            "reported" if events and exact_count == len(events)
            else "mixed" if exact_count
            else "estimated"
        )
        total_input += input_tokens
        total_output += output_tokens
        sessions.append({
            "id": record.session_id, "title": record.title or "New session",
            "model": model, "provider": provider, "messages": len(messages),
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens, "cost_usd": cost,
            "datetime": record.updated_at or "",
            "measurement": measurement, "model_calls": len(events),
        })
        session_providers: set[str] = set()
        session_models: set[str] = set()
        for event in events:
            provider_name = event["provider"]
            model_name = event["model"]
            p = by_provider.setdefault(provider_name, {"sessions": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0})
            p["input_tokens"] += event["input_tokens"]; p["output_tokens"] += event["output_tokens"]; p["cost"] += event["cost"]
            m = by_model.setdefault(model_name, {"sessions": 0, "tokens": 0, "cost": 0.0, "provider": provider_name})
            m["tokens"] += event["input_tokens"] + event["output_tokens"]; m["cost"] += event["cost"]
            date = event["date"]
            d = daily.setdefault(date, {"cost": 0.0, "tokens": 0, "sessions": 0})
            d["cost"] += event["cost"]; d["tokens"] += event["input_tokens"] + event["output_tokens"]
            daily_session_ids[date].add(record.session_id)
            session_providers.add(provider_name)
            session_models.add(model_name)
        for provider_name in session_providers:
            by_provider[provider_name]["sessions"] += 1
        for model_name in session_models:
            by_model[model_name]["sessions"] += 1

    for date, ids in daily_session_ids.items():
        daily[date]["sessions"] = len(ids)

    return {
        "sessions": sessions,
        "aggregates": {
            "total_cost_usd": sum(s["cost_usd"] for s in sessions),
            "total_tokens": total_input + total_output,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "session_count": len(sessions),
            "by_provider": by_provider, "by_model": by_model,
            "daily": dict(sorted(daily.items())),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def _provider_key(manager: Any, name: str, env_name: str) -> tuple[str, dict[str, Any]]:
    profile = manager.secrets.get(f"provider:{name}") or {}
    return str(profile.get("api_key") or os.environ.get(env_name) or "").strip(), profile


def _account_summary(manager: Any) -> dict[str, Any]:
    """Fetch official account-level billing signals without ever returning credentials."""
    result: dict[str, Any] = {}

    deepseek_key, deepseek_profile = _provider_key(manager, "deepseek", "DEEPSEEK_API_KEY")
    if deepseek_key:
        base = str(deepseek_profile.get("base_url") or "https://api.deepseek.com").rstrip("/")
        try:
            response = httpx.get(
                f"{base}/user/balance",
                headers={"Authorization": f"Bearer {deepseek_key}", "Accept": "application/json"},
                timeout=8,
            )
            response.raise_for_status()
            payload = response.json()
            balances = [
                {
                    "currency": str(item.get("currency", "")),
                    "total": float(item.get("total_balance") or 0),
                    "granted": float(item.get("granted_balance") or 0),
                    "topped_up": float(item.get("topped_up_balance") or 0),
                }
                for item in payload.get("balance_infos", [])
                if isinstance(item, dict)
            ]
            result["DeepSeek"] = {
                "configured": True, "status": "available",
                "available": bool(payload.get("is_available")), "balances": balances,
                "scope": "account", "source": "official",
            }
        except Exception:
            result["DeepSeek"] = {
                "configured": True, "status": "error", "balances": [],
                "scope": "account", "source": "official",
                "message": "Balance could not be retrieved with the configured key.",
            }

    openai_key, _ = _provider_key(manager, "openai", "OPENAI_API_KEY")
    if openai_key:
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        try:
            response = httpx.get(
                "https://api.openai.com/v1/organization/costs",
                params={"start_time": int(month_start.timestamp()), "limit": 31},
                headers={"Authorization": f"Bearer {openai_key}", "Accept": "application/json"},
                timeout=8,
            )
            response.raise_for_status()
            payload = response.json()
            spent = 0.0
            currency = "usd"
            for bucket in payload.get("data", []):
                for item in bucket.get("results", []):
                    amount = item.get("amount") or {}
                    spent += float(amount.get("value") or 0)
                    currency = str(amount.get("currency") or currency)
            result["OpenAI"] = {
                "configured": True, "status": "usage_available",
                "month_spend": spent, "currency": currency.upper(),
                "balances": [], "scope": "organization", "source": "official",
                "message": "Official month-to-date spend; OpenAI does not expose remaining credit here.",
            }
        except httpx.HTTPStatusError as exc:
            result["OpenAI"] = {
                "configured": True,
                "status": "admin_key_required" if exc.response.status_code in {401, 403} else "error",
                "balances": [], "scope": "organization", "source": "official",
                "message": "An OpenAI Admin API Key is required for official organization costs.",
            }
        except Exception:
            result["OpenAI"] = {
                "configured": True, "status": "error", "balances": [],
                "scope": "organization", "source": "official",
                "message": "Official costs could not be retrieved.",
            }

    return {"accounts": result, "updated_at": datetime.now(timezone.utc).isoformat()}


def create_dashboard_routes(app: FastAPI, manager: Any) -> None:
    @app.get("/v1/dashboard/health")
    def dashboard_health() -> dict[str, Any]:
        return {"ok": True, "models_count": len(MODEL_REGISTRY), "sessions_count": len(manager.session_store.list())}

    @app.get("/v1/dashboard/data")
    def dashboard_data() -> dict[str, Any]:
        return _dashboard_data(manager)

    @app.get("/v1/dashboard/models")
    def dashboard_models() -> dict[str, Any]:
        return {
            "registry": _dashboard_registry(manager),
            "provider_summary": _provider_summary(),
            "benchmarks": BENCHMARKS,
            "benchmark_meta": BENCHMARK_META,
            "media_capacity": MEDIA_CAPACITY,
            "benchmarks_updated_at": "2026-07-23",
        }

    @app.get("/v1/dashboard/providers")
    def dashboard_providers() -> dict[str, Any]:
        return {"providers": _provider_summary()}

    @app.get("/v1/dashboard/accounts")
    def dashboard_accounts() -> dict[str, Any]:
        return _account_summary(manager)
