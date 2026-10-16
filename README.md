# toolz — Termux + Andronix Debian 3-Pane AI Workspace

Automated multi-agent terminal workspace for **Termux + Andronix Debian (`proot`)** on Android. Launching Debian automatically opens a **3-pane side-by-side (non-overlapping) `tmux` workspace** running three AI coding assistants simultaneously:

1. **Pane 0 (Left)**: **Antigravity CLI** (`agy` / `antigravity`)
2. **Pane 1 (Middle)**: **OpenAI Codex CLI** (`codex --no-daemon`)
3. **Pane 2 (Right)**: **Google Jules CLI** (`jules`)

---

## Visual Layout

Unlike standard `tmux new-window` tabs that stack windows on top of one another (hiding inactive agents), `launch-ai-tmux.sh` splits a single workspace window (`AI-Workspace`) using `even-horizontal` layout with touch/mouse support and top title borders:

```text
┌───────────────────┬───────────────────┬───────────────────┐
│ 0: Antigravity    │ 1: Codex          │ 2: Jules          │
├───────────────────┼───────────────────┼───────────────────┤
│                   │                   │                   │
│  Antigravity CLI  │  OpenAI Codex CLI │  Google Jules CLI │
│  (agy)            │  (codex)          │  (jules)          │
│                   │                   │                   │
│  > _              │  › Ask Codex...   │  Working in: ~    │
│                   │                   │                   │
└───────────────────┴───────────────────┴───────────────────┘
 [ai] 0:AI-Workspace*
```

---

## Architecture & Startup Flow

```mermaid
flowchart LR
    A["Open Termux App"] --> B["~/start-debian.sh (Andronix proot)"]
    B --> C["Debian Login Shell (~/.bashrc)"]
    C --> D["scripts/launch-ai-tmux.sh"]
    D --> E["tmux session: ai (AI-Workspace)"]
    E --> F["Pane 0: Antigravity CLI (agy)"]
    E --> G["Pane 1: Codex CLI (codex --no-daemon)"]
    E --> H["Pane 2: Google Jules CLI (jules)"]
```

---

## Repository Structure

| Path | Description |
| :--- | :--- |
| [`scripts/launch-ai-tmux.sh`](scripts/launch-ai-tmux.sh) | Core launcher script that detects outer Termux vs. Debian `proot`, creates the 3-pane side-by-side `tmux` session (`ai`), enables touch/mouse mode, and launches `agy`, `codex --no-daemon`, and `jules`. |
| [`scripts/install-autostart.sh`](scripts/install-autostart.sh) | Idempotent setup script that installs `tmux`, configures `/usr/local/bin` symlinks (`agy`, `antigravity`, `codex`, `launch-ai-tmux.sh`), and registers the auto-launch hook in `~/.bashrc`. |
| [`docs/Home.md`](docs/Home.md) | Wiki home page and documentation index. |
| [`docs/Installation-and-Setup.md`](docs/Installation-and-Setup.md) | Complete step-by-step installation guide for both Debian and outer Termux. |
| [`docs/Architecture-and-How-It-Works.md`](docs/Architecture-and-How-It-Works.md) | Technical deep-dive into `proot` process management, `codex --no-daemon`, and `tmux` geometry. |
| [`docs/Usage-and-Shortcuts.md`](docs/Usage-and-Shortcuts.md) | Touch navigation, pane resizing, zooming, environment variables, and keyboard shortcuts. |
| [`docs/Troubleshooting.md`](docs/Troubleshooting.md) | Solutions for common `dpkg`, `proot`, `PATH`, and `tmux` issues. |

---

## Quick Start & Installation

### 1. Clone and Run the Installer Inside Debian

From inside your Andronix Debian shell (after running `~/start-debian.sh` in Termux):

```bash
git clone https://github.com/bmifsud/toolz.git ~/toolz
cd ~/toolz
chmod +x scripts/*.sh
./scripts/install-autostart.sh
```

