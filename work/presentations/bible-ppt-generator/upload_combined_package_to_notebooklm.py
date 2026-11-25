from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path


def run_command(args: list[str]) -> str:
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
            return (completed.stdout or completed.stderr).strip()
        except subprocess.CalledProcessError as exc:
            last_error = exc
            output = (exc.stdout or "") + "\n" + (exc.stderr or "")
            if "All connection attempts failed" not in output or attempt == 7:
                raise
            time.sleep(2 + attempt)
    assert last_error is not None
    raise last_error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--title", default="Bible Map Master Upload")
    args = parser.parse_args()

    package_dir = Path(args.package_dir).resolve()
    prompt_path = package_dir / "full_prompt_with_map_refs.txt"
    maps_dir = package_dir / "maps"

    create_output = run_command(["notebooklm", "create", "--use", "--json", args.title])
    notebook_id = None
    try:
        parsed = json.loads(create_output)
        notebook_id = parsed.get("id") or parsed.get("notebook_id")
    except json.JSONDecodeError:
        notebook_id = None

    items: list[dict[str, str | None]] = []

    prompt_cmd = ["notebooklm", "source", "add", "--json"]
    if notebook_id:
        prompt_cmd.extend(["--notebook", str(notebook_id)])
    prompt_cmd.extend(["--type", "file", "--title", "master prompt", str(prompt_path)])
    items.append({"path": str(prompt_path), "output": run_command(prompt_cmd)})

    for map_path in sorted(maps_dir.glob("*")):
        cmd = ["notebooklm", "source", "add", "--json"]
        if notebook_id:
            cmd.extend(["--notebook", str(notebook_id)])
        cmd.extend(["--type", "file", "--title", map_path.name, str(map_path)])
        items.append({"path": str(map_path), "output": run_command(cmd)})

    print(
        json.dumps(
            {
                "package_dir": str(package_dir),
                "notebook_title": args.title,
                "notebook_id": notebook_id,
                "uploaded_count": len(items),
                "items": items,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
