# Current status: iteration9 RAM runtime, TFTP-first normal boot

Kexec work remains suspended. Kernel/NSS source matches the pre-kexec08c04ac881 baseline; firewall4 adds a debounced netifd.wireless.done reload trigger. Iteration9 (built from49b3824932) runs with CPUs0-3 and active NSS. Normal reboot downloads the current image from p43 over TFTP, retaining original eMMC bootipq fallback. [Build and boot checkpoint](artifacts/wifi-lifecycle-49b3824932-20261026/README.md).

Automatic AP flowtable membership, active deauthentication/AP-restart recovery, a30-minute wired NAT soak, and a separate30-minute mixed wired/Wi-Fi soak passed. Receiver rates and limitations are in iteration9-* and replacement-wifi-* evidence folders. The WRT32X UDP upload plateau is now isolated to its local send-buffer budget: larger-buffer tests reached300 Mbit/s both ways and548 Mbit/s unpaced upload with NSS active; original limits restored. See evidence/udp-isolation-20261026.

[TFTP workflow/rollback](tftp-boot/README.md), [on-demand U-Boot Telnet pause](uboot-console/README.md), and [wireless lifecycle integration](wifi-lifecycle/README.md). Earlier experiments below are retained as historical records.

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

Historical pre-lifecycle RAM image: iteration5, nss-ethernet-mtuguard-03803c78cd-20261025, 18858976 bytes, SHA256 b2b63a339a3e6496a198de3d39a14ca21d19214dc08c047f00a8da1953795c56. This predates the archival commit. Full source diff/config are preserved. New builds have changed revision metadata and need not reproduce the identical image hash.

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
| Wi-Fi | User retested both5GHz SSIDs successfully on another client. Earlier QCN9074 upload problem was the original client's adapter bug. Iteration9 replacement-client results and limitations are in replacement-wifi-20261026; earlier user resolution in wifi-client-resolution-20261025.json |

Raw logs include failed attempts. Earlier validation-pending fields are historical; this table preserves baseline qualifications; the current status and iteration9 reports describe the latest run. CPU samples include idle periods. Long-term stability, QinQ and2.5G throughput are not qualified.

## Kexec bootstrap

An iteration6 bootstrap image and static ARM64 kexec-tools2.0.32 are now built. See [kexec details](kexec/README.md) for artifacts, tests and the staged qualification procedure. Offline validation and RAM boot passed, as did both kexec load/unload paths. CPU3 failed to restart after a hotplug test; its stuck-CPU guard now blocks further loads. Warm replacement remains untested. See evidence/kexec-ramboot-20261025.

## Archive policy

All custom OpenWrt source changes are committed in the source tree. historical-scripts/ contains helpers; artifacts/ contains text provenance, configs, patches, C harnesses, logs, manifests and hashes from every iteration; evidence/ contains measurements and failures; workspace/ records host setup. historical-source-guard.patch preserves a stashed earlier compile guard; do not apply it over current code.

Generated images, root filesystems, executables, firmware, toolchains and caches remain on Orb. omitted-generated-assets.json lists excluded artifact paths, lengths and SHA256. Private keys and device partition/calibration dumps are excluded. The known test Wi-Fi PSK is redacted in published copies; redactions.json records affected paths. Original checksum files describe originals; archive-sha256sums.txt verifies published copies.

Original OpenWrt/package licenses apply. New lab helper Python/shell/C code is GPL-2.0-only.

## CPU restart diagnostics: iteration7

The current source includes a temporary diagnostic kernel patch0990. Both
NSS-disabled host-control and NSS-enabled RAM images have built and passed
offline validation, including actual embedded configs and identical CPU
objects/kernel config. Neither diagnostic variant has been booted yet.
See cpu-restart/README.md and artifacts/cpu-restart-diag-20261025/.

The clean iteration6 RAM reboot restored all four CPUs and active NSS.
No further CPU hotplug attempt has been made. The next hardware test should
boot the host-control variant first using physical SCREEN recovery.
Default build overlay now identifies the NSS-enabled diagnostic variant.
These are diagnostic images, not a confirmed CPU restart correction.

