# Usage, Touch Gestures & Shortcuts

This guide covers how to navigate, resize, and manage the 3-pane AI workspace (`Antigravity`, `Codex`, `Jules`) in Termux on Android.

---

## 1. Touchscreen Controls (`mouse on`)

Because `launch-ai-tmux.sh` enables `tmux set-option -g mouse on`, you can control the panes directly with touch gestures on your Android screen:

| Action | Touch Gesture |
| :--- | :--- |
| **Select / Focus an Agent Window** | Tap anywhere inside **Pane 0 (`Antigravity`)**, **Pane 1 (`Codex`)**, or **Pane 2 (`Jules`)**. |
| **Resize Agent Windows** | Touch and drag the vertical border line between any two panes left or right. |
| **Scroll Terminal History** | Swipe up/down inside the focused pane. |

---

## 2. Keyboard Shortcuts (`tmux`)

All `tmux` commands start with the prefix key **`Ctrl+b`**, followed by a command key:

| Shortcut | Description |
| :--- | :--- |
| `Ctrl+b` then `Left` / `Right` | Move focus to the pane on the left or right. |
| `Ctrl+b` then `q` then `0` / `1` / `2` | Display pane numbers briefly and jump directly to Pane `0`, `1`, or `2`. |
| `Ctrl+b` then `z` | **Toggle Full-Screen Zoom**: Maximize the currently focused agent pane to fill the entire screen; press `Ctrl+b` then `z` again to restore all 3 side-by-side panes. |
| `Ctrl+b` then `Space` | **Cycle Layouts**: Switch between `even-horizontal` (3 side-by-side columns), `even-vertical` (3 rows, ideal for portrait orientation), and `tiled` layouts. |
| `Ctrl+b` then `d` | **Detach Session**: Leave the 3 AI agents running in the background and return to the Debian bash prompt. |
| `Ctrl+b` then `[` | Enter scroll/copy mode (press `q` to exit scroll mode). |

---

## 3. Command-Line Options & Environment Variables

### Command-Line Flags
```bash
# Launch and immediately attach to the 3-pane workspace:
~/toolz/scripts/launch-ai-tmux.sh

# Create/verify the 3-pane workspace in the background without attaching:
~/toolz/scripts/launch-ai-tmux.sh --no-attach
```

### Customizing via Environment Variables
```bash
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

# Restart the entire 3-pane workspace cleanly:
tmux kill-session -t ai && ~/toolz/scripts/launch-ai-tmux.sh
```
