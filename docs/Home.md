# `toolz` Wiki — Home

Welcome to the **`toolz`** documentation wiki. This repository provides automation scripts and configuration for running a **3-pane side-by-side AI coding workspace** inside **Termux + Andronix Debian (`proot`)** on Android.

---

## What Does `toolz` Do?

When working on an Android device using **Termux** and an **Andronix Debian** Linux installation (`start-debian.sh`), manually starting multiple sessions and launching individual AI CLIs in each session is repetitive—and using standard `tmux` windows (`new-window`) stacks terminals on top of each other so only one tool is visible at a time.

`toolz` automates the entire workflow:
1. **Detects Environment Automatically**: Whether invoked from outer Termux or inside Debian `proot`, [`scripts/launch-ai-tmux.sh`](../scripts/launch-ai-tmux.sh) transitions into Debian seamlessly.
2. **Creates 3 Distinct Side-by-Side GUI Panes**: Splits a single `tmux` window (`AI-Workspace`) into three equal horizontal columns (`even-horizontal`) so all three tools are visible side-by-side at the same time:
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
   - Manual installation steps
2. [**Architecture & How It Works**](Architecture-and-How-It-Works.md)
   - End-to-end execution lifecycle (`Termux` → `start-debian.sh` → `proot` → `~/.bashrc` → `tmux`)
   - Why running 1 `proot` with 3 `tmux` panes outperforms 3 separate `proot` instances
   - Why `codex --no-daemon` is required inside Andronix `proot`
   - Loop-prevention guards in `~/.bashrc`
3. [**Usage, Touch Gestures & Shortcuts**](Usage-and-Shortcuts.md)
   - Touchscreen controls in Termux
   - `tmux` keyboard shortcuts (switching panes, zooming, rotating layouts, detaching)
   - Environment variable customization
4. [**Troubleshooting Guide**](Troubleshooting.md)
   - Fixing interrupted `dpkg` / `apt` states in Debian
   - Resolving `start-debian.sh` vs `start_debian.sh` naming mismatches
   - Fixing `codex` Unix socket errors in `proot`
   - Recovering or resetting the `ai` `tmux` session
