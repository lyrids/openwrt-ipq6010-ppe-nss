# Persistent WRT32X station setup

User-requested endpoint root@192.168.21.154. QCN radio hardware is QCN9074; active test SSID OpenWrt-RAM-test-QCN9074, BSSIDdc:d8:7c:54:83:f0, US/channel36/80MHz. WRT phy0 runs STA wlan0-sta, UCI wireless.qcn_sta, attached to DHCP networkwwan. Existing5GHz AP section disabled; other radios remained operationally down.

wwan: proto dhcp, defaultroute0, peerdns0, metric200, ipv60, delegate0; added to existing WAN firewall zone. Physical wired WAN21.154 via21.1 stays default. Existing br-lan management alias1.3/24 made explicit alongside25.1/24 to survive reload. Credentials supplied directly from DUT to endpoint over SSH, excluded from source/evidence.

Observed actual DHCP conflict: WRT's own LAN server offered25.207 to its STA through attached LAN1/DUT LAN4, competing with DUT1.207 offer. Saved DHCP config, set dhcp.lan.ignore=1 and restarted dnsmasq, then renewedwwan. Correct lease1.207/24 obtained fromDUT1.1;3/3 interface-bound Wi-Fi pings passed. This is a deliberate persistent LAN DHCP-server change, not a DHCP client fault. All pre-change network/wireless/firewall/DHCP files are locally backed up under/root/qcn-sta-backup-20261026 mode0700; never archive those credential-bearing files.

Both wired and wireless interfaces now have addresses on1/24. For measurements, source binding alone is insufficient; use -B192.168.1.207 --bind-dev wlan0-sta. Preserve wired control through1.3 with p43 source1.132. Existing br-lan arp_ignore1 and matching server neighbor MAC were verified; no ARP sysctl was changed.

Station config persists on WRT. DUT is still an initramfs RAM image; its opt-in AP/key must be provisioned again after a DUT reboot. Runtime credentials are not baked into the image. Rollback requires restoring local backup files and reloading network/firewall/services, retaining wired management as needed.
