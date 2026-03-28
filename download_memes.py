#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "assets" / "memes"
MAX_SECONDS = 30


@dataclass(frozen=True)
class MemeDownload:
    filename: str
    url: str


MEMES = (
    MemeDownload(
        filename="pokemon_go.mp4",
        url="https://www.youtube.com/watch?v=vfc42Pb5RA8&list=RDvfc42Pb5RA8&start_radio=1",
    ),
    MemeDownload(
        filename="damn_daniel.mp4",
        url="https://www.youtube.com/shorts/kfFcyTuopbI",
    ),
    MemeDownload(
        filename="dat_boi.mp4",
        url="https://www.youtube.com/watch?v=pCOb6Fykxz0",
    ),
    MemeDownload(
        filename="harambe.mp4",
        url="https://www.youtube.com/shorts/flcY1uUmhi0",
    ),
    MemeDownload(
        filename="ppap.mp4",
        url="https://www.youtube.com/watch?v=NfuiB52K7X8&list=RDNfuiB52K7X8&start_radio=1",
    ),
)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=False,
        text=True,
        capture_output=True,
    )


def ensure_tools() -> None:
    missing = [tool for tool in ("yt-dlp", "ffmpeg") if shutil.which(tool) is None]
    if missing:
        raise SystemExit(f"Missing required tool(s): {', '.join(missing)}")


def download_video(spec: MemeDownload, temp_dir: Path) -> Path:
    stem = Path(spec.filename).stem
    output_template = str(temp_dir / f"{stem}.%(ext)s")
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-S",
        "res:720,vcodec:h264,acodec:m4a,fps",
        "-f",
        "bv*[height<=720]+ba/b[height<=720]/best[height<=720]/best",
        "--merge-output-format",
        "mp4",
        "-o",
        output_template,
        spec.url,
    ]
    result = run(cmd)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "yt-dlp failed")

    candidates = sorted(temp_dir.glob(f"{stem}.*"))
    if not candidates:
        raise RuntimeError("yt-dlp reported success but no output file was found")
    return candidates[0]


def trim_video(source: Path, destination: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-t",
        str(MAX_SECONDS),
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(destination),
    ]
    result = run(cmd)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "ffmpeg trim failed")


def main() -> int:
    ensure_tools()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    succeeded: list[str] = []
    failed: list[tuple[str, str]] = []

    with tempfile.TemporaryDirectory(prefix="quittok-downloads-") as temp_root:
        temp_dir = Path(temp_root)
        for spec in MEMES:
            print(f"[start] {spec.filename} <- {spec.url}")
            try:
                downloaded = download_video(spec, temp_dir)
                trim_video(downloaded, OUTPUT_DIR / spec.filename)
            except Exception as exc:
                failed.append((spec.filename, str(exc)))
                print(f"[failed] {spec.filename}: {exc}")
                continue

            succeeded.append(spec.filename)
            print(f"[ok] {spec.filename}")

    print("\nSummary")
    print(f"  succeeded: {len(succeeded)}")
    for name in succeeded:
        print(f"    - {name}")

    print(f"  failed: {len(failed)}")
    for name, reason in failed:
        print(f"    - {name}: {reason}")

    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
