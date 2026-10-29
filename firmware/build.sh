#!/usr/bin/env bash
# Linux only. Validation builds contain no unit record and are not ready to flash.
set -euo pipefail
# OpenWrt requires exactly 022; protect secrets with directory/file permissions.
umask 022
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ "$(uname -s)" == Linux ]] || { echo 'Use an OpenWrt-supported Linux build host.' >&2; exit 1; }
[[ $# == 1 ]] || { echo 'Usage: bash build.sh /absolute/private/UNIT.json | --validation' >&2; exit 1; }
UNIT=''
MODE=unprovisioned-validation
SERIAL=validation
if [[ "$1" != --validation ]]; then
  UNIT="$(realpath "$1")"
  SERIAL="$(python3 "$HERE/tools/build_support.py" validate-unit "$UNIT")"
  MODE=private-unit-development
fi
TREE="${OPENWRT_TREE:-$HERE/build/openwrt}"
[[ "$TREE" != *' '* && "$TREE" = /* ]] || { echo 'OPENWRT_TREE must be an absolute Linux path without spaces.' >&2; exit 1; }
OUT="$HERE/dist/$SERIAL"
[[ ! -e "$OUT" ]] || { echo "Output exists: $OUT. Archive it before rebuilding." >&2; exit 1; }
SOURCE_REVISION="$(git -C "$HERE" rev-parse HEAD)"
git -C "$HERE" diff --quiet HEAD -- . || { echo 'Commit firmware changes before building.' >&2; exit 1; }
if [ ! -d "$TREE/.git" ]; then
 git clone --depth 1 --branch v24.10.7 https://git.openwrt.org/openwrt/openwrt.git "$TREE"
fi
chmod 700 "$TREE"
cd "$TREE"
[[ "$(git rev-parse refs/tags/v24.10.7)" == 4100c39a94da53ea1afe038f87fc0bf83d2e51f9 ]]
[[ "$(git rev-parse HEAD)" == "$(git rev-parse 'v24.10.7^{commit}')" ]]
# Reject unrelated tracked edits; the one audited DTS patch is applied below.
python3 - "$TREE" <<'PY'
import subprocess,sys
allowed='target/linux/ramips/dts/mt7628an_hilink_hlk-7628n.dts'
changes=subprocess.check_output(['git','-C',sys.argv[1],'diff','HEAD','--name-only'],text=True).splitlines()
if any(p != allowed for p in changes):
    raise SystemExit('OpenWrt tree has unrelated tracked edits; use a clean checkout')
PY
python3 "$HERE/tools/build_support.py" feeds feeds.conf
./scripts/feeds update -a
python3 "$HERE/tools/build_support.py" verify-sources "$TREE"
./scripts/feeds install -a
mkdir -p package/atech-gateway
# Synchronize removes stale package files deleted by a newer source revision.
rsync -a --delete "$HERE/package/atech-gateway/" package/atech-gateway/
python3 "$HERE/tools/patch_board.py" "$TREE"
# Reject overlays from earlier units rather than leak credentials into CI artifacts.
if [[ -d files ]] && [[ -n "$(find files -type f -print -quit)" ]]; then
  echo 'OpenWrt files/ overlay is not empty. Use a separate clean tree per unit/validation build.' >&2
  exit 1
fi
mkdir -p files/etc
# Prevent a default empty-password root account even if firstboot setup fails.
cp package/base-files/files/etc/shadow files/etc/shadow
python3 - <<'PY'
from pathlib import Path
p=Path('files/etc/shadow')
rows=[]
for line in p.read_text().splitlines():
    f=line.split(':')
    if f[0]=='root': f[1]='!'
    rows.append(':'.join(f))
p.write_text('\n'.join(rows)+'\n')
PY
chmod 600 files/etc/shadow
if [[ -n "$UNIT" ]]; then
  mkdir -p files/etc/gateway
  install -m 600 "$UNIT" files/etc/gateway/unit.json
fi
cat > .config <<'CONFIG'
CONFIG_TARGET_ramips=y
CONFIG_TARGET_ramips_mt76x8=y
CONFIG_TARGET_ramips_mt76x8_DEVICE_hilink_hlk-7628n=y
CONFIG_TARGET_ROOTFS_INITRAMFS=y
CONFIG_PACKAGE_atech-gateway=y
CONFIG_PACKAGE_kmod-i2c-core=y
CONFIG_PACKAGE_kmod-i2c-dev=y
CONFIG_PACKAGE_kmod-i2c-mt7628=y
CONFIG_PACKAGE_i2c-tools=y
CONFIG_PACKAGE_luci=y
CONFIG_PACKAGE_luci-ssl=y
CONFIG_PACKAGE_luci-proto-qmi=y
CONFIG_PACKAGE_uqmi=y
CONFIG_PACKAGE_lrzsz=y
CONFIG_PACKAGE_kmod-usb2=y
CONFIG_PACKAGE_kmod-usb-net-qmi-wwan=y
CONFIG_PACKAGE_kmod-usb-serial-option=y
CONFIG_PACKAGE_wpad-basic-mbedtls=y
CONFIG
make defconfig
for config in TARGET_ramips_mt76x8_DEVICE_hilink_hlk-7628n PACKAGE_atech-gateway PACKAGE_kmod-i2c-mt7628 PACKAGE_kmod-usb-net-qmi-wwan; do
  grep -qx "CONFIG_${config}=y" .config
done
make download -j8
make -j"${JOBS:-$(nproc)}" V=s
mkdir -p "$OUT"
chmod 700 "$OUT"
cp bin/targets/ramips/mt76x8/*hilink_hlk-7628n*.bin "$OUT/"
cp .config "$OUT/build.config"
cp "$HERE/build-lock.json" "$OUT/build-lock.json"
cp feeds.conf "$OUT/feeds.txt"
git diff -- target/linux/ramips/dts/mt7628an_hilink_hlk-7628n.dts > "$OUT/carrier-dts.patch"
python3 "$HERE/tools/build_support.py" manifest "$TREE" "$OUT" "$MODE" "$SOURCE_REVISION"
chmod 600 "$OUT"/*
echo "Development artifacts: $OUT ($MODE). No hardware test or production approval."
if [[ -n "$UNIT" ]]; then
  echo 'Contains per-unit Wi-Fi credentials; keep the entire output private.'
else
  echo 'UNPROVISIONED VALIDATION ONLY. Do not flash this image to a customer unit.'
fi
