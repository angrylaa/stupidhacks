from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ClipConfig:
    clip_id: str
    file_name: str
    caption: str
    apps: tuple[str, ...]
    path: Path


@dataclass(frozen=True)
class AppConfig:
    base_duration: int
    max_duration: int
    fallback_caption: str
    clips: tuple[ClipConfig, ...]
    manifest_path: Path

    @classmethod
    def load(cls, manifest_path: Path | None = None) -> "AppConfig":
        manifest_path = manifest_path or repo_root() / "assets" / "manifest.json"
        raw = json.loads(manifest_path.read_text())
        clips = []
        memes_dir = manifest_path.parent / "memes"
        for item in raw.get("clips", []):
            clip_path = memes_dir / item["file"]
            if not clip_path.exists():
                continue
            clips.append(
                ClipConfig(
                    clip_id=item["id"],
                    file_name=item["file"],
                    caption=item.get("caption", raw.get("fallback_caption", "")),
                    apps=tuple(item.get("apps", [])),
                    path=clip_path,
                )
            )
        return cls(
            base_duration=int(raw.get("base_duration", 8)),
            max_duration=int(raw.get("max_duration", 12)),
            fallback_caption=raw.get("fallback_caption", "You brought this on yourself."),
            clips=tuple(clips),
            manifest_path=manifest_path,
        )
