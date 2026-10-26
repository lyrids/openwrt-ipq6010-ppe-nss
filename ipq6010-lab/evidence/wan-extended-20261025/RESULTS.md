# Extended WAN validation, 2026-10-25

Iteration-5 pre-kexec RAM image. Wired tests force p43 192.168.1.2 through router WAN 192.168.21.138 to server 192.168.21.154:5201. Temporary host routes removed afterward.

30-second simultaneous TCP: receiver forward 889.410 Mbit/s, reverse 930.124 Mbit/s; retransmissions 60 and 474 respectively. Active NSS monitoring and HW_OFFLOAD records confirm acceleration. Shared monitor also includes subsequent DNAT traffic; distinguish tuples and interface direction.

Initial UDP failed with connection refused; not a router throughput result. After user reopened server UDP, see wan-udp-retry-20261025: 10-second 500 Mbit/s tests, payload 1200 bytes, forward receiver 499.937 Mbit/s, reverse 500.002 Mbit/s. Both zero reported loss, jitter 0.00932 / 0.01104 ms. Monitor has 50 HW_OFFLOAD records; NSS LAN1/WAN UDP rule firmware counts reached 520798 forward and 520911 reverse. p43 sender CPU was approximately one core at this packet rate; no higher-rate qualification claimed.

WAN-originated DNAT: m4m Wi-Fi 192.168.21.60 -> WAN 192.168.21.138:5261 -> p43 192.168.1.2:5262, source-restricted runtime nft NAT and accept rules. Forward 174.547 Mbit/s, reverse 118.161 Mbit/s, limited by m4m Wi-Fi. 44 HW_OFFLOAD monitor records with advancing NSS interface 5/1 counters. Exact temporary rule handles 184/185 removed and listener stopped; route removed.

Wi-Fi NAT: isolated subnet 192.168.77.0/24, m4m wlan0 192.168.77.60, forced server route over wlan0, management retained on LAN4 192.168.1.158. QCN9074 AP reported enabled on channels 36 and 149 but was absent from m4m scan results; cause unresolved, no throughput or general QCN9074 failure claim. Integrated IPQ6018 5GHz radio on US channel 149 associated at signal around -51 dBm. Ten-second TCP receiver throughput forward 146.614 Mbit/s, reverse 192.916 Mbit/s. Active monitor has 42 HW_OFFLOAD records and advancing Wi-Fi/WAN rule counters on NSS interfaces 33/5. Test SSID still contained QCN9074 from first attempt; interface/radio mapping, not SSID text, identifies integrated radio used. See wifi-integrated-20261025.

Restoration verified: m4m back on original LY-4300-A0 with 192.168.21.60; temporary credential file removed, original WPA service restarted. Router original wireless/network/firewall configs restored (all original APs disabled). p43 server route restored to Wi-Fi. Obsolete pre-existing host route to m4m via old VLAN100 removed to restore direct LAN management, recorded on p43. Router accessible, CPUs 0-3 online, low load. No reboot, firmware write, or bootloader environment modification.

Limits: short functional/performance runs, not endurance qualification. WAN and p43 LAN are 1Gb/s; 2.5Gb/s not tested. QCN9074 visibility needs further investigation. UDP and TCP retransmission/loss conclusions apply only to the recorded rates and durations.
