# WRT32X replacement client recipe and qualifications

Endpoint: root@192.168.21.154, Linksys WRT32X, OpenWrt25.12.6, kernel6.12.112, mwlwifi phy0 (5GHz 802.11ac3SS). Physical WAN connects to21/24; LAN1 connects to DUT LAN4, br-lan has25.1/24 plus runtime1.3/24. p43 has1.2 static plus1.132 DHCP on DUT LAN1. Keep management SSH to1.3 bound to p43 source1.132, because the test explicitly routes destination1.2 over Wi-Fi.

Before configuration, back up endpoint /etc/config/network and wireless in a mode0700 directory under /tmp, keeping credentials on the endpoint only. Original radios were operationally down. /etc/board.json was pre-existing zero length, preventing all Wi-Fi setup with ucode JSON parse errors. Back up that empty file locally, then run /bin/board_detect; generated metadata identifies linksys,wrt32x. This repair is retained; the empty backup permits deliberate rollback. Do not archive raw wireless configs or keys.

DUT temporary test network: static192.168.77.1/24, assigned to LAN firewall zone; radio2 test AP is attached there instead of br-lan. QCN9074 stays US/channel36/HE80. Client: disable its existing phy0 AP, create a phy0 STA named labsta0 with static77.154/24. Provision the existing DUT key through SSH stdin, never stdout/logs. Add client host routes1.2/32 and21.63/32 via77.1 on labwifi; default WAN route and wired management stay unchanged. Make1.3/24 explicit in temporary LAN config to survive reload. Add p43 route77.154/32 via1.1 deveth0 src1.2. Verify `ip route get 192.168.1.2 from 192.168.77.154` returns labsta0; this prevents a wired bypass.

Use matched iperf3 3.20 on WRT32X and p43. Dedicated p43 listeners:1.2:5360 (wired LAN),21.63:5361 (management Wi-Fi). Run 15-second TCP forward/reverse from WRT source77.154 to each. WAN test must target p43, not the WRT's own21.154 local address. Capture conntrack SNAT reply destination21.138, HW_OFFLOAD and NSS interface31/1 or31/5 counters. Interface ID can change after AP recreation; do not assume32 permanently.

Recovery cases during active bidirectional TCP to1.2:5360:

- Diagnostic driver-level station deletion with `iw dev phy2-ap0 station del 60:38:e0:c1:c5:22`; this is not equivalent to hostapd deauthentication. Followed by AP down/up. Test completed, but standalone driver deletion was not demonstrated to recover before AP restart.
- Proper deauthentication: `ubus call hostapd.phy2-ap0 del_client '{"addr":"60:38:e0:c1:c5:22","reason":3,"deauth":true,"ban_time":0}'`. Peer43 released,44 created3.7s later; same60-second TCP session completed with new NSS counters.

Mixed30-minute run: p43 source1.2 -> WRT WAN21.154:5201 bidirectional TCP, forced by /32 route via DUT1.1; concurrently WRT source77.154 ->p43 LAN1.2:5360 bidirectional TCP. This exercises wired NAT plus Wi-Fi routing, sharing p43's gigabit LAN link. Monitor both1/5 and32/1 NSS data rules, CPU/memory/link errors. It does not establish independent maximum rates or continuous Wi-Fi-to-WAN NAT capacity.

Cleanup: restore endpoint's saved network/wireless files, reload network, restore original operational radio-down state; ensure runtime1.3/24 management remains. Retain the repaired valid board.json with original empty copy locally. Restore DUT network/wireless/firewall backup (test AP back on LAN), reload network/wireless and verify flowtable auto-populates. Remove only new p43 /32 routes and dedicated test listeners. Preserve original endpoint iperf server5201. Test AP credentials and all configuration backups stay out of Git.
