#!/usr/bin/env python3
"""Run on p43 after isolated replacement setup. Scope bypass to UDP port55002."""
import json, pathlib, subprocess
p=pathlib.Path('/home/ubuntu/openwrt-ramboot/replacement-wifi-20261026')
r=['ssh','-n','-o','BatchMode=yes','-o','ConnectTimeout=5','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/home/ubuntu/openwrt-ramboot/iteration9-known-hosts','root@192.168.1.1']
c=['ssh','-n','-b','192.168.1.132','-o','BatchMode=yes','-o','ConnectTimeout=5','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/home/ubuntu/openwrt-ramboot/replacement154-lan-known-hosts','root@192.168.1.3']
def call(cmd): return subprocess.check_output(r+[cmd],text=True)
def handles(): return {x['rule']['handle'] for x in json.loads(call('nft -j -a list chain inet fw4 forward'))['nftables'] if 'rule' in x}
before=handles(); new=set();mon=None
try:
    for expr in ['ip saddr 192.168.77.154 ip daddr 192.168.1.2 udp sport 55002 udp dport 5360 counter accept','ip saddr 192.168.1.2 ip daddr 192.168.77.154 udp sport 5360 udp dport 55002 counter accept']:
        old=handles();call('nft insert rule inet fw4 forward '+expr);new |= handles()-old
    with (p/'udp-software-control-monitor.txt').open('w') as f:
        mon=subprocess.Popen(r+['for n in $(seq 1 15); do cat /proc/uptime; conntrack -L -p udp --sport 55002 -o extended 2>/dev/null; sleep 1; done'],stdout=f,stderr=subprocess.DEVNULL)
        out=subprocess.check_output(c+['iperf3 -c 192.168.1.2 -B 192.168.77.154 -p 5360 -u -b 100M -l 1200 --cport 55002 -t 10 -J'],text=True,timeout=30)
        (p/'udp-software-control.json').write_text(out)
        mon.wait(timeout=25)
    (p/'udp-software-control-rules.json').write_text(call('nft -j -a list chain inet fw4 forward'))
    d=json.loads(out);print('error',d.get('error'),'sender',d.get('end',{}).get('sum_sent'),'receiver',d.get('end',{}).get('sum_received'))
finally:
    for handle in new: call('nft delete rule inet fw4 forward handle '+str(handle))
    if mon and mon.poll() is None:mon.terminate()
    print('Removed temporary control rule handles',sorted(new))
