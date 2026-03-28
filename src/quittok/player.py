from __future__ import annotations

from pathlib import Path

import AVFoundation
import AppKit
import CoreMedia
import objc
from Cocoa import NSURL


class PlayerContainerView(AppKit.NSView):
    def initWithFrame_(self, frame):
        self = objc.super(PlayerContainerView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.setWantsLayer_(True)
        self.playerLayer = AVFoundation.AVPlayerLayer.layer()
        self.playerLayer.setVideoGravity_(AVFoundation.AVLayerVideoGravityResizeAspect)
        self.layer().addSublayer_(self.playerLayer)
        return self

    def layout(self):
        objc.super(PlayerContainerView, self).layout()
        self.playerLayer.setFrame_(self.bounds())


class MemePlayer:
    def __init__(self, frame):
        self.view = PlayerContainerView.alloc().initWithFrame_(frame)
        self.view.setAutoresizingMask_(
            AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable
        )
        self.player = AVFoundation.AVPlayer.alloc().init()
        self.current_item = None
        self.view.playerLayer.setPlayer_(self.player)

    def play_clip(self, clip_path: Path | None):
        self.stop()
        if clip_path is None or not clip_path.exists():
            self.view.playerLayer.setPlayer_(None)
            return None, None
        url = NSURL.fileURLWithPath_(str(clip_path))
        asset = AVFoundation.AVURLAsset.alloc().initWithURL_options_(url, None)
        duration_seconds = CoreMedia.CMTimeGetSeconds(asset.duration())
        item = AVFoundation.AVPlayerItem.alloc().initWithURL_(url)
        self.current_item = item
        self.player = AVFoundation.AVPlayer.alloc().initWithPlayerItem_(item)
        self.view.playerLayer.setPlayer_(self.player)
        self.player.play()
        return item, duration_seconds

    def stop(self) -> None:
        if getattr(self, "player", None) is not None:
            self.player.pause()
            self.player.replaceCurrentItemWithPlayerItem_(None)
        self.current_item = None
