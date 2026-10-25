# Experimental ARM64 kexec support

The static kexec-tools2.0.32 utility was cross-compiled on Orb with OpenWrt GCC14.4/musl and executed on the router. SHA256:13516e64dfb8ba8aa9cb30f392d190ffa8822e28962daf08e5fcaec29238b3af. It is dynamically independent of router libraries. Compression libraries were disabled; feed it the uncompressed ARM64 Image extracted from the FIT.

The running iteration5 kernel returns ENOSYS for both rejection-only kexec syscall probes. Installing a tool cannot add these kernel features. One U-Boot RAM boot into a kexec-capable bootstrap kernel is required first.

The bootstrap configuration enables KEXEC, KEXEC_FILE, SUSPEND and HOTPLUG_CPU. On this pinned arm64 kernel, legacy KEXEC depends on PM_SLEEP_SMP; SUSPEND supplies it and selects CPU hotplug. FW_CACHE is explicitly disabled to avoid a newly exposed interactive Kconfig prompt. OpenWrt's packaged kexec utility is included in the bootstrap image.

NSS had only remove handling and EDMA had no shutdown callback. The bootstrap changes reuse NSS removal/halt for device shutdown and add EDMA shutdown that closes its netdevice, stops transmission and disables interrupts/DMA rings. ath11k AHB and PCI already have shutdown callbacks. These changes compile as part of the image; a successful cold boot or kexec load alone does not qualify hardware shutdown or warm reinitialization.

## Staged qualification

1. RAM boot the bootstrap image once using U-Boot recovery. Keep p43/m4m management Wi-Fi and physical recovery access.
2. Verify live kernel config, CPU hotplug support, NSS/Wi-Fi operation and the utility version. The invalid-argument probe should return EINVAL/EBADF or another implemented-syscall rejection instead of ENOSYS. Never probe by unloading a real pending image.
3. Extract the destination FIT into a bundle using extract-kexec-bundle.py and an independently verified source FIT SHA256. It produces an uncompressed Image with built-in initramfs and the target DTB. No separate initrd is needed for these OpenWrt RAM images.
4. Review target DTB differences and live bootloader fixups before loading. ARM64 file-based kexec uses the current kernel's DTB; legacy loading permits --dtb. A new target DTB may require preserving bootloader-supplied MAC/calibration/chosen data. Do not silently reuse it across incompatible hardware/layout changes.
5. Load only as a separate test, with a RAM-safe command line that excludes the installed eMMC root=PARTUUID argument. Check /sys/kernel/kexec_loaded, then unload the candidate. Loading reserves memory and is not a reboot. This step has not yet been performed.
6. Only after load/unload validation, schedule an explicitly authorized disruptive transition. Stop test traffic and network/Wi-Fi services, synchronize filesystems and execute the kexec transition with a recovery observer. Driver shutdown and secondary-CPU offlining must succeed.
7. Verify networking through p43 eth0, kernel identity, tmpfs root, firmware initialization, VLAN/NAT/PPPoE and both radios after the hop. Repeat a second hop before treating the workflow as usable.

kexec restarts the entire kernel and interrupts traffic. It does not preserve connections or provide a seamless driver reload. No actual load or hop has been attempted in this task. Warm reinitialization of this board's NSS/EDMA/PCIe/remoteproc hardware remains experimental.

Source references: Linux kernel/Kconfig.kexec and arch/arm64/{Kconfig,kernel/machine_kexec.c} in the pinned build; upstream userspace https://kernel.googlesource.com/pub/scm/utils/kernel/kexec/kexec-tools/+/refs/heads/main/kexec/arch/arm64/kexec-arm64.c .

## Built bootstrap artifact

Iteration6 RAM FIT:18959300 bytes, SHA2569532829d86a54e50f73e99666d92d68bb18fef7694b02cd12105aa6493a37277.
Orb path:/home/ly/projects/openwrt-dev/artifacts/nss-ethernet-kexec-20261025/images/openwrt-qualcommax-ipq60xx-jdcloud_re-cs-02-initramfs-uImage.itb.
A separate uncompressed Image/DTB bundle is under the same artifact directory's kexec-bundle/.
Offline checks passed, with385888 bytes of headroom in the6MiB kernel limit. Hardware boot, load/unload and a real warm transition remain untested. This image retains the iteration5 MTU software-fallback guard.

## Runtime result after iteration6 RAM boot

RAM boot passed. Both syscalls are implemented. File-based and legacy load/unload each passed, preserving boot ID and returning kexec_loaded to0. All three radios enumerated; NSS firmware and Ethernet backend started. No new throughput qualification was performed.

CPU3 offline succeeded, but re-online timed out and the restoration retry failed with PSCI -22. The kernel now marks a CPU as stuck and rejects new kexec loads with EBUSY. CPU3 remains offline; CPUs0-2 and wired networking/NSS startup remain operational. A normal reboot is needed to restore the previous CPU state; none has been performed. The exact cause in CPU/firmware warm startup is not yet established.

The boot/load-pending statements above describe the earlier build-time stage. Current detailed results and the failed hotplug test are in ../evidence/kexec-ramboot-20261025/. Actual kexec execution and driver warm reinitialization remain untested. Do not bypass the kernel's stuck-CPU check or offline other CPUs to repeat the failure.
