"""Isolated integration tests for the scheduled Tier-1/Tier-2 workflow."""
import os
from pathlib import Path
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def env(tmp_path, short_gnupg_home):
    home=tmp_path/'home';home.mkdir()
    bins=tmp_path/'bin';bins.mkdir()
    (home/'debian-fs').mkdir()
    (home/'debian-fs'/'sentinel').write_text('original')
    (home/'start-debian.sh').write_text('#!/bin/sh\n')
    snaps=tmp_path/'snapshots';snaps.mkdir()
    pw=tmp_path/'password';pw.write_text('test-password');pw.chmod(0o600)
    gnupg=short_gnupg_home
    d=os.environ.copy()
    d.update(HOME=str(home),PATH=str(bins)+':'+d['PATH'],
             GNUPGHOME=str(gnupg),BACKUP_PASSPHRASE_FILE=str(pw),
             ALLOW_TEST_HOST='1',SNAP_DIR=str(snaps),
             ROOTFS_DIR=str(home/'debian-fs'),START_SCRIPT=str(home/'start-debian.sh'),
             TIER1_COMMAND='true',TIER1_LOCAL_DIR=str(tmp_path/'tier1'))
    (tmp_path/'tier1').mkdir()
    def mock(name,script):
        p=bins/name;p.write_text('#!/bin/sh\n'+script+'\n');p.chmod(0o755)
    mock('pgrep','exit 1')
    mock('rclone','[ "$1" = listremotes ] && echo gdrive:\nexit 0')
    return d,tmp_path,mock

def run(env,name,*args):
    d,_,_=env
    return subprocess.run(['bash',str(ROOT/name),*args],env=d,capture_output=True,text=True,timeout=45)

@pytest.mark.parametrize('name',['backup_cline_omniroute.sh','pre_snapshot_clean.sh',
    'snapshot_andronix_debian.sh','install_backup_cron.sh','run_scheduled_backup.sh'])
def test_syntax(name):
    assert subprocess.run(['bash','-n',str(ROOT/name)]).returncode==0

@pytest.mark.parametrize('args',[('--restore',),('--invalid',),('--gdrive','extra')])
def test_invalid_snapshot_args(env,args):
    assert run(env,'snapshot_andronix_debian.sh',*args).returncode==2

def test_snapshot_encrypted_and_no_plaintext(env):
    p=run(env,'snapshot_andronix_debian.sh')
    assert p.returncode==0,p.stderr
    assert len(list((env[1]/'snapshots').glob('*.gpg')))==1
    assert not list((env[1]/'snapshots').glob('*.tar.gz'))

def test_snapshot_missing_rootfs(env):
    import shutil
    shutil.rmtree(env[0]['ROOTFS_DIR'])
    assert run(env,'snapshot_andronix_debian.sh').returncode!=0

def test_cloud_upload_failure_keeps_encrypted_copy(env):
    env[2]('rclone','[ "$1" = listremotes ] && { echo gdrive:; exit 0; }\n[ "$1" = copyto ] && exit 9\nexit 0')
    assert run(env,'snapshot_andronix_debian.sh','--gdrive').returncode!=0
    assert len(list((env[1]/'snapshots').glob('*.gpg')))==1

def test_restore_never_overwrites_existing_rootfs(env):
    assert run(env,'snapshot_andronix_debian.sh').returncode==0
    archive=next((env[1]/'snapshots').glob('*.gpg'))
    env[0]['CONFIRM_RESTORE']='RESTORE'
    assert run(env,'snapshot_andronix_debian.sh','--restore',str(archive)).returncode!=0
    assert (env[1]/'home'/'debian-fs'/'sentinel').read_text()=='original'

def test_encrypted_restore_roundtrip(env):
    import shutil
    assert run(env,'snapshot_andronix_debian.sh').returncode==0
    archive=next((env[1]/'snapshots').glob('*.gpg'))
    shutil.rmtree(env[0]['ROOTFS_DIR'])
    Path(env[0]['START_SCRIPT']).unlink()
    env[0]['CONFIRM_RESTORE']='RESTORE'
    p=run(env,'snapshot_andronix_debian.sh','--restore',str(archive))
    assert p.returncode==0,p.stderr
    assert (env[1]/'home'/'debian-fs'/'sentinel').read_text()=='original'

def test_wrong_password_fails_restore(env):
    import shutil
    assert run(env,'snapshot_andronix_debian.sh').returncode==0
    archive=next((env[1]/'snapshots').glob('*.gpg'))
    shutil.rmtree(env[0]['ROOTFS_DIR'])
    Path(env[0]['START_SCRIPT']).unlink()
    wrong=env[1]/'wrong';wrong.write_text('wrong')
    env[0].update(BACKUP_PASSPHRASE_FILE=str(wrong),CONFIRM_RESTORE='RESTORE')
    assert run(env,'snapshot_andronix_debian.sh','--restore',str(archive)).returncode!=0
    assert not Path(env[0]['ROOTFS_DIR']).exists()

def test_preflight_requires_tier1(env):
    # A failed Tier-1 upload must block Tier-2 preflight.
    # Supply a valid isolated DB so preflight reaches the rclone remote check.
    import sqlite3
    db = env[1] / 'omniroute-test.sqlite'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE fixture (id INTEGER PRIMARY KEY)')
    env[0]['OMNIROUTE_DEBIAN_DB'] = str(db)
    env[2]('rclone', '[ "$1" = listremotes ] && exit 0\nexit 1')
    result = run(env, 'pre_snapshot_clean.sh')
    assert result.returncode != 0
    assert 'remote not configured' in result.stderr

def test_scheduler_rejects_bad_mode(env):
    assert run(env,'run_scheduled_backup.sh','bad').returncode==2

def test_scheduler_requires_marker(env):
    assert run(env,'run_scheduled_backup.sh','tier2').returncode==75

def test_scheduler_skips_active_proot(env):
    env[2]('pgrep','exit 0')
    assert run(env,'run_scheduled_backup.sh','tier2').returncode==75

def test_scheduler_tier1_missing_launcher(env):
    env[0].pop('TIER1_COMMAND')
    assert run(env,'run_scheduled_backup.sh','tier1').returncode!=0

def test_cron_rejects_non_termux(env):
    env[0]['PREFIX']='/wrong'
    assert run(env,'install_backup_cron.sh').returncode!=0

def test_cron_preserves_unrelated_jobs_contract():
    source=(ROOT/'install_backup_cron.sh').read_text()
    assert 'crontab -l' in source
    assert '# BEGIN TOOLZ BACKUP' in source
    assert '# END TOOLZ BACKUP' in source
    assert '0 9,21 * * *' in source
    assert '0 3 * * 1,3,5' in source
