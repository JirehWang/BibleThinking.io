---
name: spiritual-slide-composer
description: Turn Bible-study analysis into presentation outlines, teaching slides, handouts, or visual guidance. Use when the user requests a teaching deliverable and the interpretation needed for its content is sufficiently established.
---

# Spiritual Slide Composer

Do formatting last.

## Preconditions

Before composing slides, establish the passage meaning and any theological or pastoral claims that the requested material actually uses. Complete relevant upstream research first; report unresolved source gaps instead of presenting uncertain claims as established. A slide focused on observation or background does not need an application added solely to satisfy a template.

If the requested slide is Bible-map driven, also confirm:

- the FHL source map is identified
- the viewport must stay FHL-locked
- the contour must stay FHL-locked
- any NotebookLM upload workflow has been explicitly requested and its stopping point is clear

## Style goals

- high scannability
- minimal wording
- use the requested or existing canvas; assume 16:9 only when the size is unspecified
- reverent, clean, non-busy tone
- concise Traditional Chinese phrasing when the user is working in Chinese

## Choose a layout from the content

First identify the audience, the role of the page in the deck, and its one main idea. Then choose a layout that makes the information relationship visible. Treat image-to-text ratios, number of cards, and word counts as starting suggestions; adapt them to legibility, passage length, content, and the user's instructions. A text-led slide may have no illustration. Split a dense slide before shrinking text or dropping necessary context.

| Information relationship | Useful layout | Design check |
| --- | --- | --- |
| Sequence or cause | Timeline, ordered nodes, or a path | Use directional connections for actual order; imply causation only when supported. |
| Comparison | Aligned columns or a comparison table | Compare on shared dimensions; do not create a false opposition between historical contexts or interpretations. |
| Main idea and components | Top-down cards or a central idea with branches | Make the parent and its components clear without giving decoration equal weight. |
| Scene or narrative | Full-bleed scene with a readable text zone | Use imagery to support the message; keep essential text legible. |
| Detailed object or map | Central source image with callouts | Point each label to the relevant feature and preserve the source's meaning. |

Common page roles can inform the starting composition:

- **Cover:** image on the right and a clean title area on the left; roughly 50% image and 50% text space can be a starting point.
- **Background or story:** image or map beside explanatory text; roughly 40% image and 60% text can be a starting point, adjusted when a map is the main subject.
- **Teaching flow:** ordered activity cards with optional small illustrations; roughly 20% image and 80% text can be a starting point.
- **Core truth and application:** a clear quotation or main idea above an optional scene band; roughly 30% image and 70% text can be a starting point.

These are options, not mandatory page templates or measured area requirements. Also use text-led Scripture observation, passage-to-passage correspondence, and discussion-question pages when they serve the study.

For a lesson-design presentation aimed at teachers or reviewers, show relevant learning objectives, teacher and learner activities, and how understanding will be observed. For slides used directly with learners, prioritize the passage, observation cues, discussion questions, and activity directions. Identify timing as proposed if it was not supplied.

## Scripture and visual fidelity

- Keep quoted Scripture distinguishable from paraphrase, interpretation, and application. Preserve needed context, cite the passage, and identify the translation when quoting.
- Match every cross-reference to the specific point it supports, indicating whether it is a direct quotation, thematic connection, historical continuation, or analogy where relevant.
- Illustrations are visual interpretations, not evidence for unverified historical details. Cite historical map sources and indicate uncertain places or boundaries where relevant.
- Keep important text, labels, and diagrams editable in a slide file when the tool supports it; do not rely on generated-image text for Scripture quotations. Check reading order, contrast, typography, and projection-scale legibility.

## Bible map extension

When the slide is geography-heavy, use this map-specific flow.

### Source rules

- FHL decides the viewport.
- FHL also decides the contour.
- If the FHL source crops a boundary, keep the same cropped extent.
- Do not infer or redraw missing edges from Bible text.

### Visual optimization scope

You may improve:

- terrain relief
- color harmony
- labels
- layout cleanliness
- slide readability

Do not improve by:

- inventing new contours
- extending clipped boundaries
- freehanding tribal shapes from interpretation

### Validation gate

Before accepting a refined map, compare the candidate contour against the FHL source contour.

Use:

- `work/presentations/bible-ppt-generator/validate_fhl_contour_overlap.py`

Target:

- `score >= 0.95`

If the score is below that threshold, keep correcting before calling the map ready.

### NotebookLM package flow

Only use this workflow when NotebookLM work is explicitly requested and available. Use the existing local scripts when they fit:

- `work/presentations/bible-ppt-generator/prepare_notebooklm_atlas_package.py`
- `work/presentations/bible-ppt-generator/prepare_notebooklm_deck_package.py`
- `work/presentations/bible-ppt-generator/prepare_notebooklm_combined_package.py`
- `work/presentations/bible-ppt-generator/upload_slide_package_to_notebooklm.py`
- `work/presentations/bible-ppt-generator/upload_combined_package_to_notebooklm.py`
- `work/presentations/bible-ppt-generator/FHL_SOURCE_LOCK_WORKFLOW.md`

### NotebookLM stop rule

For an explicitly requested NotebookLM upload workflow, the handoff endpoint is:

- the per-slide package is uploaded to NotebookLM, or
- the combined package is uploaded to NotebookLM

Stop there.

Do not continue into:

- waiting for generation
- pressing Generate
- pulling images back down
- rebuilding the PPT

unless the user explicitly asks for the next stage.

## Slide structure

Use this shape as a starting point, adapting to the user's requested format:

`### Slide X: [short title] | [supporting subtitle]`

Then include the requested content and, when useful for the deliverable:

- `Slide Content`
- `Visual Composition`

## Slide content rules

- use a small number of supporting points, adjusted to the page's purpose; a quotation, diagram, or discussion question can be the main content without a bullet list
- each bullet should carry one idea
- avoid paragraph blocks
- preserve theological precision and necessary context when compressing; split content across slides when needed

## Visual composition rules

- establish one clear focal idea and a legible reading path
- choose illustrations, maps, icons, diagrams, or a text-led composition according to the content and audience
- when an image prompt is needed, keep it visually specific and consistent with the chosen layout
- avoid generic stock-photo language
- for map slides, do not invent contours here; keep all geographic outlines locked to the FHL source

## Output contract

For each slide, provide the title and requested content. Add a concise visual composition when the user requests layout guidance or it is needed for the deliverable. Provide an image-generation prompt only when requested or required for the chosen image workflow; text-only slide outlines do not need one.

For map workflows, report the applicable FHL source, contour validation status, NotebookLM upload status, and next step accurately. Check that cited sources and scripts exist before using them; do not claim validation or upload when they are unavailable or were not performed.
