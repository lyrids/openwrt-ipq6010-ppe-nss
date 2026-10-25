# JDCloud RE-CS-02 / IPQ6010 PPE + NSS laboratory

This repository preserves the OpenWrt source history and the experimental Ethernet NSS backend tested on the JDCloud RE-CS-02. Community base: JuliusBairaktaris/openwrt-ppe-nss commit 03803c78cd3b6968c20dab239c0c2f688692be63; kernel 6.18.55. This is a downstream integration. Earlier official OpenWrt baseline: 5192094fd6fb7050ec3c859cf9f3f8fee5b10d91.

## Architecture and changes

Linux conntrack and netfilter flowtable submit both directions through the PPE callback. The community adapter constructs NSS Ethernet routing, NAT, VLAN and PPPoE rules. NSS firmware executes eligible flows; PPE entries steer traffic to that backend. This tree does not depend on Qualcomm qca-nss-drv, ECM or SSDK modules. The existing community ath11k/mac80211 Wi-Fi integration and its upstream history are retained.

The new backend owns a copy of the first direction and delays PPE steering until NSS accepts a complete pair. Partial installation, allocation failure, firmware rejection and destruction roll back both directions. SRCU protects callback lifetime. Interface/topology/address/MTU changes invalidate flows and release references. The package depends on kmod-nf-flow for flow_offload_teardown. Ethernet selection is latched at boot; the supplied overlay enables it. ethernet_fail_create is test injection and must be zero normally.

Reduced routed MTU uses a correctness guard: read live L3 MTU, invalidate existing flows on changes, and decline NSS when route MTU is below underlying IP capacity. Linux software forwarding then enforces MTU. Arbitrary reduced-MTU enforcement by NSS hardware is not established. Ethernet1500 and standard PPPoE1492 remain eligible.

The separate feed patch installs only selected NSS firmware12.5. Firmware binaries are fetched by the build system and excluded from this Git archive.

## Build and tests

See BUILDING.md and TESTING.md. Exact configs, feed pins, source patches, commands, regression harnesses and build logs are retained under artifacts/ and historical-scripts/. Historical scripts use fixed workspace paths and original base-commit assertions; preserve them as provenance rather than blindly re-running them on this committed tree.

Run current mocked regression tests from the repository root:

    python3 ipq6010-lab/tests/run-regressions.py

Requires Python3, GCC, ASan and UBSan. Mocked tests cover control flow; hardware evidence is separate.

Last tested RAM image: iteration5, nss-ethernet-mtuguard-03803c78cd-20261025, 18858976 bytes, SHA256 b2b63a339a3e6496a198de3d39a14ca21d19214dc08c047f00a8da1953795c56. This predates the archival commit. Full source diff/config are preserved. New builds have changed revision metadata and need not reproduce the identical image hash.

## Verification status

| Case | Result / evidence folder |
| --- | --- |
| Same-switch VLAN100 bridge | 938.76 / 938.95 Mbps; VLAN membership/isolation checks. Switch forwarding, not proof of NSS. trunk-vlan100-20261025 |
| IPv4 routing / SNAT | About937–941 Mbps; NSS firmware counters and HW_OFFLOAD. wired-nss-20261025 |
| Tagged PVID100 / rollback | Initial blackhole retained; paired-flow/VLAN fix restored forwarding, rejection injection falls back and recovers. pvid100-nss-20261025 and vlanfix-ramboot-20261025 |
| PPPoE + VLAN100 + SNAT | 932.86 / 872.14 Mbps; NSS counters/HW_OFFLOAD, teardown/reconnect,1492 passes/1493 fragmentation-needed. Iteration3 tested; iteration5 PPPoE hardware retest pending. pppoe-20261025 |
| Full duplex route/NAT/VLAN | Eleven qualification runs, IPv4 SNAT/DNAT and VLAN100/200. Some saturation retransmissions remain unexplained. extended-wired-20261025 |
| UDP | Buffered128-byte50Mbps bidirectional test zero loss; other tests have endpoint receive-buffer drops. Mixed simultaneous startup had control failures; UDP-first buffered run passed. Not unconditional loss-free qualification. extended-wired-20261025 |
| IPv6 TCP | 925.696 / 925.901 Mbps with NSS counters. IPv6 UDP bidirectional benchmark inconclusive. ipv6-mtu-20261025 |
| Reduced MTU | Iteration3 failed; iteration4 fixed existing flows only. Iteration5 guard blocked40/40 existing-flow and40/40 fresh oversize probes through software fallback; restore1500 delivered29/29 and NSS resumed. mtuguard-ramboot-20261025 |
| Wi-Fi | User retested both5GHz SSIDs successfully on another client. Earlier QCN9074 upload problem was the original client's adapter bug. No replacement measured rates supplied. wifi-client-resolution-20261025.json |

Raw logs include failed attempts. Earlier validation-pending fields are historical; this table and iteration5 summary describe latest status. CPU samples include idle periods. Long-term stability, QinQ and2.5G throughput are not qualified.

## Kexec bootstrap

An iteration6 bootstrap image and static ARM64 kexec-tools2.0.32 are now built. See [kexec details](kexec/README.md) for artifacts, tests and the staged qualification procedure. Offline validation passed; actual bootstrap boot and kernel replacement remain pending.

## Archive policy

All custom OpenWrt source changes are committed in the source tree. historical-scripts/ contains helpers; artifacts/ contains text provenance, configs, patches, C harnesses, logs, manifests and hashes from every iteration; evidence/ contains measurements and failures; workspace/ records host setup. historical-source-guard.patch preserves a stashed earlier compile guard; do not apply it over current code.

Generated images, root filesystems, executables, firmware, toolchains and caches remain on Orb. omitted-generated-assets.json lists excluded artifact paths, lengths and SHA256. Private keys and device partition/calibration dumps are excluded. The known test Wi-Fi PSK is redacted in published copies; redactions.json records affected paths. Original checksum files describe originals; archive-sha256sums.txt verifies published copies.

Original OpenWrt/package licenses apply. New lab helper Python/shell/C code is GPL-2.0-only.
