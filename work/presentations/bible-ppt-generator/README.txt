Bible Sermon PPT Generator

Purpose
- Parse sermon-style slide instructions like the user's sample.
- Build a PowerPoint deck with text, a consistent visual theme, and prompt-driven images.
- Keep the workflow reusable for future sermon, Bible map, and NotebookLM-assisted decks.

Command
- node build_sermon_deck.mjs --input "<input.txt>" --output "<output.pptx>" --workspace "<scratch-dir>" --skill-dir "<presentations-skill-dir>"

Current behavior
- Parses slide blocks beginning with "### Slide N:"
- Reads Slide Content bullet groups
- Reads Visual Composition concept and NotebookLM prompt
- Builds a 16:9 deck with left text / right visual layout
- Tries prompt-image generation first
- Falls back to a local SVG placeholder that preserves the visual prompt

Future extension points
- Swap prompt-image generation with NotebookLM or external image assets
- Detect map slides and replace them with FHL / Bible map assets
- Add a richer theme selector or template-following mode

NotebookLM atlas reference package
- Script: `prepare_notebooklm_atlas_package.py`
- Purpose: build a per-place reference package from FHL map data plus OpenBible geocoding data
- Output:
  - `manifest.json`
  - `README.md`
  - `notebooklm_prompt.txt`
  - `maps/*.gif`

Example
- python prepare_notebooklm_atlas_package.py --place "示羅" --output-dir "<dir>"
- python prepare_notebooklm_atlas_package.py --place-file "<utf8-place.txt>" --lid "0217" --output-dir "<dir>"

Intended workflow
- Resolve place name against FHL
- Pull FHL place metadata and related map gids
- Download concrete FHL map images
- Match the place against OpenBible geocoding data
- Write a NotebookLM-ready atlas prompt and manifest

Practical notes
- FHL requests are fetched with browser-like headers because plain urllib requests can be blocked
- For Windows automation, `--place-file` is the safest way to avoid terminal encoding issues with Chinese place names
- `--lid` can be used when you already know the exact FHL location id and want deterministic output

NotebookLM deck package
- Script: `prepare_notebooklm_deck_package.py`
- Purpose: build slide-by-slide NotebookLM reference folders from one slide instruction file plus a JSON spec
- Key outputs:
  - `slide-XX/notebooklm_slide_brief.txt`
  - `slide-XX/atlas/*`
  - `slide-XX/upload_kit/slide_notebooklm_rewritten_prompt.txt`
  - `slide-XX/upload_kit/maps/*`
  - `slide-XX/final-notebooklm-image.png` (target path for your returned image)
  - `image_manifest.json`

Example flow
- python prepare_notebooklm_deck_package.py --input "<slides.txt>" --spec "<atlas-spec.json>" --output-dir "<deck-package-dir>"
- For each map slide, the script now:
  - resolves the requested Bible places
  - downloads real FHL map files
  - copies one selected reference map per place into `slide-XX/upload_kit/maps/`
  - renames each selected file with slide-aware names like `slide-02-map-01-shiloh-035.gif`
  - rewrites the NotebookLM prompt so it explicitly tells NotebookLM which exact uploaded filenames to consult
- Upload the rewritten prompt plus the renamed map files from `slide-XX/upload_kit/` to NotebookLM
- After upload finishes, stop and let the user manually press Generate in NotebookLM
- When NotebookLM returns the final image, save it to the corresponding `slide-XX/final-notebooklm-image.png`
- node build_sermon_deck.mjs --input "<slides.txt>" --output "<deck.pptx>" --workspace "<scratch-dir>" --skill-dir "<presentations-skill-dir>" --image-manifest "<deck-package-dir>/image_manifest.json"

NotebookLM upload helper
- Script: `upload_slide_package_to_notebooklm.py`
- Current behavior:
  - if `slide-XX/upload_kit/` exists, upload `slide_notebooklm_rewritten_prompt.txt` first, then upload all files in `upload_kit/maps/`
  - otherwise fall back to the older brief + atlas prompt workflow

Current preferred workflow
1. Prepare the slide package with `prepare_notebooklm_deck_package.py`
2. Inspect `slide-XX/upload_kit/`
3. Upload that package to NotebookLM, manually or with `upload_slide_package_to_notebooklm.py`
4. In NotebookLM, review the uploaded rewritten prompt and maps
5. Manually click Generate
6. Save the final generated image back to `slide-XX/final-notebooklm-image.png`
7. Rebuild the PPT with `build_sermon_deck.mjs`

FHL source-lock rules
- FHL decides the viewport range.
- FHL also decides the contour.
- If a boundary is cropped in the FHL source, keep the same cropped extent.
- Do not infer missing edges from Bible text.
- Before accepting a refined map, validate contour overlap against the FHL mask with `validate_fhl_contour_overlap.py`.
- Required gate: `score >= 0.95`.

## D:\Bible project copy

This tool folder is installed at D:\Bible\work\presentations\bible-ppt-generator to match the paths used by spiritual-slide-composer. The old slide-02 helper now derives the project root from its own location.

The atlas package scripts fetch FHL map records and images when run; this folder does not include a static FHL map archive. The contour validator requires Pillow. The upload helpers invoke the NotebookLM CLI.
