#!/bin/sh
# Run on the WRT32X after p43 listener5360 and temporary max-buffer setup.
set -u
d=/tmp/udp-isolation-20261026
test -s "$d/wmem-max.before" && test -s "$d/rmem-max.before" || exit 1
sta_ip=${STA_IP:-$(ip -4 -o addr show dev wlan0-sta | awk '{print $4}' | cut -d/ -f1)}
cat /proc/sys/net/core/wmem_default > "$d/wmem-default.before"
restore() {
 sysctl -w net.core.wmem_default="$(cat "$d/wmem-default.before")" net.core.wmem_max="$(cat "$d/wmem-max.before")" net.core.rmem_max="$(cat "$d/rmem-max.before")" > "$d/buffers-restored.txt"
}
trap restore EXIT
sysctl -w net.core.wmem_default=4194304 > "$d/sender-default-change.txt"
iperf3 -c 192.168.1.2 -p 5360 -B "$sta_ip" --bind-dev wlan0-sta -u -b 100M -l 1200 -t 10 -J > "$d/wifi100-sender-default4M.json"
echo $? > "$d/wifi100-sender-default4M.exit"
sysctl -w net.core.wmem_default="$(cat "$d/wmem-default.before")"
for mode in wifi300-buffer4M wifi300-reverse-buffer4M wifi0-buffer4M; do
 rate=300M; extra=
 test "$mode" = wifi0-buffer4M && rate=0
 test "$mode" = wifi300-reverse-buffer4M && extra=-R
 echo "CASE $mode"
 iperf3 -c 192.168.1.2 -p 5360 -B "$sta_ip" --bind-dev wlan0-sta -u -b "$rate" -w 4M -l 1200 -t 10 -J $extra > "$d/$mode.json"
 echo $? > "$d/$mode.exit"
done
cat /proc/net/snmp > "$d/snmp-buffer-after.txt"
echo BUFFER-ISOLATION-DONE
