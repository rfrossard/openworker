"""Deterministic, workspace-scoped PPTX and slide-PDF generation."""

from __future__ import annotations

import os
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any

import aisuite as ai


_MAX_SLIDES = 40
_MAX_BULLETS = 6
_WIDE_WIDTH = 13.333
_WIDE_HEIGHT = 7.5

_SCHEMA = {
    "type": "function",
    "function": {
        "name": "build_presentation",
        "description": (
            "Build an editable widescreen PPTX and a matching, genuinely paginated PDF "
            "from a structured slide specification. Local images are embedded in both."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "subtitle": {"type": "string"},
                "slides": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "takeaway": {"type": "string"},
                            "bullets": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "image_path": {
                                "type": "string",
                                "description": "Optional workspace-relative PNG or JPEG.",
                            },
                            "image_caption": {"type": "string"},
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


def _atomic_destination(target: Path) -> tuple[int, str]:
    target.parent.mkdir(parents=True, exist_ok=True)
    return tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)


def _cover_image(path: Path, width: int = 1200, height: int = 750) -> BytesIO:
    from PIL import Image, ImageOps

    with Image.open(path) as source:
        fitted = ImageOps.fit(source.convert("RGB"), (width, height))
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
                "sources": sources,
            }
        )
    return normalized


def _add_pptx(
    destination: str,
    *,
    title: str,
    subtitle: str,
    slides: list[dict[str, Any]],
    accent: str,
) -> None:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt

    deck = Presentation()
    deck.slide_width = Inches(_WIDE_WIDTH)
    deck.slide_height = Inches(_WIDE_HEIGHT)
    background = RGBColor(247, 248, 250)
    ink = RGBColor(26, 31, 44)
    muted = RGBColor(91, 101, 119)
    accent_rgb = RGBColor.from_string(accent)

    def textbox(slide, text, x, y, w, h, size, color=ink, bold=False):
        shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        frame = shape.text_frame
        frame.clear()
        frame.word_wrap = True
        paragraph = frame.paragraphs[0]
        paragraph.text = text
        paragraph.font.name = "Aptos"
        paragraph.font.size = Pt(size)
        paragraph.font.bold = bold
        paragraph.font.color.rgb = color
        return shape

    cover = deck.slides.add_slide(deck.slide_layouts[6])
    cover.background.fill.solid()
    cover.background.fill.fore_color.rgb = ink
    textbox(cover, title, 0.8, 1.55, 11.7, 2.0, 40, RGBColor(255, 255, 255), True)
    textbox(cover, subtitle, 0.82, 3.8, 10.8, 1.1, 20, RGBColor(205, 213, 225))
    bar = cover.shapes.add_shape(1, Inches(0.82), Inches(5.75), Inches(1.8), Inches(0.12))
    bar.fill.solid()
    bar.fill.fore_color.rgb = accent_rgb
    bar.line.fill.background()

    for number, spec in enumerate(slides, 1):
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = background
        textbox(slide, spec["title"], 0.72, 0.45, 11.8, 0.7, 28, ink, True)
        if spec["takeaway"]:
            textbox(slide, spec["takeaway"], 0.74, 1.22, 11.7, 0.62, 17, accent_rgb, True)
        image = spec["image"]
        content_width = 5.55 if image else 11.3
        body = slide.shapes.add_textbox(
            Inches(0.76), Inches(2.02), Inches(content_width), Inches(4.55)
        )
        frame = body.text_frame
        frame.clear()
        frame.word_wrap = True
        for idx, bullet in enumerate(spec["bullets"]):
            paragraph = frame.paragraphs[0] if idx == 0 else frame.add_paragraph()
            paragraph.text = bullet
            paragraph.level = 0
            paragraph.font.name = "Aptos"
            paragraph.font.size = Pt(18)
            paragraph.font.color.rgb = ink
            paragraph.space_after = Pt(12)
        if image:
            slide.shapes.add_picture(
                _cover_image(image),
                Inches(6.65),
                Inches(2.0),
                width=Inches(5.9),
                height=Inches(3.75),
            )
            if spec["image_caption"]:
                caption = textbox(
                    slide, spec["image_caption"], 6.68, 5.86, 5.8, 0.55, 11, muted
                )
                caption.text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT
        textbox(slide, str(number), 12.25, 7.0, 0.4, 0.22, 9, muted)
        if spec["sources"]:
            try:
                notes = slide.notes_slide.notes_text_frame
                notes.text = "[Sources]\n" + "\n".join(spec["sources"])
            except (AttributeError, NotImplementedError):
                pass
    deck.save(destination)


