#!/usr/bin/env python3
"""Run on p43. Scoped VLAN/PPPoE setup and teardown; code maintained on Orb."""
import argparse,json,os,pathlib,re,shlex,subprocess,time
p=argparse.ArgumentParser();p.add_argument("action",choices=["vlan-up","vlan-down","pppoe-up","pppoe-down","firewall"]);a=p.parse_args()
known=os.environ["DUT_KNOWN_HOSTS"]
base=["ssh","-n","-o","BatchMode=yes","-o","ConnectTimeout=5","-o","StrictHostKeyChecking=yes"]
dut=base+["-o","UserKnownHostsFile="+known,"root@192.168.1.1"]
wrt=base+["-b","192.168.1.132","-o","UserKnownHostsFile="+str(pathlib.Path.home()/"openwrt-ramboot/replacement154-lan-known-hosts"),"root@192.168.1.3"]
out=pathlib.Path.home()/("openwrt-ramboot/mainline-qualification/network-tests-"+os.environ.get("MODE","nss"))
out.mkdir(parents=True,exist_ok=True)
def call(v,check=True,timeout=30):
 r=subprocess.run(v,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
 if check and r.returncode:raise RuntimeError(r.stdout)
 return r
def r(host,s,check=True):return call(host+[s],check)
def save(n,s):(out/n).write_text(s)
def handle(chain,comment,host=dut):
 s=r(host,"nft -a list chain inet fw4 "+chain).stdout
 return [re.search(r"# handle (\d+)",l).group(1) for l in s.splitlines() if comment in l]
def remove(chain,comment,host=dut):
 for h in handle(chain,comment,host):r(host,"nft delete rule inet fw4 "+chain+" handle "+h)
def accept_after_flow(expr,comment):
 s=r(dut,"nft -a list chain inet fw4 forward").stdout
 h=next((re.search(r"# handle (\d+)",l).group(1) for l in s.splitlines() if "flow add @ft" in l),None)
 # Software-only mode has no flow-add rule; insert before state dispatch.
 command="nft add rule inet fw4 forward position "+h if h else "nft insert rule inet fw4 forward"
 r(dut,command+" "+expr+" counter accept comment "+shlex.quote(comment))
if a.action=="vlan-up":
 before=r(dut,"ip -d link show br-lan; bridge vlan show").stdout;save("vlan-original.txt",before)
 assert "vlan_filtering 0" in before,"Unexpected existing VLAN filtering; inspect before modifying"
 r(dut,"bridge vlan add dev lan1 vid 100; bridge vlan add dev lan4 vid 100; bridge vlan add dev br-lan vid 100 self; ip link set br-lan type bridge vlan_filtering 1; ip link add link br-lan name br-lan.100 type vlan id 100; ip link set br-lan.100 up; ip addr add 198.18.100.1/24 dev br-lan.100")
 # Existing eth0.100 belongs to earlier experiments; retain it and its addresses.
 existing=call(["ip","link","show","eth0.100"],False).returncode==0
 save("p43-vlan-existing.txt",str(existing))
 if not existing:call(["sudo","ip","link","add","link","eth0","name","eth0.100","type","vlan","id","100"])
 call(["sudo","ip","link","set","eth0.100","up"])
 call(["sudo","ip","addr","add","198.18.100.63/24","dev","eth0.100"])
 r(wrt,"ip link add link br-lan name br-lan.100 type vlan id 100; ip link set br-lan.100 up; ip addr add 198.18.100.154/24 dev br-lan.100")
 accept_after_flow('iifname "br-lan.100" oifname "wan" ip saddr 198.18.100.0/24',"mainline-vlan")
 r(dut,'nft insert rule inet fw4 input iifname "br-lan.100" ip saddr 198.18.100.0/24 icmp type echo-request counter accept comment mainline-vlan')
 r(wrt,'nft insert rule inet fw4 input iifname "br-lan.100" ip saddr 198.18.100.63 icmp type echo-request counter accept comment mainline-vlan')
 save("vlan-state.txt",r(dut,"bridge vlan show; ip -br -4 addr; nft -a list chain inet fw4 forward").stdout)
 save("vlan-ping-router.txt",call(["ping","-c","3","-W","1","-I","198.18.100.63","198.18.100.1"]).stdout)
 save("vlan-ping-peer.txt",call(["ping","-c","3","-W","1","-I","198.18.100.63","198.18.100.154"]).stdout)
elif a.action=="vlan-down":
 remove("forward","mainline-vlan")
 remove("input","mainline-vlan")
 remove("input","mainline-vlan",wrt)
 r(wrt,"ip link del br-lan.100",False)
 call(["sudo","ip","addr","del","198.18.100.63/24","dev","eth0.100"],False)
 if (out/"p43-vlan-existing.txt").exists() and (out/"p43-vlan-existing.txt").read_text()=="False":call(["sudo","ip","link","del","eth0.100"],False)
 r(dut,"ip link del br-lan.100; bridge vlan del dev lan1 vid 100; bridge vlan del dev lan4 vid 100; bridge vlan del dev br-lan vid 100 self; ip link set br-lan type bridge vlan_filtering 0",False)
 save("vlan-restored.txt",r(dut,"ip -d link show br-lan; bridge vlan show").stdout)
elif a.action=="pppoe-up":
 # Requires tagged VLAN100 path created above. Dummy credentials are lab-only.
 options=out/"pppoe-options"
 options.write_text("noauth\nmtu 1492\nmru 1492\nnodefaultroute\nnoreplacedefaultroute\nnoipdefault\n")
 log=open(out/"pppoe-server.log","w")
 server=subprocess.Popen(["sudo","pppoe-server","-k","-F","-I","eth0.100","-L","198.18.200.1","-R","198.18.200.2","-N","1","-O",str(options)],stdout=log,stderr=subprocess.STDOUT)
 save("pppoe-server.pid",str(server.pid))
 save("pppoe-server-mode.txt","kernel\n")
 r(dut,"uci set network.labppp=interface; uci set network.labppp.proto=pppoe; uci set network.labppp.device=br-lan.100; uci set network.labppp.username=lab; uci set network.labppp.password=lab; uci set network.labppp.defaultroute=0; uci set network.labppp.peerdns=0; uci set network.labppp.ipv6=0; uci commit network; ubus call network reload; ifup labppp")
 state={}
 for i in range(25):
  time.sleep(1); state=json.loads(r(dut,"ubus call network.interface.labppp status").stdout)
  if state.get("up"):break
 assert state.get("up"),"PPPoE did not connect"
 dev=state["l3_device"];save("pppoe-device.txt",dev);save("pppoe-state.json",json.dumps(state,indent=2))
 accept_after_flow('iifname "br-lan" oifname '+shlex.quote(dev)+' ip daddr 198.18.200.1',"mainline-pppoe")
 r(dut,"nft add rule inet fw4 srcnat oifname "+shlex.quote(dev)+" ip daddr 198.18.200.1 masquerade comment mainline-pppoe")
 assert not call(["ss","-H","-lnt","sport","=",":5364"]).stdout.strip()
 server=subprocess.Popen(["iperf3","-s","-B","198.18.200.1","-p","5364"],stdout=open(out/"pppoe-iperf.log","w"),stderr=subprocess.STDOUT)
 save("pppoe-iperf.pid",str(server.pid))
elif a.action=="pppoe-down":
 for chain in ["forward","srcnat"]:remove(chain,"mainline-pppoe")
 r(dut,"ifdown labppp; uci delete network.labppp; uci commit network; ubus call network reload",False)
 for name,comm,sudo in [("pppoe-iperf","iperf3",False),("pppoe-server","sudo",True)]:
  f=out/(name+".pid")
  if not f.exists():continue
  pid=int(f.read_text());proc=pathlib.Path("/proc")/str(pid)/"cmdline"
  if proc.exists() and ("pppoe-server" if sudo else comm) in proc.read_bytes().replace(b"\0",b" ").decode():
   call((["sudo"] if sudo else [])+["kill",str(pid)],False)
elif a.action=="firewall":
 # Exercise a normal UCI deny rule for NEW connections, followed by removal.
 # Established-flow policy is stateful; do not claim a new deny revokes it.
 before=r(dut,"nft list ruleset; uci get firewall.@defaults[0].flow_offloading_hw").stdout
 save("firewall-before.txt",before)
 try:
  r(dut,"uci set firewall.labdeny=rule; uci set firewall.labdeny.name=Mainline-lab-deny; uci set firewall.labdeny.src=lan; uci set firewall.labdeny.dest=wan; uci set firewall.labdeny.dest_ip=198.18.21.154; uci set firewall.labdeny.dest_port=5366; uci set firewall.labdeny.proto=tcp; uci set firewall.labdeny.target=REJECT; uci commit firewall; /etc/init.d/firewall reload")
  call(["sudo","ip","route","add","198.18.21.154/32","via","192.168.1.1","dev","eth0","src","192.168.1.2"])
  time.sleep(2)
  result=call(["iperf3","-c","198.18.21.154","-p","5366","-B","192.168.1.2","-t","3","-J","--connect-timeout","3000"],False,timeout=8)
  save("firewall-denied.json",result.stdout)
  assert result.returncode!=0,"Firewall deny did not block new connection"
  save("firewall-deny-counters.txt",r(dut,"nft -a list chain inet fw4 forward_lan; cat /sys/kernel/debug/39000000.nss/flows").stdout)
 finally:
  r(dut,"uci -q delete firewall.labdeny; uci commit firewall; /etc/init.d/firewall reload",False)
  call(["sudo","ip","route","del","198.18.21.154/32","via","192.168.1.1","dev","eth0"],False)
 save("firewall-after.txt",r(dut,"nft list ruleset").stdout)
print("PASS",a.action)
