Experimental VLAN/NSS paired-flow fix, iteration 3.
Base 03803c78cd3b6968c20dab239c0c2f688692be63.
Plain single-tag VLAN routing no longer requires a PPPoE session.
The first Ethernet flow offer is copied into owned memory and returns EAGAIN;
no PPE steering is installed until NSS acknowledges the complete connection.
Both PPE directions are installed after that acknowledgement. Any parser,
firmware, allocation or PPE insertion failure removes both steering directions,
drops saved offers and withdraws NSS state. Firmware stop and block release
also free saved offers. Rule copies own their match data and redirect device refs.
Existing OpenWrt kmodloader startup fix and selected NSS 12.5 firmware retained.

Regression checks extract actual source functions into a userspace C harness.
Hardware operations/locking are mocked; AddressSanitizer and UBSan are enabled.
Cases: first-offer deferral, owned rule lifetime, second-offer rejection,
paired commit, paired destruction, second PPE insertion failure, allocation
failure, backend unavailable, plain VLAN independent of PPPoE, and unchanged
PPPoE+VLAN session behavior. These checks do not establish firmware acceptance
or packet forwarding on hardware.

For next RAM boot: confirm ethernet enabled=1 active=1; reproduce current
p43 eth0.100 -> router br-lan.100 -> m4 LAN4 path; verify firmware rule ACK,
PPE steering in both directions, firmware packet counters and TCP throughput.
Then test software fallback by writing 1 to
/sys/module/nss_wifi_drv/parameters/ethernet_fail_create before a NEW flow.
This injects one failure only after both directional offers are present.
No NSS rule or partial PPE entry should remain, and software TCP must continue.
Recheck untagged routing/NAT afterward.
No live module replacement or reboot has been performed.