def _add_pdf(
    destination: str,
    *,
    title: str,
    subtitle: str,
    slides: list[dict[str, Any]],
    accent: str,
) -> None:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import landscape
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen.canvas import Canvas

    page = landscape((540, 960))
    width, height = page
    canvas = Canvas(destination, pagesize=page, pageCompression=1)
    ink = HexColor("#1A1F2C")
    muted = HexColor("#5B6577")
    accent_color = HexColor(f"#{accent}")

    def text(value, x, y, size, color=ink, font="Helvetica", max_width=None):
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

    canvas.setFillColor(ink)
    canvas.rect(0, 0, width, height, stroke=0, fill=1)
    text(title, 58, 385, 32, HexColor("#FFFFFF"), "Helvetica-Bold", 840)
    text(subtitle, 60, 275, 16, HexColor("#CDD5E1"), max_width=760)
    canvas.setFillColor(accent_color)
    canvas.rect(60, 115, 130, 8, stroke=0, fill=1)
    canvas.showPage()

    for number, spec in enumerate(slides, 1):
        canvas.setFillColor(HexColor("#F7F8FA"))
        canvas.rect(0, 0, width, height, stroke=0, fill=1)
        text(spec["title"], 52, 485, 24, ink, "Helvetica-Bold", 850)
        if spec["takeaway"]:
            text(spec["takeaway"], 54, 425, 14, accent_color, "Helvetica-Bold", 840)
        image = spec["image"]
        content_width = 380 if image else 820
        y = 350
        for bullet in spec["bullets"]:
            text(f"•  {bullet}", 58, y, 13, ink, max_width=content_width)
            y -= 52
        if image:
            prepared = _cover_image(image, 800, 500)
            canvas.drawImage(
                ImageReader(prepared),
                500,
                135,
                width=400,
                height=250,
                preserveAspectRatio=True,
                anchor="c",
                mask="auto",
            )
            if spec["image_caption"]:
                text(spec["image_caption"], 502, 105, 9, muted, max_width=390)
        text(str(number), 895, 25, 8, muted)
        canvas.showPage()
    canvas.save()


def make_build_presentation_tool(*, workspace: Path | str):
    root = Path(workspace).expanduser().resolve()

    def build_presentation(
        title: str,
        slides: list[dict[str, Any]],
        pptx_path: str,
        pdf_path: str,
        subtitle: str = "",
        accent_color: str = "2F6BFF",
    ) -> dict[str, Any]:
        """Render an editable PPTX and a matching slide-formatted PDF."""
        clean_title = str(title or "").strip()
        if not clean_title:
            return {"ok": False, "error": "A presentation title is required."}
        accent = str(accent_color or "").strip().lstrip("#").upper()
        if len(accent) != 6 or any(c not in "0123456789ABCDEF" for c in accent):
            return {"ok": False, "error": "Accent color must be a six-digit hex value."}
        try:
            pptx_target = _safe_target(root, pptx_path, ".pptx")
            pdf_target = _safe_target(root, pdf_path, ".pdf")
            normalized = _normalize_slides(root, slides)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

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
                accent=accent,
            )
            _add_pdf(
                pdf_temp,
                title=clean_title[:180],
                subtitle=str(subtitle or "").strip()[:300],
                slides=normalized,
                accent=accent,
            )
            if not Path(pptx_temp).read_bytes().startswith(b"PK"):
                raise ValueError("PPTX renderer produced an invalid file.")
            if not Path(pdf_temp).read_bytes().startswith(b"%PDF-"):
                raise ValueError("PDF renderer produced an invalid file.")
            os.replace(pptx_temp, pptx_target)
            os.replace(pdf_temp, pdf_target)
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
            "images_embedded": sum(bool(item["image"]) for item in normalized),
            "formats": ["pptx", "pdf"],
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
