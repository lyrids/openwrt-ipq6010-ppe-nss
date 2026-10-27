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
current_variant=$("${D[@]}" "head -n1 /etc/image-provenance")
bench() {
 if CURRENT_VARIANT="$current_variant" python3 - "$@" <<'CHECK'
import argparse,json,os,pathlib,sys
p=argparse.ArgumentParser()
p.add_argument('--mode');p.add_argument('--path');p.add_argument('--radio',default='wired');p.add_argument('--quick',action='store_true');p.add_argument('--balanced',action='store_true')
a=p.parse_args()
need=2 if a.quick else 4 if a.balanced else 8
for f in (pathlib.Path.home()/'openwrt-ramboot/mainline-qualification').glob('*/results.json'):
 if not (f.parent/'status').exists():continue
 identity=f.parent/'identity.txt'
 if not identity.exists() or os.environ['CURRENT_VARIANT'] not in identity.read_text():continue
 rows=json.loads(f.read_text())
 if len(rows)==need and all(r.get('mode')==a.mode and r.get('path')==a.path and r.get('radio')==a.radio and r.get('seconds')==15 and not r.get('error') for r in rows):
  print('SKIP completed',f.parent.name);sys.exit(0)
sys.exit(1)
CHECK
 then return; fi
 python3 benchmark.py "$@"
}
if [[ "${SKIP_WIRED:-0}" != 1 ]]; then bench --mode "$mode" --path wired-nat; fi
for radio in qcn builtin5; do
 python3 select-client-radio.py "$radio"
 bench --mode "$mode" --radio "$radio" --path wifi-bridge --balanced
 bench --mode "$mode" --radio "$radio" --path wifi-nat --balanced
done
python3 select-client-radio.py qcn
trap 'python3 network-tests.py pppoe-down || true; python3 network-tests.py vlan-down || true' EXIT
python3 network-tests.py vlan-up
bench --mode "$mode" --path vlan-nat --quick
python3 network-tests.py pppoe-up
bench --mode "$mode" --path pppoe --quick
python3 network-tests.py pppoe-down
python3 network-tests.py vlan-down
trap - EXIT
qroot="$HOME/openwrt-ramboot/mainline-qualification/qdisc-$mode"
if [[ -f "$qroot/validated-image.txt" ]] && [[ "$(cat "$qroot/validated-image.txt")" == "$current_variant" ]] && [[ -f "$qroot/latest-run.txt" ]] && [[ -f "$(cat "$qroot/latest-run.txt")/status" ]]; then
 echo "SKIP completed qdisc $mode"
else
 python3 qdisc.py
 printf "%s\n" "$current_variant" > "$qroot/validated-image.txt"
fi
