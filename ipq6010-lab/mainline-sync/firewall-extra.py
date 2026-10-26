#!/usr/bin/env python3
"""Run on p43: unsolicited WAN input and DNAT forwarding checks."""
import json,os,pathlib,subprocess,time
out=pathlib.Path.home()/"openwrt-ramboot/mainline-qualification/firewall-extra"
out.mkdir(parents=True,exist_ok=True)
base=["ssh","-n","-o","BatchMode=yes","-o","ConnectTimeout=5","-o","StrictHostKeyChecking=yes"]
dut=base+["-o","UserKnownHostsFile="+os.environ["DUT_KNOWN_HOSTS"],"root@192.168.1.1"]
wrt=base+["-b","192.168.1.132","-o","UserKnownHostsFile="+str(pathlib.Path.home()/"openwrt-ramboot/replacement154-lan-known-hosts"),"root@192.168.1.3"]
def run(argv,check=True,timeout=25):
 r=subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
 if check and r.returncode:raise RuntimeError(r.stdout)
 return r
def r(h,s,check=True):return run(h+[s],check)
def save(n,s):(out/n).write_text(s)
try:
 r(dut,"test ! -f /tmp/mainline-input-iperf.pid && iperf3 -s -D -p 5370 -I /tmp/mainline-input-iperf.pid")
 x=run(["iperf3","-c","192.168.1.1","-p","5370","-B","192.168.1.2","-t","3","-J"])
 save("lan-local-allowed.json",x.stdout)
 x=r(wrt,"ip netns exec ppe-wan-bench iperf3 -c 198.18.21.1 -p 5370 -t 3 -J --connect-timeout 3000",False)
 save("wan-local-blocked.json",x.stdout)
 assert x.returncode!=0,"Unsolicited WAN input reached local listener"
 save("wan-input-counters.txt",r(dut,"nft -a list chain inet fw4 input_wan; nft -a list chain inet fw4 reject_from_wan").stdout)
 r(wrt,"test ! -f /tmp/mainline-dnat-iperf.pid && iperf3 -s -D -B 192.168.1.3 -p 5368 -I /tmp/mainline-dnat-iperf.pid; ip route add 198.18.21.154/32 via 192.168.1.1 dev br-lan")
 r(dut,"uci set firewall.labdnat=redirect; uci set firewall.labdnat.name=Mainline-lab-DNAT; uci set firewall.labdnat.src=wan; uci set firewall.labdnat.src_dport=5358; uci set firewall.labdnat.dest=lan; uci set firewall.labdnat.dest_ip=192.168.1.3; uci set firewall.labdnat.dest_port=5368; uci set firewall.labdnat.proto=tcp; uci set firewall.labdnat.target=DNAT; uci commit firewall; /etc/init.d/firewall reload")
 time.sleep(2)
 for direction,opt in [("inbound",""),("reverse","-R")]:
  log=open(out/("dnat-"+direction+".json"),"w")
  proc=subprocess.Popen(wrt+["ip netns exec ppe-wan-bench iperf3 -c 198.18.21.1 -p 5358 -t 10 -O 2 -J "+opt],stdout=log,stderr=subprocess.PIPE,text=True)
  time.sleep(6)
  save("dnat-"+direction+"-active.txt",r(dut,"nft -a list chain inet fw4 dstnat_wan; cat /sys/kernel/debug/39000000.nss/flows; cat /sys/kernel/debug/3a000000.ppe/flows").stdout)
  rc=proc.wait(timeout=20);log.close()
  assert rc==0,"DNAT test failed"
  data=json.loads((out/("dnat-"+direction+".json")).read_text());assert not data.get("error"),data
  print("DNAT",direction,data["end"]["sum_received"]["bits_per_second"]/1e6,flush=True)
 save("status","complete\n")
finally:
 r(dut,"uci -q delete firewall.labdnat; uci commit firewall; /etc/init.d/firewall reload; if test -f /tmp/mainline-input-iperf.pid; then p=$(cat /tmp/mainline-input-iperf.pid); case $(cat /proc/$p/comm) in iperf3) kill $p;; esac; rm -f /tmp/mainline-input-iperf.pid; fi",False)
 r(wrt,"ip route del 198.18.21.154/32 via 192.168.1.1 dev br-lan; if test -f /tmp/mainline-dnat-iperf.pid; then p=$(cat /tmp/mainline-dnat-iperf.pid); case $(cat /proc/$p/comm) in iperf3) kill $p;; esac; rm -f /tmp/mainline-dnat-iperf.pid; fi",False)
print("PASS: WAN input blocked, LAN local allowed, WAN DNAT forwarded in both directions")
