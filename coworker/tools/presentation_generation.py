"""Deterministic, workspace-scoped PPTX and slide-PDF generation."""

from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

import aisuite as ai


_MAX_SLIDES = 40
_MAX_BULLETS = 6
_WIDE_WIDTH = 13.333
_WIDE_HEIGHT = 7.5
_LAYOUTS = {
    "auto", "image-right", "image-left", "statement", "two-column", "quote", "section",
    "title-only", "big-number", "checklist", "timeline", "process", "comparison",
    "pros-cons", "three-columns", "four-cards", "metric-grid", "image-background",
    "image-top", "image-bottom", "agenda", "conclusion",
}
_TEMPLATES = {
    "atlas": {"background": "F7F8FA", "ink": "1A1F2C", "muted": "5B6577", "accent": "2F6BFF", "cover": "1A1F2C"},
    "aurora": {"background": "F3F5FA", "ink": "101827", "muted": "667085", "accent": "8B5CF6", "cover": "101827"},
    "boardroom": {"background": "F7F4ED", "ink": "14213D", "muted": "657083", "accent": "C89B3C", "cover": "14213D"},
    "editorial": {"background": "FAF7F2", "ink": "292524", "muted": "78716C", "accent": "C2410C", "cover": "292524"},
    "forest": {"background": "F2F7F3", "ink": "17352B", "muted": "64756C", "accent": "2F855A", "cover": "17352B"},
    "midnight": {"background": "171D2D", "ink": "F6F8FC", "muted": "AAB4C8", "accent": "5B8CFF", "cover": "090D18"},
    "monochrome": {"background": "FAFAFA", "ink": "171717", "muted": "737373", "accent": "525252", "cover": "171717"},
    "ocean": {"background": "F0F9FF", "ink": "123047", "muted": "617887", "accent": "0891B2", "cover": "123047"},
    "paper": {"background": "FCFBF7", "ink": "2B2A27", "muted": "77736B", "accent": "8B6F47", "cover": "2B2A27"},
    "plum": {"background": "FBF5FA", "ink": "321B3A", "muted": "806E83", "accent": "A855A0", "cover": "321B3A"},
    "signal": {"background": "FFF7ED", "ink": "18181B", "muted": "71717A", "accent": "EF4444", "cover": "18181B"},
    "studio": {"background": "F5F7FA", "ink": "20242C", "muted": "687180", "accent": "14B8A6", "cover": "20242C"},
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
    return normalized


def _add_pptx(
    destination: str,
    *,
    title: str,
    subtitle: str,
    slides: list[dict[str, Any]],
    style: dict[str, str],
    template: Path | None = None,
) -> None:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
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
        paragraph.font.name = "Aptos"
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

    cover = deck.slides.add_slide(blank_layout)
    cover.background.fill.solid()
    cover.background.fill.fore_color.rgb = cover_rgb
    textbox(cover, title, 0.8, 1.55, 11.7, 2.0, 40, RGBColor(255, 255, 255), True)
    textbox(cover, subtitle, 0.82, 3.8, 10.8, 1.1, 20, RGBColor(205, 213, 225))
    bar = cover.shapes.add_shape(1, Inches(0.82), Inches(5.75), Inches(1.8), Inches(0.12))
    bar.fill.solid()
    bar.fill.fore_color.rgb = accent_rgb
    bar.line.fill.background()

    for number, spec in enumerate(slides, 1):
        slide = deck.slides.add_slide(blank_layout)
        slide.background.fill.solid()
        layout = spec["layout"]
        slide.background.fill.fore_color.rgb = cover_rgb if layout in {"section", "conclusion"} else background
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
        textbox(slide, spec["title"], 0.72, 0.45, 11.8, 0.7, 28, ink, True)
        if spec["takeaway"]:
            textbox(slide, spec["takeaway"], 0.74, 1.22, 11.7, 0.62, 17, accent_rgb, True)
        image = spec["image"]
        if layout == "statement":
            statement = spec["takeaway"] or (spec["bullets"][0] if spec["bullets"] else spec["title"])
            textbox(slide, statement, 1.05, 2.15, 11.1, 2.7, 31, ink, True)
            textbox(slide, str(number), 12.25, 7.0, 0.4, 0.22, 9, muted)
            if spec["sources"]:
                try:
                    slide.notes_slide.notes_text_frame.text = "[Sources]\n" + "\n".join(spec["sources"])
                except (AttributeError, NotImplementedError):
                    pass
            continue
        if layout == "quote":
            quote = spec["takeaway"] or (spec["bullets"][0] if spec["bullets"] else spec["title"])
            mark = textbox(slide, "“", 0.8, 1.45, 1.0, 1.0, 70, accent_rgb, True)
            mark.text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT
            textbox(slide, quote, 1.5, 2.0, 10.35, 2.7, 29, ink, True)
            if spec["bullets"]:
                textbox(slide, spec["bullets"][-1], 1.55, 5.25, 9.8, 0.6, 14, muted)
            textbox(slide, str(number), 12.25, 7.0, 0.4, 0.22, 9, muted)
            continue
        if layout == "big-number":
            metric = spec["bullets"][0] if spec["bullets"] else "42%"
            textbox(slide, metric, 0.78, 2.0, 5.2, 2.3, 62, accent_rgb, True)
            textbox(slide, spec["takeaway"] or spec["title"], 6.0, 2.25, 6.0, 2.0, 24, ink, True)
            textbox(slide, str(number), 12.25, 7.0, 0.4, 0.22, 9, muted)
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
                    textbox(slide, spec["title"], 0.85, 0.75, 10.8, 1.2, 34, RGBColor(255, 255, 255), True)
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
                    paragraph.font.name = "Aptos"
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
            paragraph.font.name = "Aptos"
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
    style: dict[str, str],
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

    canvas.setFillColor(cover)
    canvas.rect(0, 0, width, height, stroke=0, fill=1)
    text(title, 58, 385, 32, HexColor("#FFFFFF"), "Helvetica-Bold", 840)
    text(subtitle, 60, 275, 16, HexColor("#CDD5E1"), max_width=760)
    canvas.setFillColor(accent_color)
    canvas.rect(60, 115, 130, 8, stroke=0, fill=1)
    canvas.showPage()

    for number, spec in enumerate(slides, 1):
        canvas.setFillColor(background)
        canvas.rect(0, 0, width, height, stroke=0, fill=1)
        layout = spec["layout"]
        if layout in {"section", "conclusion"}:
            canvas.setFillColor(cover)
            canvas.rect(0, 0, width, height, stroke=0, fill=1)
            text(f"{number:02d}", 60, 465, 12, accent_color, "Helvetica-Bold")
            text(spec["title"], 60, 335, 34, HexColor("#FFFFFF"), "Helvetica-Bold", 830)
            if spec["takeaway"]:
                text(spec["takeaway"], 62, 205, 16, HexColor("#CDD5E1"), max_width=760)
            canvas.setFillColor(accent_color)
            canvas.rect(62, 95, 115, 7, stroke=0, fill=1)
            canvas.showPage()
            continue
        if layout == "title-only":
            text(spec["title"], 70, 310, 36, ink, "Helvetica-Bold", 810)
            canvas.setFillColor(accent_color)
            canvas.rect(72, 120, 120, 7, stroke=0, fill=1)
            canvas.showPage()
            continue
        text(spec["title"], 52, 485, 24, ink, "Helvetica-Bold", 850)
        if spec["takeaway"]:
            text(spec["takeaway"], 54, 425, 14, accent_color, "Helvetica-Bold", 840)
        image = spec["image"]
        if layout == "statement":
            statement = spec["takeaway"] or (spec["bullets"][0] if spec["bullets"] else spec["title"])
            text(statement, 75, 320, 28, ink, "Helvetica-Bold", 810)
            text(str(number), 895, 25, 8, muted)
            canvas.showPage()
            continue
        if layout == "quote":
            quote = spec["takeaway"] or (spec["bullets"][0] if spec["bullets"] else spec["title"])
            text("“", 60, 400, 58, accent_color, "Helvetica-Bold")
            text(quote, 115, 335, 28, ink, "Helvetica-Bold", 760)
            if spec["bullets"]:
                text(spec["bullets"][-1], 120, 115, 12, muted, max_width=700)
            text(str(number), 895, 25, 8, muted)
            canvas.showPage()
            continue
        if layout == "big-number":
            metric = spec["bullets"][0] if spec["bullets"] else "42%"
            text(metric, 60, 300, 58, accent_color, "Helvetica-Bold", 400)
            text(spec["takeaway"] or spec["title"], 485, 310, 22, ink, "Helvetica-Bold", 410)
            canvas.showPage()
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
            canvas.showPage()
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
            canvas.showPage()
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
            canvas.showPage()
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
            canvas.showPage()
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
            canvas.showPage()
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
        canvas.showPage()
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
            required_images = max(0, min(_MAX_SLIDES, int(minimum_images or 0)))
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        except (TypeError, OverflowError):
            return {"ok": False, "error": "Minimum images must be a whole number."}
        embedded_images = sum(bool(item["image"]) for item in normalized)
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
                template=custom_template,
            )
            _add_pdf(
                pdf_temp,
                title=clean_title[:180],
                subtitle=str(subtitle or "").strip()[:300],
                slides=normalized,
                style=style,
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
            "images_embedded": embedded_images,
            "minimum_images": required_images,
            "visual_plan_complete": embedded_images >= required_images,
            "formats": ["pptx", "pdf"],
            "preview_paths": [str(path.relative_to(root)) for path in preview_paths],
            "contact_sheet_path": str(contact_sheet.relative_to(root)),
            "visual_review_required": True,
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
