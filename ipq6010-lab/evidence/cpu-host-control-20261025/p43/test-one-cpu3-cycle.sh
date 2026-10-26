#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
# Run on the router ONLY after RAM booting a diagnostic variant.
# One attempt per boot. Failure deliberately does not retry CPU_ON.
set -u
dir=/tmp/cpu-restart-diagnostic
mkdir -p "$dir"
test ! -e "$dir/attempted" || { echo 'A CPU restart attempt was already made this boot'; exit 1; }
dmesg > "$dir/dmesg.before"
grep -q 'ipq-cpu-diag:' "$dir/dmesg.before" || { echo 'Diagnostic kernel markers absent; refusing test'; exit 1; }
test "$(cat /sys/devices/system/cpu/online)" = 0-3 || { echo 'All four CPUs must be online initially'; exit 1; }
test "$(cat /sys/kernel/kexec_loaded)" = 0 || { echo 'A kexec candidate is already loaded'; exit 1; }
cat /etc/image-provenance > "$dir/image-provenance"
uci -q show nss-wifi > "$dir/nss-config"
cat /proc/sys/kernel/random/boot_id > "$dir/boot-id"
date -u > "$dir/attempted"
echo "before=$(cat /sys/devices/system/cpu/online)" > "$dir/result"
if ! echo 0 > /sys/devices/system/cpu/cpu3/online 2>"$dir/offline.stderr"; then
 echo 'offline failed; no CPU_ON attempt made' >> "$dir/result"
 dmesg > "$dir/dmesg.after"
 cat "$dir/result"
 exit 1
fi
echo "after_offline=$(cat /sys/devices/system/cpu/online)" >> "$dir/result"
if echo 1 > /sys/devices/system/cpu/cpu3/online 2>"$dir/online.stderr"; then
 echo "after_online=$(cat /sys/devices/system/cpu/online)" >> "$dir/result"
 rc=0
else
 rc=$?
 echo "online_write_failed=$rc" >> "$dir/result"
 echo "remaining_online=$(cat /sys/devices/system/cpu/online)" >> "$dir/result"
fi
dmesg > "$dir/dmesg.after"
cat /sys/kernel/kexec_loaded > "$dir/kexec-loaded.after"
cat "$dir/result"
grep -E 'ipq-cpu-diag|CPU3|IRQ.*affinity|stuck' "$dir/dmesg.after" || true
if test "$rc" -ne 0; then
 echo 'STOP: preserve logs; do not offline another CPU or bypass the kexec guard.'
fi
exit "$rc"
