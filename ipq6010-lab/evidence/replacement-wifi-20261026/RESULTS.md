# Iteration9 replacement-client qualification

Client WRT32X/phy0 802.11ac3SS at77.154, isolated Wi-Fi network77/24, QCN9074 US/channel36/HE80. LAN management1.3 via DUT LAN4, SSH bound to p43 source1.132. Explicit client /32 routes force test traffic over labsta0; p43 return route via DUT1.1. Both endpoints iperf3 3.20.

15-second TCP receiver rates: Wi-Fi -> wired LAN433.385 Mbit/s; reverse827.199 Mbit/s, no sender retransmissions in either direction. Wi-Fi -> p43 management-Wi-Fi address through physical WAN NAT69.693 Mbit/s; reverse56.060 Mbit/s. Both have no iperf error. The WAN test adds p43's management Wi-Fi leg; it is not a QCN9074 capacity measurement.

79 captured HW_OFFLOAD conntrack records for77.154 ->21.63, reply destination21.138 prove NAT. Installed NSS31/5 TCP firmware counts reached87857 and62920 packets on respective data directions. Wi-Fi/LAN routing31/1 counts also advanced to508519/875934. Logical NSS interface changed to32 after AP recreation; monitor actual mapping.

Requested100M UDP to WAN endpoint did not deliver that offered load: sender6.625 Mbit/s and receiver6.620 outbound; reverse sender62.303 and receiver62.215 Mbit/s. Receiver reported0 loss in both cases. Do not call this a100M pass. NSS31/5 UDP counts6902/65167 support forwarding at the observed rates. Under-delivery cause not isolated; no CPU saturation claim (recorded sender CPU low).

Active recovery:90-second bidirectional Wi-Fi/LAN TCP completed without iperf error through driver-level station deletion then AP restart; aggregate217/349 Mbit/s includes interruption. Station40 released,43 created after AP restart. Standalone iw station deletion is not normal over-the-air deauth and was not shown to reconnect independently. NSS32/1 rules resumed with advancing counters after AP restart and flowtable repopulated automatically.

Separate proper hostapd deauth during60-second bidirectional TCP: peer43 released at DUT uptime3593.436, peer44 created3597.104 (~3.668s), test completed without error at253.004/478.820 Mbit/s including interruption. NSS32/1 packet counters advanced again (over1.2M forward and2.3M reverse in samples). This qualifies recovery of active TCP forwarding after normal deauthentication.

Endpoint pre-existing empty board.json prevented Wi-Fi startup. OpenWrt board_detect regenerated valid model metadata, retained as a repair; original empty backup stays locally. Test configs/backups contain credentials and are not archived. Cleanup and30-minute mixed run documented separately.

Final UDP diagnostics: to wired LAN (removing p43's management Wi-Fi leg), default sender6.439/receiver6.436 Mbit/s, zero reported loss. 10ms pacing timer sender6.667/receiver6.666; no material improvement. Reverse LAN sender100.000/receiver99.979 Mbit/s, receiver loss0.04318%. Thus the outbound under-delivery is not specific to the added WAN-side Wi-Fi leg.

Scoped software control: UDP source55002 to1.2:5360 accepted before flowtable in forward chain, with symmetric reply rule. No OFFLOAD/HW_OFFLOAD flags captured; nft counted7,987,804 outbound bytes. Sender6.373/receiver6.370 Mbit/s, zero reported loss. Removed exact temporary handles898/899 in finally block. Under-delivery does not depend on NSS IP-flow offload in this case; Wi-Fi NSS datapath remained active, so its cause is still unisolated. Do not relabel it as a proven pure client bug.

Cleanup verified: endpoint original network/wireless files compare identical to backups; all original radios operationally down, test STA removed, runtime wired1.3 address retained and original iperf5201 preserved. Valid board.json repair retained, original empty backup local. DUT config restored to AP-on-LAN, phy2-ap0 automatically in flowtable; peer47 released after station cleanup. Temporary /32 routes and dedicated p43 servers5202/5360/5361 removed. No credential-bearing config backups were archived.
