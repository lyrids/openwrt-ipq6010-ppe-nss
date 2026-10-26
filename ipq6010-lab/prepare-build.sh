#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
lab=ipq6010-lab
cp "$lab/feeds.conf.pinned" feeds.conf
./scripts/feeds update -a
if git -C feeds/nss apply --check "../../$lab/nss-firmware-selected-line.patch"; then
 git -C feeds/nss apply "../../$lab/nss-firmware-selected-line.patch"
elif ! git -C feeds/nss apply --reverse --check "../../$lab/nss-firmware-selected-line.patch"; then
 echo 'NSS feed differs from both the pinned and expected patched state' >&2; exit 1
fi
while IFS=$'\t' read -r feed package; do
 ./scripts/feeds install -p "$feed" "$package"
done < "$lab/selected-feed-packages.tsv"
cp "$lab/config.seed" .config
python3 - <<'PY'
from pathlib import Path
import os
p=Path(".config");s=p.read_text()
s=s.replace("/home/ly/projects/openwrt-dev/ccache",os.environ.get("CCACHE_DIR",str(Path.cwd()/".ccache")))
s=s.replace("/home/ly/projects/openwrt-dev/downloads",os.environ.get("OPENWRT_DL_DIR",str(Path.cwd()/"dl")))
p.write_text(s)
PY
mkdir -p files
cp -a "$lab/overlay/." files/
make defconfig
echo 'Preparation complete. Review .config, then make download -j8 and make -j8 V=s.'
