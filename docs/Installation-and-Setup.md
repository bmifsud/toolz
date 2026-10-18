# Installation & Setup Guide

This guide walks through installing and configuring `toolz` inside your **Termux + Andronix Debian** environment so that opening Termux automatically starts Debian and attaches to your 3-pane AI workspace.

---

## Prerequisites

1. **Android Device with Termux**:
   - Termux installed with an Andronix Debian rootfs (`~/.andronix/distros/debian/rootfs`).
   - Startup script located at `~/start-debian.sh` (or `~/start_debian.sh`) in your Termux home directory.
2. **AI CLI Tools Installed Inside Debian**:
   - **Antigravity CLI**: `~/.local/bin/agy`
   - **OpenAI Codex CLI**: `~/.local/bin/codex`
   - **Google Jules CLI**: `/usr/local/bin/jules`

---

## Step 1: Clone the Repository Inside Debian

Start your Debian environment from Termux (`~/start-debian.sh`) and clone `bmifsud/toolz` if not already present:

```bash
git clone https://github.com/bmifsud/toolz.git ~/toolz
cd ~/toolz
```

---

## Step 2: Run the Automated Installer (`install-autostart.sh`)

Run the included installer script inside Debian:

```bash
chmod +x ~/toolz/scripts/*.sh
~/toolz/scripts/install-autostart.sh
```

### What `install-autostart.sh` Performs Behind the Scenes

1. **Verifies Script Permissions**:
   Ensures `~/toolz/scripts/launch-ai-tmux.sh` has executable (`chmod +x`) permissions.
2. **Repairs `dpkg` and Installs `tmux`**:
   Checks whether `tmux` is installed in Debian (`/usr/bin/tmux`). If missing, it runs `sudo dpkg --configure -a` (to clear any interrupted package installations), updates `apt`, and installs `tmux`.
3. **Creates Global `/usr/local/bin` and `~/` Symlinks**:
   Because `proot` initializes `PATH` to `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin` before reading user shell configs, `install-autostart.sh` links your CLI binaries and session launchers into `/usr/local/bin` and `~/`:
   - `/usr/local/bin/agy` → `~/.local/bin/agy`
   - `/usr/local/bin/antigravity` → `~/.local/bin/agy`
   - `/usr/local/bin/codex` → `~/.local/bin/codex`
   - `/usr/local/bin/launch-ai-tmux.sh` → `~/toolz/scripts/launch-ai-tmux.sh`
   - `/usr/local/bin/start-debian.sh` & `~/start-debian.sh` → `~/toolz/scripts/start-debian.sh`
   - `/usr/local/bin/start-debian-1.sh` & `~/start-debian-1.sh` → `~/toolz/scripts/start-debian-1.sh` (1 session)
   - `/usr/local/bin/start-debian-2.sh` & `~/start-debian-2.sh` → `~/toolz/scripts/start-debian-2.sh` (2 sessions)
   - `/usr/local/bin/start-debian-3.sh` & `~/start-debian-3.sh` → `~/toolz/scripts/start-debian-3.sh` (3 sessions)
4. **Exports Copies to Shared Storage (`/sdcard/Download`)**:
   If `/sdcard/Download` is mounted inside Debian, copies `launch-ai-tmux.sh` and `start-debian*.sh` there so they are accessible from Android/Termux as well.
5. **Registers the Auto-Launch Hook in Debian's `~/.bashrc`**:
   Appends a guarded block to `/home/b/.bashrc`:
   ```bash
   # Auto-launch 3-pane AI workspace (Antigravity, Codex, Jules) on interactive Debian login
   if [[ $- == *i* ]] && [[ -z "${TMUX:-}" ]] && [[ -z "${AI_TMUX_AUTO_LAUNCHED:-}" ]] && [[ -z "${ANTIGRAVITY_AGENT:-}" ]] && [[ -z "${SKIP_AI_TMUX:-}" ]]; then
       export AI_TMUX_AUTO_LAUNCHED=1
       if [[ -x "/home/b/toolz/scripts/launch-ai-tmux.sh" ]]; then
           "/home/b/toolz/scripts/launch-ai-tmux.sh"
       fi
   fi
   ```

---

## Step 3: Install `start-debian-{1,2,3}.sh` in Outer Termux

To launch 1, 2, or 3 sessions directly from your **outer Android Termux shell** (`/data/data/com.termux/files/home`), copy the launcher scripts from the Debian rootfs into your Termux home directory:

```bash
cp ~/.andronix/distros/debian/rootfs/home/b/toolz/scripts/start-debian*.sh ~/ && chmod +x ~/start-debian*.sh
```

You can now run any of the three launchers from outer Termux:
- `~/start-debian-1.sh` — Starts Debian with **1 session** (`Antigravity`)
- `~/start-debian-2.sh` — Starts Debian with **2 sessions** (`Antigravity` + `Codex`)
- `~/start-debian-3.sh` (or `~/start-debian.sh`) — Starts Debian with **3 sessions** (`Antigravity` + `Codex` + `Jules`)

To make Termux **automatically** launch `~/start-debian-3.sh` (or `-1` / `-2`) when opening the app, run this once in outer Termux:

```bash
grep -q "start-debian" ~/.bashrc 2>/dev/null || \
  echo '[ -z "$DEBIAN_STARTED" ] && export DEBIAN_STARTED=1 && exec ~/start-debian-3.sh' >> ~/.bashrc
```

---

## Step 4: Verify the Setup

Inside Debian, you can test the workspace creation and orientation switching without leaving your current shell:

```bash
# Test Portrait Orientation (stacked top-to-bottom):
~/toolz/scripts/launch-ai-tmux.sh --portrait --no-attach
tmux list-panes -t ai:AI-Workspace -F "Pane #{pane_index}: title=#{pane_title} geom=#{pane_width}x#{pane_height}+#{pane_left}+#{pane_top}"
```

Expected output in **Portrait** mode (3 vertically stacked panes sharing the full width, at top offsets `+1`, `+22`, `+43`):

```text
Pane 0: title=Antigravity geom=92x20+0+1
Pane 1: title=Codex geom=92x20+0+22
Pane 2: title=Jules geom=92x21+0+43
```

```bash
# Restore automatic orientation detection (switches between portrait and landscape automatically):
~/toolz/scripts/launch-ai-tmux.sh --auto --no-attach
```

When in **Landscape** mode (`180x45`), the panes arrange into 3 side-by-side columns:

```text
Pane 0: title=Antigravity geom=59x44+0+1
Pane 1: title=Codex geom=59x44+60+1
Pane 2: title=Jules geom=60x44+120+1
```
