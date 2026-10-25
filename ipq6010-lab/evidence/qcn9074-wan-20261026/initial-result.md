# Initial QCN9074 WAN NAT test

User-reported 20-second TCP summaries: outbound sender 406 Mbit/s, 29 retransmissions, receiver 404 Mbit/s; reverse sender 366 Mbit/s, 181 retransmissions, receiver 365 Mbit/s.

Captured conntrack tuples prove source 192.168.1.163 -> 192.168.21.154:5201, translated reply destination 192.168.21.138. No HW_OFFLOAD or installed NSS rules appeared during the initial run; offers/pushed counters remained unchanged. This is functional NAT validation, not an accelerated-flow pass. Wi-Fi NSS datapath participation is separate from NSS flow acceleration.

Diagnosis: nft flowtable ft device list contained only lan1..4 and wan, omitting active phy2-ap0. After /etc/init.d/firewall reload, verified ft contains phy2-ap0 and flags offload. Retest required to establish actual acceleration. No image/source change made.
