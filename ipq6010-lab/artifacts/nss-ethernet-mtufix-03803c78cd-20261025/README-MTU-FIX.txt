Iteration4: routed MTU and topology invalidation.
NSS IPv4/IPv6 rule MTUs are capped by the opposite flowtable direction's
effective routed IP MTU, after PPPoE overhead handling. Bridged entries
retain physical-port handling. Missing/invalid MTUs fall back to software.
Topology invalidation tears down kernel flowtable caches using the exported
flow_offload_teardown API; queued offers for torn-down flows are rejected.
Package explicitly depends on kmod-nf-flow, which provides that API.
Sanitizer-backed regression checks passed; hardware validation pending.
Next boot: repeat baseline IPv4/VLAN/PPPoE and IPv6 throughput, then the
reproduced IPv6 UDP MTU1400 case. Oversized1448-byte IP packets must not be
delivered by either existing or freshly created offloaded flows. Restore
MTU1500 and confirm acceleration recovery before connection-churn stress.
Wi-Fi upload issue resolved by user retest: faulty original client adapter.
