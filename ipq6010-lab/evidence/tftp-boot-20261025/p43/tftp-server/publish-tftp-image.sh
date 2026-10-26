#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-only
# Run on p43 after copying a separately validated board-specific FIT to it.
set -euo pipefail
test "$#" = 2 || { echo "Usage: $0 STAGED_FIT EXPECTED_SHA256" >&2; exit 2; }
image="$1"; expected="$2"
[[ "$expected" =~ ^[0-9a-f]{64}$ ]] || { echo 'Expected lowercase SHA256 required' >&2; exit 2; }
test -r "$image"
actual=$(sha256sum -- "$image"); actual="${actual%% *}"
test "$actual" = "$expected" || { echo 'Image SHA256 mismatch' >&2; exit 1; }
magic=$(od -An -tx1 -N4 -- "$image" | tr -d ' \n')
test "$magic" = d00dfeed || { echo 'Not a FIT/DTB container; refusing publication' >&2; exit 1; }
mkdir -p "$HOME/openwrt-ramboot"
exec 9>"$HOME/openwrt-ramboot/.tftp-publish.lock"
flock 9
root=/srv/tftp/openwrt
dest="$root/jdcloud-re-cs-02.itb"
temp="$root/.jdcloud-re-cs-02.$$.new"
trap 'sudo -n rm -f -- "$temp"' EXIT
sudo -n install -m 644 -- "$image" "$temp"
check=$(sudo -n sha256sum -- "$temp"); check="${check%% *}"
test "$check" = "$expected"
if sudo -n test -f "$dest"; then
 sudo -n cp --preserve=mode,timestamps -- "$dest" "$root/jdcloud-re-cs-02-previous.itb"
fi
sudo -n mv -T -- "$temp" "$dest"
echo "Published $expected to 192.168.1.2:openwrt/jdcloud-re-cs-02.itb"
