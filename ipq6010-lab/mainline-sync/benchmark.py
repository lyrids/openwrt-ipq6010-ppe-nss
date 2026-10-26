#!/usr/bin/env python3
"""Run on p43; code is maintained on Orb. Preserve management paths."""
import argparse,datetime,json,os,pathlib,re,shlex,subprocess,time
p=argparse.ArgumentParser()
p.add_argument("--mode",choices=["nss","ppe","software"],required=True)
p.add_argument("--path",choices=["wired-nat","vlan-nat","pppoe","wifi-bridge","wifi-nat"],required=True)
p.add_argument("--radio",default="wired")
p.add_argument("--seconds",type=int,default=15)
p.add_argument("--quick",action="store_true")
p.add_argument("--balanced",action="store_true",help="TCP1 and matched100M UDP in both directions")
p.add_argument("--qdisc",default="")
a=p.parse_args()
stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
out=pathlib.Path.home()/"openwrt-ramboot/mainline-qualification"/(stamp+"-"+a.mode+"-"+a.radio+"-"+a.path+("-tbf" if a.qdisc else ""))
out.mkdir(parents=True)
known=os.environ["DUT_KNOWN_HOSTS"]
base=["ssh","-n","-o","BatchMode=yes","-o","ConnectTimeout=5","-o","StrictHostKeyChecking=yes"]
dut=base+["-o","UserKnownHostsFile="+known,"root@192.168.1.1"]
wrtbase=base+["-b","192.168.1.132","-o","UserKnownHostsFile="+str(pathlib.Path.home()/"openwrt-ramboot/replacement154-lan-known-hosts"),"root@192.168.1.3"]
sock="/tmp/mainline-wrt-"+str(os.getpid())+".sock"
def run(v,check=True,timeout=35):
 r=subprocess.run(v,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
 if check and r.returncode: raise RuntimeError(str(v)+"\n"+r.stdout)
 return r
def remote(h,s,check=True):return run(h+[s],check)
def save(n,s):(out/n).write_text(s)
subprocess.run(wrtbase[:-1]+["-M","-S",sock,"-o","ControlPersist=600","-fNT",wrtbase[-1]],check=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20)
wrt=wrtbase[:-1]+["-S",sock,wrtbase[-1]]
snapshot="date -u; cat /proc/uptime; cat /proc/stat; cat /sys/module/ath11k/parameters/nss_offload; cat /sys/module/nss_wifi_drv/parameters/ethernet_offload 2>/dev/null; for f in /sys/kernel/debug/*.nss/boot /sys/kernel/debug/*.nss/flows /sys/kernel/debug/*.nss/wifili_rx; do echo FILE-$f; cat $f; done; for f in egress flows offload queue_drops; do echo PPE-$f; cat /sys/kernel/debug/3a000000.ppe/$f; done; nft list flowtable inet fw4 ft 2>/dev/null; cat /proc/net/nf_conntrack 2>/dev/null"
def cpus(s):
 return {l.split()[0]:list(map(int,l.split()[1:9])) for l in s.splitlines() if re.match(r"^cpu[0-9]* ",l)}
def delta_cpu(x,y):
 d={}
 for k,v in x.items():
  if k not in y:continue
  z=[b-c for c,b in zip(v,y[k])]; total=sum(z)
  if total>0:d[k]={"busy_pct":100*(total-z[3]-z[4])/total,"softirq_pct":100*z[6]/total,"irq_pct":100*z[5]/total}
 return d
def monitor_cpu(s):
 chunks=re.split(r"^SAMPLE ",s,flags=re.M)[1:]
 rows=[]
 for chunk in chunks:
  try:rows.append((float(chunk.splitlines()[0].split()[0]),cpus(chunk)))
  except (IndexError,ValueError):pass
 if len(rows)<4:return {}
 t0=rows[0][0]
 active=[r for r in rows if 3<=r[0]-t0<=a.seconds+1]
 if len(active)<2:return {}
 result=delta_cpu(active[0][1],active[-1][1])
 return {"window_seconds":active[-1][0]-active[0][0],"cores":result}
route=False; server=None; qdisc=False; results=[]
try:
 save("harness.py",pathlib.Path(__file__).read_text())
 identity=remote(dut,"ubus call system board; cat /etc/image-provenance; cat /sys/devices/system/cpu/online; ip -br -4 addr; nft list ruleset; tc qdisc show").stdout
 save("identity.txt",identity)
 assert any(v in identity for v in ("iteration 11","iteration 12")) and "jdcloud,re-cs-02" in identity
 assert remote(dut,"cat /sys/devices/system/cpu/online").stdout.strip()=="0-3"
 enabled=remote(dut,"cat /sys/module/ath11k/parameters/nss_offload").stdout.strip()
 assert (enabled=="Y")== (a.mode=="nss"),"Unexpected radio acceleration mode"
 save("wrt-state.txt",remote(wrt,"ip -br -4 addr; iw dev; ip route show default; cat /proc/stat").stdout)
 remote(dut,"ip -4 addr show dev wan | grep -q '198.18.21.1/' || ip addr add 198.18.21.1/24 dev wan")
 if a.path in ["wired-nat","vlan-nat"]:
  src,dev,gw=("198.18.100.63","eth0.100","198.18.100.1") if a.path=="vlan-nat" else ("192.168.1.2","eth0","192.168.1.1")
  assert not run(["ip","route","show","198.18.21.154/32"]).stdout.strip()
  run(["sudo","ip","route","add","198.18.21.154/32","via",gw,"dev",dev,"src",src]);route=True
  client=["iperf3","-c","198.18.21.154","-p","5366","-B",src]
 elif a.path=="pppoe":
  remote(wrt,"ip route replace 198.18.200.1/32 via 192.168.1.1 dev br-lan")
  client=wrt+["iperf3 -c 198.18.200.1 -p 5364 -B 192.168.1.3 --bind-dev br-lan"]
 else:
  st=remote(wrt,"ip -4 -o addr show dev wlan0-sta").stdout
  sta=st.split()[3].split("/")[0]; assert sta.startswith("192.168.1.")
  mac=remote(wrt,"cat /sys/class/net/wlan0-sta/address").stdout.strip()
  if a.path=="wifi-nat":
   remote(wrt,"ip route replace 198.18.21.154/32 via 192.168.1.1 dev wlan0-sta")
   target="198.18.21.154";port="5366"
  else:
   target="192.168.1.2";port="5362"
   assert not run(["ss","-H","-lnt","sport","=",":5362"]).stdout.strip()
   server=subprocess.Popen(["iperf3","-s","-B",target,"-p",port],stdout=open(out/"server.log","w"),stderr=subprocess.STDOUT)
   time.sleep(1)
  client=wrt+["iperf3 -c "+target+" -p "+port+" -B "+sta+" --bind-dev wlan0-sta"]
  save("station-link.txt",remote(wrt,"iw dev wlan0-sta link; ip route get "+target+" from "+sta+" oif wlan0-sta").stdout)
 if a.qdisc:
  old=remote(dut,"tc qdisc show dev "+a.qdisc).stdout;save("original-qdisc.txt",old)
  assert all("noqueue" in l for l in old.splitlines())
  remote(dut,"tc qdisc replace dev "+a.qdisc+" root handle 100: tbf rate 100mbit burst 64kb latency 50ms");qdisc=True
 tests=[("tcp-up",[]),("tcp-down",["-R"])]
 if not a.quick:tests += [("tcp4-up",["-P","4"]),("tcp4-down",["-P","4","-R"]),("udp100-up",["-u","-b","100M","-l","1200","-w","4M"]),("udp100-down",["-u","-b","100M","-l","1200","-w","4M","-R"]),("udp300-up",["-u","-b","300M","-l","1200","-w","4M"]),("udp300-down",["-u","-b","300M","-l","1200","-w","4M","-R"])]
 if a.balanced:tests=[t for t in tests if t[0] in ["tcp-up","tcp-down","udp100-up","udp100-down"]]
 for name,opts in tests:
  print("CASE",name,flush=True)
  save(name+"-before.txt",remote(dut,snapshot,False).stdout)
  endpoint0=remote(wrt,"cat /proc/stat").stdout
  p43cpu0=pathlib.Path("/proc/stat").read_text()
  moncmd="for i in $(seq 1 "+str(a.seconds+5)+"); do echo SAMPLE $(cut -d' ' -f1 /proc/uptime); cat /proc/stat; if [ $((i % 5)) -eq 0 ]; then cat /sys/kernel/debug/*.nss/flows 2>/dev/null; cat /sys/kernel/debug/3a000000.ppe/flows; fi; sleep 1; done"
  with open(out/(name+"-cpu.txt"),"w") as mf:
   mon=subprocess.Popen(dut+[moncmd],stdout=mf,stderr=subprocess.PIPE,text=True)
   opts=["-J","-t",str(a.seconds),"-O","2","--connect-timeout","5000","--get-server-output"]+opts
   argv=client+opts if a.path in ["wired-nat","vlan-nat"] else client[:-1]+[client[-1]+" "+shlex.join(opts)]
   try:r=run(argv,False,timeout=a.seconds+20)
   except subprocess.TimeoutExpired:r=subprocess.CompletedProcess(argv,124,"test process timed out")
   save(name+".json",r.stdout);save(name+".exit",str(r.returncode))
   try:mon.wait(timeout=8)
   except subprocess.TimeoutExpired:mon.terminate();mon.wait(timeout=5)
  endpoint1=remote(wrt,"cat /proc/stat").stdout
  p43cpu1=pathlib.Path("/proc/stat").read_text()
  if a.path.startswith("wifi"):save(name+"-station-after.txt",remote(wrt,"iw dev wlan0-sta link").stdout)
  save(name+"-active-state.txt",remote(dut,snapshot,False).stdout)
  if a.qdisc:save(name+"-tc.txt",remote(dut,"tc -s -d qdisc show dev "+a.qdisc).stdout)
  try:d=json.loads(r.stdout)
  except ValueError:d={"error":r.stdout}
  row={"case":name,"mode":a.mode,"path":a.path,"radio":a.radio,"seconds":a.seconds,"qdisc":a.qdisc,"exit":r.returncode,"error":d.get("error"),"dut_cpu":monitor_cpu((out/(name+"-cpu.txt")).read_text()),"endpoint_cpu":delta_cpu(cpus(endpoint0),cpus(endpoint1))}
  if a.path=="pppoe":row["server_mode"]=os.environ.get("PPPOE_SERVER_MODE","unspecified")
  row["p43_cpu"]=delta_cpu(cpus(p43cpu0),cpus(p43cpu1))
  rawmon=(out/(name+"-cpu.txt")).read_text()
  nsslines=[l for l in rawmon.splitlines() if re.match(r"proto (6|17) .*installed 1 ",l)]
  row["nss_flow_observations"]=list(dict.fromkeys(nsslines))
  row["nss_packet_flow_observed"]=any(max([int(v) for v in re.findall(r"(?:rx|tx) (\d+)",l)]+[0])>1000 for l in nsslines)
  end=d.get("end",{});row["receiver"]=end.get("sum_received",{});row["sender"]=end.get("sum_sent",{})
  if a.path=="wifi-bridge":
   neighbor=run(["ip","neigh","show",sta,"dev","eth0"]).stdout;save(name+"-neighbor.txt",neighbor)
   row["wifi_mac_path_ok"]=mac.lower() in neighbor.lower()
  results.append(row);save("results.json",json.dumps(results,indent=2))
  print(name,round(row["receiver"].get("bits_per_second",0)/1e6,2),"Mbit/s",row["dut_cpu"],flush=True)
  if r.returncode or d.get("error"):raise RuntimeError("Failed case "+name)
 save("status","complete\n")
finally:
 if qdisc:remote(dut,"tc qdisc del dev "+a.qdisc+" root",False)
 if route:run(["sudo","ip","route","del","198.18.21.154/32","via",gw,"dev",dev],False)
 if a.path=="pppoe":remote(wrt,"ip route del 198.18.200.1/32 via 192.168.1.1 dev br-lan",False)
 if a.path=="wifi-nat":remote(wrt,"ip route del 198.18.21.154/32 via 192.168.1.1 dev wlan0-sta",False)
 if server:server.terminate();server.wait(timeout=5)
 save("dut-final.txt",remote(dut,"dmesg; cat /sys/devices/system/cpu/online; tc qdisc show",False).stdout)
 run(wrtbase[:-1]+["-S",sock,"-O","exit",wrtbase[-1]],False)
 print("RESULTS",out,flush=True)
