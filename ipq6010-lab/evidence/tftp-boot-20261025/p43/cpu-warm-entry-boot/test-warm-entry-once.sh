#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
# Run only on a fresh iteration8 host-control RAM boot.
# This changes the volatile SCM warm entry during CPU_ON; it writes no flash.
set -eu
param=/sys/module/kernel/parameters/ipq_cpu_warm_vector
dir=/tmp/cpu-warm-entry-experiment
test -e "$param"
grep -q 'jdcloud,re-cs-02' /proc/device-tree/compatible
grep -q 'iteration 8 opt-in SCM warm-entry experiment, host-control' /etc/image-provenance
test "$(cat /sys/devices/system/cpu/online)" = 0-3
test "$(cat /sys/kernel/kexec_loaded)" = 0
test "$(uci -q get nss-wifi.general.offload)" = 0
test "$(cat /sys/kernel/debug/39000000.nss/boot)" = 0
test ! -e /tmp/cpu-restart-diagnostic/attempted
test -f /tmp/test-one-cpu3-cycle.sh
mkdir -p "$dir"
cat "$param" > "$dir/parameter.before"
test "$(cat "$param")" = N
trap 'echo N > /sys/module/kernel/parameters/ipq_cpu_warm_vector' EXIT
echo Y > "$param"
cat "$param" > "$dir/parameter.enabled"
if sh /tmp/test-one-cpu3-cycle.sh; then rc=0; else rc=$?; fi
echo N > "$param"
cat "$param" > "$dir/parameter.after"
echo "$rc" > "$dir/test-exit-code"
echo 'Opt-in parameter disabled again; this does not undo a successful SCM registration.'
exit "$rc"
