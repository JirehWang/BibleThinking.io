from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_combined_prompt(
    original_prompt: str,
    slide_manifests: list[dict],
) -> str:
    lines: list[str] = [
        original_prompt.rstrip(),
        "",
        "---",
        "",
        "【NotebookLM 地圖參考指引】",
        "以下地圖檔為歷史地理參考圖，僅供你理解各投影片的地點、疆界、相對位置與地理重點。",
        "請不要直接拼貼原始地圖檔，而是要根據這些檔案重繪最終投影片視覺。",
        "整份簡報請維持 NotebookLM 自行生成的風格，並保留高可讀性的繁體中文標示。",
        "",
    ]

    for manifest in slide_manifests:
        slide_no = manifest["slide"]
        title = manifest.get("title") or f"Slide {slide_no}"
        selected_maps = manifest.get("selected_maps", [])
        lines.append(f"Slide {slide_no}: {title}")
        if not selected_maps:
            lines.append("- 此頁沒有額外指定地圖檔。")
        else:
            lines.append("請優先參考以下上傳檔名：")
            for item in selected_maps:
                cname = item.get("place_cname") or ""
                ename = item.get("place_ename") or ""
                filename = item.get("upload_filename") or ""
                gid = item.get("map_gid") or ""
                lines.append(f"- {cname} / {ename}: `{filename}` (FHL map gid {gid})")
        lines.append("")

    lines.extend(
        [
            "總體生成要求：",
            "- 請以整份提示詞為主體來理解簡報邏輯，不要把每張圖視為獨立任務。",
            "- 各張地圖檔只作為對應頁面的地理依據。",
            "- 需要地圖的頁面，請使用該頁對應列出的檔名。",
            "- 不需要地圖的頁面，請照原提示詞直接生成。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True, help="Original full prompt text file")
    parser.add_argument("--deck-package-dir", required=True, help="Prepared deck package directory")
    parser.add_argument("--output-dir", required=True, help="Combined upload package directory")
    args = parser.parse_args()

    prompt_path = Path(args.prompt).resolve()
    deck_dir = Path(args.deck_package_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    maps_dir = output_dir / "maps"
    ensure_dir(output_dir)
    ensure_dir(maps_dir)

    slide_manifests: list[dict] = []
    copied_maps: list[str] = []

    for slide_dir in sorted(path for path in deck_dir.iterdir() if path.is_dir() and path.name.startswith("slide-")):
        manifest_path = slide_dir / "slide_manifest.json"
        if not manifest_path.exists():
            continue
        manifest = load_json(manifest_path)
        slide_manifests.append(manifest)

        upload_maps_dir = slide_dir / "upload_kit" / "maps"
        if upload_maps_dir.exists():
            for map_path in sorted(upload_maps_dir.glob("*")):
                target = maps_dir / map_path.name
                shutil.copy2(map_path, target)
                copied_maps.append(target.name)

    combined_prompt = build_combined_prompt(
        prompt_path.read_text(encoding="utf-8"),
        slide_manifests,
    )
    (output_dir / "full_prompt_with_map_refs.txt").write_text(combined_prompt, encoding="utf-8")
    (output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "prompt_file": "full_prompt_with_map_refs.txt",
                "map_count": len(copied_maps),
                "maps": copied_maps,
                "slide_count": len(slide_manifests),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / "README.md").write_text(
        "\n".join(
            [
                "# Combined NotebookLM Upload Package",
                "",
                "Upload these files to one NotebookLM notebook:",
                "1. `full_prompt_with_map_refs.txt`",
                "2. all files under `maps/`",
                "",
                "Then review the notebook and manually press Generate in NotebookLM.",
            ]
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "map_count": len(copied_maps),
                "slide_count": len(slide_manifests),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
