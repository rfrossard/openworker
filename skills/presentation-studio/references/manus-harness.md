# Manus-style Presentation Harness

Use this harness when Artifact Studio requests a Manus-style presentation. It combines
the research/presentation separation and rendered-output reflection described by
DeepPresenter and PPTAgent with the editable, template-aware product model demonstrated
by Presenton. OpenWorker implements the workflow natively; do not install or launch a
second application, Docker stack, or authentication system.

## Durable state

Create `reports/<name>.presentation.json` before research begins and update it after
every phase. Use this shape:

```json
{
  "schema_version": 1,
  "status": "briefing",
  "communication_job": {
    "audience": "",
    "decision": "",
    "outcome": "",
    "core_takeaway": ""
  },
  "phases": {
    "brief": "pending",
    "research": "pending",
    "storyboard": "pending",
    "art_direction": "pending",
    "assets": "pending",
    "render": "pending",
    "critique": "pending",
    "revision": "pending"
  },
  "slides": [],
  "asset_provenance": [],
  "critic_findings": [],
  "revision_log": [],
  "quality_decision": "pending"
}
```

Each slide record must include `number`, `narrative_job`, `claim`, `evidence`,
`source_urls`, `transition`, `layout`, `visual_intention`, and `status`. Keep state
recoverable: completed phases and outputs must survive a model failure or user pause.

## Agent phases

1. **Brief.** Define: “By the end, [audience] should [outcome] because [takeaway].”
   Identify the decision, constraints, tone, length, language, and evidence standard.
2. **Researcher.** Gather evidence independently of slide design. Prefer primary
   sources, atomize claims, record URLs and publication dates, and label uncertainty.
   Write the manuscript, sources manifest, and claim ledger before visual composition.
3. **Storyboard.** Give every slide one narrative job and one supported takeaway.
   Establish the opening tension, evidence sequence, transitions, synthesis, and action.
4. **Art Director.** Define a visual system—type scale, palette, spacing, image treatment,
   chart rules—and select varied layouts. Use at least three composition silhouettes in
   decks of eight slides or more. Visual variety must serve the narrative.
5. **Asset creation.** Generate or source visuals only after their communicative role is
   known. For generated visuals use `generate_image` with Gemini Nano Banana 2 Lite at
   1K and request a widescreen composition. Preserve prompt, provider, model, source,
   and slide mapping in `asset_provenance`.
6. **Presenter.** Create the PPTX and matching slide PDF with one complete call to
   `build_presentation`. Both formats must come from the same structured specification.
7. **Environment-grounded reflection.** Inspect every PNG returned in `preview_paths`
   and the returned contact sheet. Judge the pixels that were rendered, not the intended
   layout or hidden reasoning. Record findings by slide and severity.
8. **Revision.** Correct material findings, rebuild, and inspect the new previews.
   Perform at least one inspection and no more than three revision rounds. Never claim
   completion while a critical finding remains.

## Critic rubric

Score each dimension from 1–5 and record evidence:

- narrative coherence and transition quality;
- factual support and source-to-claim alignment;
- hierarchy and scanability at presentation distance;
- text density, clipping, overlap, and safe margins;
- image relevance, quality, cropping, and provenance;
- contrast, typography, alignment, and visual rhythm;
- layout variety without visual-system drift;
- editable PPTX integrity and PPTX/PDF parity.

The final quality decision passes only when every dimension is at least 4, there are no
critical findings, every factual slide has sources, all output signatures are valid,
and the preview count equals the PDF page count.

## Checkpoints and recovery

Set `status` to the current phase before starting it and mark the phase `completed` only
after its files exist and validate. On interruption, resume from the first incomplete
phase using the manifest; never repeat paid image generation for assets already present
and valid. Record every rebuild with timestamp, reason, affected slides, and resulting
preview folder.
