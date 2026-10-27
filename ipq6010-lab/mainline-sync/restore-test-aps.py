#!/usr/bin/env python3
"""Restore ephemeral RAM-image APs without exporting their key to a developer host."""
import os,pathlib,subprocess,time
b=["ssh","-o","BatchMode=yes","-o","ConnectTimeout=5","-o","StrictHostKeyChecking=yes"]
d=b+["-o","UserKnownHostsFile="+os.environ["DUT_KNOWN_HOSTS"],"root@192.168.1.1"]
w=b+["-b","192.168.1.132","-o","UserKnownHostsFile="+str(pathlib.Path.home()/"openwrt-ramboot/replacement154-lan-known-hosts"),"root@192.168.1.3"]
if os.environ.get("WRT_CONTROL_SOCKET"): w=w[:-1]+["-S",os.environ["WRT_CONTROL_SOCKET"],w[-1]]
source=subprocess.Popen(w+["uci -q get wireless.qcn_sta.key"],stdout=subprocess.PIPE)
script="""set -e
umask 077
cat >/tmp/wifi-mainline.key
test -s /tmp/wifi-mainline.key
for n in 0 1 2; do
 uci set wireless.radio$n.disabled=0
 uci set wireless.radio$n.country=US
 uci set wireless.default_radio$n=wifi-iface
 uci set wireless.default_radio$n.device=radio$n
 uci set wireless.default_radio$n.network=lan
 uci set wireless.default_radio$n.mode=ap
 uci set wireless.default_radio$n.disabled=0
 uci set wireless.default_radio$n.encryption=psk2
 uci set wireless.default_radio$n.key="$(cat /tmp/wifi-mainline.key)"
done
uci set wireless.radio0.channel=149
uci set wireless.radio0.htmode=HE80
uci set wireless.default_radio0.ssid=OpenWrt-RAM-test-IPQ6018-5G
uci set wireless.radio1.channel=11
uci set wireless.radio1.htmode=HE20
uci set wireless.default_radio1.ssid=OpenWrt-RAM-test-IPQ6018-2G
uci set wireless.radio2.channel=36
uci set wireless.radio2.htmode=HE80
uci set wireless.default_radio2.ssid=OpenWrt-RAM-test-QCN9074
uci set wireless.radio1.disabled=1
uci set wireless.default_radio1.disabled=1
uci commit wireless
wifi reload
ip -4 addr show dev wan | grep -q '198.18.21.1/' || ip addr add 198.18.21.1/24 dev wan
"""
r=subprocess.run(d+[script],stdin=source.stdout)
source.stdout.close()
assert source.wait()==0 and r.returncode==0
time.sleep(8)
subprocess.run(d+["iw dev; cat /sys/devices/system/cpu/online; cat /sys/module/ath11k/parameters/nss_offload; cat /sys/module/nss_wifi_drv/parameters/ethernet_offload; cat /sys/kernel/debug/39000000.nss/boot"],check=True)
