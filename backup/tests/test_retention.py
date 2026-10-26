"""Isolated integration and unit tests for safe Tier-1 retention script."""
import os
import subprocess
from pathlib import Path
import pytest

BASE = Path(__file__).resolve().parents[1]
SCRIPT = BASE / 'tier1_retention.sh'

@pytest.fixture
def retention_sandbox(tmp_path):
    home = tmp_path / 'home'
    home.mkdir()
    bins = tmp_path / 'bin'
    bins.mkdir()
    local_dir = tmp_path / 'tier1_backups'
    local_dir.mkdir()
    state_dir = home / '.local' / 'state' / 'toolz-backup'
    state_dir.mkdir(parents=True)

    rclone_script = bins / 'rclone'
    rclone_script.write_text('''#!/usr/bin/env python3
import sys, os
args = sys.argv[1:]
if not args: sys.exit(0)
cmd = args[0]
if cmd == 'listremotes':
    print("gdrive:")
    sys.exit(0)
elif cmd == 'lsf':
    target = args[1] if len(args) > 1 else ""
    filename = os.path.basename(target)
    remote_dir = os.environ.get("MOCK_REMOTE_DIR", "")
    if remote_dir and os.path.exists(os.path.join(remote_dir, filename)):
        print(filename)
    sys.exit(0)
elif cmd == 'cat':
    target = args[1] if len(args) > 1 else ""
    filename = os.path.basename(target)
    remote_dir = os.environ.get("MOCK_REMOTE_DIR", "")
    fpath = os.path.join(remote_dir, filename)
    if os.path.exists(fpath):
        with open(fpath, 'rb') as f:
            sys.stdout.buffer.write(f.read())
        sys.exit(0)
    sys.exit(1)
sys.exit(0)
''')
    rclone_script.chmod(0o755)

    remote_dir = tmp_path / 'gdrive_mock'
    remote_dir.mkdir()

    d = os.environ.copy()
    d.update(
        HOME=str(home),
        PATH=str(bins) + ':' + d['PATH'],
        TIER1_LOCAL_DIR=str(local_dir),
        MOCK_REMOTE_DIR=str(remote_dir),
        LC_ALL='C'
    )
    return d, local_dir, remote_dir, state_dir

def run_retention(env, *args):
    return subprocess.run(['bash', str(SCRIPT), *args], env=env, capture_output=True, text=True, timeout=30)

def test_syntax():
    assert subprocess.run(['bash', '-n', str(SCRIPT)]).returncode == 0

def test_retention_successful(retention_sandbox):
    d, local_dir, remote_dir, _ = retention_sandbox
    names = [
        'cline_omniroute_backup_20260101_000000.tar.gz.gpg',
        'cline_omniroute_backup_20260102_000000.tar.gz.gpg',
        'cline_omniroute_backup_20260103_000000.tar.gz.gpg'
    ]
    for name in names:
        (local_dir / name).write_text(f"content-{name}")
        (remote_dir / name).write_text(f"content-{name}")

    res = run_retention(d, '--apply')
    assert res.returncode == 0, res.stderr
    assert not (local_dir / names[0]).exists()
    assert not (local_dir / names[1]).exists()
    assert (local_dir / names[2]).exists()

def test_dry_run_preserves_local_files(retention_sandbox):
    d, local_dir, remote_dir, _ = retention_sandbox
    names = ['cline_omniroute_backup_20260101_000000.tar.gz.gpg', 'cline_omniroute_backup_20260102_000000.tar.gz.gpg']
    for name in names:
        (local_dir / name).write_text(f"content-{name}")
        (remote_dir / name).write_text(f"content-{name}")
    res = run_retention(d, '--dry-run')
    assert res.returncode == 0, res.stderr
    assert 'DRY-RUN' in res.stdout
    assert (local_dir / names[0]).exists()

def test_missing_cloud_object_fails_safely(retention_sandbox):
    d, local_dir, remote_dir, _ = retention_sandbox
    old_name = 'cline_omniroute_backup_20260101_000000.tar.gz.gpg'
    new_name = 'cline_omniroute_backup_20260102_000000.tar.gz.gpg'
    (local_dir / old_name).write_text("old")
    (local_dir / new_name).write_text("new")
    (remote_dir / new_name).write_text("new")
    res = run_retention(d, '--apply')
    assert res.returncode != 0
    assert (local_dir / old_name).exists()

def test_checksum_mismatch_fails_safely(retention_sandbox):
    d, local_dir, remote_dir, _ = retention_sandbox
    old_name = 'cline_omniroute_backup_20260101_000000.tar.gz.gpg'
    new_name = 'cline_omniroute_backup_20260102_000000.tar.gz.gpg'
    (local_dir / old_name).write_text("old-local")
    (local_dir / new_name).write_text("new")
    (remote_dir / old_name).write_text("old-remote-mismatch")
    (remote_dir / new_name).write_text("new")
    res = run_retention(d, '--apply')
    assert res.returncode != 0
    assert (local_dir / old_name).exists()

