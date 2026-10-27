#!/usr/bin/env python3
"""Run on p43. Keep WRT wired and WAN management, existing APs and PSK."""
import os,pathlib,shlex,subprocess,sys,time
choice=sys.argv[1]
settings={"builtin5":("radio0","OpenWrt-RAM-test-IPQ6018-5G","phy0-ap0"),"builtin2":("radio1","OpenWrt-RAM-test-IPQ6018-2G","phy1-ap0"),"qcn":("radio0","OpenWrt-RAM-test-QCN9074","phy2-ap0")}
assert choice in settings or choice=="stop"
base=["ssh","-n","-o","BatchMode=yes","-o","ConnectTimeout=5","-o","StrictHostKeyChecking=yes"]
wrt=base+["-b","192.168.1.132","-o","UserKnownHostsFile="+str(pathlib.Path.home()/"openwrt-ramboot/replacement154-lan-known-hosts"),"root@192.168.1.3"]
if os.environ.get("WRT_CONTROL_SOCKET"):wrt=wrt[:-1]+["-S",os.environ["WRT_CONTROL_SOCKET"],wrt[-1]]
dut=base+["-o","UserKnownHostsFile="+os.environ["DUT_KNOWN_HOSTS"],"root@192.168.1.1"]
def call(host,s,timeout=25):
 r=subprocess.run(host+[s],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
 if r.returncode:raise RuntimeError(r.stdout)
 return r.stdout
print(call(wrt,"uci set wireless.qcn_sta.disabled=1; uci commit wireless; wifi reload"))
time.sleep(3)
if choice=="stop":sys.exit(0)
dev,ssid,ap=settings[choice]
bssid=call(dut,"cat /sys/class/net/"+ap+"/address").strip()
assert len(bssid)==17
s="uci set wireless.qcn_sta.device="+dev+"; uci set wireless.qcn_sta.ifname=wlan0-sta; uci set wireless.qcn_sta.ssid="+shlex.quote(ssid)+"; uci set wireless.qcn_sta.bssid="+bssid+"; uci set wireless.qcn_sta.disabled=0; "
# Existing WRT 2.4GHz APs stay on their current channel11; STA must share it.
if dev=="radio1":s+="uci set wireless.radio1.channel=11; "
s+="uci commit wireless; wifi reload"
print(call(wrt,s))
for i in range(20):
 time.sleep(3)
 state=call(wrt,"iw dev wlan0-sta link; ip -4 -o addr show dev wlan0-sta")
 if "Connected to "+bssid in state and "inet 192.168.1." in state:
  print(state);sys.exit(0)
raise SystemExit("STA did not associate and lease; preserve logs before recovery")
