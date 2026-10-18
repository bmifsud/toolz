# `toolz` Wiki — Home

Welcome to the **`toolz`** documentation wiki. This repository provides automation scripts and configuration for running a **3-pane orientation-aware AI coding workspace** inside **Termux + Andronix Debian (`proot`)** on Android.

---

## What Does `toolz` Do?

When working on an Android device using **Termux** and an **Andronix Debian** Linux installation (`start-debian.sh`), manually starting multiple sessions and launching individual AI CLIs in each session is repetitive—and using standard `tmux` windows (`new-window`) hides background terminals so only one tool is visible at a time.

`toolz` automates the entire workflow:
1. **Detects Environment Automatically**: Whether invoked from outer Termux or inside Debian `proot`, [`scripts/launch-ai-tmux.sh`](../scripts/launch-ai-tmux.sh) transitions into Debian seamlessly.
2. **Creates 3 Distinct Orientation-Aware GUI Panes**: Splits a single `tmux` window (`AI-Workspace`) into three equal panes so all three tools are visible at the same time:
   - **Portrait Orientation (`even-vertical`)**: Stacks the 3 sessions vertically on top of each other (Top, Middle, Bottom) so each pane receives the full terminal width.
   - **Landscape Orientation (`even-horizontal`)**: Places the 3 sessions side-by-side in equal columns (Left, Middle, Right).
   - **Live Rotation Switching**: Registers `tmux` resize hooks (`client-attached`, `client-resized`, `window-resized`) so rotating your Android device between portrait and landscape automatically restacks or unstacks the panes in real time:
     - **Pane 0 (`Antigravity`)**: Google Antigravity CLI (`agy`)
     - **Pane 1 (`Codex`)**: OpenAI Codex CLI (`codex --no-daemon`)
     - **Pane 2 (`Jules`)**: Google Jules CLI (`jules`)
3. **Touch & Mouse Enabled**: Configures `tmux` with `mouse on` and labeled top pane borders (`pane-border-status top`) so you can tap any pane on your touchscreen to focus it or drag dividers to resize.
4. **Auto-Starts on Login**: [`scripts/install-autostart.sh`](../scripts/install-autostart.sh) configures Debian's `~/.bashrc` (and provides the outer Termux `~/.bashrc` hook) so opening Termux immediately drops you into the 3-pane workspace.

---

## Wiki Pages

1. [**Installation & Setup Guide**](Installation-and-Setup.md)
   - Prerequisites (`agy`, `codex`, `jules`, Andronix Debian)
   - Automated setup with `scripts/install-autostart.sh`
   - Configuring outer Termux auto-start (`~/start-debian.sh`)
   - Verifying both portrait and landscape pane layouts
2. [**Architecture & How It Works**](Architecture-and-How-It-Works.md)
   - End-to-end execution lifecycle (`Termux` → `start-debian.sh` → `proot` → `~/.bashrc` → `tmux`)
   - Why running 1 `proot` with 3 `tmux` panes outperforms 3 separate `proot` instances
   - How portrait vs. landscape orientation detection and Android soft-keyboard resilience work
   - Why `codex --no-daemon` is required inside Andronix `proot`
   - Loop-prevention guards in `~/.bashrc`
3. [**Usage, Touch Gestures & Shortcuts**](Usage-and-Shortcuts.md)
   - Touchscreen controls in Termux (portrait & landscape)
   - `tmux` keyboard shortcuts (switching panes, zooming, rotating layouts, detaching)
   - Orientation CLI flags (`--portrait`, `--landscape`, `--auto`) and environment variables
4. [**Troubleshooting Guide**](Troubleshooting.md)
   - Fixing interrupted `dpkg` / `apt` states in Debian
   - Resolving `start-debian.sh` vs `start_debian.sh` naming mismatches
   - Fixing `codex` Unix socket errors in `proot`
   - Locking portrait or landscape orientation and resetting the `ai` `tmux` session