def test_preserves_non_target_files(retention_sandbox):
    d, local_dir, remote_dir, _ = retention_sandbox
    valid_old = 'cline_omniroute_backup_20260101_000000.tar.gz.gpg'
    valid_new = 'cline_omniroute_backup_20260102_000000.tar.gz.gpg'
    other_files = ['pre_open_hands', 'recovery.tar.gz', 'andronix-debian-20260101.tar.gz.gpg']
    (local_dir / valid_old).write_text("old")
    (local_dir / valid_new).write_text("new")
    (remote_dir / valid_old).write_text("old")
    (remote_dir / valid_new).write_text("new")
    for f in other_files: (local_dir / f).write_text("unrelated")
    res = run_retention(d, '--apply')
    assert res.returncode == 0, res.stderr
    assert not (local_dir / valid_old).exists()
    for f in other_files: assert (local_dir / f).exists()

def test_concurrent_lock_skips(retention_sandbox):
    d, _, _, state_dir = retention_sandbox
    lock_file = state_dir / 'backup.lock'
    import fcntl
    with open(lock_file, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert run_retention(d, '--apply').returncode == 75

def test_real_andronix_path_resolution(retention_sandbox):
    d, _, _, _ = retention_sandbox
    home = Path(d['HOME'])
    andronix_dir = home / '.andronix' / 'distros' / 'debian' / 'rootfs' / 'home' / 'b' / 'ClineOmniRouteBackups'
    andronix_dir.mkdir(parents=True)
    # Remove TIER1_LOCAL_DIR env so it falls back to Andronix path
    env = d.copy()
    env.pop('TIER1_LOCAL_DIR', None)
    
    old_name = 'cline_omniroute_backup_20260101_000000.tar.gz.gpg'
    new_name = 'cline_omniroute_backup_20260102_000000.tar.gz.gpg'
    (andronix_dir / old_name).write_text("old")
    (andronix_dir / new_name).write_text("new")
    remote_dir = Path(d['MOCK_REMOTE_DIR'])
    (remote_dir / old_name).write_text("old")
    (remote_dir / new_name).write_text("new")

    res = run_retention(env, '--apply')
    assert res.returncode == 0, res.stderr
    assert not (andronix_dir / old_name).exists()
    assert (andronix_dir / new_name).exists()

def test_idempotency(retention_sandbox):
    d, local_dir, _, _ = retention_sandbox
    assert run_retention(d, '--apply').returncode == 0
    (local_dir / 'cline_omniroute_backup_20260101_000000.tar.gz.gpg').write_text("only")
    assert run_retention(d, '--apply').returncode == 0

def test_lock_not_dependent_on_inherited_fd9(retention_sandbox):
    d, _, _, state_dir = retention_sandbox
    # Simulate parent having an open file on fd 9 that is NOT the lock
    script = f'''
    exec 9</dev/null
    bash {SCRIPT} --dry-run
    '''
    res = subprocess.run(['bash', '-c', script], env=d, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr

def test_failed_cloud_lsf_operation(retention_sandbox):
    d, local_dir, remote_dir, _ = retention_sandbox
    # Fail rclone lsf operation
    bins = Path(d['PATH'].split(':')[0])
    (bins / 'rclone').write_text('#!/bin/sh\n[ "$1" = listremotes ] && { echo gdrive:; exit 0; }\nexit 1\n')
    names = ['cline_omniroute_backup_20260101_000000.tar.gz.gpg', 'cline_omniroute_backup_20260102_000000.tar.gz.gpg']
    for name in names:
        (local_dir / name).write_text(f"content-{name}")
    res = run_retention(d, '--apply')
    assert res.returncode != 0
    assert (local_dir / names[0]).exists()




def test_runner_inherited_lock(retention_sandbox):
    import fcntl
    d, local_dir, _, state_dir = retention_sandbox
    fd = os.open(state_dir / 'backup.lock', os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        d['TIER1_RETENTION_INHERITED_LOCK'] = '9'
        (local_dir / 'cline_omniroute_backup_20260101_000000.tar.gz.gpg').write_text('keep')
        result = subprocess.run(
            ['bash', '-c', 'exec 9<&$1; shift; exec bash "$@"', 'bash',
             str(fd), str(SCRIPT), '--apply'],
            env=d, capture_output=True, text=True, timeout=30, pass_fds=(fd,))
        assert result.returncode == 0, result.stderr
    finally:
        os.close(fd)


def test_inherited_lock_mismatch_fails_closed(retention_sandbox):
    import fcntl
    d, _, _, state_dir = retention_sandbox
    fd = os.open(state_dir / 'backup.lock', os.O_RDWR | os.O_CREAT, 0o600)
    other = os.open(state_dir / 'other.lock', os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        d['TIER1_RETENTION_INHERITED_LOCK'] = '9'
        result = subprocess.run(
            ['bash', '-c', 'exec 9<&$1; shift; exec bash "$@"', 'bash',
             str(other), str(SCRIPT), '--apply'],
            env=d, capture_output=True, text=True, timeout=30, pass_fds=(other,))
        assert result.returncode == 75
    finally:
        os.close(other)
        os.close(fd)
