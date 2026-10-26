#!/usr/bin/env python3
"""Run on p43 with agent forwarding; all code is maintained on Orb."""
import concurrent.futures, datetime, json, os, pathlib, shlex, subprocess, time
root=pathlib.Path.home()/("openwrt-ramboot/mainline-qualification/qdisc-"+os.environ.get("MODE","nss"))
run=root/("run-"+datetime.datetime.now(datetime.timezone.utc).strftime("%H%M%S"))
run.mkdir(parents=True); (root/"latest-run.txt").write_text(str(run)+"\n")
kh=os.environ.get("DUT_KNOWN_HOSTS",str(pathlib.Path.home()/"openwrt-ramboot/iteration11-known-hosts"))
base=["ssh","-n","-o","BatchMode=yes","-o","ConnectTimeout=5","-o","StrictHostKeyChecking=yes"]
dut=base+["-o","UserKnownHostsFile="+kh,"root@192.168.1.1"]
wrt=base+["-b","192.168.1.132","-o","UserKnownHostsFile="+str(pathlib.Path.home()/"openwrt-ramboot/replacement154-lan-known-hosts"),"root@192.168.1.3"]
def cmd(argv,check=True,timeout=40):
 p=subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
 if check and p.returncode: raise RuntimeError(str(argv)+"\n"+p.stdout)
 return p

def remote(host,s,check=True): return cmd(host+[s],check)
def save(name,text): (run/name).write_text(text)
def snapshot(name,dev):
 s="date -u; tc -s -d qdisc show dev "+dev+"; tc -s class show dev "+dev+"; head -n 5 /proc/stat; cat /sys/kernel/debug/39000000.nss/flows; for f in egress queues queue_drops policer offload; do echo PPE-$f; cat /sys/kernel/debug/3a000000.ppe/$f; done; grep HW_OFFLOAD /proc/net/nf_conntrack"
 save(name,remote(dut,s,False).stdout)

def test(name,dev,argv):
 print("CASE",name,flush=True)
 snapshot(name+"-before.txt",dev)
 p=subprocess.Popen(argv,text=True,stdout=open(run/(name+".json"),"w"),stderr=open(run/(name+".stderr"),"w"))
 time.sleep(5)
 snapshot(name+"-active.txt",dev)
 try: rc=p.wait(timeout=30)
 except subprocess.TimeoutExpired: p.kill(); p.wait(); rc=124
 save(name+".exit",str(rc)+"\n")
 snapshot(name+"-after.txt",dev)
 if rc: raise RuntimeError(name+" failed: "+str(rc))
 d=json.loads((run/(name+".json")).read_text())
 if d.get("error"): raise RuntimeError(d["error"])
 rate=d.get("end",{}).get("sum_received",{}).get("bits_per_second",0)/1e6
 print(name,round(rate,2),"Mbit/s",flush=True)
 return rate

def install(name,dev,options):
 p=remote(dut,"tc qdisc replace dev "+dev+" root "+options,False)
 save(name+"-install.txt",p.stdout+"\nexit="+str(p.returncode)+"\n")
 return p.returncode==0

def delete(dev):
 p=remote(dut,"tc qdisc del dev "+dev+" root",False)
 save("delete-"+dev+"-"+str(time.time_ns())+".txt",p.stdout)
 time.sleep(1)

