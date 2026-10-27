#!/bin/bash
set -euo pipefail
workspace="$HOME/projects/openwrt-dev"
. "$workspace/env.sh"
cd "$(dirname "$0")/../.."
mode=on
if [ "$#" -gt 0 ]; then mode=$1; fi
case "$mode" in on|off) ;; *) echo "Use on or off" >&2; exit 2;; esac
run="$workspace/artifacts/mainline-sync-nss-$mode-$(git rev-parse --short=10 HEAD)-$(date -u +%Y%m%d)"
mkdir -p "$run"
exec 9>"$workspace/.build.lock"
flock -n 9 || exit 1
restore_overlay() {
 cp ipq6010-lab/overlay/etc/config/nss-wifi files/etc/config/nss-wifi
 cp ipq6010-lab/overlay/etc/image-provenance files/etc/image-provenance
}
trap 'rc=$?; restore_overlay; echo "$rc" > "$run/exit-code"; test "$rc" = 0 || echo failed > "$run/status"' EXIT
mkdir -p files/etc/config
restore_overlay
if [ "$mode" = off ]; then
 sed -i "s/option offload '1'/option offload '0'/; s/option ethernet_offload '1'/option ethernet_offload '0'/" files/etc/config/nss-wifi
fi
printf "NSS control variant: %s\n" "$mode" >> files/etc/image-provenance
# Network structure layouts can change with kernel configuration. Rebuild
# out-of-tree modules instead of reusing an incompatible incremental object.
make defconfig > "$run/defconfig.log" 2>&1
config_hash=$(sha256sum .config | cut -d' ' -f1)
config_stamp=tmp/ipq6010-lab-external-config.sha256
if [ ! -f "$config_stamp" ] || [ "$(cat "$config_stamp")" != "$config_hash" ]; then
 make package/kernel/mac80211/clean package/kernel/nss-wifi-drv/clean > "$run/external-clean.log" 2>&1
fi
cp files/etc/config/nss-wifi "$run/nss-wifi.config"
cp files/etc/image-provenance "$run/image-provenance"
"$workspace/bin/snapshot-build-state" "$PWD" "$run/build-state"
git rev-parse HEAD > "$run/source-commit.txt"
git -C feeds/nss diff > "$run/firmware-feed-local.patch"
cp .config "$run/config.full"
date -u +%FT%TZ > "$run/started-utc"
echo building > "$run/status"
make -j"$BUILD_JOBS" V=s > "$run/build.log" 2>&1
mkdir -p "$run/images"
cp bin/targets/qualcommax/ipq60xx/*jdcloud_re-cs-02* "$run/images/"
(cd "$run/images"; sha256sum *) > "$run/images.sha256"
date -u +%FT%TZ > "$run/finished-utc"
printf "%s\n" "$config_hash" > "$config_stamp"
echo built > "$run/status"
