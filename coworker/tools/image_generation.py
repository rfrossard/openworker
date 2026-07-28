"""Workspace-scoped, approval-gated image generation for artifacts."""

from __future__ import annotations

import base64
import binascii
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

import aisuite as ai


_MODEL = "gemini-3.1-flash-lite-image"
_SIZES = {"1024x1024", "1536x1024", "1024x1536"}
_QUALITIES = {"low", "medium", "high"}
_MAX_IMAGE_BYTES = 30 * 1024 * 1024
_ESTIMATED_IMAGE_COST_USD = 0.0336
_ASPECT_RATIOS = {
    "1024x1024": "1:1",
    # The presentation canvas is 16:9. The public size is retained for backwards
    # compatibility with saved plans; Gemini chooses the exact 1K pixel dimensions.
    "1536x1024": "16:9",
    "1024x1536": "2:3",
}

_SCHEMA = {
    "type": "function",
    "function": {
        "name": "generate_image",
        "description": (
            "Generate one original image for an artifact using the user's configured "
            "Gemini API with Nano Banana 2 Lite. This is a paid external call and always "
            "requires approval. The PNG is written atomically inside the current workspace."
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
                    "description": (
                        "Accepted for compatibility with saved presentation plans. Nano "
                        "Banana 2 Lite always renders its supported 1K quality."
                    ),
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
            profile = secrets.get("provider:gemini") or {}
            api_key = str(
                profile.get("api_key")
                or os.environ.get("GEMINI_API_KEY")
                or os.environ.get("GOOGLE_API_KEY")
                or ""
            ).strip()
            if not api_key:
                return {
                    "ok": False,
                    "error": (
                        "Gemini image generation is not configured. Add a Gemini API key "
                        "in Settings or use sourced visuals."
                    ),
                }
            from google import genai

            image_client = genai.Client(api_key=api_key)

        try:
            response = image_client.interactions.create(
                model=_MODEL,
                input=clean_prompt,
                response_format={
                    "type": "image",
                    "aspect_ratio": _ASPECT_RATIOS[size],
                    "image_size": "1K",
                },
            )
            encoded = response.output_image.data
            payload = (
                bytes(encoded)
                if isinstance(encoded, (bytes, bytearray))
                else base64.b64decode(str(encoded or ""), validate=True)
            )
        except (AttributeError, binascii.Error, ValueError):
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
            "provider": "Google",
            "model": _MODEL,
            "size": size,
            "quality": "1K",
            "requested_quality": quality,
            "bytes": len(payload),
            "operation_usage": {
                "type": "image",
                "provider": "Google",
                "model": _MODEL,
                "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
                "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
                "units": 1,
                "estimated_cost_usd": _ESTIMATED_IMAGE_COST_USD,
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
