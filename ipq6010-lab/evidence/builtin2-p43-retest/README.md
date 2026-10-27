# Built-in 2.4 GHz retest, 2026-10-27

p43 uses its onboard brcmfmac radio as an IPv4 bridge client. Its independent
USB Ethernet address 192.168.21.130 carries management. The traffic server is
LY-WRT32X on router LAN4; it uses Ethernet, not its antenna-limited Wi-Fi.

US channel11, AP HE20, client single-stream HT20 at72.2Mbps. All six15-second
TCP/UDP cases passed in both NSS-on and matching-driver NSS-off mode.
UDP5/20Mbps reported zero loss in both directions. See summary.json for rates
and mean/max-core CPU busy percentages. These are single-run diagnostics.

Explicit interface binding, Ethernet arp_ignore=1 and the server's neighbor
MAC verify that return traffic targets p43 wlan0 rather than its LAN1 cable.
Wi-Fi power save is disabled during the run and restored afterward.

Previous LY-WRT32X 2.4 GHz runs were poor with and without NSS. The user reports
that client has only two5GHz antennas; those results do not qualify the
router's radio. This does not independently prove the precise antenna cause.

The first p43 run rejected transmit cases due to a receive-only iperf timeout
option. That harness issue was corrected and the complete campaign repeated.
Raw logs stay on Orb under evidence/mainline-qualification-20261026.
Temporary supplicant networks are removed; the PSK is used only in memory on
the authorized test client and is never included in evidence or this summary.