What `install-autostart.sh` does automatically:
- Repairs any interrupted `dpkg` state and installs `tmux` if not already installed.
- Creates global symlinks in `/usr/local/bin` (`agy`, `antigravity`, `codex`, `launch-ai-tmux.sh`) so all tools are found in `PATH` across login and non-login shells.
- Adds a loop-guarded auto-launch block to `~/.bashrc` so entering Debian via `start-debian.sh` automatically opens the 3-pane AI workspace.

### 2. Enable Auto-Start in Outer Termux (Optional)

If you want opening the **Termux** app on Android to immediately enter Debian and launch the 3-pane workspace without typing `./start-debian.sh`, run this once in an **outer Termux shell** (outside Debian):

```bash
grep -q "start-debian.sh" ~/.bashrc 2>/dev/null || \
  echo '[ -z "$DEBIAN_STARTED" ] && export DEBIAN_STARTED=1 && exec ~/start-debian.sh' >> ~/.bashrc
```

---

## Usage

### Automatic Launch
Every time you start a new interactive Debian session via `~/start-debian.sh`, `~/.bashrc` invokes `launch-ai-tmux.sh` and attaches to the `ai` session.

### Manual Launch
You can also run the launcher manually from either Termux or Debian:

```bash
# Inside Debian (via global symlink or repo path):
launch-ai-tmux.sh
# or
~/toolz/scripts/launch-ai-tmux.sh

# Pre-create the session in the background without attaching:
~/toolz/scripts/launch-ai-tmux.sh --no-attach
```

### Bypassing Auto-Launch for a Single Shell
To open a plain Debian shell without auto-attaching to `tmux`:

```bash
SKIP_AI_TMUX=1 bash
```

---

## Touch & Keyboard Controls

Because `mouse on` is enabled in the `ai` session, you can interact with the 3 panes directly on your Android touchscreen:

- **Switch active agent pane**: Tap anywhere inside **Pane 0 (`Antigravity`)**, **Pane 1 (`Codex`)**, or **Pane 2 (`Jules`)** — or press `Ctrl+b` followed by `Left` / `Right` arrow keys.
- **Resize panes**: Drag the vertical border between panes with your finger, or press `Ctrl+b` + hold `Alt` + `Left`/`Right`.
- **Full-screen zoom a single pane (toggle)**: Press `Ctrl+b` then `z` to temporarily expand the active pane to full screen; press `Ctrl+b` then `z` again to restore the 3-column side-by-side view.
- **Rotate layout (Horizontal ↔ Vertical ↔ Tiled)**: Press `Ctrl+b` then `Space` to cycle pane layouts if you rotate your device between landscape and portrait.
- **Detach from workspace (keep agents running in background)**: Press `Ctrl+b` then `d`.

---

## Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DEBIAN_LAUNCHER` | `~/start-debian.sh` (or `~/start_debian.sh`) | Path to the Andronix Debian startup script when invoked from outer Termux. |
| `AI_SESSION_NAME` | `ai` | Name of the `tmux` session created/attached by `launch-ai-tmux.sh`. |
| `AI_WORKDIR` | `$HOME` (`/home/b`) | Initial working directory for all 3 agent panes. |
| `SKIP_AI_TMUX` | *(unset)* | Set to `1` to skip auto-launching `launch-ai-tmux.sh` from `~/.bashrc`. |

---

## Wiki & Detailed Documentation

For deeper technical details, see the [`docs/`](docs/Home.md) directory:
- [**Wiki Home**](docs/Home.md)
- [**Installation & Setup Guide**](docs/Installation-and-Setup.md)
- [**Architecture & How It Works**](docs/Architecture-and-How-It-Works.md)
- [**Usage, Touch Gestures & Shortcuts**](docs/Usage-and-Shortcuts.md)
- [**Troubleshooting Guide**](docs/Troubleshooting.md)
