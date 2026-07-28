"""Workspace-scoped, approval-gated image generation for artifacts."""

from __future__ import annotations

import base64
import binascii
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

import aisuite as ai


_MODEL = "gpt-image-1.5"
_SIZES = {"1024x1024", "1536x1024", "1024x1536"}
_QUALITIES = {"low", "medium", "high"}
_MAX_IMAGE_BYTES = 30 * 1024 * 1024
_ESTIMATED_IMAGE_COST_USD = {
    ("low", "1024x1024"): 0.009,
    ("low", "1024x1536"): 0.013,
    ("low", "1536x1024"): 0.013,
    ("medium", "1024x1024"): 0.034,
    ("medium", "1024x1536"): 0.050,
    ("medium", "1536x1024"): 0.050,
    ("high", "1024x1024"): 0.133,
    ("high", "1024x1536"): 0.200,
    ("high", "1536x1024"): 0.200,
}

_SCHEMA = {
    "type": "function",
    "function": {
        "name": "generate_image",
        "description": (
            "Generate one original image for an artifact using the user's configured "
            "OpenAI image API. This is a paid external call and always requires approval. "
            "The PNG is written atomically inside the current workspace."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "A precise visual brief. Do not request fabricated data, quotes, "
                        "logos, real-person endorsements, or misleading documentary imagery."
                    ),
                },
                "path": {
                    "type": "string",
                    "description": (
                        "Workspace-relative .png destination, normally "
                        "reports/assets/<descriptive-name>.png."
                    ),
                },
                "size": {
                    "type": "string",
                    "enum": sorted(_SIZES),
                    "description": "Use 1536x1024 for widescreen presentation visuals.",
                },
                "quality": {
                    "type": "string",
                    "enum": sorted(_QUALITIES),
                    "description": "Image quality and cost tier.",
                },
            },
            "required": ["prompt", "path"],
        },
    },
}


def make_generate_image_tool(
    secrets: Any,
    *,
    workspace: Path | str,
    client: Optional[Any] = None,
):
    root = Path(workspace).expanduser().resolve()

    def generate_image(
        prompt: str,
        path: str,
        size: str = "1536x1024",
        quality: str = "medium",
    ) -> dict[str, Any]:
        """Generate an original artifact image and save it inside the workspace."""
        clean_prompt = str(prompt or "").strip()
        if not clean_prompt:
            return {"ok": False, "error": "An image prompt is required."}
        if len(clean_prompt) > 8_000:
            return {"ok": False, "error": "The image prompt is too long."}
        if size not in _SIZES:
            return {"ok": False, "error": "Unsupported image size."}
        if quality not in _QUALITIES:
            return {"ok": False, "error": "Unsupported image quality."}

        raw_path = Path(str(path or "").strip())
        if not str(raw_path) or raw_path.is_absolute() or raw_path.suffix.lower() != ".png":
            return {
                "ok": False,
                "error": "Choose a workspace-relative destination ending in .png.",
            }
        target = (root / raw_path).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return {"ok": False, "error": "Image path escapes the workspace."}

        image_client = client
        if image_client is None:
            profile = secrets.get("provider:openai") or {}
            api_key = str(
                profile.get("api_key") or os.environ.get("OPENAI_API_KEY") or ""
            ).strip()
            if not api_key:
                return {
                    "ok": False,
                    "error": (
                        "OpenAI image generation is not configured. Add an OpenAI API "
                        "key in Settings or use sourced visuals."
                    ),
                }
            from openai import OpenAI

            image_client = OpenAI(api_key=api_key)

        try:
            response = image_client.images.generate(
                model=_MODEL,
                prompt=clean_prompt,
                size=size,
                quality=quality,
                output_format="png",
                n=1,
            )
            encoded = str(response.data[0].b64_json or "")
            payload = base64.b64decode(encoded, validate=True)
        except (IndexError, AttributeError, binascii.Error, ValueError):
            return {"ok": False, "error": "The image provider returned invalid image data."}
        except Exception as exc:
            # Provider exceptions can include request IDs but must never echo request
            # bodies, authorization headers, or credential-bearing response objects.
            name = type(exc).__name__
            return {"ok": False, "error": f"Image generation failed ({name})."}

        if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
            return {"ok": False, "error": "The image provider did not return a PNG."}
        if len(payload) > _MAX_IMAGE_BYTES:
            return {"ok": False, "error": "The generated image exceeds the 30 MB limit."}

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(
                prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
            )
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, target)
            except Exception:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
                raise
        except OSError:
            return {"ok": False, "error": "Could not save the generated image."}

        usage = getattr(response, "usage", None)
        return {
            "ok": True,
            "path": str(target.relative_to(root)),
            "provider": "OpenAI",
            "model": _MODEL,
            "size": size,
            "quality": quality,
            "bytes": len(payload),
            "operation_usage": {
                "type": "image",
                "provider": "OpenAI",
                "model": _MODEL,
                "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
                "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
                "units": 1,
                "estimated_cost_usd": _ESTIMATED_IMAGE_COST_USD[(quality, size)],
                "measurement": "estimated",
            },
        }

    generate_image.__name__ = "generate_image"
    generate_image.__doc__ = _SCHEMA["function"]["description"]
    generate_image.__aisuite_tool_metadata__ = ai.ToolMetadata(
        name="generate_image",
        category="external_api",
        risk_level="high",
        capabilities=["network", "write", "paid"],
        requires_approval=True,
    )
    generate_image.__coworker_schema__ = _SCHEMA
    return generate_image
