# QCN9074 station reconnect and accelerated WAN forwarding

User reports outbound sender 368 Mbit/s /31 retransmissions, receiver 367 Mbit/s; inbound sender 515 Mbit/s /286 retransmissions, receiver 514 Mbit/s. Sequential 20-second TCP tests after manual disconnect/reconnect.

Collected kernel/hostapd events confirm station 62:ba:80:c7:2d:19 disconnected and NSS peer id 11 released at router uptime 12237.568876, then new peer id 12 created at 12263.786082 and station associated. Approximately 26 seconds between events. Router wall-clock collection timestamps are retained in raw monitor; use uptime for ordering.

38 client HW_OFFLOAD records captured for new TCP connections from 192.168.1.163 to 192.168.21.154:5201, reply destination NAT 192.168.21.138. NSS installed interface 32/5 rules show advancing firmware counts, including flow RX 586254 and reverse RX 667231. Sample maxima are not exact iperf byte accounting.

Pass: old peer release, reassociation/new peer creation, and resumed hardware-accelerated WAN NAT. Does not prove cleanup of an actively transmitting old flow at disconnect because no traffic was requested during disconnection. Reverse TCP retransmissions remain a performance caveat; no Wi-Fi capacity or endurance claim. Current QCN9074 AP remains enabled on US channel 36 HE80. This completes the five-step manual Wi-Fi validation series.
