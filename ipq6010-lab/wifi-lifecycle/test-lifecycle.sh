#!/bin/bash
# Run on p43 after enabling the test AP; never reload firewall manually here.
set -euo pipefail
known=${DUT_KNOWN_HOSTS:-/home/ubuntu/openwrt-ramboot/iteration9-known-hosts}
cycles=${1:-2}
[[ "$cycles" =~ ^[1-9][0-9]*$ ]] || exit 2
rssh() { ssh -n -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$known" root@192.168.1.1 "$@"; }
[[ "$(rssh cat /tmp/sysinfo/board_name)" = jdcloud,re-cs-02 ]] || exit 1
wait_member() {
 local expected=$1 state attempt
 for attempt in $(seq 1 15); do
  state=$(rssh nft list flowtable inet fw4 ft)
  if grep -Fq '"phy2-ap0"' <<< "$state"; then
   [[ "$expected" = present ]] && { echo "$state"; return 0; }
  else
   [[ "$expected" = absent ]] && { echo "$state"; return 0; }
  fi
  sleep 1
 done
 echo "FAIL: expected phy2-ap0 $expected in flowtable" >&2
 return 1
}
trap 'rssh wifi up radio2 >/dev/null 2>&1 || true' EXIT
wait_member present
for cycle in $(seq 1 "$cycles"); do
 echo "CYCLE $cycle DOWN"
 rssh wifi down radio2
 wait_member absent
 echo "CYCLE $cycle UP"
 rssh wifi up radio2
 wait_member present
done
trap - EXIT
echo "PASS: automatic wireless flowtable membership across $cycles cycles"
