from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


STATE_DIR = Path.home() / "Library" / "Application Support" / "QuitTok 2016"
STATE_PATH = STATE_DIR / "state.json"


@dataclass
class PlaybackState:
    recent_clip_ids: list[str] = field(default_factory=list)
    play_counts: dict[str, int] = field(default_factory=dict)
    last_manifest_index: int = -1


class StateStore:
    def __init__(self, path: Path = STATE_PATH) -> None:
        self.path = path

    def load(self) -> PlaybackState:
        if not self.path.exists():
            return PlaybackState()
        try:
            raw = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            return PlaybackState()
        return PlaybackState(
            recent_clip_ids=list(raw.get("recent_clip_ids", []))[-2:],
            play_counts=dict(raw.get("play_counts", {})),
            last_manifest_index=int(raw.get("last_manifest_index", -1)),
        )

    def save(self, state: PlaybackState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "recent_clip_ids": state.recent_clip_ids[-2:],
            "play_counts": state.play_counts,
            "last_manifest_index": state.last_manifest_index,
        }
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True))

