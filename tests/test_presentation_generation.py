from __future__ import annotations

import zipfile

from PIL import Image
from pypdf import PdfReader
from pptx import Presentation

from coworker.server.manager import SessionManager
from coworker.skills import SkillLoader
from coworker.tools.presentation_generation import make_build_presentation_tool


def _sample_image(path):
    Image.new("RGB", (640, 360), (35, 76, 142)).save(path, "PNG")


def test_build_presentation_creates_real_matching_files_with_image(tmp_path):
    image = tmp_path / "visual.png"
    _sample_image(image)
    tool = make_build_presentation_tool(workspace=tmp_path)

    result = tool(
        title="Evidence into decisions",
        subtitle="A validated presentation pipeline",
        slides=[
            {
                "title": "Visual evidence improves the narrative",
                "takeaway": "One structured specification drives both final formats.",
                "bullets": ["Research claims first", "Use a distinct relevant visual"],
                "image_path": "visual.png",
                "image_caption": "Test visual",
                "layout": "image-left",
                "sources": ["https://example.com/research"],
            },
            {
                "title": "Quality gates prevent fake deliverables",
                "layout": "statement",
                "bullets": ["Validate signatures", "Keep output editable"],
            },
        ],
        pptx_path="reports/deck.pptx",
        pdf_path="reports/deck.pdf",
    )

    assert result["ok"] is True
    assert result["slides"] == 3
    assert result["images_embedded"] == 1
    assert len(result["preview_paths"]) == 3
    assert result["visual_review_required"] is True
    pptx = tmp_path / "reports/deck.pptx"
    pdf = tmp_path / "reports/deck.pdf"
    assert pptx.read_bytes().startswith(b"PK")
    assert pdf.read_bytes().startswith(b"%PDF-")
    assert len(Presentation(pptx).slides) == 3
    assert len(PdfReader(pdf).pages) == 3
    for path in result["preview_paths"]:
        assert (tmp_path / path).read_bytes().startswith(b"\x89PNG")
    assert (tmp_path / result["contact_sheet_path"]).read_bytes().startswith(b"\x89PNG")
    with zipfile.ZipFile(pptx) as archive:
        assert any(name.startswith("ppt/media/") for name in archive.namelist())


def test_build_presentation_rejects_path_escape_and_missing_image(tmp_path):
    tool = make_build_presentation_tool(workspace=tmp_path)
    escaped = tool(
        title="Deck",
        slides=[{"title": "Slide"}],
        pptx_path="../deck.pptx",
        pdf_path="deck.pdf",
    )
    missing = tool(
        title="Deck",
        slides=[{"title": "Slide", "image_path": "missing.png"}],
        pptx_path="deck.pptx",
        pdf_path="deck.pdf",
    )
    assert escaped["ok"] is False
    assert "escapes" in escaped["error"]
    assert missing["ok"] is False
    assert "not found" in missing["error"]


def test_quality_gate_rejects_markdown_renamed_as_pdf(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "deck.pptx").write_bytes(b"PK\x03\x04")
    (reports / "deck.pdf").write_text("# This is Markdown", encoding="utf-8")
    run = {
        "deliverable": "presentation",
        "artifact_paths": ["reports/deck.pptx", "reports/deck.pdf"],
        "method": "standard",
        "image_mode": "none",
    }
    quality = SessionManager._research_quality(run, workspace=tmp_path)
    assert quality["status"] == "needs_attention"
    assert "The PDF file is not a real PDF document." in quality["issues"]


def test_presentation_studio_skill_has_no_placeholders():
    loader = SkillLoader(
        [
            (
                __import__("pathlib").Path(__file__).resolve().parents[1]
                / "skills"
            )
        ]
    )
    skill = loader.get("presentation-studio")
    assert skill is not None
    assert "build_presentation" in skill.instructions
    assert "TODO" not in skill.instructions
