# Troubleshooting Guide

Common issues and solutions when running the 3-pane AI workspace in **Termux + Andronix Debian (`proot`)**.

---

## 1. `E: dpkg was interrupted, you must manually run 'sudo dpkg --configure -a'`

**Symptom**:
Installing `tmux` or other packages inside Andronix Debian fails because a previous `apt-get` process was interrupted.

**Fix**:
Run `install-autostart.sh` (which runs `sudo dpkg --configure -a` automatically), or run manually inside Debian:

```bash
sudo dpkg --configure -a
sudo apt-get update && sudo apt-get install -y tmux
```

---

## 2. `Debian launcher not found or not executable`

**Symptom**:
Running `launch-ai-tmux.sh` from outer Termux prints:
`Error: Debian launcher not found or not executable.`

**Cause**:
Andronix names the script `~/start-debian.sh` (with a hyphen), whereas some custom setups use `~/start_debian.sh` (with an underscore) or store it in another path.

**Fix**:
`launch-ai-tmux.sh` automatically checks both `~/start-debian.sh` and `~/start_debian.sh`. Ensure the script in Termux is executable:

```bash
chmod +x ~/start-debian.sh
```
Or pass a custom path via `DEBIAN_LAUNCHER`:
```bash
DEBIAN_LAUNCHER=/path/to/your/start-debian.sh ~/launch-ai-tmux.sh
```

---

## 3. Codex Exits Immediately with `app-server-control.sock: No such file or directory`

**Symptom**:
Running `codex` without flags inside Andronix `proot` exits back to bash with:
`failed to connect to /home/b/.codex/app-server-control/app-server-control.sock: No such file or directory (os error 2)`

**Fix**:
`launch-ai-tmux.sh` already resolves this by launching `codex --no-daemon`. If you ever launch `codex` manually in a pane, use:

```bash
codex --no-daemon
```

---

## 4. `antigravity: command not found` or `agy: command not found`

**Symptom**:
A non-login shell cannot find `agy`, `antigravity`, or `codex`.

**Cause**:
The Antigravity CLI binary is named `agy` and installed in `~/.local/bin/agy`. Non-login shells inside `proot` may only search `/usr/local/bin:/usr/bin:/bin`.

**Fix**:
Re-run the installer script to recreate the `/usr/local/bin` symlinks:

```bash
~/toolz/scripts/install-autostart.sh
```

---

## 5. Forcing Portrait (Stacked) or Landscape (Side-by-Side) Layout

**Symptom**:
You want to lock the workspace to always stack panes on top of each other (`even-vertical`) or always place them side-by-side (`even-horizontal`), or update an existing session that was created before upgrading `toolz`.

**Fix**:
Run `launch-ai-tmux.sh` with `--portrait`, `--landscape`, or `--auto` (can be applied live to an already-running session with `--no-attach`):

```bash
# Apply dynamic portrait/landscape auto-detection to the running session:
~/toolz/scripts/launch-ai-tmux.sh --auto --no-attach

# Lock to portrait (stacked vertically on top of each other):
~/toolz/scripts/launch-ai-tmux.sh --portrait --no-attach

# Lock to landscape (side-by-side columns):
~/toolz/scripts/launch-ai-tmux.sh --landscape --no-attach
```

---

## 6. Resetting a Stuck `tmux` Session

If you want to start fresh with three brand-new agent panes:

```bash
tmux kill-session -t ai
~/toolz/scripts/launch-ai-tmux.sh
```
