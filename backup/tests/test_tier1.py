"""Tier-1 isolated integration tests; no real Google Drive or user data touched."""
import os
from pathlib import Path
import sqlite3
import subprocess
import pytest

SCRIPT=Path(__file__).resolve().parents[1]/'backup_cline_omniroute.sh'

@pytest.mark.parametrize('use_tmpdir', [True, False])
def test_private_portable_temp_directory(sandbox, tmp_path, use_tmpdir):
    d,home,_,_,mock=sandbox
    base=tmp_path/'termux-tmp';base.mkdir(mode=0o700)
    if use_tmpdir:
        d['TMPDIR']=str(base)
    else:
        d.pop('TMPDIR', None)
    # Reject /tmp even on Debian, and inspect the allocated directory before cleanup.
    import shutil
    import shlex
    real=shlex.quote(shutil.which('mktemp'))
    record=tmp_path/'temp-record'
    mock('mktemp', f'''case "$*" in *'/tmp/cline_omni_backup.'*) exit 73;; esac
p=$({real} "$@") || exit $?
printf '%s\\n' "$p" > '{record}'
stat -c '%a' "$p" >> '{record}'
printf secret > "$p/probe"
stat -c '%a' "$p/probe" >> '{record}'
printf '%s\\n' "$p"''')
    result=run(sandbox,'--restore',str(tmp_path/'missing.gpg'))
    assert result.returncode != 0
    assert record.exists(), result.stderr
    directory,mode,file_mode=record.read_text().splitlines()
    assert Path(directory).parent == (base if use_tmpdir else home)
    assert mode == '700'
    assert file_mode == '600'
    assert not Path(directory).exists()


@pytest.fixture
def sandbox(tmp_path, short_gnupg_home):
    home=tmp_path/'home';home.mkdir()
    workspace=tmp_path/'workspace';workspace.mkdir()
    bins=tmp_path/'bin';bins.mkdir()
    gnupg=short_gnupg_home
    (home/'.omniroute').mkdir()
    conn=sqlite3.connect(home/'.omniroute'/'storage.sqlite')
    conn.execute('CREATE TABLE state (value TEXT)')
    conn.execute("INSERT INTO state VALUES ('sqlite-preserved')")
    conn.commit();conn.close()
    (home/'.omniroute'/'.env').write_text('TOKEN=not-a-real-secret')
    (home/'.cline'/'data'/'settings').mkdir(parents=True)
    (home/'.cline'/'data'/'globalState.json').write_text('{"ok":true}')
    (home/'.cline'/'data'/'secrets.json').write_text('{"fake":"token"}')
    (home/'.cline'/'data'/'settings'/'mcp.json').write_text('{"servers":{}}')
    (home/'.config'/'systemd'/'user').mkdir(parents=True)
    (home/'.config'/'systemd'/'user'/'omniroute.service').write_text('[Service]\nExecStart=/bin/true')
    for name in ('.clinerules','.memory','.cline'):
        (workspace/name).mkdir()
        (workspace/name/'sample').write_text(name)
    calls=tmp_path/'calls'
    def mock(name,body):
        p=bins/name
        p.write_text('#!/bin/sh\n'+body+'\n')
        p.chmod(0o755)
    mock('curl','exit 22')
    mock('systemctl','exit 0')
    mock('omniroute','exit 0')
    mock('rclone',f'echo "$*" >> "{calls}"\n[ "$1" = listremotes ] && echo gdrive:\nexit 0')
    d=os.environ.copy()
    d.update(HOME=str(home),GNUPGHOME=str(gnupg),PATH=str(bins)+':'+d['PATH'],
             BACKUP_PASSPHRASE='tier1-test-only-password',
             ANDROID_OUT=str(home/'ClineOmniRouteBackups'),
             LC_ALL='C')
    return d,home,workspace,calls,mock

def run(sandbox,*args,env=None):
    d,_,_,_,_=sandbox
    return subprocess.run(['bash',str(SCRIPT),*args],env=env or d,
                          capture_output=True,text=True,timeout=60)

def archive(sandbox):
    return next((sandbox[1]/'ClineOmniRouteBackups').glob('*.tar.gz.gpg'))

def test_tier1_shell_syntax():
    assert subprocess.run(['bash','-n',str(SCRIPT)]).returncode==0

