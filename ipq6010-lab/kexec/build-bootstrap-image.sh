#!/bin/bash
set -euo pipefail
workspace=/home/ly/projects/openwrt-dev
run="$workspace/artifacts/nss-ethernet-kexec-20261025"
mkdir -p "$run"
exec 9>"$workspace/.build.lock"
flock -n 9
cd "$workspace/src/openwrt-ppe-nss"
trap 'rc=$?; echo "$rc" > "$run/exit-code"; if test "$rc" -ne 0; then echo failed > "$run/status"; fi' EXIT
date -u +%FT%TZ > "$run/started-utc"
git rev-parse HEAD > "$run/source-base"
git diff > "$run/source-local.patch"
cp .config "$run/config.full"
echo cleaning > "$run/status"
make target/linux/clean > "$run/kernel-clean.log" 2>&1
echo downloading > "$run/status"
make download -j8 > "$run/download.log" 2>&1
echo building > "$run/status"
make -j8 V=s > "$run/build.log" 2>&1
echo built > "$run/status"
date -u +%FT%TZ > "$run/finished-utc"
