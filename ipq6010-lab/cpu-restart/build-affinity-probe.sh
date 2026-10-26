#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-only
set -euo pipefail
workspace=/home/ly/projects/openwrt-dev
tree="$workspace/src/openwrt-ppe-nss"
run="$workspace/artifacts/cpu-restart-affinity-probe-20261025"
mkdir -p "$run/build"
cp "$tree/ipq6010-lab/cpu-restart/affinity-probe/"{Makefile,ipq_psci_affinity_probe.c} "$run/build/"
export STAGING_DIR="$tree/staging_dir"
make -C "$tree/build_dir/target-aarch64_cortex-a53_musl/linux-qualcommax_ipq60xx/linux-6.18.55" M="$run/build" ARCH=arm64 CROSS_COMPILE="$STAGING_DIR/toolchain-aarch64_cortex-a53_gcc-14.4.0_musl/bin/aarch64-openwrt-linux-musl-" -j4 modules > "$run/build.log" 2>&1
cp "$run/build/ipq_psci_affinity_probe.ko" "$run/"
sha256sum "$run/ipq_psci_affinity_probe.ko"
