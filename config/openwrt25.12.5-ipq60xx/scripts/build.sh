#!/usr/bin/env bash
set -Eeuo pipefail
export TZ=UTC
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
mkdir -p "$ROOT/logs" "$ROOT/work" "$ROOT/output" "$ROOT/cache/downloads" "$ROOT/cache/ccache"
export CCACHE_DIR="$ROOT/cache/ccache"
exec > >(tee -a "$ROOT/logs/build.log") 2>&1
trap 'rc=$?; printf "Exit status: %s; time: %s\n" "$rc" "$(date -u +%FT%TZ)"; exit "$rc"' EXIT
printf 'Collection scope: local/cloud compilation only; time: %s\n' "$(date -u +%FT%TZ)"
test "$(uname -s)" = Linux || { echo 'A Linux build host is required.'; exit 1; }
MODE=${1:-all}
case "$MODE" in all|--prepare|--compile) ;; *) echo 'Unknown build mode'; exit 1 ;; esac
if [ "$MODE" != --compile ]; then
test ! -e "$ROOT/work/openwrt" || { echo 'Use a fresh work directory; existing source will not be overwritten.'; exit 1; }
python3 "$ROOT/scripts/prepare-board-data.py"
unset ZN_M2_BOARD_DATA_GZ_B64
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
python3 "$ROOT/scripts/repair-build-inputs.py" "$PWD"
./scripts/feeds install -a
python3 "$ROOT/scripts/verify-ruby-configure.py" "$PWD"
cp -a "$ROOT/work/OpenClash/luci-app-openclash" package/
mkdir -p package/UA3F
cp -a "$ROOT/work/UA3F/." package/UA3F/
cp -a "$ROOT/packages/mihomo-builtin" package/
cp -a "$ROOT/packages/ipq-wifi-zn-m2" package/
cp "$ROOT/board/ipq6018-zn-m2.dts" target/linux/qualcommax/files/arch/arm64/boot/dts/qcom/
cat "$ROOT/board/device.mk" >> target/linux/qualcommax/image/ipq60xx.mk
mkdir -p files/etc/board.d files/etc/hotplug.d/firmware
cp "$ROOT/board/10-zn-m2-network" files/etc/board.d/
cp "$ROOT/board/11-zn-m2-caldata" files/etc/hotplug.d/firmware/
chmod 0755 files/etc/board.d/10-zn-m2-network files/etc/hotplug.d/firmware/11-zn-m2-caldata
cp "$ROOT/config.seed" .config
make DL_DIR="$ROOT/cache/downloads" CCACHE_DIR="$ROOT/cache/ccache" defconfig
if grep -E 'WARNING: Makefile .* (dependency|build dependency) .*which does not exist' "$ROOT/logs/build.log"; then
  echo 'Unresolved package dependency metadata; stopping before compilation.'
  exit 1
fi
grep -Fxq 'CONFIG_TARGET_qualcommax_ipq60xx_DEVICE_zn_m2=y' .config
for package in luci-app-openclash ua3f mihomo-builtin ipq-wifi-zn-m2; do
  grep -Fxq "CONFIG_PACKAGE_${package}=y" .config || { echo "Missing configured package: $package"; exit 1; }
done
fi
if [ "$MODE" = --prepare ]; then
  echo 'Source, feeds dependencies and Ruby configure checks passed.'
  exit 0
fi
cd "$ROOT/work/openwrt"
test -f .config
make DL_DIR="$ROOT/cache/downloads" CCACHE_DIR="$ROOT/cache/ccache" download -j8
JOBS=$(nproc)
make DL_DIR="$ROOT/cache/downloads" CCACHE_DIR="$ROOT/cache/ccache" tools/install -j"$JOBS" V=s
make DL_DIR="$ROOT/cache/downloads" CCACHE_DIR="$ROOT/cache/ccache" toolchain/install -j"$JOBS" V=s
make DL_DIR="$ROOT/cache/downloads" CCACHE_DIR="$ROOT/cache/ccache" -j"$JOBS" V=s
test -x "$PWD/staging_dir/host/bin/fakeroot"
"$PWD/staging_dir/host/bin/fakeroot" -- python3 "$ROOT/scripts/make-factory.py" "$PWD" "$ROOT/output"
find bin -type f \( -name '*.apk' -o -name '*.ipk' \) -print0 | sort -z | xargs -0 -r sha256sum > "$ROOT/logs/packages.sha256"
echo 'Complete zn,m2 firmware image generated; static layout gates passed. Runtime boot and recovery remain unverified.'
