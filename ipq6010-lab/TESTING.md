# Hardware test procedures and interpretation

These procedures reconstruct the experiments recorded in evidence/. They change the isolated test interfaces and router forwarding configuration. Keep both servers' management Wi-Fi active and preserve their original addresses/routes before making changes. They are manual lab procedures, not an unattended harness.

## Topology

p43 (management192.168.21.63) eth0 -> gigabitLAN1; m4m (management192.168.21.60) end0 -> gigabitLAN4. Router root SSH is192.168.1.1. In the retained tagged configuration:
- p43 eth0 has no IPv4; eth0.100 is192.168.100.63/24.
- Router bridge vlan_filtering=1, lan1 VLAN100 PVID with tagged egress and no VLAN1.
- Router br-lan.100 is192.168.100.1/24; br-lan is192.168.1.1/24.
- lan4 remains VLAN1 PVID untagged; m4m end0 is192.168.1.158/24.
- Route on p43:192.168.1.158/32 via192.168.100.1 deveth0.100 src192.168.100.63.
- Both router L3 interfaces and underlying links must be restored toMTU1500 after MTU testing.

PVID classifies untagged ingress. It does not strip the tag from egress; LAN1 VLAN100 tagged egress is intentional. bridge vlan show, ip -d link and an endpoint tcpdump -eni eth0 vlan100 establish the actual configuration. Retain scoped firewall accepts for the test subnets; do not disable the whole firewall.

## Distinguish switch forwarding and NSS

For the VLAN100 L2 case, temporarily place LAN4 in tagged VLAN100 and give m4m end0.100 address192.168.100.60/24. Run iperf3 across100.63/100.60, capture VLAN100, remove/re-add LAN4 membership and probe VLAN101 isolation. Same-switch throughput and hardware FDB entries prove switch forwarding. Unchanged NSS flow counters mean this case is not evidence of NSS execution.

For NSS tests, route between different subnets through the router. Collect before/during/after:
- conntrack -L with OFFLOAD/HW_OFFLOAD state.
- NSS debugfs under /sys/kernel/debug/39000000.nss (rule interface pairs, pushed/rejected counts and firmware packet counters).
- PPE debugfs under /sys/kernel/debug/3a000000.ppe (steering entries, counters and drops).
- Linux netdev counters and endpoint /proc/net/snmp.
- iperf JSON, exit status and server log.

NSS firmware packet deltas matching the test, bidirectional rules, eligibility and hardware flow state together establish offload. Throughput or low CPU alone do not.

## TCP, UDP and NAT

Use matching iperf3 versions on both endpoints (the recorded matched tool was3.17.1). Start a server on m4m bound to the test address; run from p43 with explicit source binding:
    iperf3 -c192.168.1.158 -B192.168.100.63 -p5230 -t30 -J
Repeat with -R. For full duplex use --bidir -P4 with matching versions. Test plain routing, scoped SNAT, scoped DNAT and VLAN100/200 routing separately, with fresh connections and rule snapshots between cases. Firewall/NAT rules and counters used in each run are retained in the corresponding live-state files.

For UDP use -u, explicit -b/-l and matching tools. Run1400-byte700Mbps each direction, then128-byte50Mbps bidirectional with a1MiB socket buffer. Compare endpoint RcvbufErrors deltas before attributing packet loss to the router. Mixed tests start UDP first, then TCP and a parallel ping. Some simultaneous-start mixed runs failed control negotiation and remain inconclusive.

## Fault injection and cleanup

Set the nss-wifi-drv ethernet_fail_create module parameter to a bounded nonzero count to reject complete NSS rule offers. Establish fresh routed flows, verify Linux software forwarding continues without a partial PPE steering pair, restore the parameter to0 and verify a fresh flow re-offloads. Exact counter observations are in vlanfix-ramboot-20261025. This is destructive to test flows, so isolate the test interfaces.

Remove temporary firewall/NAT rules, stop only test PIDs, remove temporary addresses/routes and restore original VLAN membership. Preserve pre-existing iperf processes. Verify management reachability and test pings afterward.

## PPPoE

Stage1: m4m is PPPoE client over end0.100, p43 is PPPoE server over eth0.100, router switches taggedVLAN100. This stage is a connectivity baseline, not NSS routing.
Stage2: router is PPPoE client over br-lan.100 toward p43; server172.31.100.1/client172.31.100.2. m4m remains plainLAN1-subnet test source and is SNATed to the PPP address. Use an isolated no-auth server only for this test. Confirm NSS rule interface4/1, PPP session encapsulation and HW_OFFLOAD. Check MTU1492 DF and1493 failure, destroy session and confirm rule cleanup, reconnect and retest. Historical options and exact session/counter logs: pppoe-20261025. Iteration5 hardware rerun remains pending.

## IPv6 and live MTU

Use isolated IPv6 test prefixes on the two routed segments, preserving prior disable_ipv6 settings. Run TCP both directions and capture NSS counters. Use historical-scripts/udp6-mtu-probe.py with its documented arguments (--help) for oversize probes; the client deliberately ignores cached PMTU while fitting the ingress1500 link.

At1500 warm an existing flow, then lower the router's egress bridge/VLAN L3MTU to1400. Send IP-length1448 probes. Repeat with a fresh flow warmed using small packets. Iteration5 must decline NSS, leave no partial steering, and block all oversize probes through software. Restore BOTH br-lan and br-lan.100 to1500, establish a fresh flow and verify probes and NSS counters recover. Existing/fresh40-probe failures and29/29 recovery are in mtuguard-ramboot-20261025. Iteration4 fresh-flow failure is deliberately retained.

## RAM boot

Historical helper p43-ram-upload records the HTTP multipart /upload initramfs request and /result boot action. Enter U-Boot recovery with SCREEN during an explicitly authorized reboot. Verify the actual recovery address/port and verify uploaded size/hash before booting. Only initramfs RAM boot was used. No sysupgrade, flash write, GPT repair or bootenv change is part of these procedures.
