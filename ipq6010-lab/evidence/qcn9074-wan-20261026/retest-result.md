# QCN9074 WAN NAT retest after firewall reload

User-reported 20-second TCP results: outbound sender 394 Mbit/s, receiver 393 Mbit/s, 0 retransmissions; reverse sender 397 Mbit/s, receiver 396 Mbit/s, 292 retransmissions.

NSS acceleration confirmed: 38 captured HW_OFFLOAD conntrack records for client 192.168.1.163 to server 192.168.21.154:5201, with reply destination 192.168.21.138 confirming SNAT. User-test source ports 56628/56629 and 56651/56652. Installed Wi-Fi/WAN interface 32/5 rules and advancing firmware counters captured. Large per-rule counts include flow RX 639707 and reverse-direction TX 508839; shared monitor includes background client connections, so maxima are corroborating traffic-volume evidence, not exact iperf byte accounting.

Pass for functional accelerated Wi-Fi WAN NAT in both directions. Similar throughput to initial unaccelerated run does not establish speed benefit or CPU reduction. Reverse TCP retransmissions remain a performance caveat. Initial failure and firewall membership correction documented separately in initial-result.md. No firmware rebuild/reboot was required. QCN9074 remains active on channel 36.