save("harness.py",pathlib.Path(__file__).read_text())
control="/tmp/qdisc-wrt-"+str(os.getpid())+".sock"
master=wrt.copy()
subprocess.run(master[:-1]+["-M","-S",control,"-o","ControlPersist=600","-fNT",master[-1]],check=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20)
wrt=master[:-1]+["-S",control,master[-1]]
server=None; route_added=False; touched=set()
try:
 identity=remote(dut,"ubus call system board; cat /etc/image-provenance; tc -V; tc qdisc show; sysctl net.core.wmem_default net.core.wmem_max net.core.rmem_max").stdout
 save("identity.txt",identity)
 assert "JDCloud" in identity and "iteration 11" in identity
 for dev in ["wan","phy2-ap0"]:
  q=remote(dut,"tc qdisc show dev "+dev).stdout
  save("original-"+dev+".txt",q)
  assert q.strip() and all("qdisc noqueue " in l for l in q.splitlines()), "Unexpected existing qdisc: "+q
 sta=remote(wrt,"ip -4 -o addr show dev wlan0-sta").stdout.split()[3].split("/")[0]
 assert sta.startswith("192.168.1.")
 save("client-path.txt",remote(wrt,"iw dev wlan0-sta link; ip route show default; ip -s link show wlan0-sta").stdout)
 common=["-J","-t","12","-O","2","--connect-timeout","5000"]
 if os.environ.get("SECTION") != "wifi":
  assert not cmd(["ip","route","show","198.18.21.154/32"]).stdout.strip(), "Existing test host route"
  cmd(["sudo","ip","route","add","198.18.21.154/32","via","192.168.1.1","dev","eth0","src","192.168.1.2"]); route_added=True
  save("wired-route.txt",cmd(["ip","route","get","198.18.21.154","from","192.168.1.2"]).stdout)
  wired=["iperf3","-c","198.18.21.154","-p","5366","-B","192.168.1.2"]+common
  test("ethernet-baseline","wan",wired)
  for rate in [100,200]:
   name="ethernet-tbf"+str(rate)
   touched.add("wan")
   if install(name,"wan","handle 100: tbf rate "+str(rate)+"mbit burst 64kb latency 50ms"):
    test(name,"wan",wired)
   delete("wan")
  for name,options in [("fq-codel","handle 150: fq_codel"),("cake100","handle 150: cake bandwidth 100mbit")]:
   if install("ethernet-"+name,"wan",options): test("ethernet-"+name,"wan",wired)
   delete("wan")
  test("ethernet-recovery","wan",wired)
  # Standard priority qdisc API acceptance; this is not a fairness test.
  if install("ethernet-prio","wan","handle 200: prio bands 3 priomap 2 2 2 2 1 1 1 1 0 0 0 0 0 0 0 0"):
   test("ethernet-prio","wan",wired)
  delete("wan")
 # Use a dedicated server. Never stop unrelated user listeners.
 assert not cmd(["ss","-H","-lnt","sport","=",":5362"]).stdout.strip()
 server=subprocess.Popen(["iperf3","-s","-B","192.168.1.2","-p","5362"],stdout=open(run/"wifi-server.log","w"),stderr=subprocess.STDOUT)
 time.sleep(1)
 wireless=wrt+["iperf3 -c 192.168.1.2 -p 5362 -B "+sta+" --bind-dev wlan0-sta -R "+shlex.join(common)]
 test("wifi-baseline","phy2-ap0",wireless)
 modes=[("fq-codel","handle 300: fq_codel"),("tbf100","handle 300: tbf rate 100mbit burst 64kb latency 50ms"),("cake100","handle 300: cake bandwidth 100mbit")]
 for name,options in modes:
  touched.add("phy2-ap0")
  if install("wifi-"+name,"phy2-ap0",options): test("wifi-"+name,"phy2-ap0",wireless)
  delete("phy2-ap0")
 if install("wifi-htb100","phy2-ap0","handle 300: htb default 10"):
  p=remote(dut,"tc class add dev phy2-ap0 parent 300: classid 300:10 htb rate 100mbit ceil 100mbit; tc qdisc add dev phy2-ap0 parent 300:10 handle 310: fq_codel",False)
  save("wifi-htb100-classes.txt",p.stdout+"\nexit="+str(p.returncode))
  if p.returncode==0: test("wifi-htb100","phy2-ap0",wireless)
 delete("phy2-ap0")
 test("wifi-recovery","phy2-ap0",wireless)
 save("peer-neighbor.txt",cmd(["ip","neigh","show",sta,"dev","eth0"]).stdout)
 # Locally originated downlink calibration uses the same Wi-Fi qdisc but no forwarded NSS flow.
 r=remote(dut,"test ! -e /tmp/qdisc-local-server.pid && iperf3 -s -D -B 192.168.1.1 -p 5363 -I /tmp/qdisc-local-server.pid",False)
 save("local-server-start.txt",r.stdout)
 if r.returncode==0:
  try:
   local=wrt+["iperf3 -c 192.168.1.1 -p 5363 -B "+sta+" --bind-dev wlan0-sta -R "+shlex.join(common)]
   test("wifi-local-baseline","phy2-ap0",local)
   if install("wifi-local-tbf100","phy2-ap0","handle 300: tbf rate 100mbit burst 64kb latency 50ms"): test("wifi-local-tbf100","phy2-ap0",local)
   delete("phy2-ap0")
  finally:
   remote(dut,"p=$(cat /tmp/qdisc-local-server.pid); case $(cat /proc/$p/comm) in iperf3) kill $p;; esac; rm -f /tmp/qdisc-local-server.pid",False)
 save("status","complete\n")
finally:
 for dev in touched:
  delete(dev)
  save("restored-"+dev+".txt",remote(dut,"tc -s -d qdisc show dev "+dev,False).stdout)
 if route_added: cmd(["sudo","ip","route","del","198.18.21.154/32","via","192.168.1.1","dev","eth0"],False)
 if server: server.terminate(); server.wait(timeout=5)
 cmd(master[:-1]+["-S",control,"-O","exit",master[-1]],False)
 save("dut-final.txt",remote(dut,"dmesg; cat /sys/devices/system/cpu/online; tc qdisc show",False).stdout)
 print("RESULTS",run,flush=True)