## CPU restart control result and opt-in experiment

The iteration7 NSS-disabled control booted with four CPUs but reproduced
CPU3 restart failure. CPU_ON returned0; CPU3 remained ON_PENDING minutes
later and never reached the C checkpoints. NSS offload is not required to
trigger this failure. Current router state after testing:CPUs0-2, NSS off,
no kexec candidate loaded, management networking reachable.

An iteration8 board-scoped SCM warm-entry registration experiment has built
and passed offline checks. It is off by default and not yet runtime tested.
It is not a confirmed fix. See cpu-restart/WARM-ENTRY-EXPERIMENT.md.
No actual kexec transition or persistent firmware write has been performed.

## Wireless/WAN validation update (2026-10-26)

QCN9074 channel36 HE80: LAN bridge received432 Mbit/s outbound, reverse sender503; NSS bridge32/1 counters confirmed. WAN NAT received393/396 Mbit/s after refreshing flowtable Wi-Fi membership. Simultaneous60-second TCP250/166 Mbit/s, NSS active. UDP100/200/300 Mbit/s sweep accelerated; isolated0.1% inbound loss at200 was not reproduced over60 seconds;300 outbound lost2 datagrams. Reconnect released peer11, created12, resumed NSS NAT at367/514 Mbit/s. See qcn9074-* evidence. Wired WAN to192.168.21.154 reached936.5 Mbit/s each way; WAN negotiated1Gb/s, not2.5Gb/s.

Lifecycle fix and reproducible test AP recipe: [wifi-lifecycle](wifi-lifecycle/README.md). Iteration9 build retains pre-kexec iteration5 datapath and adds firewall completion-event trigger. Live repeated AP down/up membership tests pass; new image boot validation remains pending.

## Iteration9 RAM-boot qualification (2026-10-26)

Source49b3824932 produced FIT1f1cc86103aa7ead9dcdaf8c4b814ed9450c56383eed0de310dee5c435637f4e and successfully normal-TFTP RAM-booted. Automatic AP lifecycle membership passes. Thirty-minute wired NAT bidirectional899/924 Mbit/s; additional thirty-minute mixed wired NAT plus Wi-Fi routing saturated shared gigabit LAN at938/939 Mbit/s aggregate per direction, with four NSS rules active and mean normalized DUT CPU0.25%. No new kernel failure markers or WAN errors. WRT32X Wi-Fi/LAN short tests433/827 Mbit/s; proper deauth reconnected in3.7s and active TCP/NSS resumed. Retransmissions and endpoint UDP under-delivery are retained in reports, not hidden by a blanket loss-free claim. See iteration9-* and replacement-wifi-* evidence, and wifi-lifecycle/replacement-client.md. No kexec, bootloader rewrite, or eMMC firmware flash.

## Persistent WRT32X STA performance (2026-10-26)

Current DHCP STA1.207 on QCN9074, explicitly interface-bound: single TCP432/835 Mbit/s, four streams523/921, simultaneous291/470. NSS bridge firmware counters confirmed the Wi-Fi path. UDP down100/298 Mbit/s with0.012%/0.65% reported loss; upload stayed6..8 Mbit/s including unpaced/burst controls. Root cause unresolved; no full-rate UDP upload pass. See [matrix report](evidence/wrt32x-sta-performance-20261026/RESULTS.md) and [persistent STA setup](wifi-lifecycle/wrt32x-persistent-sta.md).

## UDP buffer diagnosis resolved (2026-10-26)

[Controlled endpoint tests](evidence/udp-isolation-20261026/RESULTS.md) isolated the WRT Wi-Fi send-buffer constraint. Sender-only4MiB default restored100M delivery; explicit -w4M allowed300M both ways with zero reported loss and548M unpaced upload. Restoring176KiB defaults returned the6..8M plateau. Original limits remain in place; use the documented temporary per-test buffer settings. DUT firmware unchanged. Earlier unresolved reports describe their original default-buffer runs.
