---
name: industrial-board-layout-en
description: Plan English industrial design exhibition-board compositions for image models using product evidence, English word wrapping, text hierarchy, thin gutters and cross-region alignment. Use for English boards or English versions; use the Chinese skill for Chinese boards. Outputs a reviewed composition guide, not a final board.
---

# Industrial board composition — English

Produce a product-specific composition guide for an image model: editable SVG, PNG wireframe, layout JSON, framing notes and generation prompt. The primary board copy is English regardless of conversation language. Read [English typography](references/language-typesetting.md) for every project. Never reuse Chinese type sizes, line breaks or boxes by simple translation.

## Scope

“Try it” means prepare the guide. Continue to image generation only when explicitly requested or already authorized for this run. Feedback about alignment first changes the guide and prompt; do not silently switch to compositing a precise final board from source photos. A placement proof may validate the guide, but must be labelled as such. If the user asks for a Chinese version, use industrial-board-layout-zh when available; never assume another skill is installed, and retain the user's language request in the handoff. Explicit bilingual requests require separately planned language roles and reflow, not parallel translations by default.

## Evidence and composition

Read [product evidence](references/product-evidence.md). Inspect each supplied view and bind each image slot to its actual source and state. Record evidence_status/evidence_note. Few images mean fewer supported modules: do not invent unseen views, internals, mechanisms, functional claims, research or design-development history to fill the board.

Read [composition decisions](references/composition-decisions.md). Let silhouette, orientation, information priorities, image inventory and English copy determine the visual anchor and reading order before choosing a grid. No default sidebar, central hero, bottom sequence or fixed column count. A repeated crop is not new evidence. When web research is authorized, seek supported views/details/states of the same product. Preserve requested paper size and orientation; disclose preview assumptions. Consult [layout defaults](references/layout-defaults.md) only for a calculation starting point.

Read [type and image](references/type-and-image.md). Compose titles, prose, captions and images together. Establish project-specific thin gutters, group spacing, heading-image spacing and image-caption spacing; declare every image adjacency in gap_rules. Keep source aspect ratio, purposeful crop and comparable visual scale within peer groups. Position numbers and headings as separate elements.

## English text and detail framing

Apply [English typography](references/language-typesetting.md): actual Latin-font measurement, word-based wrapping, consistent heading case, long-word handling, widow/orphan review and caption baselines. Recalculate text areas and adjacent regions from the actual English copy. Preserve user wording; propose substantive edits rather than silently changing meaning. Frame edges, first/last baselines and ink bounds are different checks.

For detail slots read [detail framing](references/detail-framing.md). Bind source_region, target_feature and exclude_features to the exact reference. Render and inspect source markers; a label such as “heel” is not sufficient evidence of the intended region.

Use [composition evaluation](references/composition-evaluation.md) to assess density, hierarchy, reading order and text-image ownership. Geometry checks can locate problems but do not judge all aesthetics. Distinguish actual cross-product tests, hypothetical cases and unexecuted plans.

## Build and review

Read [wireframe handoff](references/wireframe-to-image.md) and the [schema](references/layout-schema.md). Start a new free-elements layout for the current product; assets/example-board-wireframe.json illustrates data only. Run scripts/render_wireframe.py with the real layout and output directory; the CLI applies this package's English language policy. It does not generate a product image. Dependencies and actual fonts must be available before claiming PNG rendering or measured typography.

Declare whole-board alignment_bands for shared heading rows, image ends and caption first/last baselines, plus gap_rules for repeated spacings. Inspect relationships across modules, not only easy local pairs. Intentional stagger needs a design reason; never relabel a user-reported mistake as deliberate.

Before handoff execute all [five review passes](references/five-pass-review.md) in order: content/evidence; geometry/alignment; real-image placement/framing/scale; English typography/readability; density/version/prompt consistency. Each pass includes actual PNG viewing; pass 2 includes measurement evidence and pass 5 checks the real prompt. Repeating one script five times is insufficient. Fix, rerender and repeat the current-version reviews after changes. Do not claim passed reviews without the necessary viewing ability or evidence.

Only after all five passes have passed with no open issues, run scripts/review_gate.py check --dir <guide-directory>. Review records bind to current artifacts. Never hand an unreviewed draft to the image model. The gate validates records and versions; it cannot guarantee aesthetic judgment or model compliance.

## Deliver

Follow [delivery modes](references/delivery-modes.md). Deliver the composition rationale, editable SVG and PNG, layout JSON, framing instructions and generation prompt. Explain the input roles: product identity from source photos, geometry from wireframe, style from style references. Use current proportions, anchors and gaps; remove conflicting old constraints. Prompts must state English text strategy, source-bound product identity and guide-label removal.

If generation is authorized, follow [model validation](references/model-validation.md): freeze actual input roles/limits/fingerprints, retain raw outputs and review three times after generation: composition/gaps/baselines; each product and state; actual copy/caption ownership/guide removal. Wrong parts, substituted states or unsupported views are hard failures even in an attractive image. Record pass/fail/unconfirmed separately. Default to one targeted repair within the authorized run, then report remaining failures rather than endlessly regenerating. A successful wireframe or single model result is not evidence of stable generative compliance.
