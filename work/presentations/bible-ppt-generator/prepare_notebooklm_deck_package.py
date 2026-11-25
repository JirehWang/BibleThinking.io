from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
import shutil


SCRIPT_DIR = Path(__file__).resolve().parent
ATLAS_SCRIPT = SCRIPT_DIR / "prepare_notebooklm_atlas_package.py"


@dataclass
class SlideData:
    number: int
    heading: str
    title: str
    content_lines: list[str]
    visual_lines: list[str]
    concept: str
    prompt: str


def strip_markdown(value: str) -> str:
    return value.replace("\r", "").strip().lstrip("*- ").replace("**", "").strip()


def split_label_value(raw_line: str) -> tuple[str, str] | None:
    line = strip_markdown(raw_line)
    if ":" not in line:
        return None
    label, value = line.split(":", 1)
    return label.strip(), value.strip()


def parse_slides(source_text: str) -> list[SlideData]:
    normalized = source_text.lstrip("\ufeff")
    matches = list(re.finditer(r"^###\s*Slide\s+(\d+):[^\n]*$", normalized, re.M))
    slides: list[SlideData] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        block = normalized[start:end].strip()
        lines = [line.rstrip() for line in block.splitlines()]
        heading = lines[0].strip()
        title = re.sub(r"^###\s*Slide\s+\d+:\s*", "", heading).strip()

        content_index = next((i for i, line in enumerate(lines) if "slide content" in line.lower()), -1)
        visual_index = next((i for i, line in enumerate(lines) if "visual composition" in line.lower()), -1)
        content_lines = lines[content_index + 1 : visual_index if visual_index >= 0 else None] if content_index >= 0 else []
        visual_lines = lines[visual_index + 1 :] if visual_index >= 0 else []

        concept = ""
        prompt = ""
        for line in visual_lines:
            parsed = split_label_value(line)
            if not parsed:
                continue
            label, value = parsed
            lowered = label.lower()
            if "concept" in lowered:
                concept = value
            if "prompt" in lowered:
                prompt = value

        slides.append(
            SlideData(
                number=int(match.group(1)),
                heading=heading,
                title=title,
                content_lines=[line for line in content_lines if line.strip()],
                visual_lines=[line for line in visual_lines if line.strip()],
                concept=concept,
                prompt=prompt,
            )
        )
    return slides


def load_spec(spec_path: Path) -> dict:
    return json.loads(spec_path.read_text(encoding="utf-8"))


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def run_atlas_command(
    python_exe: str,
    *,
    place: str | None,
    place_file: str | None,
    lid: str | None,
    output_dir: Path,
    cache_dir: Path,
    offline: bool,
) -> None:
    cmd = [python_exe, str(ATLAS_SCRIPT)]
    if place:
        cmd.extend(["--place", place])
    if place_file:
        cmd.extend(["--place-file", place_file])
    if lid:
        cmd.extend(["--lid", lid])
    if offline:
        cmd.append("--offline")
    cmd.extend(["--output-dir", str(output_dir), "--cache-dir", str(cache_dir)])
    subprocess.run(cmd, check=True)


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def copy_map_for_upload(
    atlas_dir: Path,
    upload_maps_dir: Path,
    slide_no: int,
    atlas_index: int,
    slug: str,
) -> tuple[str | None, str | None]:
    maps_dir = atlas_dir / "maps"
    maps = sorted(maps_dir.glob("*"))
    if not maps:
        return None, None

    source = maps[0]
    map_gid = source.stem.split("-")[-1]
    target_name = f"slide-{slide_no:02d}-map-{atlas_index:02d}-{slug}-{map_gid}{source.suffix.lower()}"
    target_path = upload_maps_dir / target_name
    shutil.copy2(source, target_path)
    return target_name, map_gid


