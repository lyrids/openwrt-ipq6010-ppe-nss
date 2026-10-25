#!/bin/bash
set -u
w=/home/ubuntu/openwrt-ramboot/iteration9-soak-20261026
mkdir -p "$w"
exec 9>"$w/run.lock"
flock -n 9 || exit 1
rssh() { ssh -n -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/home/ubuntu/openwrt-ramboot/iteration9-known-hosts root@192.168.1.1 "$@"; }
if test -n "$(ip route show 192.168.21.154/32)"; then echo existing-host-route; exit 1; fi
ip route get 192.168.21.154 > "$w/route-before.txt"
sudo -n ip route add 192.168.21.154/32 via 192.168.1.1 dev eth0 src 192.168.1.2 || exit 1
cleanup() { sudo -n ip route del 192.168.21.154/32 via 192.168.1.1 dev eth0; }
trap cleanup EXIT
ip route get 192.168.21.154 from 192.168.1.2 > "$w/route-test.txt"
rssh 'uptime; cat /proc/meminfo; dmesg; ip -s link show wan; cat /sys/kernel/debug/39000000.nss/flows' > "$w/before.txt"
rssh 'for i in $(seq 1 182); do echo SAMPLE-$i; cat /proc/uptime; head -n 5 /proc/stat; grep -E "MemFree:|MemAvailable:|Slab:|SUnreclaim:" /proc/meminfo; cat /sys/kernel/debug/39000000.nss/flows; conntrack -L -p tcp --dport 5201 -o extended 2>/dev/null; sleep 10; done' > "$w/monitor.txt" 2> "$w/monitor.stderr" &
mon=$!
date -u +%FT%TZ > "$w/started-utc"
echo running > "$w/status"
timeout 1830s /home/ubuntu/openwrt-ramboot/extended-wired/iperf3-matched -c 192.168.21.154 -B 192.168.1.2 -p 5201 --bidir -t 1800 -J > "$w/bidir.json" 2> "$w/bidir.stderr"
rc=$?
echo "$rc" > "$w/iperf.exit"
wait "$mon"
rssh 'uptime; cat /proc/meminfo; dmesg; ip -s link show wan; cat /sys/devices/system/cpu/online; cat /sys/kernel/debug/39000000.nss/flows' > "$w/after.txt"
date -u +%FT%TZ > "$w/finished-utc"
echo complete > "$w/status"
exit "$rc"
