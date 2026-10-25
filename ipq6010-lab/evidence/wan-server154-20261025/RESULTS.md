# WAN throughput to 192.168.21.154:5201

2026-10-25, iteration-5 pre-kexec RAM image. p43 source 192.168.1.2, LAN1 -> routed SNAT -> WAN 192.168.21.138 -> server. Temporary destination /32 route forced Ethernet/router path; removed after testing and original Wi-Fi route verified restored.

15-second single-stream TCP tests: forward receiver 936.516 Mbit/s, reverse receiver 936.521 Mbit/s. Forward sender 195 retransmits; reverse sender 0. Both JSON reports contain no error. These are near gigabit line-rate results, not loss-free qualification.

Active monitor recorded 62 HW_OFFLOAD entries and 62 LAN1/WAN interface-pair rule records, with advancing NSS firmware counters. This supports actual NSS forwarding, rather than merely switch forwarding or software flowtable status.

WAN remains negotiated at 1000 Mbit/s full duplex, partner advertising at most gigabit. p43 LAN1 is also gigabit. No 2.5G throughput claim is possible with this topology.

Router stayed accessible, CPUs 0-3 online. No persistent configuration changes.
