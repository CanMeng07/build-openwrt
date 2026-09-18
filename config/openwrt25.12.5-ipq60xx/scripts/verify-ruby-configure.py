"""Verify configure regeneration against the pinned, patched Ruby source."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tarfile
import urllib.request

source = Path(sys.argv[1]).resolve()
root = Path(__file__).resolve().parent.parent
archive = root / 'cache/downloads/ruby-3.4.9.tar.gz'
expected = '7bb4d4f5e807cc27251d14d9d6086d182c5b25875191e44ab15b709cd7a7dd9c'
if not archive.exists():
    urllib.request.urlretrieve('https://cache.ruby-lang.org/pub/ruby/3.4/ruby-3.4.9.tar.gz', archive)
if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
    raise SystemExit('Ruby source archive SHA-256 mismatch')
work = root / 'work/ruby-configure-check'
work.mkdir()
with tarfile.open(archive) as tar:
    tar.extractall(work, filter='data')
ruby = work / 'ruby-3.4.9'
subprocess.run([str(source / 'scripts/patch-kernel.sh'), str(ruby),
                str(source / 'feeds/packages/lang/ruby/patches')], check=True)
subprocess.run(['autoconf', '--force', '--include=tool/m4', '--include=.'],
               cwd=ruby, check=True)
subprocess.run(['sh', '-n', str(ruby / 'configure')], check=True)
print('Pinned, patched Ruby configure regeneration and shell syntax checks passed')
