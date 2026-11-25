# FHL Source-Locked Map Workflow

Use this workflow when a Bible map must stay tied to a concrete FHL source instead of being reinterpreted from text.

## Hard rules

1. FHL decides the viewport.
2. FHL also decides the contour.
3. If the FHL source crops a boundary, keep the same cropped extent.
4. Do not infer or redraw missing edges from Bible text.
5. Only optimize terrain, color, labels, and slide composition after the contour is locked.
6. Contour overlap must score at least `0.95` before the image can move forward.

## Recommended steps

1. Pick the exact FHL source map or source set for the slide.
2. Export or isolate a binary contour mask from the FHL source.
3. Build the improved visual on top of the same extent.
4. Export a candidate contour mask from the improved image.
5. Compare the masks with `validate_fhl_contour_overlap.py`.
6. If the score is below `0.95`, keep correcting before aesthetic polish.
7. Once the contour passes, finish terrain relief, palette, typography, and slide cleanup.

## Validation command

```powershell
python validate_fhl_contour_overlap.py `
  --source-mask "<fhl-mask.png>" `
  --candidate-mask "<candidate-mask.png>" `
  --threshold 0.95 `
  --output-json "<report.json>"
```

## Interpretation of the report

- `source_coverage`
  - how much of the FHL contour is still covered by the candidate
- `candidate_precision`
  - how much of the candidate stays inside the FHL contour
- `iou`
  - classic intersection-over-union for extra reference
- `score`
  - the gate metric used here: `min(source_coverage, candidate_precision)`

Pass only when `score >= 0.95`.