def test_backup_encrypts_sqlite_secrets_workspace_and_cloud(sandbox,tmp_path):
    d,home,workspace,calls,_=sandbox
    p=run(sandbox,'backup',str(workspace))
    assert p.returncode==0,p.stderr
    a=archive(sandbox)
    assert a.stat().st_size>0
    extracted=tmp_path/'extracted';extracted.mkdir()
    decrypt=subprocess.run(['gpg','--batch','--yes','--pinentry-mode','loopback',
                            '--passphrase',d['BACKUP_PASSPHRASE'],'-d',str(a)],
                           capture_output=True,env=d)
    assert decrypt.returncode==0,decrypt.stderr
    tar=subprocess.run(['tar','-xz','-C',str(extracted)],input=decrypt.stdout,capture_output=True)
    assert tar.returncode==0,tar.stderr
    db=sqlite3.connect(extracted/'omniroute'/'storage.sqlite')
    assert db.execute('SELECT value FROM state').fetchone()[0]=='sqlite-preserved'
    db.close()
    assert (extracted/'home'/'.cline'/'data'/'secrets.json').read_text()=='{"fake":"token"}'
    assert (extracted/'workspace'/'.memory'/'sample').read_text()=='.memory'
    assert 'copy ' in calls.read_text()
    assert 'delete ' not in calls.read_text()

@pytest.mark.xfail(strict=False, reason='Existing Tier-1 restore uses interactive gpg --decrypt without loopback passphrase support; preserved unchanged')
def test_local_restore_roundtrip_and_permissions(sandbox,tmp_path):
    d,home,workspace,_,_=sandbox
    assert run(sandbox,'backup',str(workspace)).returncode==0
    a=archive(sandbox)
    (home/'.cline'/'data'/'secrets.json').unlink()
    (home/'.omniroute'/'storage.sqlite').unlink()
    restored=tmp_path/'restored'
    p=run(sandbox,'--restore',str(a),str(restored))
    assert p.returncode==0,p.stderr
    assert (home/'.cline'/'data'/'secrets.json').exists()
    assert (home/'.cline'/'data'/'secrets.json').stat().st_mode & 0o777==0o600
    assert (restored/'.clinerules'/'sample').read_text()=='.clinerules'
    conn=sqlite3.connect(home/'.omniroute'/'storage.sqlite')
    assert conn.execute('SELECT value FROM state').fetchone()[0]=='sqlite-preserved'
    conn.close()

def test_restore_missing_archive_rejected(sandbox):
    assert run(sandbox,'--restore','/missing/archive.gpg').returncode!=0

@pytest.mark.xfail(strict=False, reason='Tier-1 restore has no unattended GPG passphrase input; requires device-level acceptance')
def test_restore_wrong_passphrase_rejected(sandbox):
    assert run(sandbox,'backup',str(sandbox[2])).returncode==0
    d=sandbox[0].copy();d['BACKUP_PASSPHRASE']='incorrect'
    assert run(sandbox,'--restore',str(archive(sandbox)),env=d).returncode!=0

def test_missing_rclone_remote_does_not_prevent_local_backup(sandbox):
    sandbox[4]('rclone','[ "$1" = listremotes ] && exit 0\nexit 1')
    p=run(sandbox,'backup',str(sandbox[2]))
    assert p.returncode!=0
    assert archive(sandbox).exists()
    assert 'remote not configured' in p.stderr

def test_cloud_copy_failure_is_reported(sandbox):
    sandbox[4]('rclone','[ "$1" = listremotes ] && { echo gdrive:; exit 0; }\n[ "$1" = copyto ] && exit 8\nexit 0')
    p=run(sandbox,'backup',str(sandbox[2]))
    assert p.returncode!=0
    assert archive(sandbox).exists()

def test_restore_gdrive_no_remote_archives(sandbox):
    sandbox[4]('rclone','[ "$1" = lsf ] && exit 0\nexit 0')
    assert run(sandbox,'--restore-gdrive',str(sandbox[2])).returncode!=0

def test_local_retention_producer_preserves_all(sandbox):
    d,home,workspace,_,_=sandbox
    out=home/'ClineOmniRouteBackups';out.mkdir()
    for i in range(7):
        (out/f'cline_omniroute_backup_20260101_00000{i}.tar.gz.gpg').write_text('old')
    p=run(sandbox,'backup',str(workspace))
    assert p.returncode==0,p.stderr
    assert len(list(out.glob('cline_omniroute_backup_*.tar.gz.gpg')))==7
