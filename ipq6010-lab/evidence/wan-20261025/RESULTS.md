# WAN IPv4 NAT validation, 2026-10-25

Running iteration 5 pre-kexec MTU-guard RAM image, kernel 6.18.55.

Path: p43 192.168.1.2 on LAN1 -> router WAN 192.168.21.138 -> m4m 192.168.21.60 over its management Wi-Fi. A temporary /32 route on p43 forced traffic through the router. Matched iperf3 3.17.1 endpoints, port 5260, 10 seconds per direction.

- Forward received: 156.328 Mbit/s; reverse received: 170.794 Mbit/s. Both exited 0 without iperf errors.
- Active monitor includes 40 HW_OFFLOAD records and 40 installed LAN1/WAN (interface 1/5) rule records. Firmware flow/return RX/TX counters advanced; see monitor.txt. Conntrack reply destination 192.168.21.138 confirms SNAT.
- WAN negotiated 1000 Mbit/s full duplex. Partner advertised at most 1000; 2.5G capability is not qualified by this test.
- m4m Wi-Fi limits benchmark capacity. These rates are not router throughput ceilings.
- Temporary p43 /32 route removed, original Wi-Fi route restored. New m4m port-5260 server stopped. Router phase marker removed. Existing boot setup and other servers preserved.
- Router remained accessible, CPUs 0-3 online. No firmware, boot environment, or persistent firewall changes made.

Not covered: WAN-originated DNAT, WAN IPv6, 2.5G saturation, prolonged load, or switch/VLAN isolation on the shared upstream network.
