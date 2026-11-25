from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - dependency error path
    raise SystemExit(
        "Pillow is required for validate_fhl_contour_overlap.py. "
        "Install it with `pip install pillow`."
    ) from exc


def parse_rgb(value: str) -> tuple[int, int, int]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 3:
        raise ValueError("--background-rgb must look like R,G,B")
    rgb = tuple(int(part) for part in parts)
    if any(channel < 0 or channel > 255 for channel in rgb):
        raise ValueError("RGB values must be between 0 and 255")
    return rgb


def color_distance(pixel: tuple[int, int, int], background: tuple[int, int, int]) -> int:
    return sum(abs(a - b) for a, b in zip(pixel, background))


def load_mask(
    path: Path,
    *,
    background_rgb: tuple[int, int, int],
    background_tolerance: int,
) -> tuple[list[bool], int, int]:
    image = Image.open(path).convert("RGBA")
    width, height = image.size
    mask: list[bool] = []
    for red, green, blue, alpha in image.getdata():
        is_foreground = (
            alpha >= 16
            and color_distance((red, green, blue), background_rgb) > background_tolerance
        )
        mask.append(is_foreground)
    return mask, width, height


def resize_candidate_mask(
    path: Path,
    *,
    width: int,
    height: int,
    background_rgb: tuple[int, int, int],
    background_tolerance: int,
) -> list[bool]:
    image = Image.open(path).convert("RGBA").resize((width, height), Image.NEAREST)
    mask: list[bool] = []
    for red, green, blue, alpha in image.getdata():
        is_foreground = (
            alpha >= 16
            and color_distance((red, green, blue), background_rgb) > background_tolerance
        )
        mask.append(is_foreground)
    return mask


def summarize_overlap(source_mask: list[bool], candidate_mask: list[bool]) -> dict[str, float | int]:
    source_area = sum(1 for bit in source_mask if bit)
    candidate_area = sum(1 for bit in candidate_mask if bit)
    intersection = sum(1 for src, cand in zip(source_mask, candidate_mask) if src and cand)
    union = sum(1 for src, cand in zip(source_mask, candidate_mask) if src or cand)

    source_coverage = (intersection / source_area) if source_area else 0.0
    candidate_precision = (intersection / candidate_area) if candidate_area else 0.0
    iou = (intersection / union) if union else 0.0
    score = min(source_coverage, candidate_precision)

    return {
        "source_area": source_area,
        "candidate_area": candidate_area,
        "intersection": intersection,
        "union": union,
        "source_coverage": source_coverage,
        "candidate_precision": candidate_precision,
        "iou": iou,
        "score": score,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate whether a candidate contour overlay stays within the locked FHL contour. "
            "The score is min(source_coverage, candidate_precision)."
        )
    )
    parser.add_argument("--source-mask", required=True, help="Source FHL contour mask image")
    parser.add_argument("--candidate-mask", required=True, help="Candidate contour mask image")
    parser.add_argument("--threshold", type=float, default=0.95, help="Minimum pass score")
    parser.add_argument(
        "--background-rgb",
        default="255,255,255",
        help="Background RGB used to separate foreground contour from the background",
    )
    parser.add_argument(
        "--background-tolerance",
        type=int,
        default=24,
        help="Sum-of-channel color distance needed to count as foreground",
    )
    parser.add_argument(
        "--allow-resize",
        action="store_true",
        help="Resize the candidate mask to the source mask size with nearest-neighbor scaling",
    )
    parser.add_argument("--output-json", help="Optional JSON report path")
    args = parser.parse_args()

    background_rgb = parse_rgb(args.background_rgb)
    source_path = Path(args.source_mask).resolve()
    candidate_path = Path(args.candidate_mask).resolve()

    source_mask, source_width, source_height = load_mask(
        source_path,
        background_rgb=background_rgb,
        background_tolerance=args.background_tolerance,
    )
    candidate_mask, candidate_width, candidate_height = load_mask(
        candidate_path,
        background_rgb=background_rgb,
        background_tolerance=args.background_tolerance,
    )

    if (candidate_width, candidate_height) != (source_width, source_height):
        if not args.allow_resize:
            raise SystemExit(
                f"Mask size mismatch: source={source_width}x{source_height}, "
                f"candidate={candidate_width}x{candidate_height}. "
                "Pass --allow-resize to compare after nearest-neighbor resize."
            )
        candidate_mask = resize_candidate_mask(
            candidate_path,
            width=source_width,
            height=source_height,
            background_rgb=background_rgb,
            background_tolerance=args.background_tolerance,
        )

    report = summarize_overlap(source_mask, candidate_mask)
    report.update(
        {
            "source_mask": str(source_path),
            "candidate_mask": str(candidate_path),
            "threshold": args.threshold,
            "pass": report["score"] >= args.threshold,
            "rule": "Contour must remain locked to FHL. If clipped in source, keep the same cropped extent.",
        }
    )

    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output_json:
        output_path = Path(args.output_json).resolve()
        output_path.write_text(output, encoding="utf-8")
    print(output)
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
