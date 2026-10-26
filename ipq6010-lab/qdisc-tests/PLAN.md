# PPE/NSS qdisc qualification

Current source exposes PPE DSA TC setup for TBF/PRIO/ETS/MQPRIO/RED/GRED. This is capability inspection, not hardware qualification. EDMA conduit only delegates TC_SETUP_FT. Community Wi-Fi NSS adapter has no equivalent vendor nss_* qdisc API. Measure real behavior; no assumption that attaching a standard qdisc means hardware packets are scheduled through it.

Image includes tc-full, sched-core (TBF/HTB/HFSC), general schedulers, CAKE, PRIO/ETS/MQPRIO/RED/GRED and flower/police. No Qualcomm vendor modules. All modules built with the image; never mix packages with another kernel ABI.

Test Ethernet egress wan using p43 LAN ->WRT WAN21.154:5201, forced /32 route via DUT. Baseline then100M/200M root TBF with NSS active; correlate receiver rates, tc stats, NSS firmware counters and PPE queue/egress state. Remove qdisc and prove recovery. Test PRIO/MQPRIO hardware acceptance separately; acceptance alone is not QoS/fairness proof.

Test Wi-Fi egress phy2-ap0 with p43 ->WRT STA, explicit radio path verified by STA MAC. fq_codel attachment/forwarding first, then100M TBF and100M HTB+fq_codel or CAKE. Record whether hardware flow bypasses software scheduling. Root noqueue state is not itself a limitation on which qdiscs can be attached.

Software comparison must really bypass NSS flow installation. Prefer an isolated routed test alias (198.18.0.1/24 on DUT br-lan and198.18.0.2/24 on p43 eth0) with explicit station /32 route over wlan0-sta and p43 return /32 through198.18.0.1, leaving wired management1.3/1.132 intact. Source/destination/port-scoped nft accept rules before flow-add bypass IP flow offload for only the test. Confirm no HW_OFFLOAD for fresh control tuples and advancing Linux tc counters. Avoid claiming an inet rule disables the separate NSS bridge path.

For every mode: capture installation errors, offload indicators, configured versus measured rate, drops/backlog, CPU, firmware counters, topology, and restore exact prior qdisc/routes/aliases/rules. Do not replace qdiscs on p43 management Wi-Fi. Preserve WRT persistent STA and use its existing key only to reprovision the DUT after RAM boot; no credentials in image or Git. Keep previous known-good FIT available.
