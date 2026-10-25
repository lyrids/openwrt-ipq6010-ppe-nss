Iteration5: live routed-MTU guard.
The adapter checks both the cached flowtable MTU and the live routed upper
device (DIRECT out.ifidx or NEIGH ifidx), separately from physical DSA ports.
Reduced routed MTUs below the underlying effective IP capacity are declined
before firmware rule creation. Linux handles PMTU and oversized packets.
Normal MTU1500 and standard PPPoE1492 remain eligible. Custom PPPoE MTUs below
1492 also fall back. This is a correctness fix using safe fallback, not proof
that closed firmware can enforce arbitrary per-route MTUs.
Kernel flow teardown on topology changes and paired-PPE rollback are retained.
Debugfs flows gains mtu_policy fields: link,route,rule,l3if,limited; host MTU
rejections are labelled mtu rather than firmware.

Next RAM boot:
1. Baseline IPv4/IPv6/VLAN routing with firmware counters.
2. Warm IPv6 UDP at1500, lower br-lan to1400:1448-byte IP probes must stop.
3. Warm a fresh small UDP flow at1400, then probe1448-byte IP packets:
   zero deliveries, mtu rejection counter increasing, no NSS/PPE steering
   for that flow, software path handles Packet Too Big.
4. Restore1500 and verify fresh NSS acceleration returns.
5. Recheck PPPoE1492+VLAN+NAT eligibility.
Hardware validation remains pending. Sources and sanitizer regressions saved.
