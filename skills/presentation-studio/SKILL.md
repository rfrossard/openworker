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
4. Read [art-direction.md](references/art-direction.md). Choose a coherent visual
   direction, establish a typographic scale, and plan a varied but purposeful sequence
   of slide silhouettes without changing the visual system.
   Apply the template selected in Artifact Studio. Built-in templates are editable design
   tokens; a workspace `.potx` takes precedence and its masters, layouts, theme, and
   placeholders must remain intact. Read [template-catalog.md](references/template-catalog.md).
5. Create or source a distinct relevant image for slides that materially benefit from
   imagery. Use the native `generate_image` tool, which is configured for Gemini Nano
   Banana 2 Lite at 1K, and request 1536×1024 for a widescreen aspect ratio. Never invent
   charts, people, quotes, logos, or documentary evidence.
   Copy the exact successful tool `path` into the slide's `image_path`; a planned visual
   remains incomplete until that workspace file exists. If generation is unavailable,
   use a sourced visual with provenance rather than silently dropping the asset.
6. Call `build_presentation` once with the complete structured slide specification,
   workspace-relative image paths, the selected `template_id` or `template_path`, and
   destinations under `reports/`.
7. Verify that the returned result says `ok: true`, includes both formats, reports the
   expected number of embedded images, and returns slide previews plus a contact sheet.
   Inspect the rendered previews before accepting the deck; do not judge only the slide
   specification. Run the rendered-deck taste audit in `art-direction.md`, record the
   findings, and fix the specification before rebuilding on failure.
   When visuals were requested, require `visual_plan_complete: true`. Never approve a
   deck with `images_embedded: 0` or mark image relevance “not applicable.”
8. Save the storyboard, slide-by-slide source manifest, and factual claim ledger beside
   the PPTX and PDF.

## Slide specification

- Keep the title slide minimal and use a 50–64 pt title.
- Give every content slide a specific takeaway title.
- Keep slide titles at 35–44 pt, key messages at 24–30 pt, and body copy at 16–22 pt.
- Use at most six concise bullets; prefer three or four.
- Put explanation in the presentation narrative, not dense paragraphs.
- Add `image_path`, `image_caption`, and source URLs when relevant.
- Set `image_required: true` for every storyboard visual. Choose `image_fit` (`cover` or
  `contain`) and `image_focus` (`left`, `center`, or `right`) based on the composition.
- Pass the approved visual count as `minimum_images` so rendering fails if assets are
  missing instead of quietly producing an incomplete deck.
- Select `image-left`, `image-right`, or `statement` layouts when they strengthen the
   narrative; use `auto` only when no deliberate alternative is warranted.
- Never repeat one layout more than twice consecutively. Keep card grids below 20% of
  the deck and alternate text-led, visual-led, data-led, and transition silhouettes.
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
