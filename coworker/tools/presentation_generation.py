"""Deterministic, workspace-scoped PPTX and slide-PDF generation."""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import aisuite as ai


_MAX_SLIDES = 40
_MAX_BULLETS = 6
_WIDE_WIDTH = 13.333
_WIDE_HEIGHT = 7.5
_COPYRIGHT_OWNER = "Frossard"
_LAYOUTS = {
    "auto", "image-right", "image-left", "statement", "two-column", "quote", "section",
    "title-only", "big-number", "checklist", "timeline", "process", "comparison",
    "pros-cons", "three-columns", "four-cards", "metric-grid", "image-background",
    "image-top", "image-bottom", "agenda", "conclusion", "table", "bar-chart",
    "donut-chart", "flow-diagram", "org-chart", "roadmap", "map",
}
_TEMPLATES = {
    "atlas": {"background": "F7F8FA", "ink": "1A1F2C", "muted": "5B6577", "accent": "2F6BFF", "cover": "1A1F2C"},
    "aurora": {"background": "F3F5FA", "ink": "101827", "muted": "667085", "accent": "8B5CF6", "cover": "101827"},
    "boardroom": {"background": "101713", "ink": "F4F1DF", "muted": "B1B9A5", "accent": "F6C453", "cover": "101713", "gradient": "1C2A22", "transition": "wipe", "font": "Chalkboard SE"},
    "editorial": {"id": "editorial", "background": "F5F0E6", "ink": "211D19", "muted": "766F63", "accent": "B63C2E", "cover": "211D19", "gradient": "E7DFD1", "transition": "fade", "composition": "editorial", "font": "Georgia", "title_size": 29},
    "forest": {"background": "F2F7F3", "ink": "17352B", "muted": "64756C", "accent": "2F855A", "cover": "17352B"},
    "midnight": {"background": "171D2D", "ink": "F6F8FC", "muted": "AAB4C8", "accent": "5B8CFF", "cover": "090D18"},
    "monochrome": {"background": "FAFAFA", "ink": "171717", "muted": "737373", "accent": "525252", "cover": "171717"},
    "ocean": {"background": "F0F9FF", "ink": "123047", "muted": "617887", "accent": "0891B2", "cover": "123047"},
    "paper": {"id": "paper", "background": "F7F1DF", "ink": "25231F", "muted": "6F695D", "accent": "637D52", "cover": "25231F", "gradient": "E9DFC7", "transition": "fade", "font": "Bradley Hand ITC", "title_size": 30},
    "plum": {"background": "FBF5FA", "ink": "321B3A", "muted": "806E83", "accent": "A855A0", "cover": "321B3A"},
    "signal": {"background": "FFF7ED", "ink": "18181B", "muted": "71717A", "accent": "EF4444", "cover": "18181B"},
    "studio": {"background": "F5F7FA", "ink": "20242C", "muted": "687180", "accent": "14B8A6", "cover": "20242C"},
    "neon-flow": {"background": "0F172A", "ink": "F8FAFC", "muted": "94A3B8", "accent": "22D3EE", "cover": "07111F", "gradient": "312E81", "transition": "push"},
    "sunrise": {"background": "FFF7ED", "ink": "3B1D2A", "muted": "9A6B5B", "accent": "F97316", "cover": "3B1D2A", "gradient": "FED7AA", "transition": "fade"},
    "cyber-grid": {"background": "0F172A", "ink": "E0F2FE", "muted": "7DD3FC", "accent": "38BDF8", "cover": "020617", "gradient": "172554", "transition": "wipe"},
    "prism": {"background": "FAF5FF", "ink": "24123A", "muted": "7E5A91", "accent": "D946EF", "cover": "24123A", "gradient": "DBEAFE", "transition": "split"},
    "velocity": {"background": "FFF1F2", "ink": "111827", "muted": "7F5B64", "accent": "F43F5E", "cover": "111827", "gradient": "FFE4E6", "transition": "push"},
    "ember": {"background": "431407", "ink": "FFF7ED", "muted": "FDBA74", "accent": "F97316", "cover": "2A1208", "gradient": "7C2D12", "transition": "cover"},
    "glacier": {"background": "ECFEFF", "ink": "0C4A6E", "muted": "5E8798", "accent": "06B6D4", "cover": "0C4A6E", "gradient": "CFFAFE", "transition": "fade"},
    "bloom": {"background": "FFF1F2", "ink": "4A1830", "muted": "98687D", "accent": "EC4899", "cover": "4A1830", "gradient": "FCE7F3", "transition": "split"},
    "orbit": {"background": "151936", "ink": "F5F3FF", "muted": "A5B4FC", "accent": "818CF8", "cover": "090B20", "gradient": "312E81", "transition": "cover"},
    "horizon": {"background": "F0F9FF", "ink": "172554", "muted": "64748B", "accent": "0EA5E9", "cover": "172554", "gradient": "DBEAFE", "transition": "wipe"},
    "aurora-glass": {"background": "ECFDF5", "ink": "10233C", "muted": "667C85", "accent": "14B8A6", "cover": "10233C", "gradient": "E0E7FF", "transition": "fade"},
    "executive-gradient": {"background": "F8FAFC", "ink": "111827", "muted": "64748B", "accent": "D4A72C", "cover": "111827", "gradient": "E2E8F0", "transition": "fade"},
    "data-wave": {"background": "F0F9FF", "ink": "082F49", "muted": "5B7484", "accent": "0284C7", "cover": "082F49", "gradient": "F0FDFA", "transition": "push"},
    "financial-pulse": {"background": "F0FDF4", "ink": "052E16", "muted": "5E7866", "accent": "22C55E", "cover": "052E16", "gradient": "DCFCE7", "transition": "wipe"},
    "editorial-motion": {"background": "FFFBEB", "ink": "292524", "muted": "78716C", "accent": "E11D48", "cover": "292524", "gradient": "FFE4E6", "transition": "split"},
    "photo-story": {"background": "374151", "ink": "F9FAFB", "muted": "D1D5DB", "accent": "F59E0B", "cover": "111827", "gradient": "111827", "transition": "fade"},
    "cinematic-frame": {"background": "18181B", "ink": "FAFAFA", "muted": "A1A1AA", "accent": "EAB308", "cover": "09090B", "gradient": "27272A", "transition": "cover"},
    "dashboard-pro": {"background": "0D1617", "ink": "EDF7F1", "muted": "A8BBB0", "accent": "4ADE80", "cover": "0D1617", "gradient": "142527", "transition": "push", "font": "Aptos Display"},
    "science-spectrum": {"background": "F0FDFA", "ink": "134E4A", "muted": "64748B", "accent": "8B5CF6", "cover": "134E4A", "gradient": "F5F3FF", "transition": "wipe"},
    "impact-report": {"background": "FAFAF9", "ink": "1C1917", "muted": "78716C", "accent": "16A34A", "cover": "1C1917", "gradient": "F0FDF4", "transition": "fade"},
    "science-studio": {"background": "070B12", "ink": "E8F7FA", "muted": "94A9B3", "accent": "56CFE1", "cover": "070B12", "gradient": "122B3A", "transition": "fade", "composition": "photo-right"},
    "digital-pulse": {"background": "F8FAFC", "ink": "17191C", "muted": "667085", "accent": "C7F43B", "cover": "17191C", "gradient": "334155", "transition": "push", "composition": "photo-left"},
    "eco-sketchbook": {"background": "FFFDFC", "ink": "1F2937", "muted": "73807B", "accent": "4FA8A5", "cover": "FFFDFC", "gradient": "FDE3D4", "transition": "wipe", "composition": "botanical", "cover_ink": "1F2937"},
    "social-workshop": {"background": "FFFDF8", "ink": "292524", "muted": "78716C", "accent": "F5C542", "cover": "292524", "gradient": "57534E", "transition": "split", "composition": "collage"},
    "environmental-fieldwork": {"background": "FFFEFB", "ink": "12372A", "muted": "708276", "accent": "91B29A", "cover": "FFFEFB", "gradient": "EAF4EC", "transition": "wipe", "composition": "torn-photo", "cover_ink": "12372A"},
    "personal-brand": {"background": "F7F3F2", "ink": "09090B", "muted": "71717A", "accent": "0B5CAD", "cover": "F7F3F2", "gradient": "EEE9E7", "transition": "cover", "composition": "editorial", "cover_ink": "09090B"},
    "botanical-noir": {"background": "102016", "ink": "F0F8E8", "muted": "B1C7A9", "accent": "A8D67B", "cover": "102016", "gradient": "1B3A25", "transition": "fade", "composition": "botanical", "font": "Georgia"},
    "nature-balance": {"background": "0D2C22", "ink": "F7FFF9", "muted": "B7CCC0", "accent": "A8D5BA", "cover": "0D2C22", "gradient": "0B3B50", "transition": "cover", "composition": "full-bleed"},
    "storytelling-lab": {"background": "F7F3EB", "ink": "111111", "muted": "69635A", "accent": "2C8C8C", "cover": "F7F3EB", "gradient": "EEE8DC", "transition": "push", "composition": "minimal-frame", "cover_ink": "111111"},
    "agricultural-motion": {"background": "263A18", "ink": "FFFFFF", "muted": "CBD5B5", "accent": "A8C96A", "cover": "263A18", "gradient": "566B25", "transition": "push", "composition": "full-bleed"},
    "cultural-heritage": {"background": "17120F", "ink": "F6ECD8", "muted": "C2B29C", "accent": "B88A3B", "cover": "17120F", "gradient": "3B2419", "transition": "fade", "composition": "heritage"},
    "cyan-infographic": {"background": "F4FCFD", "ink": "083344", "muted": "52727B", "accent": "0EA5C9", "cover": "F4FCFD", "gradient": "D7F3F7", "transition": "wipe", "composition": "infographic", "cover_ink": "083344"},
    "growth-momentum": {"background": "07131C", "ink": "F8FAFC", "muted": "94A3B8", "accent": "38BDF8", "cover": "07131C", "gradient": "0C4A6E", "transition": "push", "composition": "infographic"},
    "home-investment": {"background": "FCFAF7", "ink": "312E2B", "muted": "78716C", "accent": "F0645A", "cover": "FCFAF7", "gradient": "F4E8DA", "transition": "split", "composition": "minimal-frame", "cover_ink": "312E2B"},
    "museum-editorial": {"background": "15110E", "ink": "F2E7D2", "muted": "B8A998", "accent": "9D6B2F", "cover": "15110E", "gradient": "30221B", "transition": "fade", "composition": "heritage"},
    "itau": {"id": "itau", "background": "001E60", "ink": "FFFFFF", "muted": "C8D4F1", "accent": "EC7000", "cover": "001E60", "gradient": "173B80", "transition": "fade", "font": "Arial", "title_size": 31},
    "tron": {"background": "051016", "ink": "EAF9FF", "muted": "A1CDD6", "accent": "38DDF5", "cover": "051016", "gradient": "0A2432", "transition": "push", "font": "Aptos Display"},
    "minecraft": {"id": "minecraft", "background": "24351F", "ink": "F7F3D9", "muted": "C5D6AD", "accent": "78B849", "cover": "24351F", "gradient": "426F38", "transition": "wipe", "font": "Aptos Display"},
    "mckinsey": {"id": "mckinsey", "background": "FFFFFF", "ink": "12263F", "muted": "64748B", "accent": "1D5D9B", "cover": "12263F", "gradient": "EDF3F8", "transition": "fade", "font": "Arial", "title_size": 31},
    "accenture": {"id": "accenture", "background": "F7F4FA", "ink": "1A1A1A", "muted": "655D6B", "accent": "A100FF", "cover": "1A1A1A", "gradient": "EBDDFF", "transition": "push", "font": "Arial", "title_size": 31},
    "bcp": {"id": "bcp", "background": "FCFAF5", "ink": "172A4D", "muted": "766D5D", "accent": "F5B335", "cover": "172A4D", "gradient": "F2E5C8", "transition": "fade", "font": "Arial", "title_size": 31},
    "bain": {"id": "bain", "background": "FFFDFC", "ink": "1D1D1D", "muted": "716B68", "accent": "CC1F2F", "cover": "1D1D1D", "gradient": "F5E3E2", "transition": "cover", "font": "Arial", "title_size": 31},
}

