#!/usr/bin/env bash
set -Eeuo pipefail
export TZ=UTC
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
mkdir -p "$ROOT/logs" "$ROOT/work"
exec > >(tee -a "$ROOT/logs/build.log") 2>&1
trap 'rc=$?; printf "Exit status: %s; time: %s\n" "$rc" "$(date -u +%FT%TZ)"; exit "$rc"' EXIT
printf 'Collection scope: local/cloud compilation only; time: %s\n' "$(date -u +%FT%TZ)"
test "$(uname -s)" = Linux || { echo 'A Linux build host is required.'; exit 1; }
test ! -e "$ROOT/work/openwrt" || { echo 'Use a fresh work directory; existing source will not be overwritten.'; exit 1; }
clone_pinned() {
  local url=$1 tag=$2 commit=$3 dest=$4
  git -c core.autocrlf=false clone --depth 1 --branch "$tag" "$url" "$dest"
  test "$(git -C "$dest" rev-parse HEAD)" = "$commit"
  printf '%s %s\n' "$url" "$commit" >> "$ROOT/logs/source-lock.txt"
}
clone_pinned https://github.com/openwrt/openwrt.git v25.12.5 f0a60eee2fe051741c643ea6118718aae1ef17fb "$ROOT/work/openwrt"
clone_pinned https://github.com/vernesong/OpenClash.git v0.47.116 23896d2662a7d49fa870d37c5cda4b3247a35ae4 "$ROOT/work/OpenClash"
clone_pinned https://github.com/SunBK201/UA3F.git v3.6.0 ac39645779823e94628435a2d69cd086a4e4b9fc "$ROOT/work/UA3F"
cd "$ROOT/work/openwrt"
./scripts/feeds update -a
./scripts/feeds install -a
cp -a "$ROOT/work/OpenClash/luci-app-openclash" package/
mkdir -p package/UA3F
cp -a "$ROOT/work/UA3F/." package/UA3F/
cp -a "$ROOT/packages/mihomo-builtin" package/
cp "$ROOT/config.seed" .config
make defconfig
for package in luci-app-openclash ua3f mihomo-builtin; do
  grep -Fxq "CONFIG_PACKAGE_${package}=y" .config || { echo "Missing configured package: $package"; exit 1; }
done
make download -j8
JOBS=$(nproc)
make tools/install -j"$JOBS" V=s
make toolchain/install -j"$JOBS" V=s
make target/linux/compile -j"$JOBS" V=s
make package/compile -j"$JOBS" V=s
find bin -type f \( -name '*.apk' -o -name '*.ipk' \) -print0 | sort -z | xargs -0 -r sha256sum > "$ROOT/logs/packages.sha256"
echo 'Platform and package compilation completed. No board firmware or flashable recovery image has been generated.'