def build_rewritten_prompt(slide: SlideData, atlases: list[dict], selected_maps: list[dict]) -> str:
    selected_lines = []
    for item in selected_maps:
        selected_lines.append(
            f"- {item['place_cname']} / {item['place_ename']}: use `{item['upload_filename']}` (FHL map gid {item['map_gid']})"
        )

    atlas_lines = []
    for atlas in atlases:
        place = atlas["place"]
        openbible = atlas.get("openbible", {})
        atlas_lines.append(
            f"- {place['cname']} / {place['ename']} | lid {place['lid']} | "
            f"coords {openbible.get('coordinates') or 'unknown'} | "
            f"candidate map gids {', '.join(atlas.get('fhl_map_gids', [])[:6]) or 'none'}"
        )

    return (
        f"Slide title:\n{slide.title}\n\n"
        f"Base concept:\n{slide.concept or 'N/A'}\n\n"
        f"Base prompt:\n{slide.prompt or 'N/A'}\n\n"
        "Selected reference maps for this slide:\n"
        f"{chr(10).join(selected_lines) if selected_lines else '- none'}\n\n"
        "Place summary:\n"
        f"{chr(10).join(atlas_lines) if atlas_lines else '- none'}\n\n"
        "Instruction for NotebookLM:\n"
        "Use the uploaded FHL map files as the locked geographic source. "
        "When interpreting the slide, explicitly consult the selected map files named above. "
        "Preserve the FHL viewport and FHL contour from those exact files. "
        "If any boundary is cropped in the FHL source, keep the same cropped extent and do not reconstruct the missing edge. "
        "Do not reinterpret tribal boundaries from Bible text alone. "
        "Do not directly paste or collage the source maps. Re-render the final visual as a single premium presentation image after the source geography is preserved. "
        "Keep the output fully NotebookLM-rendered, in a Sacred Inheritance Atlas-like style, with high legibility Traditional Chinese labels.\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Slide instruction text file")
    parser.add_argument("--spec", required=True, help="JSON mapping slides to biblical places")
    parser.add_argument("--output-dir", required=True, help="Output folder for deck package")
    parser.add_argument("--python-exe", default=sys.executable)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    spec_path = Path(args.spec).resolve()
    output_dir = Path(args.output_dir).resolve()
    cache_root = output_dir / "_cache"
    ensure_dir(output_dir)
    ensure_dir(cache_root)

    slides = {slide.number: slide for slide in parse_slides(input_path.read_text(encoding="utf-8"))}
    spec = load_spec(spec_path)
    slide_targets = spec.get("slides", [])
    if not slide_targets:
        raise ValueError("Spec must contain a non-empty slides array")

    package_manifest: dict[str, object] = {
        "input": str(input_path),
        "spec": str(spec_path),
        "generated_slides": [],
    }
    image_manifest: dict[str, str] = {}

    for slide_target in slide_targets:
        slide_no = int(slide_target["slide"])
        slide = slides.get(slide_no)
        if slide is None:
            raise KeyError(f"Slide {slide_no} not found in input")

        slide_dir = output_dir / f"slide-{slide_no:02d}"
        atlas_root = slide_dir / "atlas"
        upload_root = slide_dir / "upload_kit"
        upload_maps_dir = upload_root / "maps"
        ensure_dir(slide_dir)
        ensure_dir(atlas_root)
        ensure_dir(upload_maps_dir)

        atlases = []
        selected_maps = []
        for index, place_spec in enumerate(slide_target.get("places", []), start=1):
            slug = place_spec.get("slug", "place")
            atlas_dir = atlas_root / f"{index:02d}-{slug}"
            cache_dir = cache_root / f"slide-{slide_no:02d}" / atlas_dir.name
            ensure_dir(cache_dir)
            run_atlas_command(
                args.python_exe,
                place=place_spec.get("place"),
                place_file=place_spec.get("place_file"),
                lid=place_spec.get("lid"),
                output_dir=atlas_dir,
                cache_dir=cache_dir,
                offline=args.offline,
            )
            atlas_manifest = json.loads((atlas_dir / "manifest.json").read_text(encoding="utf-8"))
            atlases.append(atlas_manifest)
            upload_filename, map_gid = copy_map_for_upload(atlas_dir, upload_maps_dir, slide_no, index, slug)
            if upload_filename:
                place = atlas_manifest["place"]
                selected_maps.append(
                    {
                        "place_cname": place["cname"],
                        "place_ename": place["ename"],
                        "upload_filename": upload_filename,
                        "map_gid": map_gid,
                    }
                )

        atlas_summary_lines = []
        for atlas in atlases:
            place = atlas["place"]
            openbible = atlas.get("openbible", {})
            atlas_summary_lines.append(
                f"- {place['cname']} / {place['ename']} | lid {place['lid']} | "
                f"coords {openbible.get('coordinates') or 'unknown'} | "
                f"maps {', '.join(atlas.get('fhl_map_gids', [])[:4]) or 'none'}"
            )

        notebooklm_brief = (
            f"Slide {slide_no}: {slide.title}\n\n"
            f"Base visual concept:\n{slide.concept or 'N/A'}\n\n"
            f"Base NotebookLM prompt:\n{slide.prompt or 'N/A'}\n\n"
            f"Atlas references for this slide:\n"
            f"{chr(10).join(atlas_summary_lines) if atlas_summary_lines else '- none'}\n\n"
            "Instruction:\n"
            "Use the attached FHL map images as the locked source for viewport and contour. "
            "If the FHL source crops a boundary, keep the same cropped extent and do not reconstruct the missing edge. "
            "Generate one final 16:9 presentation image fully rendered by NotebookLM, "
            "consistent with the Sacred_Inheritance_Atlas visual language. "
            "Keep Traditional Chinese labels where appropriate.\n"
        )
        write_text(slide_dir / "notebooklm_slide_brief.txt", notebooklm_brief)
        rewritten_prompt = build_rewritten_prompt(slide, atlases, selected_maps)
        write_text(upload_root / "slide_notebooklm_rewritten_prompt.txt", rewritten_prompt)
        upload_readme = (
            f"# Slide {slide_no:02d} Upload Kit\n\n"
            "Upload these files to NotebookLM:\n"
            "1. `slide_notebooklm_rewritten_prompt.txt`\n"
            "2. all files under `maps/`\n\n"
            "Then ask NotebookLM to generate the final slide image using the rewritten prompt.\n"
        )
        write_text(upload_root / "README.md", upload_readme)

        image_manifest[str(slide_no)] = str(slide_dir / "final-notebooklm-image.png")
        slide_manifest = {
            "slide": slide_no,
            "title": slide.title,
            "heading": slide.heading,
            "concept": slide.concept,
            "prompt": slide.prompt,
            "atlas_count": len(atlases),
            "atlas_dirs": [str(path.relative_to(output_dir)) for path in atlas_root.iterdir() if path.is_dir()],
            "selected_maps": selected_maps,
            "upload_kit_dir": str(upload_root.relative_to(output_dir)),
            "final_image_target": f"slide-{slide_no:02d}/final-notebooklm-image.png",
        }
        write_text(slide_dir / "slide_manifest.json", json.dumps(slide_manifest, ensure_ascii=False, indent=2))
        package_manifest["generated_slides"].append(slide_manifest)

    write_text(output_dir / "image_manifest.json", json.dumps(image_manifest, ensure_ascii=False, indent=2))
    write_text(output_dir / "deck_package_manifest.json", json.dumps(package_manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
