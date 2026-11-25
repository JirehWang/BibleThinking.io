from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FHL_LIST_URL = "https://bible.fhl.net/LMAP/list.php"
FHL_SEARCH_URL = "https://bible.fhl.net/LMAP/search.php"
FHL_MAP_PAGE_URL = "https://bible.fhl.net/LMAP/index.php?gid={gid}"
FHL_MAP_IMAGE_URL = "https://bible.fhl.net/LMAP/map/{gid}.GIF"
OPENBIBLE_ANCIENT_URL = (
    "https://raw.githubusercontent.com/openbibleinfo/Bible-Geocoding-Data/main/data/ancient.jsonl"
)
OPENBIBLE_MODERN_URL = (
    "https://raw.githubusercontent.com/openbibleinfo/Bible-Geocoding-Data/main/data/modern.jsonl"
)
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/json,text/plain,*/*",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


class FhlListParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.entries: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attr_map = dict(attrs)
        href = attr_map.get("href")
        if href and href.startswith("show.html?"):
            self._href = href
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._href is None:
            return
        name = "".join(self._text_parts).strip()
        lid = self._href.split("?", 1)[1].strip("=")
        if name and lid:
            self.entries.append((lid, name))
        self._href = None
        self._text_parts = []


@dataclass
class FhlMatch:
    lid: str
    name: str


def fetch_text(url: str, *, method: str = "GET", data: bytes | None = None) -> str:
    headers = dict(DEFAULT_HEADERS)
    if "bible.fhl.net" in url:
        headers["Referer"] = "https://bible.fhl.net/new/smap.html"
        headers["Origin"] = "https://bible.fhl.net"
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    request = Request(url, data=data, method=method, headers=headers)
    with urlopen(request) as response:
        raw = response.read()
        encodings: list[str] = []
        charset = response.headers.get_content_charset()
        if charset:
            encodings.append(charset)
        if "bible.fhl.net" in url:
            encodings.extend(["big5", "cp950", "utf-8"])
        else:
            encodings.extend(["utf-8", "big5"])
        for encoding in encodings:
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode(encodings[0], errors="replace")


def fetch_bytes(url: str) -> bytes:
    headers = dict(DEFAULT_HEADERS)
    if "bible.fhl.net" in url:
        headers["Referer"] = "https://bible.fhl.net/new/smap.html"
    request = Request(url, headers=headers)
    with urlopen(request) as response:
        return response.read()


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", "", name).lower()


def sanitize_slug(value: str) -> str:
    asciiish = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "-", value.strip())
    asciiish = re.sub(r"-{2,}", "-", asciiish).strip("-")
    return asciiish or "atlas-package"


def load_fhl_index(cache_dir: Path, *, offline: bool) -> list[FhlMatch]:
    cache_path = cache_dir / "fhl-list.html"
    if cache_path.exists():
      html = cache_path.read_text(encoding="utf-8", errors="replace")
    elif offline:
      raise FileNotFoundError(f"Offline mode requires cached file: {cache_path}")
    else:
      html = fetch_text(FHL_LIST_URL)
      cache_path.write_text(html, encoding="utf-8")

    parser = FhlListParser()
    parser.feed(html)
    return [FhlMatch(lid=lid, name=name) for lid, name in parser.entries]


def resolve_fhl_place(index: list[FhlMatch], query: str) -> FhlMatch:
    normalized_query = normalize_name(query)
    exact = [entry for entry in index if normalize_name(entry.name) == normalized_query]
    if exact:
        return exact[0]

    contains = [entry for entry in index if normalized_query in normalize_name(entry.name)]
    if contains:
        return contains[0]

    raise LookupError(f"Could not resolve FHL place name: {query}")


def load_fhl_place_json(cache_dir: Path, lid: str, *, offline: bool) -> dict:
    cache_path = cache_dir / f"fhl-place-{lid}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    if offline:
        raise FileNotFoundError(f"Offline mode requires cached file: {cache_path}")

    body = urlencode({"lid": lid}).encode("utf-8")
    text = fetch_text(FHL_SEARCH_URL, method="POST", data=body)
    data = json.loads(text)
    if not data:
        raise LookupError(f"No FHL place JSON returned for lid={lid}")
    cache_path.write_text(json.dumps(data[0], ensure_ascii=False, indent=2), encoding="utf-8")
    return data[0]


def read_place_arg(place: str | None, place_file: str | None) -> str:
    if place:
        return place.strip()
    if place_file:
        return Path(place_file).read_text(encoding="utf-8").strip()
    raise ValueError("Either --place or --place-file is required")


def extract_gids(place_data: dict) -> list[str]:
    gids: list[str] = []
    for key in ("dec", "dec1", "dec2", "dec3", "remark"):
        value = place_data.get(key, "")
        gids.extend(re.findall(r"\$(\d{3})", value))
    return sorted(set(gids))


def load_map_page(cache_dir: Path, gid: str, *, offline: bool) -> str:
    cache_path = cache_dir / f"fhl-map-page-{gid}.html"
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8", errors="replace")
    if offline:
        raise FileNotFoundError(f"Offline mode requires cached file: {cache_path}")
    html = fetch_text(FHL_MAP_PAGE_URL.format(gid=gid))
    cache_path.write_text(html, encoding="utf-8")
    return html


def download_map_image(cache_dir: Path, output_dir: Path, gid: str, *, offline: bool) -> Path:
    output_path = output_dir / f"fhl-map-{gid}.gif"
    if output_path.exists():
        return output_path
    cache_path = cache_dir / f"fhl-map-{gid}.gif"
    if cache_path.exists():
        output_path.write_bytes(cache_path.read_bytes())
        return output_path
    if offline:
        raise FileNotFoundError(f"Offline mode requires cached file: {cache_path}")
    data = fetch_bytes(FHL_MAP_IMAGE_URL.format(gid=gid))
    cache_path.write_bytes(data)
    output_path.write_bytes(data)
    return output_path


def stream_jsonl_match(url: str, matcher, cache_path: Path | None = None) -> dict | None:
    if cache_path and cache_path.exists():
        with cache_path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                obj = json.loads(line)
                if matcher(obj):
                    return obj
        return None

    request = Request(url, headers=DEFAULT_HEADERS)
    with urlopen(request) as response:
        for raw_line in response:
            if not raw_line.strip():
                continue
            obj = json.loads(raw_line.decode("utf-8"))
            if matcher(obj):
                return obj
    return None


def load_openbible_place(cache_dir: Path, place_data: dict, *, offline: bool) -> tuple[dict | None, dict | None]:
    cache_ancient = cache_dir / "openbible-ancient.jsonl"
    cache_modern = cache_dir / "openbible-modern.jsonl"

    english_name = place_data.get("ename", "").strip()
    english_names = {english_name.lower(), english_name.replace("-", " ").lower()}

    def ancient_match(obj: dict) -> bool:
        friendly = str(obj.get("friendly_id", "")).lower()
        if friendly in english_names:
            return True
        for assoc in obj.get("modern_associations", {}).values():
            if str(assoc.get("name", "")).lower() in english_names:
                return True
        return False

    ancient = stream_jsonl_match(
        OPENBIBLE_ANCIENT_URL,
        ancient_match,
        cache_path=cache_ancient if cache_ancient.exists() else None,
    )
    if ancient is None and offline:
        return None, None
    if ancient is None:
        return None, None

    modern_id = None
    if ancient.get("modern_associations"):
        modern_id = next(iter(ancient["modern_associations"].keys()))

    modern = None
    if modern_id:
        modern = stream_jsonl_match(
            OPENBIBLE_MODERN_URL,
            lambda obj: obj.get("id") == modern_id,
            cache_path=cache_modern if cache_modern.exists() else None,
        )
    return ancient, modern


def summarize_verses(ancient: dict | None, limit: int = 8) -> list[str]:
    if not ancient:
        return []
    verses = ancient.get("verses", [])
    return [item.get("readable", item.get("osis", "")) for item in verses[:limit]]


def build_notebooklm_prompt(
    place_data: dict,
    gids: list[str],
    ancient: dict | None,
    modern: dict | None,
    map_files: Iterable[Path],
) -> str:
    cname = place_data.get("cname", "").strip()
    ename = place_data.get("ename", "").strip()
    verses = ", ".join(summarize_verses(ancient))
    coords = ""
    if ancient:
        ident = ancient.get("identifications", [{}])[0]
        resolutions = ident.get("resolutions", [])
        if resolutions:
            coords = resolutions[0].get("lonlat", "")
    modern_name = ""
    if modern:
        modern_name = modern.get("friendly_id", "")

    file_lines = "\n".join(f"- {path.name}" for path in map_files)
    return (
        f"NotebookLM atlas image brief for {cname} ({ename})\n\n"
        f"Use the attached FHL map images as historical map references, not as final visual style.\n"
        f"Generate a cinematic Bible atlas slide in the spirit of Sacred_Inheritance_Atlas.\n\n"
        f"Place: {cname} / {ename}\n"
        f"FHL lid: {place_data.get('lid', '').strip()}\n"
        f"Map gids: {', '.join(gids) if gids else 'none'}\n"
        f"OpenBible modern identification: {modern_name or 'unknown'}\n"
        f"Approx coordinates: {coords or 'unknown'}\n"
        f"Example verses: {verses or 'not found'}\n\n"
        f"Visual direction:\n"
        f"- Keep the final slide fully NotebookLM-rendered\n"
        f"- Preserve key geography and place relationships from the references\n"
        f"- Use deep navy atmosphere, warm gold highlights, sacred/cartographic lighting, embossed terrain, and high legibility Chinese labels\n"
        f"- Do not simply paste or trace the source map; reinterpret it as a premium atlas illustration\n\n"
        f"Reference files:\n{file_lines}\n"
    )


def write_package(output_dir: Path, manifest: dict, prompt: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "notebooklm_prompt.txt").write_text(prompt, encoding="utf-8")

    summary_lines = [
        f"# {manifest['place']['cname']} / {manifest['place']['ename']}",
        "",
        "## FHL",
        f"- lid: {manifest['place']['lid']}",
        f"- map gids: {', '.join(manifest['fhl_map_gids']) if manifest['fhl_map_gids'] else 'none'}",
        f"- map files: {', '.join(path['file'] for path in manifest['map_files']) if manifest['map_files'] else 'none'}",
        "",
        "## OpenBible",
        f"- ancient id: {manifest.get('openbible', {}).get('ancient_id', 'n/a')}",
        f"- modern id: {manifest.get('openbible', {}).get('modern_id', 'n/a')}",
        f"- coordinates: {manifest.get('openbible', {}).get('coordinates', 'n/a')}",
        "",
        "## NotebookLM",
        "- Use `notebooklm_prompt.txt` plus the downloaded map files as the reference package.",
    ]
    (output_dir / "README.md").write_text("\n".join(summary_lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--place", help="Chinese biblical place name")
    parser.add_argument("--place-file", help="UTF-8 text file containing the place name")
    parser.add_argument("--lid", help="Direct FHL lid override, bypassing name lookup")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--cache-dir")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    place_query = read_place_arg(args.place, args.place_file)
    output_dir = Path(args.output_dir).resolve()
    cache_dir = Path(args.cache_dir).resolve() if args.cache_dir else output_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    maps_dir = output_dir / "maps"
    maps_dir.mkdir(parents=True, exist_ok=True)

    if args.lid:
        resolved = FhlMatch(lid=args.lid, name=place_query or args.lid)
    else:
        fhl_index = load_fhl_index(cache_dir, offline=args.offline)
        resolved = resolve_fhl_place(fhl_index, place_query)

    place_data = load_fhl_place_json(cache_dir, resolved.lid, offline=args.offline)
    gids = extract_gids(place_data)

    map_files: list[Path] = []
    map_pages = []
    for gid in gids[:4]:
        map_pages.append({"gid": gid, "url": FHL_MAP_PAGE_URL.format(gid=gid)})
        load_map_page(cache_dir, gid, offline=args.offline)
        map_files.append(download_map_image(cache_dir, maps_dir, gid, offline=args.offline))

    ancient, modern = load_openbible_place(cache_dir, place_data, offline=args.offline)

    manifest = {
        "place": {
            "query": place_query,
            "lid": place_data.get("lid", "").strip(),
            "cname": place_data.get("cname", "").strip(),
            "ename": place_data.get("ename", "").strip(),
            "meaning": place_data.get("cexp", "").strip(),
        },
        "fhl_map_gids": gids,
        "map_pages": map_pages,
        "map_files": [{"gid": gid, "file": path.name} for gid, path in zip(gids[:4], map_files)],
        "fhl_notes": {
            "dec": place_data.get("dec", ""),
            "dec1": place_data.get("dec1", ""),
            "dec2": place_data.get("dec2", ""),
            "dec3": place_data.get("dec3", ""),
            "remark": place_data.get("remark", ""),
        },
        "openbible": {
            "ancient_id": ancient.get("id") if ancient else None,
            "modern_id": next(iter(ancient.get("modern_associations", {}).keys())) if ancient and ancient.get("modern_associations") else None,
            "friendly_id": ancient.get("friendly_id") if ancient else None,
            "coordinates": (
                ancient.get("identifications", [{}])[0].get("resolutions", [{}])[0].get("lonlat")
                if ancient
                else None
            ),
            "verses": summarize_verses(ancient),
            "modern_friendly_id": modern.get("friendly_id") if modern else None,
        },
    }

    prompt = build_notebooklm_prompt(place_data, gids, ancient, modern, map_files)
    write_package(output_dir, manifest, prompt)
    print(json.dumps({"output_dir": str(output_dir), "map_count": len(map_files), "gids": gids}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
