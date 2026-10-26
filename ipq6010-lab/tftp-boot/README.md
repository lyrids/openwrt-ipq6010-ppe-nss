# TFTP-first normal boot on JDCloud RE-CS-02

Current runtime and default source are restored to the pre-kexec iteration5
NSS Ethernet/MTU-guard image. Kexec experiments are suspended. Their source,
build records and failed CPU tests are retained as historical lab material;
the experimental patches and kernel features were removed from the active
build configuration.

## Installed boot sequence

The actual installed U-Boot is2016.01-3011049. Its original bootcmd was
bootipq and original bootargs was console=ttyMSM0,115200n8. Both were read
from the installed bootloader and from CRC-accepted fw_printenv output.
Installed Hush conditionals, TFTP loading, iminfo and bootm were exercised.

Persistent bootcmd is now:

    run boot_tftp; run boot_emmc

boot_tftp downloads the file to0x50000000, verifies FIT hashes with iminfo,
sets RAM-safe console arguments and boots config@cp03-c3. It only calls
bootm after successful transfer and FIT validation. If transfer, validation,
or bootm returns, original console arguments are restored and boot_emmc
runs the original bootipq path. TFTP setup initially kept bootdelay2; the later on-demand console setup
sets it to5 (see ../uboot-console/README.md). autostart=no prevents
implicit execution by the TFTP download command.

Exact variables: tftp-first.env and expected-environment.json.
restore-original.env restores the original named variables and deletes the
new names. It does not overwrite unrelated environment settings.
The environment mapping was verified as:
    /dev/mmcblk0p12 0x0 0x40000 0x20000
with PARTNAME=0:APPSBLENV. fw_setenv --script minimized writes.
Only the U-Boot environment was written; no firmware/rootfs partition,
bootloader binary or GPT was changed. No raw environment dump was copied.

## Persistent p43 server

Host management:ubuntu@192.168.21.63 over Wi-Fi.
Boot server:192.168.1.2/24 on eth0.
Router bootloader address:192.168.1.1.
Cable:p43 eth0 to router gigabit LAN1, verified during normal boot.

TFTP service:tftpd-hpa, enabled at host startup, bound to192.168.1.2:69.
Chroot root:/srv/tftp. No upload/create option is enabled.
Image:/srv/tftp/openwrt/jdcloud-re-cs-02.itb.
Current image:18858976 bytes, SHA256
b2b63a339a3e6496a198de3d39a14ca21d19214dc08c047f00a8da1953795c56.

A networkd drop-in for10-netplan-eth0.network adds the static address.
DHCP remains available on eth0, but its supplied routes and DNS are ignored;
management's default route remains Wi-Fi. Ethernet is not required for
network-online. The service restarts on failure. This keeps the boot-server
address stable across DHCP changes and router reboots.
Exact host configuration and setup commands are included in this directory.

## Verified

- A full Linux TFTP client download matched the expected SHA256.
- Installed U-Boot downloaded the complete FIT and verified kernel/FDT CRC32
  and SHA1 hashes.
- A missing filename selected the eMMC fallback branch without executing
  old RAM contents.
- Stopping the TFTP service while p43 remained online selected the fallback
  branch in about2seconds; the service was restarted afterward.
- An ordinary Linux reboot, with SCREEN released, generated a TFTP RRQ
  from192.168.1.1 and booted iteration5 into tmpfs root.
- A new boot ID, all four CPUs online, NSS enabled/active and absence of
  kexec support were checked.

The failure branches were tested without executing the full installed
eMMC operating system; bootipq is the unchanged existing fallback.
A completely powered-off/unreachable p43 has not been timed. ARP retry
behavior may differ from the tested stopped-service case. Do not infer
a universal2second fallback timeout.

## Image test workflow

1. Build and validate the board-specific initramfs FIT on Orb. Verify target,
   board DTB/config, firmware selection, hashes and image constraints.
2. Copy the validated FIT to p43 using the existing controller/SSH relay.
   Orb currently cannot directly reach the private LAN; the controller can
   stream bytes between SSH sessions without doing source development.
3. Run on p43:
       bash publish-tftp-image.sh /path/to/staged.itb EXPECTED_SHA256
   The helper checks SHA256/container magic, serializes updates, preserves
   the previous image and atomically replaces the stable served filename.
   It is a publication helper, not a substitute for the full image validator.
4. Reboot the router normally through SSH. Do not hold SCREEN.
5. Observe p43's service log and wait for router networking; check boot ID,
   image provenance, tmpfs root, NSS state and the required traffic tests.
   RAM boots generate fresh SSH host keys; use a fresh per-run known-hosts
   file and verify device/image identity over the isolated wired connection.

A kernel hang after bootm transfers control cannot be caught by the
bootcmd fallback. Fully unattended recovery from a bad running kernel
needs separately validated watchdog/boot-count/power-control handling.
No actual kexec transition is part of this workflow.

## Next extension

USB boot can be inserted between run boot_tftp and run boot_emmc after
checking the installed USB/filesystem commands, actual storage device,
image path and failure return behavior. USB is not configured yet.
