#!/bin/bash
# Launch through ssh -A p43; source is maintained on Orb. Keep wired management separate.
set -u
root=/home/ubuntu/openwrt-ramboot/wrt32x-sta-performance-20261026
w="$root/run-$(date -u +%H%M%S)"
mkdir -p "$w"
echo "$w" > "$root/latest-run.txt"
rssh() { ssh -n -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/home/ubuntu/openwrt-ramboot/iteration9-known-hosts root@192.168.1.1 "$@"; }
cssh() { ssh -n -b 192.168.1.132 -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/home/ubuntu/openwrt-ramboot/replacement154-lan-known-hosts root@192.168.1.3 "$@"; }
sta_ip=$(cssh 'ip -4 -o addr show dev wlan0-sta' | awk '{print $4}' | cut -d/ -f1)
sta_mac=$(cssh cat /sys/class/net/wlan0-sta/address)
case "$sta_ip" in 192.168.1.*) ;; *) echo 'Unexpected STA subnet'; exit 1;; esac
cssh iw dev wlan0-sta link | grep -q 'Connected to dc:d8:7c:54:83:f0' || exit 1
test -z "$(ss -H -lnt sport = :5360)" || { echo 'Test port is in use'; exit 1; }
/usr/bin/iperf3 -s -B 192.168.1.2 -p 5360 > "$w/server.log" 2>&1 &
server=$!
mon=
cleanup() { kill "$server" 2>/dev/null || true; if test -n "$mon"; then kill "$mon" 2>/dev/null || true; wait "$mon" 2>/dev/null || true; fi; }
trap cleanup EXIT
printf 'STA_IP=%s\nSTA_MAC=%s\n' "$sta_ip" "$sta_mac" > "$w/endpoint.txt"
date -u +%FT%TZ > "$w/started-utc"
cssh "iw dev wlan0-sta link; ip route get 192.168.1.2 from $sta_ip oif wlan0-sta; ip -s link show wlan0-sta; ip route show default" > "$w/client-before.txt"
rssh 'uptime; cat /proc/meminfo; dmesg; cat /sys/kernel/debug/39000000.nss/wifili_rx' > "$w/dut-before.txt"
rssh 'for n in $(seq 1 120); do echo SAMPLE-$n; cat /proc/uptime; head -n 5 /proc/stat; cat /sys/kernel/debug/39000000.nss/flows; cat /sys/kernel/debug/39000000.nss/wifili_rx; iw dev phy2-ap0 station dump; sleep 2; done' > "$w/monitor.txt" 2> "$w/monitor.stderr" &
mon=$!
run_case() {
 local name=$1; shift
 echo "CASE $name started"
 timeout 50s ssh -n -b 192.168.1.132 -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/home/ubuntu/openwrt-ramboot/replacement154-lan-known-hosts root@192.168.1.3 "iperf3 -c 192.168.1.2 -p 5360 -B $sta_ip --bind-dev wlan0-sta -J --connect-timeout 5000 --rcv-timeout 15000 --snd-timeout 15000 $*" > "$w/$name.json" 2> "$w/$name.stderr"
 echo $? > "$w/$name.exit"
 echo "CASE $name finished"
}
if [[ "${1:-full}" = udp-extra ]]; then
 run_case udp0-forward -u -b 0 -l 1200 -t 10
 run_case udp100burst-forward -u -b 100M/64 -l 1200 -t 10
else
run_case tcp-forward -t 20
run_case tcp-reverse -t 20 -R
run_case tcp4-forward -t 20 -P 4
run_case tcp4-reverse -t 20 -P 4 -R
run_case tcp-bidir -t 30 --bidir
run_case udp100-forward -u -b 100M -l 1200 -t 10
run_case udp100-reverse -u -b 100M -l 1200 -t 10 -R
run_case udp300-forward -u -b 300M -l 1200 -t 10
run_case udp300-reverse -u -b 300M -l 1200 -t 10 -R
fi
cssh 'iw dev wlan0-sta link; ip -s link show wlan0-sta; ip route show default' > "$w/client-after.txt"
rssh 'uptime; cat /proc/meminfo; dmesg; cat /sys/devices/system/cpu/online; cat /sys/kernel/debug/39000000.nss/wifili_rx' > "$w/dut-after.txt"
ip neigh show "$sta_ip" dev eth0 > "$w/peer-neighbor.txt"
if grep -qi "$sta_mac" "$w/peer-neighbor.txt"; then echo 'PASS: server neighbor is Wi-Fi STA MAC' > "$w/path-check.txt"; else echo 'FAIL: server neighbor differs from Wi-Fi STA MAC' > "$w/path-check.txt"; fi
date -u +%FT%TZ > "$w/finished-utc"
echo complete > "$w/status"
echo "RESULTS $w"
