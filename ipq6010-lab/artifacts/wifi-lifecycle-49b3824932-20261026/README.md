# Iteration 9 build and boot checkpoint

Source commit49b38249321ada6e3953993f65e3b4c08f899730, kernel6.18.55, pre-kexec iteration5 NSS datapath. Incremental unprivileged Linux/Orb build, 8 jobs, passed. FIT18857692 bytes, SHA2561f1cc86103aa7ead9dcdaf8c4b814ed9450c56383eed0de310dee5c435637f4e. Config config@cp03-c3 validated using dumpimage. Kexec disabled.

Only manifest differences from iteration5 are base-files revision metadata and firewall4 release2 ->3. Actual behavioral change is the debounced wireless-completion firewall reload; image provenance updated. Selected NSS firmware12.5 remains unchanged. FIT/sysupgrade binaries are outside Git in Orb workspace artifacts. Sysupgrade was not flashed.

Verified normal U-Boot TFTP RAM boot from p43, rootfs_type initramfs, revision r37715-49b3824932, all CPUs0-3 online. Trigger registered automatically from image. Two AP down/up cycles automatically removed/readded phy2-ap0 in offload flowtable; no manual firewall reload. AP channel36 HE80 US. Optional AP configuration is runtime, not baked-in Wi-Fi credentials.

Known-good iteration5 image retained as /srv/tftp/openwrt/jdcloud-re-cs-02-previous.itb on p43. Current TFTP filename remains openwrt/jdcloud-re-cs-02.itb. No boot environment changes, eMMC flash, or kexec.

Wired30-minute qualification recorded separately under evidence/iteration9-soak-20261026. After m4m failed, the user authorized WRT32X replacement; new-image Wi-Fi routing/NAT, active recovery and a separate30-minute mixed soak are recorded in replacement-wifi-20261026 and iteration9-mixed-20261026. Historical iteration5 results remain identified separately.
