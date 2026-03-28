# QuitTok 2016

QuitTok 2016 is a macOS menu bar agent built for a stupid hacks hackathon with a 2016 nostalgia theme. It hijacks close, quit, and window-button interactions, then retaliates with a full-screen 2016 meme clip at max volume. It is surreal, over-engineered, intentionally hostile, and designed for a live demo rather than normal human use.

## Project pitch

You try to close something. The computer decides you now deserve Harambe, PPAP, Pokemon GO, or some other cursed relic of 2016 internet culture.

The app sits in the menu bar, watches for quit and close behavior, and then:

- lets the original close/minimize action go through
- slams a meme video over the screen
- maxes the volume
- blocks normal escape routes while the clip plays
- rotates clips evenly so the punishment stays fresh

## What it does

- Runs as a background menu bar app
- Watches for app terminations via `NSWorkspace`
- Intercepts global `Cmd+Q` and `Cmd+W` with a Quartz event tap
- Opens a borderless, always-on-top overlay across Spaces
- Plays a local MP4 clip selected from a manifest
- Forces output volume to max during playback
- Ignores `Cmd+Q`, `Cmd+W`, and `Escape` while the overlay is active
- Reveals a single dismiss button only after the countdown expires

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
.venv/bin/python -m ensurepip --upgrade
.venv/bin/python -m pip install --upgrade pip setuptools wheel
pip install -e .
```

The app expects local MP4 assets in [`assets/memes`](/Users/stsang/Development/stupid-ideas-hackathon/assets/memes). The repository only includes the manifest and folder structure, so add your own short H.264 meme clips there.

Suggested filenames:

- `harambe.mp4`
- `ppap.mp4`
- `dat_boi.mp4`
- `pokemon_go.mp4`
- `damn_daniel.mp4`

## Run

```bash
quittok
```

Or:

```bash
python -m quittok
```

On first launch, macOS should prompt for Accessibility access. You can also re-prompt from the menu bar item. Without Accessibility, the app still supports manual triggering and app-termination notifications, but the global keyboard hook will stay disabled.

## Fetch Meme Assets

Install media tools:

```bash
/opt/homebrew/bin/python3.13 -m venv .venv-media
source .venv-media/bin/activate
python -m pip install --upgrade pip setuptools wheel yt-dlp
brew install ffmpeg
```

Preview candidate source URLs:

```bash
.venv-media/bin/python scripts/fetch_memes.py --search
```

Download the default clip set into [`assets/memes`](/Users/stsang/Development/stupid-ideas-hackathon/assets/memes):

```bash
.venv-media/bin/python scripts/fetch_memes.py --download
```

If you want raw downloads without trimming:

```bash
.venv-media/bin/python scripts/fetch_memes.py --download --no-trim
```

## Demo controls

- Menu bar item: `2016`
- `Enabled`: master toggle for all automatic triggers
- `Safe Demo Mode`: blocks automatic triggers while keeping the manual test button available
- `Trigger Meme Now`: forces the overlay immediately
- `Prompt for Accessibility`: reopens the system trust prompt
- `Web bridge`: shows whether the local Edge-extension loopback bridge is live

## Edge Extension Integration

The repository now includes [`shitty-ui-extension`](/Users/stsang/Development/stupid-ideas-hackathon/shitty-ui-extension), an unpacked Edge extension that intercepts captchable website button clicks.

Integrated flow:

1. the extension blocks the original web click
2. it calls QuitTok over `http://127.0.0.1:47616/api/web-trigger`
3. QuitTok plays a meme and only responds after the overlay closes
4. the extension opens the fake captcha gauntlet
5. after captcha success, the original click is replayed once

Manual Edge setup:

```bash
python3 -m http.server 8016
open -na "/Applications/Microsoft Edge.app" --args \
  --user-data-dir=/tmp/quittok-edge-profile \
  --disable-extensions-except=/Users/stsang/Development/stupid-ideas-hackathon/shitty-ui-extension \
  --load-extension=/Users/stsang/Development/stupid-ideas-hackathon/shitty-ui-extension \
  http://127.0.0.1:8016/shitty-ui-extension/test-page.html
```

Then open `edge://extensions`, enable Developer mode if needed, confirm the unpacked extension is loaded, and click the test button on the page.

## Packaging

- [`packaging/Info.plist`](/Users/stsang/Development/stupid-ideas-hackathon/packaging/Info.plist) contains the `LSUIElement` app configuration for accessory-style packaging
- [`packaging/launchagent.plist`](/Users/stsang/Development/stupid-ideas-hackathon/packaging/launchagent.plist) is an example LaunchAgent for login startup

## Notes

- The app is intentionally rude, but not literally inescapable. Force Quit and other system-level interventions still exist.
- Volume is restored to its previous level when the overlay is dismissed.
- Missing clips fall back to a black screen with captions so the app is still demoable before you load the real assets.
