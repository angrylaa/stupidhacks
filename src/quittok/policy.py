from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import AppConfig, ClipConfig
from .state import PlaybackState, StateStore


@dataclass(frozen=True)
class PunishmentEvent:
    clip_id: str
    clip_path: Path | None
    caption: str
    trigger_source: str
    app_name: str
    bundle_id: str | None
    lock_seconds: int
    kill_count: int


class PunishmentPolicy:
    def __init__(self, config: AppConfig, state_store: StateStore | None = None) -> None:
        self.config = config
        self.kill_count = 0
        self.state_store = state_store or StateStore()
        self.state = self.state_store.load()

    def _eligible_clips(self) -> list[tuple[int, ClipConfig]]:
        indexed = list(enumerate(self.config.clips))
        if len(indexed) <= 2:
            return indexed
        recent = set(self.state.recent_clip_ids[-2:])
        eligible = [(idx, clip) for idx, clip in indexed if clip.clip_id not in recent]
        return eligible or indexed

    def _pick_next_clip(self) -> ClipConfig | None:
        eligible = self._eligible_clips()
        if not eligible:
            return None

        min_count = min(self.state.play_counts.get(clip.clip_id, 0) for _, clip in eligible)
        least_played = [(idx, clip) for idx, clip in eligible if self.state.play_counts.get(clip.clip_id, 0) == min_count]

        for idx, clip in least_played:
            if idx > self.state.last_manifest_index:
                self._remember_clip(idx, clip.clip_id)
                return clip

        idx, clip = least_played[0]
        self._remember_clip(idx, clip.clip_id)
        return clip

    def _remember_clip(self, manifest_index: int, clip_id: str) -> None:
        recent = [existing for existing in self.state.recent_clip_ids if existing != clip_id]
        recent.append(clip_id)
        self.state.recent_clip_ids = recent[-2:]
        self.state.play_counts[clip_id] = self.state.play_counts.get(clip_id, 0) + 1
        self.state.last_manifest_index = manifest_index
        self.state_store.save(self.state)

    def build_event(
        self,
        trigger_source: str,
        bundle_id: str | None = None,
        app_name: str | None = None,
    ) -> PunishmentEvent:
        self.kill_count += 1
        clip = self._pick_next_clip()
        app_label = app_name or "something important"
        lock_seconds = min(
            self.config.base_duration + max(self.kill_count - 1, 0),
            self.config.max_duration,
        )
        if clip is None:
            return PunishmentEvent(
                clip_id="fallback",
                clip_path=None,
                caption=self.config.fallback_caption,
                trigger_source=trigger_source,
                app_name=app_label,
                bundle_id=bundle_id,
                lock_seconds=lock_seconds,
                kill_count=self.kill_count,
            )
        return PunishmentEvent(
            clip_id=clip.clip_id,
            clip_path=clip.path,
            caption=clip.caption,
            trigger_source=trigger_source,
            app_name=app_label,
            bundle_id=bundle_id,
            lock_seconds=lock_seconds,
            kill_count=self.kill_count,
        )
