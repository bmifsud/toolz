import os, pathlib, subprocess
import pytest
BASE=pathlib.Path(__file__).resolve().parents[1]
@pytest.fixture
def setup(tmp_path, short_gnupg_home):
 h=tmp_path/'home'; (h/'debian-fs').mkdir(parents=True); (h/'start-debian.sh').write_text('start')
 b=tmp_path/'bin'; b.mkdir(); r=b/'rclone'; r.write_text('#!/bin/sh\n[ "$1" = listremotes ] && echo gdrive:\nexit 0\n'); r.chmod(0o755)
 p=tmp_path/'pw'; p.write_text('testpassphrase'); s=tmp_path/'snaps'; s.mkdir()
 d=os.environ.copy(); d.update(HOME=str(h),ALLOW_TEST_HOST='1',SNAP_DIR=str(s),BACKUP_PASSPHRASE_FILE=str(p),PATH=str(b)+':'+d['PATH'],GNUPGHOME=str(short_gnupg_home))
 return d,h,s

def invoke(setup,*args):
 d,h,s=setup
 return subprocess.run(['bash',str(BASE/'snapshot_andronix_debian.sh'),*args],env=d,capture_output=True,text=True)

def test_syntax():
 for f in BASE.glob('*.sh'): assert subprocess.run(['bash','-n',str(f)]).returncode==0

def test_encrypted_snapshot(setup):
 p=invoke(setup); assert p.returncode==0,p.stderr
 assert len(list(setup[2].glob('*.gpg')))==1
 assert not list(setup[2].glob('*.tar.gz'))

def test_missing_rootfs(setup):
 import shutil
 shutil.rmtree(setup[1]/'debian-fs')
 assert invoke(setup).returncode!=0

def test_bad_arguments(setup):
 for args in [('--restore',),('--invalid',),('--gdrive','extra')]: assert invoke(setup,*args).returncode==2

def test_restore_refuses_existing_rootfs(setup):
 assert invoke(setup).returncode==0
 archive=next(setup[2].glob('*.gpg'))
 assert invoke(setup,'--restore',str(archive)).returncode!=0

def test_preflight_missing_tier1(setup, tmp_path):
 # Isolate the preflight script so neither repository nor HOME has a Tier-1 launcher.
 import shutil
 d,h,s=setup
 isolated=tmp_path/'isolated-preflight';isolated.mkdir()
 shutil.copy(BASE/'pre_snapshot_clean.sh', isolated/'pre_snapshot_clean.sh')
 p=subprocess.run(['bash',str(isolated/'pre_snapshot_clean.sh')],env=d,capture_output=True,text=True)
 assert p.returncode!=0
 assert 'Tier-1 backup script missing' in p.stderr

def test_roundtrip_restore_into_clean_home(setup):
 d,h,s=setup
 (h/'debian-fs'/'marker.txt').write_text('restore-me')
 assert invoke(setup).returncode==0
 archive=next(s.glob('*.gpg'))
 import shutil
 shutil.rmtree(h/'debian-fs')
 (h/'start-debian.sh').unlink()
 d['CONFIRM_RESTORE']='RESTORE'
 result=invoke(setup,'--restore',str(archive))
 assert result.returncode==0,result.stderr
 assert (h/'debian-fs'/'marker.txt').read_text()=='restore-me'

def test_wrong_passphrase_does_not_restore(setup,tmp_path):
 d,h,s=setup
 assert invoke(setup).returncode==0
 archive=next(s.glob('*.gpg'))
 import shutil
 shutil.rmtree(h/'debian-fs')
 wrong=tmp_path/'wrong';wrong.write_text('wrong-password')
 d['BACKUP_PASSPHRASE_FILE']=str(wrong);d['CONFIRM_RESTORE']='RESTORE'
 assert invoke(setup,'--restore',str(archive)).returncode!=0
 assert not (h/'debian-fs').exists()

def test_local_retention_two(setup):
 import time
 d,h,s=setup
 for n in range(3):
  d['SNAP_DIR']=str(s)
  p=invoke(setup)
  assert p.returncode==0,p.stderr
  time.sleep(1.1)
 assert len(list(s.glob('andronix-debian-*.tar.gz.gpg')))==2

def test_cloud_upload_and_scoped_pruning(setup,tmp_path):
 d,h,s=setup
 log=tmp_path/'rclone.log';d['RCLONE_LOG']=str(log)
 r=tmp_path/'bin'/'rclone'
 r.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$RCLONE_LOG"\n[ "$1" = listremotes ] && echo gdrive:\nexit 0\n');r.chmod(0o755)
 p=invoke(setup,'--gdrive')
 assert p.returncode==0,p.stderr
 calls=log.read_text()
 assert 'copyto ' in calls
 assert '--min-age 60d --include andronix-debian-*.tar.gz.gpg' in calls

def test_cloud_failure_preserves_encrypted_copy(setup,tmp_path):
 d,h,s=setup
 r=tmp_path/'bin'/'rclone'
 r.write_text('#!/bin/sh\n[ "$1" = listremotes ] && { echo gdrive:; exit 0; }\n[ "$1" = copyto ] && exit 8\nexit 0\n');r.chmod(0o755)
 p=invoke(setup,'--gdrive')
 assert p.returncode!=0
 assert len(list(s.glob('*.gpg')))==1
 assert not list(s.glob('*.tar.gz'))

def test_preflight_tier1_failure_blocks_cleanup(setup,tmp_path):
 d,h,s=setup
 project=tmp_path/'project';project.mkdir()
 script=project/'backup_cline_omniroute.sh'
 script.write_text('#!/bin/sh\nexit 7\n');script.chmod(0o755)
 import shutil
 shutil.copy(BASE/'pre_snapshot_clean.sh',project/'pre_snapshot_clean.sh')
 p=subprocess.run(['bash',str(project/'pre_snapshot_clean.sh')],env=d,capture_output=True,text=True)
 assert p.returncode==7
