# Persistent UDP socket defaults

Profile99-udp-socket-buffers.conf sets net.core.wmem_default and wmem_max to8388608, rmem_max to8388608. Receive default and TCP-specific autotuning settings are not changed. Linux doubled iperf -w4M to8MiB actual; this profile makes that validated actual send budget the default for new UDP sockets. Buffer capacity is allocated as used, not all reserved at socket creation. Existing open sockets retain their prior settings.

WRT32X: install in /etc/sysctl.d on persistent UBIFS overlay; its enabled S11sysctl reads profiles at boot. Back up numeric original values and any prior profile locally under /root/udp-buffer-defaults-20261026. Apply only this profile with sysctl -p; avoid restarting the broad sysctl service during live networking.

AX6600: current root is initramfs. Apply the same live profile, and build it into the custom image via the tracked lab overlay and workspace files overlay. Publish the rebuilt FIT through the existing atomic p43 TFTP helper. This makes it persistent for future custom TFTP boots. The separate stock eMMC fallback is not modified. Runtime SSID configuration remains the existing opt-in RAM test setup.

Build wrapper build-udp-defaults records source commit/config/feed pins and image hashes. Adds matching standard TC scheduler modules for qdisc qualification; no NSS datapath or bootloader code change, firmware flash or kexec. Validate new no-window-option UDP sockets report8MiB send buffer. Live profiles apply immediately; the qdisc qualification image needs a normal TFTP RAM reboot before scheduler testing.

Rollback: restore the prior local profile (or remove this added profile) and numeric live values. Rebuild/republish prior overlay or use the previous FIT for AX custom-boot rollback. Never archive credential-bearing router configuration backups.
