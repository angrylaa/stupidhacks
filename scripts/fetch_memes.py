#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "assets"
MEMES_DIR = ASSETS_DIR / "memes"
RAW_DIR = ASSETS_DIR / "raw"


@dataclass(frozen=True)
class MemeTarget:
    output_name: str
    query: str
    title_hint: str
    start: str
    duration: int


TARGETS = (
    MemeTarget("harambe.mp4", "Harambe meme 2016", "harambe", "00:00:00", 8),
    MemeTarget("ppap.mp4", "PPAP official 2016", "ppap", "00:00:00", 8),
    MemeTarget("datboi.mp4", "Dat Boi meme 2016", "dat boi", "00:00:00", 8),
    MemeTarget("saltbae.mp4", "Salt Bae meme 2017", "salt bae", "00:00:00", 8),
    MemeTarget("we-are-number-one.mp4", "We Are Number One 2016", "number one", "00:00:35", 8),
)


def run(cmd: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=False,
        text=True,
        capture_output=capture,
    )


def ensure_tool(name: str) -> None:
    if shutil.which(name):
        return
    raise SystemExit(f"Missing required tool: {name}")


def yt_dlp_search(target: MemeTarget, limit: int) -> list[dict]:
    cmd = [
        "yt-dlp",
        "--dump-single-json",
        "--flat-playlist",
        "--dateafter",
        "20160101",
        "--datebefore",
        "20171231",
        "--match-filters",
        "!is_live",
        f"ytsearch{limit}:{target.query}",
    ]
    result = run(cmd, capture=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"yt-dlp search failed for {target.output_name}")
    payload = json.loads(result.stdout)
    entries = payload.get("entries") or []
    return list(entries)


def pick_entry(entries: list[dict], title_hint: str) -> dict | None:
    hint = title_hint.lower()
    for entry in entries:
        title = (entry.get("title") or "").lower()
        if hint in title:
            return entry
    return entries[0] if entries else None


def search_mode(limit: int) -> int:
    for target in TARGETS:
        try:
            entries = yt_dlp_search(target, limit)
        except Exception as exc:  # pragma: no cover - operator-facing script
            print(f"[search-error] {target.output_name}: {exc}", file=sys.stderr)
            continue
        print(f"\n== {target.output_name} ==")
        for entry in entries:
            print(f"- {entry.get('title')} | https://www.youtube.com/watch?v={entry.get('id')}")
    return 0


def trim_with_ffmpeg(source: Path, destination: Path, start: str, duration: int) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        start,
        "-i",
        str(source),
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(destination),
    ]
    result = run(cmd, capture=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"ffmpeg trim failed for {destination.name}")


def download_target(target: MemeTarget, limit: int, trim: bool) -> None:
    entries = yt_dlp_search(target, limit)
    entry = pick_entry(entries, target.title_hint)
    if entry is None:
        raise RuntimeError(f"No result found for {target.output_name}")

    video_url = f"https://www.youtube.com/watch?v={entry['id']}"
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    MEMES_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = RAW_DIR / target.output_name
    output_template = str(raw_path)
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-S",
        "vcodec:h264,acodec:m4a,res:720,fps",
        "-f",
        "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best",
        "--merge-output-format",
        "mp4",
        "-o",
        output_template,
        video_url,
    ]
    result = run(cmd, capture=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"Download failed for {video_url}")

    final_path = MEMES_DIR / target.output_name
    if trim and shutil.which("ffmpeg"):
        trim_with_ffmpeg(raw_path, final_path, target.start, target.duration)
    else:
        shutil.copy2(raw_path, final_path)

    print(f"[ok] {target.output_name} <- {video_url}")


def download_mode(limit: int, trim: bool) -> int:
    for target in TARGETS:
        try:
            download_target(target, limit, trim)
        except Exception as exc:  # pragma: no cover - operator-facing script
            print(f"[download-error] {target.output_name}: {exc}", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Search and download 2016 meme clips for QuitTok.")
    parser.add_argument("--search", action="store_true", help="Print candidate URLs without downloading.")
    parser.add_argument("--download", action="store_true", help="Download the default target set.")
    parser.add_argument("--limit", type=int, default=5, help="Number of search candidates per meme.")
    parser.add_argument(
        "--no-trim",
        action="store_true",
        help="Skip ffmpeg trimming even when ffmpeg is available.",
    )
    args = parser.parse_args()

    if not args.search and not args.download:
        parser.error("Choose at least one of --search or --download")

    ensure_tool("yt-dlp")
    if args.search:
        search_mode(args.limit)
    if args.download:
        download_mode(args.limit, trim=not args.no_trim)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
