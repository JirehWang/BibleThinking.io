from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class UploadItem:
    path: Path
    title: str | None = None
    source_type: str | None = None


def run_command(args: list[str], *, dry_run: bool) -> str:
    if dry_run:
        print("$", " ".join(args))
        return ""
    last_error: subprocess.CalledProcessError | None = None
    for attempt in range(8):
        try:
            completed = subprocess.run(
                args,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if completed.stdout:
                return completed.stdout.strip()
            return completed.stderr.strip()
        except subprocess.CalledProcessError as exc:
            last_error = exc
            output = (exc.stdout or "") + "\n" + (exc.stderr or "")
            if "All connection attempts failed" not in output or attempt == 7:
                raise
            time.sleep(2 + attempt)
    assert last_error is not None
    raise last_error


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_upload_items(slide_dir: Path, *, maps_per_atlas: int) -> list[UploadItem]:
    items: list[UploadItem] = []
    upload_kit_dir = slide_dir / "upload_kit"
    rewritten_prompt = upload_kit_dir / "slide_notebooklm_rewritten_prompt.txt"
    if rewritten_prompt.exists():
        items.append(
            UploadItem(
                path=rewritten_prompt,
                title=f"{slide_dir.name} rewritten prompt",
                source_type="file",
            )
        )

        for map_path in sorted((upload_kit_dir / "maps").glob("*")):
            items.append(UploadItem(path=map_path, title=map_path.name, source_type="file"))
        return items

    brief_path = slide_dir / "notebooklm_slide_brief.txt"
    if brief_path.exists():
        items.append(UploadItem(path=brief_path, title=f"{slide_dir.name} brief", source_type="file"))

    atlas_root = slide_dir / "atlas"
    for atlas_dir in sorted(path for path in atlas_root.iterdir() if path.is_dir()):
        prompt_path = atlas_dir / "notebooklm_prompt.txt"
        if prompt_path.exists():
            items.append(UploadItem(path=prompt_path, title=f"{atlas_dir.name} prompt", source_type="file"))

        maps = sorted((atlas_dir / "maps").glob("*"))
        for map_path in maps[:maps_per_atlas]:
            items.append(UploadItem(path=map_path, title=map_path.stem, source_type="file"))

    return items


def create_notebook_title(slide_manifest: dict, fallback: str) -> str:
    slide_no = slide_manifest.get("slide", "?")
    return f"Bible Map Slide {slide_no}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slide-dir", required=True)
    parser.add_argument("--notebook-title")
    parser.add_argument("--maps-per-atlas", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    slide_dir = Path(args.slide_dir).resolve()
    slide_manifest_path = slide_dir / "slide_manifest.json"
    if not slide_manifest_path.exists():
        raise FileNotFoundError(f"Missing slide manifest: {slide_manifest_path}")

    slide_manifest = load_json(slide_manifest_path)
    notebook_title = args.notebook_title or create_notebook_title(slide_manifest, slide_dir.name)
    upload_items = collect_upload_items(slide_dir, maps_per_atlas=args.maps_per_atlas)
    if not upload_items:
        raise ValueError(f"No upload items found in {slide_dir}")

    create_output = run_command(["notebooklm", "create", "--use", "--json", notebook_title], dry_run=args.dry_run)
    notebook_id = None
    if create_output:
        try:
            parsed = json.loads(create_output)
            notebook_id = parsed.get("id") or parsed.get("notebook_id")
        except json.JSONDecodeError:
            notebook_id = None

    results: list[dict[str, str | None]] = []
    for item in upload_items:
        cmd = ["notebooklm", "source", "add", "--json"]
        if notebook_id:
            cmd.extend(["--notebook", str(notebook_id)])
        if item.source_type:
            cmd.extend(["--type", item.source_type])
        if item.title:
            cmd.extend(["--title", item.title])
        cmd.append(str(item.path))
        output = run_command(cmd, dry_run=args.dry_run)
        results.append(
            {
                "path": str(item.path),
                "title": item.title,
                "output": output or None,
            }
        )

    print(
        json.dumps(
            {
                "slide_dir": str(slide_dir),
                "notebook_title": notebook_title,
                "notebook_id": notebook_id,
                "uploaded_count": len(results),
                "items": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
