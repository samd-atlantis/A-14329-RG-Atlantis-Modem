#!/bin/sh
# READ ONLY. Run on an already-booting OpenWrt module over USB console or SSH.
# This is not an OEM U-Boot command and does not write flash, UCI or GPIOs.
set -eu
. /usr/share/libubox/jshn.sh
board="$(ubus call system board)"
json_init
json_add_string schema 'mb00-device-probe-1'
json_add_string board_name "$(printf '%s' "$board" | jsonfilter -e '@.board_name')"
json_add_string model "$(printf '%s' "$board" | jsonfilter -e '@.model')"
json_add_string distribution "$(printf '%s' "$board" | jsonfilter -e '@.release.distribution')"
json_add_string version "$(printf '%s' "$board" | jsonfilter -e '@.release.version')"
json_add_string kernel "$(uname -r)"
json_add_string memtotal_kib "$(awk '/^MemTotal:/{print $2}' /proc/meminfo)"
json_add_string mtd "$(cat /proc/mtd)"
json_add_string serial "$(uci -q get gateway.main.serial || true)"
json_add_string provisioned "$(uci -q get gateway.main.provisioned || true)"
json_add_string wifi_mac "$(cat /sys/class/ieee80211/phy0/macaddress 2>/dev/null || true)"
lan_device="$(ubus call network.interface.lan status 2>/dev/null | jsonfilter -e '@.l3_device' || true)"
case "$lan_device" in
  ''|*[!a-zA-Z0-9_.:-]*) lan_mac='' ;;
  *) lan_mac="$(cat "/sys/class/net/$lan_device/address" 2>/dev/null || true)" ;;
esac
# Effective LAN MAC, kept separate from the permanent internal Wi-Fi MAC.
json_add_string lan_mac "$lan_mac"
json_add_string ssid "$(uci -q get wireless.default_radio0.ssid || true)"
json_add_string hardware_validated "$(uci -q get gateway.main.hardware_validated || true)"
json_add_boolean modem_qmi_present "$([ -c /dev/cdc-wdm0 ] && echo 1 || echo 0)"
json_add_array usb_devices
for node in /sys/bus/usb/devices/*; do
  [ -r "$node/idVendor" ] && [ -r "$node/idProduct" ] || continue
  json_add_object ''
  json_add_string path "${node##*/}"
  json_add_string vendor "$(cat "$node/idVendor")"
  json_add_string product "$(cat "$node/idProduct")"
  json_close_object
done
json_close_array
json_dump
