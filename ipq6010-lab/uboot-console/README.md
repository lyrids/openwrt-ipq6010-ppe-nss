# On-demand U-Boot Telnet console

Implemented using the existing firmware's network-abort feature. No bootloader
binary, kernel, stdio device selection or TFTP/eMMC boot command was changed.

## Reviewed implementation

Installed U-Boot:2016.01-3011049, JDCloud RE-CS-02.
Source tag:26.08.16-14.22.36-3011049.
Pinned commit:3011049917bfb2fdc9a141196b3a94b63e58b96a.
Repository:https://github.com/chenxin527/uboot-qsdk12.5-build .

Relevant source under u-boot-2016/:
- net/net_abort.c: UDP37541 accepts exactly UBOOT:ABORT; reply is
  UBOOT:ABORTED on UDP37540. The abort handler enters httpd/failsafe.
- common/autoboot.c: polls Ethernet during the autoboot countdown.
- failsafe/failsafe.c: telnet_en enables Telnet when entering failsafe;
  this is the same path used by physical SCREEN recovery.
- net/telnetd.c: telnet_port selects the port; default23.

The help text mentions telnetd_enable, but the actual release implementation
uses telnet_en. The implementation and the installed strings were checked.
This is a Telnet command console; stdin/stdout/stderr remain serial@78B1000.

## Saved environment

    net_abort_en=1
    telnet_en=1
    telnet_port=23
    bootdelay=5

The previous three enable/port settings were undefined; bootdelay was2.
Applied with fw_setenv --script after saving only the named variables.
Exact apply and rollback scripts:console.env and restore-before-console.env.

bootcmd remains:

    run boot_tftp; run boot_emmc

Ordinary boots continue to TFTP/eMMC after the5-second autoboot window if
p43 sends no pause request. Telnet is not continuously listening during
an unpaused countdown; the selected behavior is network-triggered pause.
A pause deliberately holds U-Boot in its existing recovery event loop.

## Use from p43

Start this BEFORE rebooting the router, in one terminal:

    sudo -n python3 ~/openwrt-ramboot/uboot-console/pause-autoboot.py --interface eth0 --timeout 45

Reboot the running router normally from another terminal or automation task.
Do not hold SCREEN. The helper sends requests only through eth0, validates
the router's acknowledgement and waits for the U-Boot Telnet prompt. It
then exits and stops transmitting. It does not reboot or resume the router.

Connect:

    telnet 192.168.1.1 23

At the IPQ6018 prompt, inspect settings or resume the normal boot chain:

    version
    printenv bootcmd
    run bootcmd

Physical SCREEN recovery also provides Telnet at192.168.1.1:23. The console
exists only while U-Boot is running. It does not capture subsequent Linux
kernel output or the earliest ROM/SBL stages as a UART would.
Keep this unauthenticated bootloader console on the trusted wired test LAN.

The helper sends UDP broadcast with SO_BINDTODEVICE=eth0, so it does not
broadcast pause requests through management Wi-Fi. It accepts only the
exact reply from192.168.1.1:37540, has a bounded timeout, and checks the
actual U-Boot banner/prompt. Run it only when a deliberate pause is wanted;
do not install it as an always-transmitting service.

## Verification

- Real loopback UDP protocol test: invalid reply ignored, valid reply
  accepted; missing reply times out.
- Four persistent settings read back; original serial device selection and
  TFTP/eMMC bootcmd unchanged.
- Normal reboot with p43 helper, without SCREEN: acknowledgement received
  after15.915seconds/159 packets; U-Boot Telnet prompt verified.
- version/printenv/help telnetd executed through Telnet.
- run bootcmd resumed TFTP, returning to iteration5 RAM firmware with all
  four CPUs online and NSS active.
- A separate normal reboot with no pause helper validates automatic boot.
  The per-run evidence and validation.json record the final result.

No USB boot or kexec work was introduced. The pre-kexec image is retained.

## Restore these changes

Copy restore-before-console.env to the running router, then:

    fw_setenv --script /tmp/restore-before-console.env

This restores bootdelay2 and deletes the three new explicit settings.
Their original firmware defaults apply again; recovery Telnet was already
enabled by default before this change. The TFTP boot sequence is preserved.