_SCHEMA = {
    "type": "function",
    "function": {
        "name": "build_presentation",
        "description": (
            "Build an editable widescreen PPTX and a matching, genuinely paginated PDF "
            "from a structured slide specification. Local images are embedded in both, "
            "and rendered slide previews plus a contact sheet support visual review."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "subtitle": {"type": "string"},
                "cover_image_path": {
                    "type": "string",
                    "description": "Optional workspace-relative PNG or JPEG composed for the selected template cover.",
                },
                "slides": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "takeaway": {"type": "string"},
                            "metric_value": {"type": "string", "description": "Large metric for a big-number slide."},
                            "metric_label": {"type": "string", "description": "Plain-language explanation for the large metric."},
                            "visual_annotation": {"type": "string", "description": "One concise, evidence-backed annotation for a structured visual."},
                            "bullets": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    "Content rows. Use Label | Value for charts, pipe-separated "
                                    "cells for tables, Parent > Child for org charts, and Location | Value | Insight for maps."
                                ),
                            },
                            "image_path": {
                                "type": "string",
                                "description": "Optional workspace-relative PNG or JPEG.",
                            },
                            "image_caption": {"type": "string"},
                            "image_fit": {
                                "type": "string",
                                "enum": ["cover", "contain"],
                                "description": "Cover crops to fill; contain preserves the entire image.",
                            },
                            "image_focus": {
                                "type": "string",
                                "enum": ["left", "center", "right"],
                                "description": "Horizontal focal point used when cover-cropping.",
                            },
                            "image_required": {
                                "type": "boolean",
                                "description": "Fail instead of silently rendering this slide without its planned visual.",
                            },
                            "layout": {
                                "type": "string",
                                "enum": sorted(_LAYOUTS),
                                "description": "Intentional slide composition; auto selects image-right when an image exists.",
                            },
                            "sources": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["title"],
                    },
                },
                "pptx_path": {
                    "type": "string",
                    "description": "Workspace-relative destination ending in .pptx.",
                },
                "pdf_path": {
                    "type": "string",
                    "description": "Workspace-relative destination ending in .pdf.",
                },
                "accent_color": {
                    "type": "string",
                    "description": "Six-digit hex color without #.",
                },
                "template_id": {
                    "type": "string",
                    "enum": list(_TEMPLATES),
                    "description": "Editable built-in visual template.",
                },
                "template_path": {
                    "type": "string",
                    "description": "Optional workspace-relative .potx file; overrides template_id.",
                },
                "minimum_images": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": _MAX_SLIDES,
                    "description": "Fail when fewer images are embedded than the approved visual plan requires.",
                },
            },
            "required": ["title", "slides", "pptx_path", "pdf_path"],
        },
    },
}


def _safe_target(root: Path, raw: str, suffix: str) -> Path:
    value = Path(str(raw or "").strip())
    if not str(value) or value.is_absolute() or value.suffix.lower() != suffix:
        raise ValueError(f"Choose a workspace-relative destination ending in {suffix}.")
    target = (root / value).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("Presentation path escapes the workspace.") from exc
    return target


def _safe_image(root: Path, raw: str) -> Path | None:
    if not str(raw or "").strip():
        return None
    value = Path(str(raw).strip())
    if value.is_absolute() or value.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        raise ValueError("Slide images must be workspace-relative PNG or JPEG files.")
    target = (root / value).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("Slide image path escapes the workspace.") from exc
    if not target.is_file():
        raise ValueError(f"Slide image was not found: {value}")
    return target


def _safe_template(root: Path, raw: str) -> Path | None:
    if not str(raw or "").strip():
        return None
    value = Path(str(raw).strip())
    if value.is_absolute() or value.suffix.lower() != ".potx":
        raise ValueError("PowerPoint templates must be workspace-relative POTX files.")
    target = (root / value).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("PowerPoint template path escapes the workspace.") from exc
    if not target.is_file():
        raise ValueError(f"PowerPoint template was not found: {value}")
    return target


def _atomic_destination(target: Path) -> tuple[int, str]:
    target.parent.mkdir(parents=True, exist_ok=True)
    return tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)


def _editable_copy_of_potx(template: Path) -> Path:
    """Create a temporary macro-free PPTX package from a genuine POTX package."""
    fd, raw = tempfile.mkstemp(prefix=".openworker-template.", suffix=".pptx")
    os.close(fd)
    destination = Path(raw)
    template_type = b"application/vnd.openxmlformats-officedocument.presentationml.template.main+xml"
    presentation_type = b"application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"
    try:
        with zipfile.ZipFile(template, "r") as source, zipfile.ZipFile(
            destination, "w", compression=zipfile.ZIP_DEFLATED
        ) as output:
            names = source.namelist()
            if "[Content_Types].xml" not in names or "ppt/presentation.xml" not in names:
                raise ValueError("The POTX package is missing required PowerPoint parts.")
            for name in names:
                data = source.read(name)
                if name == "[Content_Types].xml":
                    if template_type not in data and presentation_type not in data:
                        raise ValueError("The file is not a supported PowerPoint template.")
                    data = data.replace(template_type, presentation_type)
                output.writestr(name, data)
        return destination
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def _cover_image(
    path: Path,
    width: int = 1200,
    height: int = 750,
    *,
    fit: str = "cover",
    focus: str = "center",
) -> BytesIO:
    from PIL import Image, ImageOps

    with Image.open(path) as source:
        source_rgb = source.convert("RGB")
        if fit == "contain":
            fitted = ImageOps.pad(source_rgb, (width, height), color="#EEF1F5")
        else:
            centering = {"left": (0.2, 0.5), "center": (0.5, 0.5), "right": (0.8, 0.5)}[focus]
            fitted = ImageOps.fit(source_rgb, (width, height), centering=centering)
        stream = BytesIO()
        fitted.save(stream, format="JPEG", quality=92, optimize=True)
    stream.seek(0)
    return stream


