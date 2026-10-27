#!/usr/bin/env python3
"""Run on p43: sustain QCN downlink while exercising scoped datapath transitions."""
import datetime,json,os,pathlib,shlex,subprocess,time
root=pathlib.Path.home()/"openwrt-ramboot/mainline-qualification/crash-triage"
out=root/datetime.datetime.now(datetime.timezone.utc).strftime("transitions-%Y%m%dT%H%M%SZ")
out.mkdir(parents=True)
base=["ssh","-n","-o","BatchMode=yes","-o","ConnectTimeout=5","-o","StrictHostKeyChecking=yes"]
dut=base+["-o","UserKnownHostsFile="+os.environ["DUT_KNOWN_HOSTS"],"root@192.168.1.1"]
wrt=base+["-b","192.168.1.132","-o","UserKnownHostsFile="+str(pathlib.Path.home()/"openwrt-ramboot/replacement154-lan-known-hosts"),"root@192.168.1.3"]
def call(v,check=True):
 r=subprocess.run(v,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
 if check and r.returncode:raise RuntimeError(r.stdout)
 return r
def remote(s,check=True):return call(dut+[s],check)
def save(n,s):(out/n).write_text(s)
save("harness.py",pathlib.Path(__file__).read_text())
old=[remote("uci get firewall.@defaults[0]."+k).stdout.strip() for k in ["flow_offloading","flow_offloading_hw"]]
for dev in ["wan","phy2-ap0"]:
 s=remote("tc qdisc show dev "+dev).stdout;save("original-"+dev+".txt",s)
 assert all("noqueue" in l for l in s.splitlines())
assert not call(["ss","-H","-lnt","sport","=",":5372"]).stdout.strip()
sta=call(wrt+["ip -4 -o addr show dev wlan0-sta"]).stdout.split()[3].split("/")[0]
save("before.txt",remote("date -u; uptime; brctl show; nft list ruleset; cat /sys/kernel/debug/39000000.nss/boot; dmesg").stdout)
server=subprocess.Popen(["iperf3","-s","-B","192.168.1.2","-p","5372"],stdout=open(out/"server.log","w"),stderr=subprocess.STDOUT)
client=None;monitor=None
def mark(text):
 remote("printf "+shlex.quote("<3>TRIAGE "+text+"\n")+" >/dev/kmsg")
def fw(flag):
 remote("uci set firewall.@defaults[0].flow_offloading="+str(flag)+"; uci set firewall.@defaults[0].flow_offloading_hw="+str(flag)+"; uci commit firewall; /etc/init.d/firewall reload")
try:
 fw(0 if os.environ.get("TRIAGE_PEERS") else 1);mark("start")
 monitor=subprocess.Popen(dut+["for i in $(seq 1 100); do date -u; cat /proc/uptime; cat /sys/class/thermal/thermal_zone*/temp; head -5 /proc/stat; sleep 2; done"],stdout=open(out/"liveness.txt","w"),stderr=open(out/"monitor.stderr","w"))
 time.sleep(1)
 client=subprocess.Popen(wrt+["iperf3 -c 192.168.1.2 -p 5372 -B "+sta+" --bind-dev wlan0-sta -R -t 150 -O 2 -J --connect-timeout 5000"],stdout=open(out/"iperf.json","w"),stderr=open(out/"iperf.stderr","w"))
 actions=[("flowtable-off",lambda:fw(0)),("flowtable-on",lambda:fw(1)),
 ("wifi-tbf100",lambda:remote("tc qdisc replace dev phy2-ap0 root tbf rate 100mbit burst 64kb latency 50ms")),
 ("wifi-qdisc-delete",lambda:remote("tc qdisc del dev phy2-ap0 root")),
 ("wan-tbf100",lambda:remote("tc qdisc replace dev wan root tbf rate 100mbit burst 64kb latency 50ms")),
 ("wan-qdisc-delete",lambda:remote("tc qdisc del dev wan root")),
 ("flowtable-off-2",lambda:fw(0)),("flowtable-on-2",lambda:fw(1)),
 ("wifi-cake100",lambda:remote("tc qdisc replace dev phy2-ap0 root cake bandwidth 100mbit")),
 ("wifi-cake-delete",lambda:remote("tc qdisc del dev phy2-ap0 root")),
 ("flowtable-off-final",lambda:fw(0))]
 if os.environ.get("TRIAGE_PEERS"):
  mac=call(wrt+["cat /sys/class/net/wlan0-sta/address"]).stdout.strip()
  request=shlex.quote(json.dumps({"addr":mac,"reason":5,"deauth":True,"ban_time":0}))
  def deauth():remote("ubus call hostapd.phy2-ap0 del_client "+request)
  actions=[("peer-deauth-"+str(i+1),deauth) for i in range(8)]
 for i,(name,fn) in enumerate(actions):
  time.sleep(5 if i==0 else 10)
  assert client.poll() is None,"iperf ended before transitions completed"
  print(name,flush=True);mark(name);fn();save(name+".txt",remote("uptime; tc -s qdisc show; nft list ruleset",False).stdout)
 rc=client.wait(timeout=80);save("iperf.exit",str(rc))
 data=json.loads((out/"iperf.json").read_text())
 assert rc==0 and not data.get("error"),data.get("error","iperf failed")
 save("status","complete\n");print("PASS sustained transitions",flush=True)
finally:
 for dev in ["phy2-ap0","wan"]:remote("tc qdisc del dev "+dev+" root",False)
 remote("uci set firewall.@defaults[0].flow_offloading="+old[0]+"; uci set firewall.@defaults[0].flow_offloading_hw="+old[1]+"; uci commit firewall; /etc/init.d/firewall reload",False)
 if client and client.poll() is None:client.terminate();client.wait(timeout=5)
 if monitor and monitor.poll() is None:monitor.terminate();monitor.wait(timeout=5)
 server.terminate();server.wait(timeout=5)
 save("after.txt",remote("uptime; cat /sys/devices/system/cpu/online; dmesg",False).stdout)
 print("EVIDENCE",out,flush=True)
