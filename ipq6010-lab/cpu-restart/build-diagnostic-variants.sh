#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-only
set -euo pipefail
workspace=/home/ly/projects/openwrt-dev
tree="$workspace/src/openwrt-ppe-nss"
root="$workspace/artifacts/cpu-restart-diag-20261025"
mkdir -p "$root"
exec 9>"$workspace/.build.lock"
flock -n 9
cd "$tree"
trap 'rc=$?; echo "$rc" > "$root/exit-code"; if test "$rc" -ne 0; then echo failed > "$root/status"; fi' EXIT
git rev-parse HEAD > "$root/source-base.txt"
cp target/linux/qualcommax/patches-6.18/0990-arm64-trace-ipq-cpu-restart.patch "$root/diagnostic-kernel.patch"
cp .config "$root/config.full"
date -u +%FT%TZ > "$root/started-utc"
echo cleaning > "$root/status"
make target/linux/clean > "$root/kernel-clean.log" 2>&1
echo downloading > "$root/status"
make download -j8 > "$root/download.log" 2>&1
for variant in host-control nss-enabled; do
 run="$root/$variant"
 mkdir -p "$run"
 VARIANT="$variant" python3 - <<'PY'
from pathlib import Path
import os
t=Path.cwd();variant=os.environ["VARIANT"]
s=(t/"ipq6010-lab/overlay/etc/config/nss-wifi").read_text()
if variant=="host-control":
 s=s.replace("option offload '1'","option offload '0'").replace("option ethernet_offload '1'","option ethernet_offload '0'")
(t/"files/etc/config/nss-wifi").write_text(s)
p=t/"files/etc/image-provenance"
p.write_text("Variant: iteration 7 CPU restart diagnostics, "+variant+"\nSource base: e3caef34ec plus 0990-arm64-trace-ipq-cpu-restart.patch\nKernel: KEXEC/KEXEC_FILE/HOTPLUG_CPU/SUSPEND retained\nPSCI: raw CPU_ON result, entry/affinity, secondary-C checkpoints\nNSS firmware packaging: 12.5 only; no secure firmware modifications\nCPU restart fix: none applied, diagnostics only\n")
PY
 cp files/etc/config/nss-wifi "$run/nss-wifi.config"
 cp files/etc/image-provenance "$run/image-provenance"
 echo "building $variant" > "$root/status"
 make -j8 V=s > "$run/build.log" 2>&1
 mkdir -p "$run/images"
 cp bin/targets/qualcommax/ipq60xx/*initramfs-uImage.itb bin/targets/qualcommax/ipq60xx/*sysupgrade.bin bin/targets/qualcommax/ipq60xx/*.manifest bin/targets/qualcommax/ipq60xx/*.buildinfo bin/targets/qualcommax/ipq60xx/profiles.json bin/targets/qualcommax/ipq60xx/sha256sums "$run/images/"
 kernel=build_dir/target-aarch64_cortex-a53_musl/linux-qualcommax_ipq60xx/linux-6.18.55
 cp "$kernel/.config" "$run/kernel.config"
 sha256sum "$kernel/arch/arm64/kernel/psci.o" "$kernel/arch/arm64/kernel/smp.o" "$kernel/drivers/firmware/psci/psci.o" > "$run/cpu-object-sha256sums.txt"
 echo built > "$run/status"
 date -u +%FT%TZ > "$run/finished-utc"
done
echo built > "$root/status"
date -u +%FT%TZ > "$root/finished-utc"
