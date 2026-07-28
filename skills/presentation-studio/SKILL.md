---
name: presentation-studio
description: Create researched, image-rich slide decks as editable PPTX plus matching slide-formatted PDF. Use for presentations, pitch decks, research decks, PPT/PPTX, slide PDFs, or when converting research into audience-ready visual storytelling with sources and quality checks.
---

# Presentation Studio

Produce a real slide deck, never Markdown renamed as PDF. Use the native
`build_presentation` tool for both final formats and `generate_image` when original
visuals are requested.

## Workflow

For a Manus-style Presentation artifact, first read
[manus-harness.md](references/manus-harness.md) and maintain its durable harness manifest
through every phase.

1. Define in one sentence: “By the end, [audience] should [outcome] because [takeaway].”
2. Research claims before designing slides. Prefer primary sources, record URLs, and
   preserve disagreement or uncertainty.
3. Write a storyboard with one narrative job and one evidence-backed takeaway per slide.
4. Choose a coherent visual direction and vary slide composition without changing the
   visual system.
5. Create or source a distinct relevant image for slides that materially benefit from
   imagery. Use the native `generate_image` tool, which is configured for Gemini Nano
   Banana 2 Lite at 1K, and request 1536×1024 for a widescreen aspect ratio. Never invent
   charts, people, quotes, logos, or documentary evidence.
6. Call `build_presentation` once with the complete structured slide specification,
   workspace-relative image paths, and destinations under `reports/`.
7. Verify that the returned result says `ok: true`, includes both formats, reports the
   expected number of embedded images, and returns slide previews plus a contact sheet.
   Inspect the rendered previews before accepting the deck; do not judge only the slide
   specification. Fix the specification and rebuild on failure.
8. Save the storyboard, slide-by-slide source manifest, and factual claim ledger beside
   the PPTX and PDF.

## Slide specification

- Keep the title slide minimal.
- Give every content slide a specific takeaway title.
- Use at most six concise bullets; prefer three or four.
- Put explanation in the presentation narrative, not dense paragraphs.
- Add `image_path`, `image_caption`, and source URLs when relevant.
- Select `image-left`, `image-right`, or `statement` layouts when they strengthen the
  narrative; use `auto` only when no deliberate alternative is warranted.
- Use one image at most once unless it is an intentional background.
- Close by resolving the opening question, making a decision, or defining next actions.
- Keep all audience-facing content in the user’s requested language.

## Required outputs

- `reports/<name>.pptx`: editable widescreen PowerPoint.
- `reports/<name>.pdf`: the same deck as one visually composed slide per PDF page.
- `reports/<name>-storyboard.md`: slide purpose, claim, visual, and transition.
- `reports/<name>.sources.md`: source and image provenance by slide.
- `reports/<name>.claims.json`: atomic factual claims and supporting URLs.
- `reports/<name>-previews/`: rendered PNG slides and a contact sheet for visual review.

Never create the PDF with a Markdown writer or plain-text converter. Never mark the task
complete based only on file extensions.

## Quality gate

Read [quality-gate.md](references/quality-gate.md) before finalizing. If any required
check fails, revise and rebuild instead of describing the deck as complete.
