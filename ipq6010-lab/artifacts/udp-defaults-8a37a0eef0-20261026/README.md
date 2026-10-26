# Iteration 10: UDP defaults and TC qualification tools

Built on Orb from 8a37a0eef0; the qdisc harness was committed separately during compilation and is not included in the image. The OpenWrt cached release revision still displays d614d3f1a9; source-commit.txt and image-provenance identify this build. Kernel/NSS datapath is unchanged from iteration9. Standard scheduler modules, tc-full and the persistent socket profile are added.

FIT: 19219496 bytes, SHA256 3efc36b646da67cd4c99563f97a39b7b787ad3a1a9821bd6231bba72d996a7c4. Configuration config@cp03-c3, kernel load/entry 0x41000000, Linux6.18.55. No kexec or firmware flash. Image binaries stay outside Git.

Published atomically on p43 to the existing TFTP filename, with iteration9 retained as previous. U-Boot RRQ at 2026-10-26T04:55:28Z. Boot verified as jdcloud,re-cs-02 initramfs, iteration10, CPUs0-3, tc iproute2-6.18.0. Socket wmem_default/wmem_max/rmem_max all8388608 after boot. WRT32X independently rebooted to recover its mwlwifi firmware and retained the same sysctl profile on its UBIFS overlay.

Test SSID key is restored directly from the existing WRT32X STA configuration; no credential is included in the image or evidence. Stock eMMC fallback is untouched.
