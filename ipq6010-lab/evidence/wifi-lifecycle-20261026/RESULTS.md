# Wireless flowtable lifecycle live validation

Pinned wifi-scripts already emits netifd.wireless.done after queued handlers complete. Added a 1000 ms procd raw trigger to firewall4 init script; registered live with firewall start. No netifd/kernel/driver changes.

On iteration5 RAM kernel, with trigger installed: initial AP enable populated phy2-ap0. Two explicit wifi down radio2 / wifi up radio2 cycles removed then readded phy2-ap0 in nft flowtable ft, without manual firewall reload. US channel36 HE80 AP returned each time. Raw transcript live-test.txt includes procd trigger registration. Existing three backend mocked regression harnesses passed.

During preparation, router host key/uptime changed and same iteration5 image was verified using a separate per-run known-hosts file. Agent did not issue this reboot. Cause/user confirmation pending. m4m LAN4 cable was disconnected; user acknowledged and intends reconnection. Autonomous Wi-Fi/stress tests require reverified LAN management fallback.
