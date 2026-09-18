import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from image_gates import LEB, VOLUMES, check_fit, check_ubi, require

source, output = (Path(p).resolve() for p in sys.argv[1:3])
root = Path(__file__).resolve().parent.parent
require(source.is_relative_to(root / 'work'), 'Source outside owned build workspace')
require(output == root / 'output', 'Output outside owned artifact directory')
target = source / 'bin/targets/qualcommax/ipq60xx'
def one(pattern):
    paths = list(target.glob(pattern))
    require(len(paths) == 1, 'Expected one build component: ' + pattern)
    return paths[0]

fit = one('*-zn_m2-uImage.itb')
full_rootfs = one('*-zn_m2-squashfs-rootfs.squashfs')
fit_report = check_fit(fit.read_bytes())
work = root / 'work/factory'
require(not work.exists(), 'Existing factory workspace will not be overwritten')
work.mkdir()
base, overlay = work / 'base', work / 'overlay'
subprocess.run(['unsquashfs', '-d', str(base), str(full_rootfs)], check=True)
console = (base / 'dev/console').stat()
require(stat.S_ISCHR(console.st_mode) and os.major(console.st_rdev) == 5
        and os.minor(console.st_rdev) == 1, 'Missing or invalid /dev/console character device')
(overlay / 'upper').mkdir(parents=True)
(overlay / 'work').mkdir()

def digest_files(tree):
    result = {}
    for p in tree.rglob('*'):
        rel = p.relative_to(tree).as_posix()
        if p.is_symlink():
            result[rel] = 'symlink:' + os.readlink(p)
        elif p.is_file():
            result[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result

original = digest_files(base)
paths = ['etc/openclash/core/clash_meta', 'usr/bin/ua3f', 'usr/lib/ruby', 'usr/share/openclash']
paths += [p.relative_to(base).as_posix() for p in (base / 'usr/lib').glob('libruby*')]
moved = []
for rel in paths:
    p, q = base / rel, overlay / 'upper' / rel
    if p.exists() or p.is_symlink():
        require(p.parent.resolve().is_relative_to(base), 'Payload path outside rootfs')
        q.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(q))
        moved.append(rel)
require('etc/openclash/core/clash_meta' in moved and 'usr/bin/ua3f' in moved,
        'Requested built-in proxy payload missing')
base_files, upper_files = digest_files(base), digest_files(overlay / 'upper')
require(not (base_files.keys() & upper_files.keys()), 'Duplicate payload paths')
require(original == base_files | upper_files, 'Combined base/overlay payload changed during split')

squashfs, ubifs = work / 'rootfs.squashfs', work / 'rootfs_data.ubifs'
subprocess.run(['mksquashfs', str(base), str(squashfs), '-noappend', '-all-root',
                '-comp', 'xz', '-b', '262144', '-no-progress'], check=True)
require(squashfs.stat().st_size <= VOLUMES[1][1] * LEB, 'SquashFS exceeds existing 189-LEB rootfs volume')
subprocess.run(['mkfs.ubifs', '-r', str(overlay), '-o', str(ubifs), '-m', '2048',
                '-e', str(LEB), '-c', '514', '-x', 'zlib', '-F', '-U'], check=True)
require(ubifs.stat().st_size <= VOLUMES[2][1] * LEB, 'Seeded overlay exceeds existing 514-LEB volume')
cfg = work / 'ubinize.cfg'
sections = []
for i, p in ((0, fit), (1, squashfs), (2, ubifs)):
    name, count = VOLUMES[i]
    sections.append(f'[{name}]\nmode=ubi\nimage={p}\nvol_id={i}\nvol_type=dynamic\n'
                    f'vol_name={name}\nvol_alignment=1\nvol_size={count * LEB}\n')
cfg.write_text('\n'.join(sections), encoding='utf-8')
candidate = work / 'complete-firmware.ubi'
subprocess.run(['ubinize', '-o', str(candidate), '-p', '131072', '-m', '2048',
                '-s', '2048', '-O', '2048', str(cfg)], check=True)
ubi_report = check_ubi(candidate.read_bytes(), {0: fit.read_bytes(), 1: squashfs.read_bytes(), 2: ubifs.read_bytes()})
output.mkdir(exist_ok=True)
final = output / '当前设备-OpenWrt25.12.5-完整固件.ubi'
require(not final.exists(), 'Existing firmware artifact will not be overwritten')
shutil.copy2(candidate, final)
sha = hashlib.sha256(final.read_bytes()).hexdigest()
final.with_suffix('.ubi.sha256').write_text(sha + '  ' + final.name + '\n', encoding='utf-8')
report = {'device': 'zn,m2', 'release': '25.12.5', 'fit': fit_report, 'ubi': ubi_report,
          'rootfs_bytes': squashfs.stat().st_size, 'seeded_overlay_bytes': ubifs.stat().st_size,
          'payload_paths_in_overlay': moved, 'combined_payload_integrity': 'passed',
          'ubi_component_integrity': 'passed',
          'sha256': sha, 'router_written': False, 'bootloader_or_env_modified': False,
          'runtime_boot_verified': False, 'recovery_flash_verified': False}
(output / '固件构建与容量检查.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
