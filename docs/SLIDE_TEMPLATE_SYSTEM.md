# Slide Designer template system

The Slide Designer has a deliberately curated catalog. Each theme is an editable
PowerPoint system—not a downloaded slide pack or a flattened background image.
Brand and franchise names identify a high-level communication direction only; the
implementation does not ship logos, proprietary fonts, copied consulting materials,
or third-party photography.

## Shared quality rules

- Keep a 16:9 canvas, 5–8% outer margins, and one dominant message per slide.
- Use a minimum 4.5:1 base text/background contrast; choose a light or dark ink token
  before rendering a slide.
- Use no more than two font families. Decorative families have safe editable fallbacks.
- Generate five deterministic background compositions per themed family from CSS and
  native editable PowerPoint shapes. They create rhythm without external image rights.
- Use native, semantic charts, tables, flows, and text. A theme must never disguise a
  weak data choice with decoration.

## Theme grammar

| Theme | Intended job | Distinguishing visual elements |
|---|---|---|
| Boardroom | Workshop, strategy, teaching | matte slate, chalk type fallback, ruled baselines, chalk dust, hand-drawn underline, formula corner, sticky-note panel, clipped margin, tally marks, boxed hypothesis, numbered exercise, yellow chalk accent |
| Paper | Research, field notes, manuscript review | ivory paper, ruled/graph/kraft/spiral/field-note variants, pencil type fallback, red margin, binder edge, page shadow, handwritten underline, page number, tape marker, notebook tab, annotation box, muted green pencil accent |
| Editorial | Narrative, policy, culture | broadsheet/magazine/columns/clippings/press variants, masthead rule, serif hierarchy, column guide, issue label, deck line, pull-quote bar, caption rule, crop frame, byline, page folio, brick-red accent |
| Botanical Noir | Nature and human-impact stories | canopy/fern/trunks/moss/grove variants, dark forest base, leaf silhouettes, branch lines, moss texture, soft vignette, botanical serif, mint field label, photo-safe panel, section marker, restrained lime accent, no decorative dots |
| Dashboard Pro | Metrics, operating reviews, financial decisions | matrix/KPI/terminal/market/signal variants, dark canvas, green-positive/orange-attention semantics, subtle grid, value rail, period marker, rank labels, metric frame, threshold line, source stamp, focused chart area, monospace metadata |
| Cyan Infographic | Explain systems simply | modular/index/map/cards/signals variants, contained blocks, numbered nodes, cyan connectors, bounded diagrams, compact legend, label rail, highlighted step, plain-language caption, whitespace band, no crossing decorative line |
| Itaú | Accessible product and service story | own orange/navy palette, curved orange field, clear cards, accessible contrast, route/path motif, friendly rounded emphasis, summary chips, high-visibility callout, journey marker, action band, plain-language data label |
| Tron | Future system story | original perspective grid, HUD frame, circuit rail, portal, scanline, neon glow, light trail, coordinate labels, status marker, pixel edge, dark contrast, user-selectable cyan/green/orange light |
| Minecraft | Playful learning and planning | original pixel grid, block panels, grass/cave/craft/sunset/map variants, squared corners, terrain layers, inventory chips, map marker, crafting sequence, pixel divider, block shadow, legible fallback type |
| Consulting | Executive recommendation | thesis bar, evidence hierarchy, answer-first title, data emphasis, decision frame, footnote rail, exhibit label, source line, comparison discipline, practical action box, restrained palette, no copied proprietary material |

`McKinsey`, `Accenture`, `BCP`, and `Bain` are grouped under **Consulting** and use
different original palettes and emphasis while following the shared consulting grammar.
The `Tron` light selector changes only an editable accent token.

## Reference posture

The system takes high-level inspiration from publicly observable product and visual
storytelling practices, including [Itaú’s public site](https://www.itau.com.br/),
[Figma’s Itaú case study](https://www.figma.com/customers/itau-unibanco-launched-45-digital-products-with-figma/),
and [McKinsey’s description of its visual storytelling work](https://www.mckinsey.com/careers/our-roles/internal-roles/capabilities-and-roles/visual-graphics-and-media).
No external assets are copied into OpenWorker.
