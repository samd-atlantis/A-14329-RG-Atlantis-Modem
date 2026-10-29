#!/usr/bin/env bash
# Run as a normal user on an OpenWrt-supported Linux build host (not Windows).
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
UNIT="${1:?Usage: ./build.sh /absolute/path/to/private/UNIT.json}"
UNIT="$(realpath "$UNIT")"
python3 - "$UNIT" <<'PY'
import json,re,sys
u=json.load(open(sys.argv[1]))
assert re.fullmatch(r'[A-Za-z0-9-]{1,24}',u['serial'])
assert 16 <= len(u['wifi_password']) <= 63
assert u['ssid'] and len(u['ssid'].encode()) <= 32
assert u['root_hash'].startswith('$6$')
PY
TREE="$HERE/build/openwrt"
if [ ! -d "$TREE/.git" ]; then
 git clone --depth 1 --branch v24.10.7 https://git.openwrt.org/openwrt/openwrt.git "$TREE"
fi
cd "$TREE"
[ "$(git describe --tags --exact-match HEAD)" = v24.10.7 ]
./scripts/feeds update -a
./scripts/feeds install -a
mkdir -p package/atech-gateway
cp -a "$HERE/package/atech-gateway/." package/atech-gateway/
python3 "$HERE/tools/patch_board.py" "$TREE"
mkdir -p files/etc/gateway
install -m 600 "$UNIT" files/etc/gateway/unit.json
cat > .config <<'CONFIG'
CONFIG_TARGET_ramips=y
CONFIG_TARGET_ramips_mt76x8=y
CONFIG_TARGET_ramips_mt76x8_DEVICE_hilink_hlk-7628n=y
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
grep -q '^CONFIG_PACKAGE_atech-gateway=y$' .config
grep -q '^CONFIG_PACKAGE_kmod-i2c-mt7628=y$' .config
make download -j8
make -j"${JOBS:-$(nproc)}" V=s
serial="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["serial"])' "$UNIT")"
OUT="$HERE/dist/$serial"
mkdir -p "$OUT"
cp bin/targets/ramips/mt76x8/*hilink_hlk-7628n* "$OUT/"
cp .config "$OUT/build.config"
git rev-parse HEAD > "$OUT/source-commit.txt"
./scripts/feeds list -s > "$OUT/feeds.txt"
for feed in feeds/*/.git; do
 [ -e "$feed" ] || continue
 git -C "${feed%/.git}" rev-parse HEAD >> "$OUT/feeds-commits.txt"
done
(cd "$OUT" && sha256sum *.bin > SHA256SUMS)
echo "Development image written to $OUT. Contains unit Wi-Fi credentials: keep private."
echo 'Do not flash until partition layout, calibration backup, memory variant and recovery have been verified.'