def _normalize_slides(root: Path, slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not slides or len(slides) > _MAX_SLIDES:
        raise ValueError(f"Provide between 1 and {_MAX_SLIDES} content slides.")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(slides, 1):
        if not isinstance(item, dict):
            raise ValueError(f"Slide {index} is not an object.")
        title = str(item.get("title") or "").strip()
        if not title:
            raise ValueError(f"Slide {index} needs a title.")
        bullets = [
            str(value).strip()
            for value in list(item.get("bullets") or [])[:_MAX_BULLETS]
            if str(value).strip()
        ]
        sources = [
            str(value).strip()
            for value in list(item.get("sources") or [])
            if str(value).strip().startswith(("https://", "http://"))
        ]
        normalized.append(
            {
                "title": title[:140],
                "takeaway": str(item.get("takeaway") or "").strip()[:280],
                "bullets": [value[:360] for value in bullets],
                "image": _safe_image(root, str(item.get("image_path") or "")),
                "image_caption": str(item.get("image_caption") or "").strip()[:220],
                "image_fit": str(item.get("image_fit") or "cover").strip().lower(),
                "image_focus": str(item.get("image_focus") or "center").strip().lower(),
                "image_required": bool(item.get("image_required")),
                "sources": sources,
                "layout": str(item.get("layout") or "auto").strip().lower(),
                "metric_value": str(item.get("metric_value") or "").strip()[:80],
                "metric_label": str(item.get("metric_label") or "").strip()[:220],
                "visual_annotation": str(item.get("visual_annotation") or "").strip()[:180],
            }
        )
        if normalized[-1]["layout"] not in _LAYOUTS:
            raise ValueError(f"Slide {index} has an unsupported layout.")
        if normalized[-1]["image_fit"] not in {"cover", "contain"}:
            raise ValueError(f"Slide {index} has an unsupported image fit.")
        if normalized[-1]["image_focus"] not in {"left", "center", "right"}:
            raise ValueError(f"Slide {index} has an unsupported image focus.")
        if normalized[-1]["image_required"] and not normalized[-1]["image"]:
            raise ValueError(f"Slide {index} requires its planned image before rendering.")
        layout = normalized[-1]["layout"]
        if layout in {"bar-chart", "donut-chart"} and len(_chart_values(bullets)) < 2:
            raise ValueError(
                f"Slide {index} needs at least two chart rows formatted as Label | Value."
            )
        if layout == "table":
            rows = _table_rows(bullets)
            if len(rows) < 2 or max((len(row) for row in rows), default=0) < 2:
                raise ValueError(
                    f"Slide {index} needs a header and at least one pipe-separated table row."
                )
        if layout in {"flow-diagram", "org-chart", "roadmap"} and len(bullets) < 2:
            raise ValueError(f"Slide {index} needs at least two connected items.")
        if layout == "map" and len(_table_rows(bullets)) < 2:
            raise ValueError(
                f"Slide {index} needs at least two evidence-backed locations formatted as Location | Value | Insight."
            )
    return normalized


def _big_number_parts(spec: dict[str, Any]) -> tuple[str, str]:
    """Extract the display metric from structured research, never a whole data row."""
    explicit_value = str(spec.get("metric_value") or "").strip()
    explicit_label = str(spec.get("metric_label") or "").strip()
    if explicit_value:
        return explicit_value, explicit_label or str(spec.get("takeaway") or spec["title"])
    metric_pattern = re.compile(r"(?:(?:US\$|R\$|[$€£])\s*)?\d[\d.,]*(?:\s?(?:bilh(?:ão|ões)|milh(?:ão|ões)|billion|million|trillion|bn?|%|x|k|m))?", re.I)

    def select_metric(value: str) -> str:
        matches = [match.group(0).strip() for match in metric_pattern.finditer(value)]
        def score(metric: str) -> tuple[int, int]:
            value_score = (100 if re.search(r"(?:US\$|R\$|[$€£])", metric) else 0)
            value_score += 50 if re.search(r"(?:million|billion|trillion|milh|bilh|\bbn?\b)", metric, re.I) else 0
            value_score += 20 if "%" in metric else 0
            value_score -= 35 if re.fullmatch(r"(?:19|20)\d{2}", metric) else 0
            return value_score, len(metric)
        return max(matches, key=score, default="")

    candidates = list(spec.get("bullets") or [])
    candidate = next((item for item in candidates if select_metric(item)), candidates[0] if candidates else "42%")
    parts = [part.strip() for part in candidate.split("|") if part.strip()]
    if len(parts) >= 2:
        numeric = max((select_metric(part) for part in parts), key=len, default=parts[0])
        return numeric, next((part for part in parts if part != numeric), str(spec.get("takeaway") or spec["title"]))
    metric = select_metric(candidate)
    if metric:
        label = re.sub(r"\s*\[C\d+(?:,\s*C\d+)*\]", "", candidate.replace(metric, ""))
        label = re.sub(r"\s+", " ", re.sub(r"^[\s:—–-]+|[\s:—–-]+$", "", label))
        return metric, label or str(spec.get("takeaway") or spec["title"])
    return candidate, str(spec.get("takeaway") or spec["title"])


def _consistent_title_size(slides: list[dict[str, Any]], baseline: int = 32) -> int:
    """Fit the longest ordinary title once, so titles remain uniform across a deck."""
    longest = max((len(str(slide.get("title") or "")) for slide in slides), default=0)
    if longest > 112:
        return min(baseline, 23)
    if longest > 82:
        return min(baseline, 26)
    if longest > 58:
        return min(baseline, 29)
    return baseline


def _split_semantic_row(value: str) -> list[str]:
    return [part.strip() for part in str(value).split("|") if part.strip()]


def _chart_values(values: list[str]) -> list[tuple[str, float]]:
    parsed: list[tuple[str, float]] = []
    for value in values[:6]:
        parts = _split_semantic_row(value)
        if len(parts) < 2:
            parts = [part.strip() for part in str(value).rsplit(":", 1)]
        if len(parts) < 2:
            continue
        try:
            number = float(parts[-1].replace("%", "").replace(",", ""))
        except ValueError:
            continue
        parsed.append((parts[0][:50], number))
    return parsed


def _table_rows(values: list[str]) -> list[list[str]]:
    rows = [_split_semantic_row(value)[:5] for value in values[:6]]
    return [row for row in rows if row]


def _org_edges(values: list[str]) -> list[tuple[str, str]]:
    edges: list[tuple[str, str]] = []
    for value in values[:6]:
        if ">" not in value:
            continue
        parent, child = (part.strip() for part in value.split(">", 1))
        if parent and child:
            edges.append((parent[:50], child[:50]))
    return edges


def _quality_gate(slides: list[dict[str, Any]]) -> dict[str, Any]:
    warnings: list[str] = []
    checks = {
        "semantic_data_valid": True,
        "visual_plan_complete": all(
            not slide["image_required"] or bool(slide["image"]) for slide in slides
        ),
        "titles_concise": True,
        "layout_variety": True,
        "data_sources_present": True,
    }
    for index, slide in enumerate(slides, 1):
        if len(slide["title"]) > 82:
            checks["titles_concise"] = False
            warnings.append(f"Slide {index} title may wrap excessively.")
        if slide["layout"] in {"table", "bar-chart", "donut-chart"} and not slide["sources"]:
            checks["data_sources_present"] = False
            warnings.append(f"Slide {index} presents data without a source.")
    for index in range(2, len(slides)):
        if slides[index]["layout"] == slides[index - 1]["layout"] == slides[index - 2]["layout"]:
            checks["layout_variety"] = False
            warnings.append(
                f"Slides {index - 1}-{index + 1} repeat the same layout; consider varying the rhythm."
            )
            break
    score = max(0, 100 - 8 * len(warnings))
    critical = not checks["semantic_data_valid"] or not checks["visual_plan_complete"]
    return {
        "passed": not critical,
        "score": score,
        "checks": checks,
        "warnings": warnings,
    }


def _copyright_notice() -> str:
    """Return the consistent ownership mark used on every rendered slide."""
    return f"© {_COPYRIGHT_OWNER} · {datetime.now().strftime('%B %Y')}"


def _add_pptx(
    destination: str,
    *,
    title: str,
    subtitle: str,
    slides: list[dict[str, Any]],
    style: dict[str, str],
    cover_image: Path | None = None,
    template: Path | None = None,
) -> None:
    from pptx import Presentation
    from pptx.chart.data import ChartData
    from pptx.dml.color import RGBColor
    from pptx.enum.chart import XL_CHART_TYPE, XL_DATA_LABEL_POSITION, XL_LEGEND_POSITION
    from pptx.enum.shapes import MSO_CONNECTOR
    from pptx.enum.text import PP_ALIGN
    from pptx.oxml.xmlchemy import OxmlElement
    from pptx.util import Inches, Pt

    editable_template = _editable_copy_of_potx(template) if template else None
    try:
        deck = Presentation(str(editable_template)) if editable_template else Presentation()
    finally:
        if editable_template:
            editable_template.unlink(missing_ok=True)
    deck.slide_width = Inches(_WIDE_WIDTH)
    deck.slide_height = Inches(_WIDE_HEIGHT)
    background = RGBColor.from_string(style["background"])
    ink = RGBColor.from_string(style["ink"])
    muted = RGBColor.from_string(style["muted"])
    accent_rgb = RGBColor.from_string(style["accent"])
    cover_rgb = RGBColor.from_string(style["cover"])
    cover_ink = RGBColor.from_string(style.get("cover_ink", "FFFFFF"))
    deck_font = style.get("font", "Aptos")
    title_size = _consistent_title_size(slides, int(style.get("title_size", 35)))
    copyright_notice = _copyright_notice()
    blank_layout = next(
        (layout for layout in deck.slide_layouts if "blank" in layout.name.lower()),
        deck.slide_layouts[-1],
    )

    def textbox(slide, text, x, y, w, h, size, color=ink, bold=False):
        shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        frame = shape.text_frame
        frame.clear()
        frame.word_wrap = True
        paragraph = frame.paragraphs[0]
        paragraph.text = text
        # Themes only use common, editable PowerPoint fonts. If a host does not have a
        # decorative family, PowerPoint safely substitutes its default rather than
        # flattening content or changing its structure.
        paragraph.font.name = deck_font
        paragraph.font.size = Pt(size)
        paragraph.font.bold = bold
        paragraph.font.color.rgb = color
        return shape

    def panel(slide, x, y, w, h, color=background):
        shape = slide.shapes.add_shape(5, Inches(x), Inches(y), Inches(w), Inches(h))
        shape.fill.solid()
        shape.fill.fore_color.rgb = color
        shape.line.color.rgb = muted
        return shape

    def apply_template_canvas(slide, *, cover_slide=False):
        gradient_hex = style.get("gradient")
        if gradient_hex:
            base_hex = style["cover"] if cover_slide else style["background"]
            canvas = slide.shapes.add_shape(
                1, 0, 0, Inches(_WIDE_WIDTH), Inches(_WIDE_HEIGHT)
            )
            canvas.fill.gradient()
            canvas.fill.gradient_angle = 320.0
            stops = canvas.fill.gradient_stops
            stops[0].color.rgb = RGBColor.from_string(base_hex)
            stops[-1].color.rgb = RGBColor.from_string(gradient_hex)
            canvas.line.fill.background()
        # Editable, brand-appropriate motifs replace decorative circles and retain
        # text-safe areas. They intentionally use only native PowerPoint shapes.
        template_id = style.get("id", "")
        if template_id == "paper" and not cover_slide:
            for position in range(12, 96, 11):
                line = slide.shapes.add_shape(1, Inches(0), Inches(position / 10), Inches(_WIDE_WIDTH), Inches(0.012))
                line.fill.solid(); line.fill.fore_color.rgb = RGBColor(137, 157, 184); line.fill.transparency = 62; line.line.fill.background()
            margin = slide.shapes.add_shape(1, Inches(0.58), 0, Inches(0.024), Inches(_WIDE_HEIGHT))
            margin.fill.solid(); margin.fill.fore_color.rgb = RGBColor(198, 92, 75); margin.fill.transparency = 45; margin.line.fill.background()
        elif template_id == "itau":
            rail = slide.shapes.add_shape(1, 0, 0, Inches(0.34), Inches(_WIDE_HEIGHT))
            rail.fill.solid(); rail.fill.fore_color.rgb = accent_rgb; rail.line.fill.background()
            for x, y, w in ((9.9, 0.55, 2.55), (10.55, 6.25, 1.9)):
                tile = slide.shapes.add_shape(5, Inches(x), Inches(y), Inches(w), Inches(0.24))
                tile.fill.solid(); tile.fill.fore_color.rgb = accent_rgb; tile.line.fill.background()
        elif template_id == "minecraft":
            for x, y, color in ((11.55, 0.42, "78B849"), (11.95, 0.42, "A77A45"), (11.55, 0.82, "A77A45"), (11.95, 0.82, "5E7C3A")):
                tile = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(0.36), Inches(0.36))
                tile.fill.solid(); tile.fill.fore_color.rgb = RGBColor.from_string(color); tile.line.fill.background()
        transition_name = style.get("transition")
        if transition_name:
            transition = OxmlElement("p:transition")
            transition.set("spd", "med")
            effect = OxmlElement(
                f"p:{'fade' if transition_name == 'cover' else transition_name}"
            )
            if transition_name == "push":
                effect.set("dir", "l")
            elif transition_name == "wipe":
                effect.set("dir", "r")
            elif transition_name == "split":
                effect.set("orient", "vert")
                effect.set("dir", "out")
            transition.append(effect)
            slide._element.append(transition)

    def attach_notes(slide, sources):
        lines = [f"Copyright: {copyright_notice}. All rights reserved."]
        if sources:
            lines.extend(["", "[Sources]", *sources])
        try:
            slide.notes_slide.notes_text_frame.text = "\n".join(lines)
        except (AttributeError, NotImplementedError):
            pass

    def stamp_slide(slide, *, is_dark=False, sources=None):
        footer_color = cover_ink if is_dark else muted
        textbox(slide, copyright_notice, 0.76, 7.08, 4.2, 0.18, 8, footer_color)
        attach_notes(slide, sources or [])

    cover = deck.slides.add_slide(blank_layout)
    cover.background.fill.solid()
    cover.background.fill.fore_color.rgb = cover_rgb
    apply_template_canvas(cover, cover_slide=True)
    composition = style.get("composition", "standard")
    title_box = (0.8, 1.45, 11.7, 2.2, 52)
    subtitle_box = (0.82, 3.8, 10.8, 1.1, 20)
    if composition in {"photo-right", "editorial"}:
        visual = cover.shapes.add_shape(1, Inches(7.0), 0, Inches(6.34), Inches(7.5))
        visual.fill.solid()
        visual.fill.fore_color.rgb = accent_rgb
        visual.line.fill.background()
        title_box = (0.72, 1.5, 5.8, 3.0, 50)
        subtitle_box = (0.76, 4.7, 5.6, 1.0, 17)
    elif composition == "photo-left":
        visual = cover.shapes.add_shape(1, 0, 0, Inches(6.25), Inches(7.5))
        visual.fill.solid()
        visual.fill.fore_color.rgb = accent_rgb
        visual.line.fill.background()
        title_box = (6.75, 1.5, 5.8, 3.0, 50)
        subtitle_box = (6.78, 4.7, 5.6, 1.0, 17)
    elif composition == "collage":
        for x, y, w, h, color in (
            (7.4, 0.6, 4.8, 3.0, accent_rgb),
            (8.2, 3.85, 4.2, 2.7, muted),
        ):
            visual = cover.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Inches(h))
            visual.fill.solid()
            visual.fill.fore_color.rgb = color
            visual.line.fill.background()
        title_box = (0.72, 3.65, 6.3, 2.35, 50)
        subtitle_box = (0.76, 6.0, 5.8, 0.7, 16)
    elif composition == "torn-photo":
        visual = cover.shapes.add_shape(1, 0, 0, Inches(13.34), Inches(4.25))
        visual.fill.solid()
        visual.fill.fore_color.rgb = accent_rgb
        visual.line.fill.background()
        title_box = (0.72, 4.35, 7.4, 1.8, 50)
        subtitle_box = (8.45, 5.0, 4.0, 1.0, 16)
    elif composition == "minimal-frame":
        visual = cover.shapes.add_shape(1, Inches(7.45), Inches(0.75), Inches(4.8), Inches(2.85))
        visual.fill.solid()
        visual.fill.fore_color.rgb = accent_rgb
        visual.line.color.rgb = cover_ink
        title_box = (0.78, 3.82, 8.9, 2.1, 50)
        subtitle_box = (8.95, 5.55, 3.4, 0.85, 15)
    elif composition == "infographic":
        rail = cover.shapes.add_shape(1, 0, 0, Inches(1.75), Inches(7.5))
        rail.fill.solid()
        rail.fill.fore_color.rgb = accent_rgb
        rail.line.fill.background()
        title_box = (2.25, 1.45, 9.8, 2.45, 52)
        subtitle_box = (2.28, 4.15, 8.8, 0.9, 18)
    elif composition == "botanical":
        title_box = (3.0, 1.55, 7.35, 2.4, 50)
        subtitle_box = (3.02, 4.0, 7.2, 0.9, 18)
    elif composition == "heritage":
        title_box = (0.72, 1.05, 7.0, 3.1, 50)
        subtitle_box = (0.76, 5.55, 4.2, 0.9, 16)
    elif composition == "full-bleed":
        title_box = (0.52, 0.62, 9.8, 2.5, 56)
        subtitle_box = (9.25, 6.15, 3.3, 0.7, 15)
    if cover_image:
        image_frame = {
            "photo-right": (7.0, 0, 6.34, 7.5),
            "editorial": (7.0, 0, 6.34, 7.5),
            "photo-left": (0, 0, 6.25, 7.5),
            "collage": (7.4, 0.6, 4.8, 5.95),
            "torn-photo": (0, 0, 13.34, 4.25),
            "minimal-frame": (7.45, 0.75, 4.8, 2.85),
            "infographic": (8.65, 0.72, 3.75, 2.75),
            "botanical": (0, 0, 13.34, 7.5),
            "heritage": (0, 0, 13.34, 7.5),
            "full-bleed": (0, 0, 13.34, 7.5),
        }.get(composition, (6.7, 0, 6.64, 7.5))
        x, y, w, h = image_frame
        cover.shapes.add_picture(
            _cover_image(cover_image, fit="cover", focus="center"),
            Inches(x), Inches(y), width=Inches(w), height=Inches(h),
        )
    textbox(cover, title, *title_box, cover_ink, True)
    textbox(cover, subtitle, *subtitle_box, cover_ink)
    bar = cover.shapes.add_shape(1, Inches(title_box[0]), Inches(6.82), Inches(1.8), Inches(0.12))
    bar.fill.solid()
    bar.fill.fore_color.rgb = accent_rgb
    bar.line.fill.background()

    for number, spec in enumerate(slides, 1):
        slide = deck.slides.add_slide(blank_layout)
        slide.background.fill.solid()
        layout = spec["layout"]
        slide.background.fill.fore_color.rgb = cover_rgb if layout in {"section", "conclusion"} else background
        apply_template_canvas(slide, cover_slide=layout in {"section", "conclusion"})
        if layout in {"section", "conclusion"}:
            textbox(slide, f"{number:02d}", 0.82, 0.72, 1.0, 0.45, 13, accent_rgb, True)
            textbox(slide, spec["title"], 0.82, 2.05, 11.4, 1.7, 42, RGBColor(255, 255, 255), True)
            if spec["takeaway"]:
                textbox(slide, spec["takeaway"], 0.86, 4.15, 10.6, 1.15, 19, RGBColor(205, 213, 225))
            bar = slide.shapes.add_shape(1, Inches(0.84), Inches(5.78), Inches(1.6), Inches(0.1))
            bar.fill.solid()
            bar.fill.fore_color.rgb = accent_rgb
            bar.line.fill.background()
            continue
        if layout == "title-only":
            textbox(slide, spec["title"], 0.95, 2.2, 11.4, 2.2, 42, ink, True)
            bar = slide.shapes.add_shape(1, Inches(0.98), Inches(4.85), Inches(1.7), Inches(0.1))
            bar.fill.solid()
            bar.fill.fore_color.rgb = accent_rgb
            bar.line.fill.background()
            continue
        textbox(slide, spec["title"], 0.72, 0.38, 11.85, 1.02, title_size, ink, True)
        if spec["takeaway"]:
            textbox(slide, spec["takeaway"], 0.74, 1.4, 11.7, 0.55, 17, accent_rgb, True)
        image = spec["image"]
        if layout == "statement":
            statement = spec["takeaway"] or (spec["bullets"][0] if spec["bullets"] else spec["title"])
            textbox(slide, statement, 1.05, 2.15, 11.1, 2.7, 31, ink, True)
            textbox(slide, str(number), 12.25, 7.0, 0.4, 0.22, 9, muted)
            continue
        if layout == "quote":
            quote = spec["takeaway"] or (spec["bullets"][0] if spec["bullets"] else spec["title"])
            mark = textbox(slide, "“", 0.8, 1.45, 1.0, 1.0, 70, accent_rgb, True)
            mark.text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT
            quote_size = 29 if len(quote) <= 150 else 24 if len(quote) <= 240 else 20
            textbox(slide, quote, 1.5, 1.78, 10.45, 3.55, quote_size, ink, True)
            if spec["bullets"]:
                textbox(slide, spec["bullets"][-1], 1.55, 5.25, 9.8, 0.6, 14, muted)
            textbox(slide, str(number), 12.25, 7.0, 0.4, 0.22, 9, muted)
            continue
        if layout == "big-number":
            metric, metric_label = _big_number_parts(spec)
            textbox(slide, metric, 0.78, 2.0, 5.2, 2.3, 62, accent_rgb, True)
            textbox(slide, metric_label, 6.0, 2.25, 6.0, 2.0, 24, ink, True)
            textbox(slide, str(number), 12.25, 7.0, 0.4, 0.22, 9, muted)
            continue
        if layout == "table":
            rows = _table_rows(spec["bullets"])
            columns = max(len(row) for row in rows)
            table_shape = slide.shapes.add_table(
                len(rows), columns, Inches(0.78), Inches(2.05), Inches(11.75), Inches(4.35)
            )
            table = table_shape.table
            for row_index, row in enumerate(rows):
                for column_index in range(columns):
                    cell = table.cell(row_index, column_index)
                    cell.text = row[column_index] if column_index < len(row) else ""
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = accent_rgb if row_index == 0 else background
                    for paragraph in cell.text_frame.paragraphs:
                        paragraph.font.name = deck_font
                        paragraph.font.size = Pt(15 if row_index else 16)
                        paragraph.font.bold = row_index == 0
                        paragraph.font.color.rgb = RGBColor(255, 255, 255) if row_index == 0 else ink
            continue
        if layout in {"bar-chart", "donut-chart"}:
            values = _chart_values(spec["bullets"])
            chart_data = ChartData()
            chart_data.categories = [label for label, _ in values]
            chart_data.add_series(spec["takeaway"] or "Value", [value for _, value in values])
            chart_type = (
                XL_CHART_TYPE.DOUGHNUT
                if layout == "donut-chart"
                else XL_CHART_TYPE.BAR_CLUSTERED
            )
            chart = slide.shapes.add_chart(
                chart_type,
                Inches(0.85),
                Inches(2.0),
                Inches(11.6),
                Inches(4.45),
                chart_data,
            ).chart
            chart.has_title = False
            chart.has_legend = layout == "donut-chart"
            if chart.has_legend:
                chart.legend.position = XL_LEGEND_POSITION.RIGHT
                chart.legend.include_in_layout = False
            if layout == "bar-chart":
                chart.value_axis.has_major_gridlines = True
                chart.category_axis.tick_labels.font.size = Pt(13)
                chart.category_axis.reverse_order = True
                chart.plots[0].has_data_labels = True
                chart.plots[0].data_labels.position = XL_DATA_LABEL_POSITION.OUTSIDE_END
                chart.plots[0].data_labels.font.size = Pt(12)
                chart.plots[0].data_labels.font.bold = True
                chart.has_legend = False
            chart.series[0].format.fill.solid()
            chart.series[0].format.fill.fore_color.rgb = accent_rgb
            if spec["visual_annotation"]:
                textbox(slide, spec["visual_annotation"], 0.88, 6.53, 11.35, 0.26, 11, muted, False)
            continue
        if layout in {"flow-diagram", "roadmap"}:
            values = spec["bullets"][:6]
            node_width = min(2.1, 10.9 / len(values))
            gap = (11.65 - node_width * len(values)) / max(1, len(values) - 1)
            xs = [0.82 + index * (node_width + gap) for index in range(len(values))]
            for index in range(len(values) - 1):
                y = 3.45 if layout == "flow-diagram" else 4.05 - (index % 2) * 1.35
                next_y = 3.45 if layout == "flow-diagram" else 4.05 - ((index + 1) % 2) * 1.35
                connector = slide.shapes.add_connector(
                    MSO_CONNECTOR.STRAIGHT,
                    Inches(xs[index] + node_width),
                    Inches(y + 0.55),
                    Inches(xs[index + 1]),
                    Inches(next_y + 0.55),
                )
                connector.line.color.rgb = accent_rgb
                connector.line.width = Pt(2)
            for index, value in enumerate(values):
                y = 3.45 if layout == "flow-diagram" else 4.05 - (index % 2) * 1.35
                panel(slide, xs[index], y, node_width, 1.1)
                textbox(slide, str(index + 1), xs[index] + 0.12, y + 0.13, 0.35, 0.28, 11, accent_rgb, True)
                textbox(slide, value, xs[index] + 0.48, y + 0.14, node_width - 0.57, 0.75, 14, ink, True)
            continue
        if layout == "org-chart":
            edges = _org_edges(spec["bullets"])
            root = edges[0][0] if edges else spec["bullets"][0]
            children = list(dict.fromkeys(
                [child for parent, child in edges if parent == root]
                or spec["bullets"][1:5]
            ))[:4]
            child_width = min(2.45, 10.9 / max(1, len(children)))
            gap = (11.1 - child_width * len(children)) / max(1, len(children) - 1)
            child_xs = [1.1 + index * (child_width + gap) for index in range(len(children))]
            for child_x in child_xs:
                connector = slide.shapes.add_connector(
                    MSO_CONNECTOR.STRAIGHT,
                    Inches(6.65),
                    Inches(3.15),
                    Inches(child_x + child_width / 2),
                    Inches(4.3),
                )
                connector.line.color.rgb = muted
                connector.line.width = Pt(1.5)
            root_panel = panel(slide, 5.25, 2.15, 2.8, 1.0, accent_rgb)
            root_panel.line.fill.background()
            textbox(slide, root, 5.5, 2.38, 2.3, 0.5, 17, RGBColor(255, 255, 255), True)
            for child_x, child in zip(child_xs, children):
                panel(slide, child_x, 4.3, child_width, 1.15)
                textbox(slide, child, child_x + 0.18, 4.58, child_width - 0.36, 0.55, 15, ink, True)
            continue
        if layout == "map":
            # Geography must be supplied as a real map/territory image. The editable
            # location register remains beside it so the output never implies fake precision.
            if not image:
                raise ValueError("Map slides require a planned map or geographic image.")
            slide.shapes.add_picture(
                _cover_image(image, fit=spec["image_fit"], focus=spec["image_focus"]),
                Inches(0.78), Inches(2.0), width=Inches(6.35), height=Inches(4.45),
            )
            locations = _table_rows(spec["bullets"])[:5]
            for item_index, row in enumerate(locations):
                y = 2.0 + item_index * 0.82
                marker = slide.shapes.add_shape(9, Inches(7.45), Inches(y + 0.1), Inches(0.34), Inches(0.34))
                marker.fill.solid(); marker.fill.fore_color.rgb = accent_rgb; marker.line.fill.background()
                textbox(slide, str(item_index + 1), 7.54, y + 0.15, 0.16, 0.12, 8, RGBColor(255, 255, 255), True)
                location = row[0] if row else "Location"
                value = row[1] if len(row) > 1 else ""
                detail = row[2] if len(row) > 2 else ""
                textbox(slide, location, 7.9, y, 3.95, 0.25, 15, ink, True)
                textbox(slide, value, 11.15, y, 1.05, 0.25, 14, accent_rgb, True)
                if detail:
                    textbox(slide, detail, 7.9, y + 0.30, 4.2, 0.35, 11, muted)
            continue
        if layout in {"comparison", "pros-cons"}:
            midpoint = max(1, (len(spec["bullets"]) + 1) // 2)
            headings = ("Pros", "Cons") if layout == "pros-cons" else ("Option A", "Option B")
            for column, values in enumerate((spec["bullets"][:midpoint], spec["bullets"][midpoint:])):
                x = 0.76 + column * 6.15
                panel(slide, x, 2.0, 5.65, 4.5)
                textbox(slide, headings[column], x + 0.3, 2.28, 4.9, 0.5, 20, accent_rgb, True)
                textbox(slide, "\n".join(f"• {value}" for value in values), x + 0.3, 3.0, 4.9, 2.9, 17, ink)
            continue
        if layout in {"timeline", "process"}:
            values = spec["bullets"][:5] or [spec["takeaway"] or spec["title"]]
            step_width = 11.7 / len(values)
            for index, value in enumerate(values):
                x = 0.8 + index * step_width
                panel(slide, x, 2.4, step_width - 0.18, 2.7)
                textbox(slide, str(index + 1), x + 0.18, 2.64, 0.55, 0.5, 19, accent_rgb, True)
                textbox(slide, value, x + 0.18, 3.38, step_width - 0.55, 1.25, 15, ink, True)
            continue
        if layout in {"checklist", "three-columns", "four-cards", "metric-grid", "agenda"}:
            values = spec["bullets"][:6] or [spec["takeaway"] or spec["title"]]
            columns = 3 if layout == "three-columns" else 2
            if layout == "agenda":
                columns = 2
            rows = (len(values) + columns - 1) // columns
            card_w = 11.75 / columns
            card_h = min(1.35, 4.45 / max(1, rows))
            for index, value in enumerate(values):
                column, row = index % columns, index // columns
                x, y = 0.78 + column * card_w, 2.0 + row * (card_h + 0.14)
                panel(slide, x, y, card_w - 0.16, card_h)
                marker = "✓" if layout == "checklist" else f"{index + 1:02d}"
                textbox(slide, marker, x + 0.18, y + 0.2, 0.7, 0.35, 13, accent_rgb, True)
                size = 22 if layout == "metric-grid" else 15
                textbox(slide, value, x + 0.9, y + 0.18, card_w - 1.25, card_h - 0.25, size, ink, layout == "metric-grid")
            continue
        if layout in {"image-background", "image-top", "image-bottom"}:
            if image:
                if layout == "image-background":
                    slide.shapes.add_picture(_cover_image(image), 0, 0, width=Inches(_WIDE_WIDTH), height=Inches(_WIDE_HEIGHT))
                    overlay = slide.shapes.add_shape(1, 0, 0, Inches(_WIDE_WIDTH), Inches(_WIDE_HEIGHT))
                    overlay.fill.solid()
                    overlay.fill.fore_color.rgb = cover_rgb
                    overlay.fill.transparency = 30
                    overlay.line.fill.background()
                    textbox(slide, spec["title"], 0.85, 0.75, 10.8, 1.2, 35, RGBColor(255, 255, 255), True)
                    textbox(slide, spec["takeaway"], 0.88, 5.4, 9.7, 0.9, 21, RGBColor(255, 255, 255), True)
                else:
                    image_y = 1.65 if layout == "image-top" else 4.15
                    slide.shapes.add_picture(_cover_image(image), Inches(0.76), Inches(image_y), width=Inches(11.8), height=Inches(2.55))
                    body_y = 4.48 if layout == "image-top" else 1.8
                    textbox(slide, spec["takeaway"], 0.8, body_y, 11.6, 0.65, 17, accent_rgb, True)
                    textbox(slide, "\n".join(f"• {value}" for value in spec["bullets"][:4]), 0.8, body_y + 0.75, 11.4, 1.3, 16, ink)
            continue
        if layout == "two-column":
            midpoint = max(1, (len(spec["bullets"]) + 1) // 2)
            for column, values in enumerate((spec["bullets"][:midpoint], spec["bullets"][midpoint:])):
                body = slide.shapes.add_textbox(
                    Inches(0.76 + column * 6.15), Inches(2.02), Inches(5.65), Inches(4.55)
                )
                frame = body.text_frame
                frame.clear()
                frame.word_wrap = True
                for idx, bullet in enumerate(values):
                    paragraph = frame.paragraphs[0] if idx == 0 else frame.add_paragraph()
                    paragraph.text = bullet
                    paragraph.font.name = deck_font
                    paragraph.font.size = Pt(18)
                    paragraph.font.color.rgb = ink
                    paragraph.space_after = Pt(12)
            divider = slide.shapes.add_shape(1, Inches(6.61), Inches(2.05), Inches(0.02), Inches(4.1))
            divider.fill.solid()
            divider.fill.fore_color.rgb = muted
            divider.line.fill.background()
            textbox(slide, str(number), 12.25, 7.0, 0.4, 0.22, 9, muted)
            continue
        content_width = 5.55 if image else 11.3
        body_x = 6.98 if image and layout == "image-left" else 0.76
        body = slide.shapes.add_textbox(
            Inches(body_x), Inches(2.02), Inches(content_width), Inches(4.55)
        )
        frame = body.text_frame
        frame.clear()
        frame.word_wrap = True
        for idx, bullet in enumerate(spec["bullets"]):
            paragraph = frame.paragraphs[0] if idx == 0 else frame.add_paragraph()
            paragraph.text = bullet
            paragraph.level = 0
            paragraph.font.name = deck_font
            paragraph.font.size = Pt(18)
            paragraph.font.color.rgb = ink
            paragraph.space_after = Pt(12)
        if image:
            image_x = 0.76 if layout == "image-left" else 6.65
            slide.shapes.add_picture(
                _cover_image(
                    image,
                    fit=spec["image_fit"],
                    focus=spec["image_focus"],
                ),
                Inches(image_x),
                Inches(2.0),
                width=Inches(5.9),
                height=Inches(3.75),
            )
            if spec["image_caption"]:
                caption = textbox(
                    slide, spec["image_caption"], image_x + 0.03, 5.86, 5.8, 0.55, 11, muted
                )
                caption.text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT
        textbox(slide, str(number), 12.25, 7.0, 0.4, 0.22, 9, muted)
        attach_notes(slide, spec["sources"])
    for index, slide in enumerate(deck.slides):
        layout = "cover" if index == 0 else slides[index - 1]["layout"]
        stamp_slide(
            slide,
            is_dark=layout in {"cover", "section", "conclusion"},
            sources=[] if index == 0 else slides[index - 1]["sources"],
        )
    deck.save(destination)


def _add_pdf(
    destination: str,
    *,
    title: str,
    subtitle: str,
    slides: list[dict[str, Any]],
    style: dict[str, str],
    cover_image: Path | None = None,
) -> None:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import landscape
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen.canvas import Canvas

    page = landscape((540, 960))
    width, height = page
    canvas = Canvas(destination, pagesize=page, pageCompression=1)
    ink = HexColor(f"#{style['ink']}")
    muted = HexColor(f"#{style['muted']}")
    accent_color = HexColor(f"#{style['accent']}")
    background = HexColor(f"#{style['background']}")
    cover = HexColor(f"#{style['cover']}")
    cover_ink = HexColor(f"#{style.get('cover_ink', 'FFFFFF')}")
    copyright_notice = _copyright_notice()
    pdf_regular, pdf_bold = {
        "Georgia": ("Times-Roman", "Times-Bold"),
        "Bradley Hand ITC": ("Helvetica-Oblique", "Helvetica-BoldOblique"),
        "Chalkboard SE": ("Helvetica", "Helvetica-Bold"),
    }.get(style.get("font", ""), ("Helvetica", "Helvetica-Bold"))
    page_footer_color = cover_ink
    raw_show_page = canvas.showPage

    def show_page():
        """Finish every PDF page with the same ownership mark as its PPTX slide."""
        canvas.setFillColor(page_footer_color)
        canvas.setFont(pdf_regular, 7)
        canvas.drawString(55, 18, copyright_notice)
        raw_show_page()

    def paint_background(color, *, cover_page=False):
        canvas.setFillColor(color)
        canvas.rect(0, 0, width, height, stroke=0, fill=1)
        gradient_hex = style.get("gradient")
        if gradient_hex:
            start_hex = style["cover"] if cover_page else style["background"]
            canvas.linearGradient(
                0, height, width, 0,
                [HexColor(f"#{start_hex}"), HexColor(f"#{gradient_hex}")],
                extend=True,
            )

    def text(value, x, y, size, color=ink, font=None, max_width=None):
        font = font or pdf_regular
        canvas.setFillColor(color)
        canvas.setFont(font, size)
        if not max_width:
            canvas.drawString(x, y, value)
            return
        words, lines, current = value.split(), [], ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if canvas.stringWidth(candidate, font, size) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        for offset, line in enumerate(lines[:4]):
            canvas.drawString(x, y - offset * size * 1.25, line)

    paint_background(cover, cover_page=True)
    composition = style.get("composition", "standard")
    title_position = (58, 385, 32, 840)
    subtitle_position = (60, 275, 16, 760)
    if composition in {"photo-right", "editorial"}:
        canvas.setFillColor(accent_color)
        canvas.rect(width * .53, 0, width * .47, height, stroke=0, fill=1)
        title_position = (52, 360, 30, 420)
        subtitle_position = (54, 165, 14, 400)
    elif composition == "photo-left":
        canvas.setFillColor(accent_color)
        canvas.rect(0, 0, width * .47, height, stroke=0, fill=1)
        title_position = (510, 360, 30, 390)
        subtitle_position = (512, 165, 14, 380)
    elif composition == "collage":
        canvas.setFillColor(accent_color)
        canvas.rect(560, 270, 315, 205, stroke=0, fill=1)
        canvas.setFillColor(muted)
        canvas.rect(620, 65, 275, 165, stroke=0, fill=1)
        title_position = (54, 190, 30, 460)
        subtitle_position = (56, 75, 14, 430)
    elif composition == "torn-photo":
        canvas.setFillColor(accent_color)
        canvas.rect(0, 235, width, 305, stroke=0, fill=1)
        title_position = (55, 135, 28, 560)
        subtitle_position = (660, 85, 14, 250)
    elif composition == "minimal-frame":
        canvas.setFillColor(accent_color)
        canvas.rect(565, 280, 315, 190, stroke=0, fill=1)
        title_position = (58, 135, 31, 680)
        subtitle_position = (700, 70, 13, 210)
    elif composition == "infographic":
        canvas.setFillColor(accent_color)
        canvas.rect(0, 0, 135, height, stroke=0, fill=1)
        title_position = (180, 360, 32, 700)
        subtitle_position = (182, 235, 15, 650)
    elif composition == "botanical":
        title_position = (220, 350, 31, 570)
        subtitle_position = (222, 235, 15, 550)
    elif composition == "heritage":
        title_position = (55, 350, 31, 540)
        subtitle_position = (58, 80, 14, 330)
    elif composition == "full-bleed":
        title_position = (42, 420, 37, 730)
        subtitle_position = (700, 55, 13, 220)
    if cover_image:
        x, y, w, h = {
            "photo-right": (width * .53, 0, width * .47, height),
            "editorial": (width * .53, 0, width * .47, height),
            "photo-left": (0, 0, width * .47, height),
            "collage": (560, 65, 315, 410),
            "torn-photo": (0, 235, width, 305),
            "minimal-frame": (565, 280, 315, 190),
            "infographic": (665, 285, 245, 175),
            "botanical": (0, 0, width, height),
            "heritage": (0, 0, width, height),
            "full-bleed": (0, 0, width, height),
        }.get(composition, (width * .5, 0, width * .5, height))
        prepared = _cover_image(cover_image, 1200, 750, fit="cover", focus="center")
        canvas.drawImage(ImageReader(prepared), x, y, width=w, height=h, preserveAspectRatio=False, mask="auto")
    text(title, *title_position[:3], cover_ink, pdf_bold, title_position[3])
    text(subtitle, *subtitle_position[:3], cover_ink, max_width=subtitle_position[3])
    canvas.setFillColor(accent_color)
    canvas.rect(60, 115, 130, 8, stroke=0, fill=1)
    show_page()
    page_footer_color = muted

    for number, spec in enumerate(slides, 1):
        paint_background(background)
        layout = spec["layout"]
        if layout in {"section", "conclusion"}:
            paint_background(cover, cover_page=True)
            text(f"{number:02d}", 60, 465, 12, accent_color, pdf_bold)
            text(spec["title"], 60, 335, 34, HexColor("#FFFFFF"), pdf_bold, 830)
            if spec["takeaway"]:
                text(spec["takeaway"], 62, 205, 16, HexColor("#CDD5E1"), max_width=760)
            canvas.setFillColor(accent_color)
            canvas.rect(62, 95, 115, 7, stroke=0, fill=1)
            show_page()
            continue
        if layout == "table":
            rows = _table_rows(spec["bullets"])
            columns = max(len(row) for row in rows)
            x, top, total_width = 58, 385, 842
            row_height = min(46, 270 / len(rows))
            column_width = total_width / columns
            for row_index, row in enumerate(rows):
                y = top - (row_index + 1) * row_height
                canvas.setFillColor(accent_color if row_index == 0 else background)
                canvas.rect(x, y, total_width, row_height, stroke=1, fill=1)
                for column_index in range(columns):
                    cell_x = x + column_index * column_width
                    canvas.line(cell_x, y, cell_x, y + row_height)
                    value = row[column_index] if column_index < len(row) else ""
                    text(
                        value,
                        cell_x + 9,
                        y + row_height / 2 - 4,
                        11,
                        HexColor("#FFFFFF") if row_index == 0 else ink,
                        "Helvetica-Bold" if row_index == 0 else "Helvetica",
                        column_width - 18,
                    )
            show_page()
            continue
        if layout == "bar-chart":
            values = _chart_values(spec["bullets"])
            max_value = max(value for _, value in values) or 1
            chart_x, chart_y, chart_w, chart_h = 85, 105, 790, 275
            slot = chart_w / len(values)
            canvas.setStrokeColor(muted)
            canvas.line(chart_x, chart_y, chart_x + chart_w, chart_y)
            for index, (label, value) in enumerate(values):
                bar_height = chart_h * max(0, value) / max_value
                bar_x = chart_x + index * slot + slot * 0.2
                canvas.setFillColor(accent_color)
                canvas.roundRect(bar_x, chart_y, slot * 0.6, bar_height, 4, stroke=0, fill=1)
                text(f"{value:g}", bar_x, chart_y + bar_height + 10, 10, ink, "Helvetica-Bold", slot * 0.6)
                text(label, bar_x, chart_y - 28, 9, muted, max_width=slot * 0.72)
            show_page()
            continue
        if layout == "donut-chart":
            values = _chart_values(spec["bullets"])
            total = sum(max(0, value) for _, value in values) or 1
            palette = [accent_color, ink, muted, HexColor("#94A3B8"), HexColor("#CBD5E1"), HexColor("#E2E8F0")]
            angle = 90.0
            for index, (_, value) in enumerate(values):
                extent = 360.0 * max(0, value) / total
                canvas.setFillColor(palette[index % len(palette)])
                canvas.wedge(100, 105, 430, 435, angle, extent, stroke=0, fill=1)
                angle += extent
            canvas.setFillColor(background)
            canvas.circle(265, 270, 88, stroke=0, fill=1)
            legend_y = 360
            for index, (label, value) in enumerate(values):
                canvas.setFillColor(palette[index % len(palette)])
                canvas.circle(540, legend_y + 4, 5, stroke=0, fill=1)
                text(f"{label}  {value:g}", 555, legend_y, 12, ink, "Helvetica-Bold", 290)
                legend_y -= 43
            show_page()
            continue
        if layout in {"flow-diagram", "roadmap"}:
            values = spec["bullets"][:6]
            node_width = min(145, 750 / len(values))
            gap = (820 - node_width * len(values)) / max(1, len(values) - 1)
            xs = [65 + index * (node_width + gap) for index in range(len(values))]
            for index in range(len(values) - 1):
                y = 245 if layout == "flow-diagram" else 265 - (index % 2) * 90
                next_y = 245 if layout == "flow-diagram" else 265 - ((index + 1) % 2) * 90
                canvas.setStrokeColor(accent_color)
                canvas.setLineWidth(2)
                canvas.line(xs[index] + node_width, y + 35, xs[index + 1], next_y + 35)
            for index, value in enumerate(values):
                y = 245 if layout == "flow-diagram" else 265 - (index % 2) * 90
                canvas.setFillColor(background)
                canvas.roundRect(xs[index], y, node_width, 70, 8, stroke=1, fill=1)
                text(str(index + 1), xs[index] + 10, y + 43, 10, accent_color, "Helvetica-Bold")
                text(value, xs[index] + 30, y + 43, 10, ink, "Helvetica-Bold", node_width - 38)
            show_page()
            continue
        if layout == "org-chart":
            edges = _org_edges(spec["bullets"])
            root = edges[0][0] if edges else spec["bullets"][0]
            children = list(dict.fromkeys(
                [child for parent, child in edges if parent == root]
                or spec["bullets"][1:5]
            ))[:4]
            child_width = min(170, 760 / max(1, len(children)))
            gap = (820 - child_width * len(children)) / max(1, len(children) - 1)
            child_xs = [65 + index * (child_width + gap) for index in range(len(children))]
            for child_x in child_xs:
                canvas.setStrokeColor(muted)
                canvas.line(480, 310, child_x + child_width / 2, 225)
            canvas.setFillColor(accent_color)
            canvas.roundRect(370, 310, 220, 65, 8, stroke=0, fill=1)
            text(root, 390, 340, 14, HexColor("#FFFFFF"), "Helvetica-Bold", 180)
            for child_x, child in zip(child_xs, children):
                canvas.setFillColor(background)
                canvas.roundRect(child_x, 160, child_width, 65, 8, stroke=1, fill=1)
                text(child, child_x + 12, 190, 11, ink, "Helvetica-Bold", child_width - 24)
            show_page()
            continue
        if layout == "title-only":
            text(spec["title"], 70, 310, 36, ink, "Helvetica-Bold", 810)
            canvas.setFillColor(accent_color)
            canvas.rect(72, 120, 120, 7, stroke=0, fill=1)
            show_page()
            continue
        text(spec["title"], 52, 478, 30, ink, pdf_bold, 850)
        if spec["takeaway"]:
            text(spec["takeaway"], 54, 425, 14, accent_color, "Helvetica-Bold", 840)
        image = spec["image"]
        if layout == "statement":
            statement = spec["takeaway"] or (spec["bullets"][0] if spec["bullets"] else spec["title"])
            text(statement, 75, 320, 28, ink, "Helvetica-Bold", 810)
            text(str(number), 895, 25, 8, muted)
            show_page()
            continue
        if layout == "quote":
            quote = spec["takeaway"] or (spec["bullets"][0] if spec["bullets"] else spec["title"])
            quote_size = 28 if len(quote) <= 150 else 23 if len(quote) <= 240 else 19
            text("“", 60, 400, 58, accent_color, pdf_bold)
            text(quote, 115, 335, quote_size, ink, pdf_bold, 760)
            if spec["bullets"]:
                text(spec["bullets"][-1], 120, 115, 12, muted, max_width=700)
            text(str(number), 895, 25, 8, muted)
            show_page()
            continue
        if layout == "big-number":
            metric, metric_label = _big_number_parts(spec)
            text(metric, 60, 300, 58, accent_color, pdf_bold, 400)
            text(metric_label, 485, 310, 22, ink, pdf_bold, 410)
            show_page()
            continue
        if layout == "map":
            if not image:
                raise ValueError("Map slides require a planned map or geographic image.")
            prepared = _cover_image(image, 900, 600, fit=spec["image_fit"], focus=spec["image_focus"])
            canvas.drawImage(ImageReader(prepared), 55, 100, width=480, height=300, mask="auto")
            for item_index, row in enumerate(_table_rows(spec["bullets"])[:5]):
                y = 365 - item_index * 58
                location = row[0] if row else "Location"
                value = row[1] if len(row) > 1 else ""
                detail = row[2] if len(row) > 2 else ""
                canvas.setFillColor(accent_color)
                canvas.circle(570, y + 4, 10, stroke=0, fill=1)
                text(str(item_index + 1), 567, y, 8, HexColor("#FFFFFF"), "Helvetica-Bold")
                text(location, 590, y + 5, 12, ink, "Helvetica-Bold", 190)
                text(value, 805, y + 5, 11, accent_color, "Helvetica-Bold", 95)
                if detail:
                    text(detail, 590, y - 14, 9, muted, max_width=300)
            show_page()
            continue
        if layout in {"comparison", "pros-cons"}:
            midpoint = max(1, (len(spec["bullets"]) + 1) // 2)
            headings = ("Pros", "Cons") if layout == "pros-cons" else ("Option A", "Option B")
            for column, values in enumerate((spec["bullets"][:midpoint], spec["bullets"][midpoint:])):
                x = 55 + column * 455
                canvas.setFillColor(HexColor(f"#{style['background']}"))
                canvas.roundRect(x, 90, 395, 300, 10, stroke=1, fill=1)
                text(headings[column], x + 22, 350, 18, accent_color, "Helvetica-Bold")
                y = 305
                for value in values:
                    text(f"• {value}", x + 22, y, 12, ink, max_width=345)
                    y -= 52
            show_page()
            continue
        if layout in {"timeline", "process"}:
            values = spec["bullets"][:5] or [spec["takeaway"] or spec["title"]]
            step_width = 830 / len(values)
            for index, value in enumerate(values):
                x = 60 + index * step_width
                canvas.setFillColor(accent_color)
                canvas.circle(x + 14, 315, 14, stroke=0, fill=1)
                text(str(index + 1), x + 10, 310, 9, HexColor("#FFFFFF"), "Helvetica-Bold")
                text(value, x, 260, 11, ink, "Helvetica-Bold", step_width - 18)
            show_page()
            continue
        if layout in {"checklist", "three-columns", "four-cards", "metric-grid", "agenda"}:
            values = spec["bullets"][:6] or [spec["takeaway"] or spec["title"]]
            columns = 3 if layout == "three-columns" else 2
            card_width = 840 / columns
            for index, value in enumerate(values):
                column, row = index % columns, index // columns
                x, y = 55 + column * card_width, 345 - row * 95
                marker = "✓" if layout == "checklist" else f"{index + 1:02d}"
                text(marker, x + 12, y, 11, accent_color, "Helvetica-Bold")
                text(value, x + 52, y, 15 if layout == "metric-grid" else 11, ink, "Helvetica-Bold", card_width - 75)
            show_page()
            continue
        if layout in {"image-background", "image-top", "image-bottom"}:
            if image:
                prepared = _cover_image(image, 1200, 675, fit=spec["image_fit"], focus=spec["image_focus"])
                if layout == "image-background":
                    canvas.drawImage(ImageReader(prepared), 0, 0, width=960, height=540, mask="auto")
                    canvas.setFillColorRGB(0, 0, 0, alpha=0.5)
                    canvas.rect(0, 0, 960, 540, stroke=0, fill=1)
                    text(spec["title"], 55, 445, 28, HexColor("#FFFFFF"), "Helvetica-Bold", 820)
                    text(spec["takeaway"], 58, 100, 18, HexColor("#FFFFFF"), "Helvetica-Bold", 760)
                else:
                    image_y = 245 if layout == "image-top" else 35
                    canvas.drawImage(ImageReader(prepared), 55, image_y, width=850, height=225, mask="auto")
                    body_y = 190 if layout == "image-top" else 385
                    text(spec["takeaway"], 58, body_y, 15, accent_color, "Helvetica-Bold", 820)
            show_page()
            continue
        if layout == "two-column":
            midpoint = max(1, (len(spec["bullets"]) + 1) // 2)
            for column, values in enumerate((spec["bullets"][:midpoint], spec["bullets"][midpoint:])):
                y = 350
                for bullet in values:
                    text(f"•  {bullet}", 58 + column * 455, y, 13, ink, max_width=385)
                    y -= 52
            canvas.setStrokeColor(muted)
            canvas.setLineWidth(0.5)
            canvas.line(480, 95, 480, 380)
            text(str(number), 895, 25, 8, muted)
            show_page()
            continue
        content_width = 380 if image else 820
        body_x = 510 if image and layout == "image-left" else 58
        y = 350
        for bullet in spec["bullets"]:
            text(f"•  {bullet}", body_x, y, 13, ink, max_width=content_width)
            y -= 52
        if image:
            image_x = 54 if layout == "image-left" else 500
            prepared = _cover_image(
                image,
                800,
                500,
                fit=spec["image_fit"],
                focus=spec["image_focus"],
            )
            canvas.drawImage(
                ImageReader(prepared),
                image_x,
                135,
                width=400,
                height=250,
                preserveAspectRatio=True,
                anchor="c",
                mask="auto",
            )
            if spec["image_caption"]:
                text(spec["image_caption"], image_x + 2, 105, 9, muted, max_width=390)
        text(str(number), 895, 25, 8, muted)
        show_page()
    canvas.save()


def _available_preview_dir(pdf_target: Path) -> Path:
    base = pdf_target.with_name(f"{pdf_target.stem}-previews")
    if not base.exists():
        return base
    for index in range(2, 1000):
        candidate = pdf_target.with_name(f"{pdf_target.stem}-previews-{index}")
        if not candidate.exists():
            return candidate
    raise ValueError("Could not allocate a presentation preview folder.")


def _render_previews(pdf_path: Path, destination: Path) -> tuple[list[Path], Path]:
    import pypdfium2 as pdfium
    from PIL import Image, ImageDraw

    temporary = Path(tempfile.mkdtemp(prefix=".presentation-previews.", dir=destination.parent))
    previews: list[Path] = []
    try:
        document = pdfium.PdfDocument(str(pdf_path))
        for index in range(len(document)):
            page = document[index]
            rendered = page.render(scale=1.5).to_pil().convert("RGB")
            path = temporary / f"slide-{index + 1:03d}.png"
            rendered.save(path, "PNG", optimize=True)
            previews.append(path)
            page.close()
        document.close()
        if not previews:
            raise ValueError("The presentation PDF has no renderable pages.")

        thumb_width = 480
        gap = 24
        columns = 2
        thumbs: list[Image.Image] = []
        for path in previews:
            with Image.open(path) as image:
                thumb = image.convert("RGB")
                thumb.thumbnail((thumb_width, 320))
                thumbs.append(thumb.copy())
        cell_height = max(image.height for image in thumbs) + 48
        rows = (len(thumbs) + columns - 1) // columns
        sheet = Image.new(
            "RGB",
            (columns * thumb_width + (columns + 1) * gap, rows * cell_height + (rows + 1) * gap),
            "#E8EBF0",
        )
        draw = ImageDraw.Draw(sheet)
        for index, thumb in enumerate(thumbs):
            column = index % columns
            row = index // columns
            x = gap + column * (thumb_width + gap)
            y = gap + row * cell_height
            sheet.paste(thumb, (x, y))
            draw.text((x, y + thumb.height + 10), f"Slide {index + 1}", fill="#1A1F2C")
        contact_sheet = temporary / "contact-sheet.png"
        sheet.save(contact_sheet, "PNG", optimize=True)
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temporary, destination)
        return (
            [destination / path.name for path in previews],
            destination / contact_sheet.name,
        )
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def make_build_presentation_tool(*, workspace: Path | str):
    root = Path(workspace).expanduser().resolve()

    def build_presentation(
        title: str,
        slides: list[dict[str, Any]],
        pptx_path: str,
        pdf_path: str,
        subtitle: str = "",
        accent_color: str = "",
        template_id: str = "atlas",
        template_path: str = "",
        cover_image_path: str = "",
        minimum_images: int = 0,
    ) -> dict[str, Any]:
        """Render an editable PPTX and a matching slide-formatted PDF."""
        clean_title = str(title or "").strip()
        if not clean_title:
            return {"ok": False, "error": "A presentation title is required."}
        selected_template = str(template_id or "atlas").strip().lower()
        if selected_template not in _TEMPLATES:
            return {"ok": False, "error": "Choose a supported presentation template."}
        style = dict(_TEMPLATES[selected_template])
        accent = str(accent_color or "").strip().lstrip("#").upper()
        if accent:
            if len(accent) != 6 or any(c not in "0123456789ABCDEF" for c in accent):
                return {"ok": False, "error": "Accent color must be a six-digit hex value."}
            style["accent"] = accent
        try:
            pptx_target = _safe_target(root, pptx_path, ".pptx")
            pdf_target = _safe_target(root, pdf_path, ".pdf")
            normalized = _normalize_slides(root, slides)
            custom_template = _safe_template(root, template_path)
            cover_image = _safe_image(root, cover_image_path)
            required_images = max(0, min(_MAX_SLIDES, int(minimum_images or 0)))
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        except (TypeError, OverflowError):
            return {"ok": False, "error": "Minimum images must be a whole number."}
        embedded_images = sum(bool(item["image"]) for item in normalized)
        quality_gate = _quality_gate(normalized)
        if embedded_images < required_images:
            return {
                "ok": False,
                "error": (
                    f"The approved visual plan requires at least {required_images} images, "
                    f"but only {embedded_images} valid image files were provided."
                ),
            }

        pptx_fd, pptx_temp = _atomic_destination(pptx_target)
        pdf_fd, pdf_temp = _atomic_destination(pdf_target)
        os.close(pptx_fd)
        os.close(pdf_fd)
        try:
            _add_pptx(
                pptx_temp,
                title=clean_title[:180],
                subtitle=str(subtitle or "").strip()[:300],
                slides=normalized,
                style=style,
                cover_image=cover_image,
                template=custom_template,
            )
            _add_pdf(
                pdf_temp,
                title=clean_title[:180],
                subtitle=str(subtitle or "").strip()[:300],
                slides=normalized,
                style=style,
                cover_image=cover_image,
            )
            if not Path(pptx_temp).read_bytes().startswith(b"PK"):
                raise ValueError("PPTX renderer produced an invalid file.")
            if not Path(pdf_temp).read_bytes().startswith(b"%PDF-"):
                raise ValueError("PDF renderer produced an invalid file.")
            os.replace(pptx_temp, pptx_target)
            os.replace(pdf_temp, pdf_target)
            preview_dir = _available_preview_dir(pdf_target)
            preview_paths, contact_sheet = _render_previews(pdf_target, preview_dir)
        except Exception as exc:
            for temporary in (pptx_temp, pdf_temp):
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
            return {
                "ok": False,
                "error": f"Presentation rendering failed ({type(exc).__name__}).",
            }
        return {
            "ok": True,
            "pptx_path": str(pptx_target.relative_to(root)),
            "pdf_path": str(pdf_target.relative_to(root)),
            "slides": len(normalized) + 1,
            "images_embedded": embedded_images + bool(cover_image),
            "minimum_images": required_images,
            "visual_plan_complete": embedded_images >= required_images,
            "formats": ["pptx", "pdf"],
            "preview_paths": [str(path.relative_to(root)) for path in preview_paths],
            "contact_sheet_path": str(contact_sheet.relative_to(root)),
            "visual_review_required": True,
            "quality_gate": quality_gate,
            "template_id": selected_template,
            "template_path": str(custom_template.relative_to(root)) if custom_template else None,
            "operation_usage": {
                "type": "artifact",
                "provider": "Local",
                "model": "presentation-studio",
                "units": 2,
                "estimated_cost_usd": 0.0,
                "measurement": "local",
            },
        }

    build_presentation.__name__ = "build_presentation"
    build_presentation.__doc__ = _SCHEMA["function"]["description"]
    build_presentation.__aisuite_tool_metadata__ = ai.ToolMetadata(
        name="build_presentation",
        category="filesystem",
        risk_level="medium",
        capabilities=["write", "artifact"],
    )
    build_presentation.__coworker_schema__ = _SCHEMA
    return build_presentation
