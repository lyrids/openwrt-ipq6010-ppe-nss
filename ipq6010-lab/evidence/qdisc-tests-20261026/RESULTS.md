# PPE/NSS qdisc qualification — 2026-10-26

Before this run, attaching and enforcing qdiscs on the community NSS image had not been qualified. Iteration10 adds tc-full and matching standard scheduler modules; no vendor NSS driver or new NSS datapath patch is involved.

## Results

All rates are receiver TCP payload Mbit/s, 12-second measured interval after a 2-second omission. Each case creates fresh TCP flows. These are functional checks, not long-term or multiclient fairness qualification.

| Egress/path | Setting | Received | Interpretation |
|---|---|---:|---|
| WAN, routed/NAT Ethernet | noqueue baseline | 936.53 | reference |
| WAN, routed/NAT Ethernet | TBF100M | 94.87 | hardware cap enforced; tc offloaded flag and NSS installed-flow counters |
| WAN, routed/NAT Ethernet | TBF200M | 188.28 | hardware cap enforced |
| WAN, routed/NAT Ethernet | fq_codel | 936.56 | attaches; accelerated data bypasses Linux qdisc |
| WAN, routed/NAT Ethernet | CAKE100M | 936.25 | attaches, but does not cap NSS data |
| WAN, routed/NAT Ethernet | PRIO3 | 935.63 | hardware attachment/counters pass; priority arbitration not tested |
| WAN, routed/NAT Ethernet | removed/recovery | 936.46 | no lingering cap |
| QCN9074 downlink bridge | noqueue baseline | 854.87 | reference |
| QCN9074 downlink bridge | fq_codel | 840.61 | attaches; accelerated data bypasses Linux qdisc |
| QCN9074 downlink bridge | TBF100M | 845.69 | no effective cap on NSS-forwarded flow |
| QCN9074 downlink bridge | CAKE100M | 836.73 | no effective cap |
| QCN9074 downlink bridge | HTB100M + fq_codel | 849.36 | no effective cap |
| QCN9074 downlink bridge | removed/recovery | 851.61 | forwarding restored |
| Router-local QCN9074 downlink | noqueue | 834.80 | same radio/client, no forwarded NSS flow |
| Router-local QCN9074 downlink | TBF100M | 95.68 | Linux qdisc works when traffic traverses it |

TBF payload rates below the configured physical rate include framing/protocol effects. The test does not establish byte-perfect accounting or every burst/overhead setting.

The WAN TBF snapshot reports `offloaded` and tens of MB through TC counters while an installed NSS Ethernet rule advances. The Wi-Fi TBF snapshot counts only413 bytes/6 packets despite about846Mbit/s; installed NSS bridge31/1 firmware counters advance. The local Wi-Fi control counts63,363,292 bytes/41,864 packets during its active snapshot with overlimits, and enforces95.68Mbit/s. Together these distinguish queue bypass from an invalid Linux TBF setup.

## Topology and commands

Ethernet: p43 192.168.1.2 -> DUT LAN1 -> routed/NAT WAN192.168.21.138 -> WRT WAN192.168.21.154:5201. A temporary p43 /32 route via192.168.1.1 forces this path instead of p43 management Wi-Fi. WAN link is1G; 2.5G capacity is not qualified.

Wi-Fi: p43 server1.2:5362 -> DUT LAN1 -> QCN9074 phy2-ap0 -> WRT wlan0-sta1.144. WRT client uses `-B 192.168.1.144 --bind-dev wlan0-sta -R`. p43 neighbor1.144 matches station60:38:e0:c1:c5:22, not WRT wired MAC. Client is3SS VHT80, not an HE client. Local control uses DUT server1.1:5363 with the same station binding and reverse direction.

TC commands are preserved in run-060636/harness.py and the maintained qdisc-tests/run-qdisc-tests.py. Example: `tc qdisc replace dev wan root handle 100: tbf rate 100mbit burst 64kb latency 50ms`. Hardware PRIO uses the fixed supported3-band map: `2 2 2 2 1 1 1 1 0 0 0 0 0 0 0 0`.

Snapshots include TC/class counters, NSS firmware flow counters, PPE egress/queue/drop data and CPU counters before/during/after traffic. `tc` is iproute2-6.18.0; kernel6.18.55, image SHA3efc36b646da67cd4c99563f97a39b7b787ad3a1a9821bd6231bba72d996a7c4. Matching image modules are used; no foreign-ABI modules installed.

## Scope, interruptions and cleanup

run-052438 contains the completed Ethernet matrix. Its later Wi-Fi section timed out in SSH authentication before client execution; it is not a valid Wi-Fi measurement. The successful Wi-Fi-only continuation is run-060636, which reuses one authenticated SSH control connection and records status complete. The first harness launch rejected an iperf3 3.20 mode-specific timeout option before traffic; the option was removed before the archived accepted Ethernet run.

WRT mwlwifi firmware stalled after DUT AP outage (blocked iw and radar/channel command timeouts); evidence is wrt-client-firmware-stall.txt. The client recovered after reboot; its original management addresses and persistent socket defaults survived. This client recovery is separate from DUT NSS behavior.

Root qdiscs on wan and phy2-ap0 returned to original noqueue. Test host route, owned p43 server, router-local server and SSH control socket were removed. No DUT crash/Oops/panic markers appeared in the captured final kernel logs; all4 CPUs remain online. Test AP/STA and persistent8MiB socket defaults are retained. The stock eMMC fallback and bootloader configuration were not changed.

## Source interpretation and next work

The pinned community PPE source registers DSA port_setup_tc, whose TBF hook programs the physical PPE egress shaper. NSS-accelerated Ethernet frames still leave that shaped port; this is PPE hardware scheduling through standard TC, not an NSS firmware qdisc implementation. PRIO has a fixed supported hardware map. ETS/MQPRIO/RED/GRED are present in source and packaged, but their semantics were not qualified by this matrix.

The community Wi-Fi adapter has no corresponding standard TC-to-NSS scheduler integration. Linux TBF/HTB/CAKE attachment alone does not impose QoS on its bridge fast path. A working Wi-Fi SQM design needs a verified exclusion from acceleration into Linux scheduling, or a separately implemented firmware scheduler interface. Neither has been implemented by these tests. Wi-Fi routed/NAT QoS, uplink shaping, PPPoE/VLAN combinations, AQM latency and priority/fairness under contention remain separate qualification cases.
