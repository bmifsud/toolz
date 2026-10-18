# Usage, Touch Gestures & Shortcuts

This guide covers how to navigate, resize, and manage the 3-pane AI workspace (`Antigravity`, `Codex`, `Jules`) in Termux on Android across both **Portrait** (stacked top-to-bottom) and **Landscape** (side-by-side) orientations.

---

## 1. Touchscreen Controls (`mouse on`)

Because `launch-ai-tmux.sh` enables `tmux set-option -g mouse on`, you can control the panes directly with touch gestures on your Android screen:

| Action | Touch Gesture |
| :--- | :--- |
| **Select / Focus an Agent Window** | Tap anywhere inside **Pane 0 (`Antigravity`)**, **Pane 1 (`Codex`)**, or **Pane 2 (`Jules`)**. |
| **Resize Agent Windows (Portrait)** | Touch and drag the **horizontal** border line between any two stacked panes up or down. |
| **Resize Agent Windows (Landscape)** | Touch and drag the **vertical** border line between any two side-by-side panes left or right. |
| **Scroll Terminal History** | Swipe up/down inside the focused pane. |
| **Switch Portrait ↔ Landscape** | Simply rotate your Android device — `tmux` resize hooks automatically restack the panes vertically in portrait (`even-vertical`) or place them side-by-side in landscape (`even-horizontal`). |

---

## 2. Keyboard Shortcuts (`tmux`)

All `tmux` commands start with the prefix key **`Ctrl+b`**, followed by a command key:

| Shortcut | Description |
| :--- | :--- |
| `Ctrl+b` then `Up` / `Down` | Move focus to the pane above or below (in Portrait stacked layout). |
| `Ctrl+b` then `Left` / `Right` | Move focus to the pane on the left or right (in Landscape side-by-side layout). |
| `Ctrl+b` then `q` then `0` / `1` / `2` | Display pane numbers briefly and jump directly to Pane `0`, `1`, or `2`. |
| `Ctrl+b` then `z` | **Toggle Full-Screen Zoom**: Maximize the currently focused agent pane to fill the entire screen; press `Ctrl+b` then `z` again to restore all 3 panes. |
| `Ctrl+b` then `Space` | **Cycle Layouts Manually**: Cycle between `even-vertical` (3 stacked rows), `even-horizontal` (3 side-by-side columns), and `tiled` layouts. |
| `Ctrl+b` then `d` | **Detach Session**: Leave the 3 AI agents running in the background and return to the Debian bash prompt. |
| `Ctrl+b` then `[` | Enter scroll/copy mode (press `q` to exit scroll mode). |

---

## 3. Session Launchers & Command-Line Options

### Launching 1, 2, or 3 Sessions (`start-debian-{1,2,3}.sh`)
```bash
# Launch (or scale running workspace to) 1 session (Antigravity):
~/start-debian-1.sh
# or: launch-ai-tmux.sh --sessions 1

# Launch (or scale running workspace to) 2 sessions (Antigravity + Codex):
~/start-debian-2.sh
# or: launch-ai-tmux.sh --sessions 2

# Launch (or scale running workspace to) 3 sessions (Antigravity + Codex + Jules):
~/start-debian-3.sh
# or: ~/start-debian.sh
# or: launch-ai-tmux.sh --sessions 3
```

### Orientation Command-Line Flags
```bash
# Launch and auto-detect portrait vs. landscape orientation (default):
~/toolz/scripts/launch-ai-tmux.sh

# Force portrait orientation (stack active sessions vertically on top of each other):
~/toolz/scripts/launch-ai-tmux.sh --portrait
~/start-debian-2.sh --portrait

# Force landscape orientation (side-by-side columns):
~/toolz/scripts/launch-ai-tmux.sh --landscape
~/start-debian-3.sh --landscape

# Restore automatic orientation detection on an existing session:
~/toolz/scripts/launch-ai-tmux.sh --auto

# Create/update the workspace in the background without attaching:
~/toolz/scripts/launch-ai-tmux.sh --no-attach
~/start-debian-2.sh --portrait --no-attach
```

### Customizing via Environment Variables
```bash
# Launch a specific number of sessions (1, 2, or 3):
AI_SESSION_COUNT=2 ~/toolz/scripts/launch-ai-tmux.sh

# Always stack panes vertically in portrait mode:
AI_ORIENTATION=portrait ~/toolz/scripts/launch-ai-tmux.sh

# Always place panes side-by-side in landscape mode:
AI_ORIENTATION=landscape ~/toolz/scripts/launch-ai-tmux.sh

# Customize minimum column threshold for switching to landscape in auto mode (default: 115):
AI_MIN_LANDSCAPE_COLS=120 ~/toolz/scripts/launch-ai-tmux.sh

# Start all 3 AI agents in a specific project directory:
AI_WORKDIR=~/my-project ~/toolz/scripts/launch-ai-tmux.sh

# Create a separate named tmux session:
AI_SESSION_NAME=ai-work ~/toolz/scripts/launch-ai-tmux.sh

# Open an interactive bash shell without triggering auto-launch:
SKIP_AI_TMUX=1 bash
```

---

## 4. Managing the Session Lifecycle

```bash
# Re-attach to the running AI workspace from Debian:
tmux attach -t ai

# Inspect pane status and geometry from outside tmux:
tmux list-panes -t ai:AI-Workspace

# Switch an already-running session to portrait stacked layout without restarting agents:
~/toolz/scripts/launch-ai-tmux.sh --portrait --no-attach

# Restart the entire 3-pane workspace cleanly:
tmux kill-session -t ai && ~/toolz/scripts/launch-ai-tmux.sh
```
