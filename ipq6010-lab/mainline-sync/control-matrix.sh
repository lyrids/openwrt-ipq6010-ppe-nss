#!/bin/bash
# Run on p43 with SSH agent forwarding. Do not reboot or change persistent boot policy.
set -euo pipefail
cd "$(dirname "$0")"
mode="${1:?ppe or software}"
[[ "$mode" == ppe || "$mode" == software ]]
export MODE="$mode" PPPOE_SERVER_MODE=kernel
D=(ssh -o BatchMode=yes -o ConnectTimeout=5 -o UserKnownHostsFile="$DUT_KNOWN_HOSTS" root@192.168.1.1)
[[ "$("${D[@]}" 'cat /sys/module/ath11k/parameters/nss_offload')" == N ]]
if [[ "$mode" == ppe ]]; then flag=1; else flag=0; fi
"${D[@]}" "uci set firewall.@defaults[0].flow_offloading=$flag; uci set firewall.@defaults[0].flow_offloading_hw=$flag; uci commit firewall; /etc/init.d/firewall reload"
mkdir -p "$HOME/openwrt-ramboot/mainline-qualification/mode-$mode"
"${D[@]}" 'nft list ruleset; cat /sys/kernel/debug/39000000.nss/boot; cat /sys/module/nss_wifi_drv/parameters/ethernet_offload' > "$HOME/openwrt-ramboot/mainline-qualification/mode-$mode/verification.txt"
if [[ "${SKIP_WIRED:-0}" != 1 ]]; then python3 benchmark.py --mode "$mode" --path wired-nat; fi
for radio in qcn builtin5; do
 python3 select-client-radio.py "$radio"
 python3 benchmark.py --mode "$mode" --radio "$radio" --path wifi-bridge --balanced
 python3 benchmark.py --mode "$mode" --radio "$radio" --path wifi-nat --balanced
done
python3 select-client-radio.py qcn
trap 'python3 network-tests.py pppoe-down || true; python3 network-tests.py vlan-down || true' EXIT
python3 network-tests.py vlan-up
python3 benchmark.py --mode "$mode" --path vlan-nat --quick
python3 network-tests.py pppoe-up
python3 benchmark.py --mode "$mode" --path pppoe --quick
python3 network-tests.py pppoe-down
python3 network-tests.py vlan-down
trap - EXIT
python3 qdisc.py
