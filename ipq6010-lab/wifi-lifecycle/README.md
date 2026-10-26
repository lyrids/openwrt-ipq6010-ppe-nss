# Wi-Fi flowtable lifecycle integration

The pinned wireless manager already emits service event `netifd.wireless.done` after its handler queue completes. Joining an AP to an already-up br-lan does not generate a new LAN ifup event, so firewall4 previously retained only Ethernet devices in its flowtable.

Patch firewall4's procd service trigger registration to reload on that existing completion event, debounced by 1000 ms. No kernel, NSS, netifd or vendor-driver change is required. A station reconnect does not invoke wireless setup, so it does not trigger a firewall reload. The trigger also follows completed teardown/reconfiguration. It rebuilds the normal firewall ruleset and may retire existing accelerated connections; established Linux conntrack state is retained.

After installing an updated init script live, run `/etc/init.d/firewall start` once to register the new procd trigger. Normal boot registers it automatically. Verify `/etc/init.d/firewall info`, enable the AP with `configure-test-ap.sh`, then check `nft list flowtable inet fw4 ft` for phy2-ap0 without manually reloading the firewall. Repeat AP down/up and inspect removal/readdition.

The optional AP recipe uses US channel36 HE80 and a per-router random WPA2 key under /tmp mode0600. It changes only the test radio and is not installed as an automatic image startup script. Read the key locally when needed; never archive it. Production credentials are not embedded.

Rollback the source patch or restore the original init script, then register the original service again. Kexec remains disabled. Hardware validation records reside in evidence/wifi-lifecycle-20261026.
