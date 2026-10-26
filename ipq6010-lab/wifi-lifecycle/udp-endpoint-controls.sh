#!/bin/sh
# Run on WRT32X with a dedicated p43 server listening on1.2:5360.
set -u
d=${RUN_DIR:-/tmp/udp-isolation-20261026}
mkdir -p "$d"
sta_ip=${STA_IP:-$(ip -4 -o addr show dev wlan0-sta | awk '{print $4}' | cut -d/ -f1)}
cat /proc/net/snmp > "$d/snmp-before.txt"
iperf3 -s -B 127.0.0.1 -p 5362 -D --pidfile "$d/loop-server.pid" --logfile "$d/loop-server.log" || exit 1
trap 'kill "$(cat "$d/loop-server.pid")" 2>/dev/null || true' EXIT
for mode in wired100 wifi100 loop100 loop0 wired0; do
 addr=192.168.1.2; port=5360; src=192.168.1.3; dev=br-lan; rate=100M
 case "$mode" in
  wifi100) src=$sta_ip; dev=wlan0-sta;;
  loop*) addr=127.0.0.1; port=5362; src=127.0.0.1; dev=lo;;
 esac
 case "$mode" in loop0|wired0) rate=0;; esac
 iperf3 -c "$addr" -p "$port" -B "$src" --bind-dev "$dev" -u -b "$rate" -l 1200 -t 10 --connect-timeout 5000 -J > "$d/$mode.json"
 echo $? > "$d/$mode.exit"
done
cat /proc/net/snmp > "$d/snmp-after.txt"
