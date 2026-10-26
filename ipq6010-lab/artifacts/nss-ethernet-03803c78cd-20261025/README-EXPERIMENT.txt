Experimental JDCloud RE-CS-02 PPE + NSS Ethernet RAM image, iteration 1
Base project: JuliusBairaktaris/openwrt-ppe-nss ppe-nss
Pinned base: 03803c78cd3b6968c20dab239c0c2f688692be63
Firmware feed: 1f60d7e9409930bbd298eae1831c5b76d21eb1d2 + selected-line packaging patch
No Qualcomm qca-nss-drv, ECM, vendor datapath driver or NSS qdiscs.

Added architecture:
- Linux netfilter/conntrack remains the authority for admitted routed flows.
- The existing PPE DSA flow block offers rules to a small optional NSS callback.
- SRCU protects the sleeping firmware callback and its unregister lifetime.
- Both flow ends must map to physical ports armed by the running NSS core.
- NSS receives the existing adapter's paired IPv4/IPv6/NAT/encapsulation rules.
- PPE installs BRIDGE steering to CPU/NSS, not competing routing/NAT rewrites.
- No netfilter core patches and no runtime replacement of net_device ops.
- The mode is selected at module load; source default is disabled.
- This RAM image explicitly enables ethernet_offload=1 in /etc/config/nss-wifi.
- A reservation survives firmware failure until reboot. No competing PPE NAT
  rule is admitted during firmware restart; software remains the fallback.
- Flow destruction, flow-block release, core halt and topology invalidation
  remove firmware state and/or steering entries.
- Ethernet counters and labelled rules are exposed in the NSS flows debugfs.

Scope:
This is a compile-validated experimental implementation, not a validated claim
of full acceleration. Existing code parses IPv4/IPv6 route, IPv4 NAT, single
802.1Q and PPPoE actions; actual firmware support on IPQ6018 must be tested.
QinQ/non-802.1Q ingress tags are rejected. Other unsupported combinations
fall back to software. Tagged NSS L2 bridge forwarding is still unsupported.
The earlier QCN9074 upload slowdown is not fixed by these changes.
Basic Ethernet L2 switching/VLAN enforcement remains PPE's responsibility.

Acceptance sequence (RAM only):
1. Verify new image identity, Ethernet module parameter=Y, NSS core up,
   wired SSH from both lab servers, and all radio handoffs.
2. Start with separate untagged LAN/WAN IPv4 subnets, no NAT. Generate TCP/UDP.
   Require NSS 'ethernet' rule installation, firmware packet counters, and
   corresponding PPE steering entries rather than route/SNAT/DNAT entries.
3. Repeat with IPv4 NAT; verify server-observed translated addresses and
   unchanged conntrack ownership; test rejected connections stay rejected.
4. Compare same image with ethernet_offload=0 at a separate RAM boot.
5. Test VLAN ingress/egress, overlapping addresses in isolated VLANs, and
   absence of cross-VLAN leakage before claiming VLAN support.
6. Add laboratory PPPoE; test reconnect, session change, MTU/MSS and teardown.
7. Test firewall reload/flow-block removal, link down/up, address/MTU/topology
   changes, and NSS halt/recovery. Require no stale NAT/steering entries.
8. Regress integrated and PCIe Wi-Fi separately; record the known uplink issue.

Image inputs: build-state, source-local.patch, firmware-feed-local.patch,
rootfs-overlay and patch hashes. Previous tested images remain archived.
No router reboot or flash is performed by this build.
