"""Prepare complete feed links and Ruby's native autoconf generation."""
import hashlib
import os
from pathlib import Path
import re
import sys

source = Path(sys.argv[1]).resolve()
if not (source / 'include/autotools.mk').is_file():
    raise SystemExit('Not an OpenWrt source tree')

# Feed install scans installed packages before creating links. Prelink indexed
# sources first, preserving feed order and existing core packages.
core = {p.parent.name for p in (source / 'package').rglob('Makefile')
        if 'feeds' not in p.relative_to(source / 'package').parts}
seen = set(core)
count = 0
for line in (source / 'feeds.conf.default').read_text().splitlines():
    fields = line.split()
    if not fields or fields[0].startswith('#'):
        continue
    if len(fields) != 3 or fields[0] != 'src-git':
        raise SystemExit('Unexpected pinned feed declaration: ' + line)
    name = fields[1]
    index = source / 'feeds' / (name + '.index')
    for item in re.findall(r'^Source-Makefile:\s*(.+?/Makefile)\s*$',
                           index.read_text(), re.M):
        path = source / item.strip()
        if not path.is_file() or not path.resolve().is_relative_to(source / 'feeds' / name):
            raise SystemExit('Invalid indexed feed path: ' + item)
        package = path.parent.name
        if package in seen:
            continue
        destination = source / 'package/feeds' / name / package
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() or destination.is_symlink():
            raise SystemExit('Refusing to overwrite feed link: ' + str(destination))
        destination.symlink_to(os.path.relpath(path.parent, destination.parent), target_is_directory=True)
        seen.add(package)
        count += 1

required = {'ruby': 'lang/ruby', 'libev': 'libs/libev',
            'libpam': 'libs/libpam', 'libtirpc': 'libs/libtirpc',
            'liblzma': 'utils/xz', 'libnetsnmp': 'net/net-snmp'}
for package, directory in required.items():
    expected = (source / 'feeds/packages' / directory).resolve()
    link = source / 'package/feeds/packages' / expected.name
    if not (expected / 'Makefile').is_file() or link.resolve() != expected:
        raise SystemExit('Missing required dependency definition: ' + package)

ruby = source / 'feeds/packages/lang/ruby/Makefile'
data = ruby.read_bytes()
expected = 'ee70b14866d4f701b91f2dc1e173668d93a70b88dfac4b847f24919db82861e9'
if hashlib.sha256(data).hexdigest() != expected:
    raise SystemExit('Pinned Ruby Makefile changed; review before patching')
text = data.decode()
if text.count('PKG_FIXUP:=autoreconf') != 1:
    raise SystemExit('Unexpected Ruby fixup declaration')
text = text.replace('PKG_FIXUP:=autoreconf', 'PKG_FIXUP:=')
hooks = '''
# Ruby includes its m4 definitions directly in configure.ac. Regenerate
# configure with autoconf; aclocal cannot trace RUBY_M4_INCLUDE's $1 argument.
define Ruby/GenerateConfigure
\t(cd $(1); \\
\t\tM4=$(STAGING_DIR_HOST)/bin/m4 \\
\t\tAUTOM4TE=$(STAGING_DIR_HOST)/bin/autom4te \\
\t\t$(STAGING_DIR_HOST)/bin/autoconf --force --include=tool/m4 --include=.)
endef

define Ruby/HostGenerateConfigure
\t$(call Ruby/GenerateConfigure,$(HOST_BUILD_DIR))
endef

define Ruby/TargetGenerateConfigure
\t$(call Ruby/GenerateConfigure,$(PKG_BUILD_DIR))
endef

Hooks/HostConfigure/Pre += Ruby/HostGenerateConfigure
Hooks/Configure/Pre += Ruby/TargetGenerateConfigure

'''
marker = 'HOST_CONFIGURE_ARGS += '
if marker not in text:
    raise SystemExit('Ruby configure insertion point missing')
text = text.replace(marker, hooks + marker, 1)
ruby.write_text(text, encoding='utf-8', newline='\n')
print(f'Prepared {count} feed source links; all six dependency definitions available')
print('Ruby host and target configure generation uses checked autoconf commands')
