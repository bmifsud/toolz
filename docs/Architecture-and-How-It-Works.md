# Architecture & How It Works

This document explains the internal design of [`scripts/launch-ai-tmux.sh`](../scripts/launch-ai-tmux.sh) and [`scripts/install-autostart.sh`](../scripts/install-autostart.sh), and why specific technical choices were made for the **Termux + Andronix Debian (`proot`)** environment.

---

## 1. End-to-End Execution Pipeline

```mermaid
sequenceDiagram
    participant User as Android User
    participant Termux as Outer Termux (~/.bashrc)
    participant Proot as start-debian.sh (proot)
    participant DebBash as Debian ~/.bashrc
    participant Launcher as launch-ai-tmux.sh
    participant Tmux as tmux Session ("ai")

    User->>Termux: Opens Termux App
    Termux->>Proot: exec ~/start-debian.sh
    Proot->>DebBash: Starts /bin/bash -l (USER=b, HOME=/home/b)
    DebBash->>Launcher: Calls /home/b/toolz/scripts/launch-ai-tmux.sh
    alt Session "ai" does not exist
        Launcher->>Tmux: new-session -d -s ai (Pane 0: agy)
        Launcher->>Tmux: split-window -h (Pane 1: codex --no-daemon)
        Launcher->>Tmux: split-window -h (Pane 2: jules)
        Launcher->>Tmux: select-layout even-horizontal + mouse on
    end
    Launcher->>Tmux: exec tmux attach-session -t ai
```

---

## 2. Key Engineering Decisions

### A. Single `proot` + 3 `tmux` Panes vs. 3 Separate `proot` Processes
Andronix's `start-debian.sh` launches Debian using `proot` (user-space `chroot` via `ptrace`/syscall translation) alongside a `pulseaudio` server.
- Launching 3 separate Termux sessions that each run `start-debian.sh` spawns **3 independent `proot` instances and 3 `pulseaudio` daemons**, increasing memory usage and syscall translation overhead.
- Running `tmux` **inside** a single Debian `proot` session and splitting the window into 3 panes (`split-window -h`) runs all 3 AI tools under one `proot` supervisor and displays all 3 side-by-side simultaneously.
- Additionally, because Andronix's default `start-debian.sh` ends with `/bin/bash -l` and does **not** forward extra CLI arguments (`-- ...`) into Debian without manual script edits, triggering `launch-ai-tmux.sh` from Debian's `~/.bashrc` works out of the box with an unmodified `start-debian.sh`.

### B. Non-Overlapping Side-by-Side Layout (`even-horizontal`)
- Using `tmux new-window` creates multiple background windows (tabs) stacked on top of each other so only one CLI is visible on screen at a time.
- Instead, `launch-ai-tmux.sh` creates a single window (`AI-Workspace`), splits it twice with `tmux split-window -h`, and applies `tmux select-layout even-horizontal`:
  - **Pane 0 (`Antigravity`)**: Left third of the screen
  - **Pane 1 (`Codex`)**: Middle third of the screen
  - **Pane 2 (`Jules`)**: Right third of the screen
- Combined with `pane-border-status top`, each pane gets its own dedicated title bar (`0: Antigravity`, `1: Codex`, `2: Jules`), giving each agent a distinct GUI box.

### C. Why `codex --no-daemon` Is Used Inside `proot`
By default, the OpenAI Codex CLI attempts to spawn and connect to a background daemon over a Unix domain socket (`~/.codex/app-server-control/app-server-control.sock`).
Inside Android `proot` environments, stale or cross-session Unix domain sockets in `~/.codex/` can fail with:
```text
failed to connect to /home/b/.codex/app-server-control/app-server-control.sock: No such file or directory (os error 2)
To work without the background server, rerun the same command with --no-daemon
```
Passing `codex --no-daemon` in Pane 1 runs Codex directly in-process, completely avoiding socket failures inside `proot`.

### D. `agy` vs. `antigravity` Binary Naming
The Antigravity CLI installer places the executable at `~/.local/bin/agy` (not `antigravity`). To ensure compatibility with scripts or users expecting either command name:
- `launch-ai-tmux.sh` invokes `agy` directly and prepends `$HOME/.local/bin:/usr/local/bin` to `PATH`.
- `install-autostart.sh` creates symlinks for both `/usr/local/bin/agy` and `/usr/local/bin/antigravity`.

### E. Loop-Prevention Guards in `~/.bashrc`
To guarantee that `~/.bashrc` never triggers recursive `tmux` launches or interferes with background agent commands, the auto-start hook checks five conditions before launching:
1. `[[ $- == *i* ]]` — Must be an interactive shell (ignores non-interactive subshells and scripts).
2. `[[ -z "${TMUX:-}" ]]` — Must not already be inside a `tmux` pane.
3. `[[ -z "${AI_TMUX_AUTO_LAUNCHED:-}" ]]` — Ensures that if you detach from `tmux` (`Ctrl+b d`), your parent shell does not re-launch `tmux` again.
4. `[[ -z "${ANTIGRAVITY_AGENT:-}" ]]` — Prevents tool-execution subshells spawned by Antigravity from triggering `tmux`.
5. `[[ -z "${SKIP_AI_TMUX:-}" ]]` — Allows manual opt-out via `SKIP_AI_TMUX=1`.
