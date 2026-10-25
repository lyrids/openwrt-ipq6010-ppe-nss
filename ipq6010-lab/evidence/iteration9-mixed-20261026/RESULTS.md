# Iteration9 mixed wired NAT and Wi-Fi routing soak

Two concurrent bidirectional TCP tests, each1800 seconds, both exit0 with no iperf JSON error. Wired p43 source1.2 ->WRT WAN21.154:5201 forced via DUT1.1. Wi-Fi WRT source77.154 ->p43 LAN1.2:5360 forced over labsta0. This is concurrent Ethernet NAT plus Wi-Fi routing, not independent link capacity or continuous Wi-Fi/WAN NAT qualification.

Received rates: wired outbound368.518 Mbit/s, inbound834.230; Wi-Fi outbound105.204, inbound569.126 (Wi-Fi direction named relative to client station). p43 LAN transmit shared total937.645 Mbit/s, receive939.433 Mbit/s, consistent with saturation of its gigabit LAN link. Sender TCP retransmissions: wired20/4393, Wi-Fi4061/522. Stability pass, not loss-free or fairness qualification.

Four installed NSS data rules in179/182 samples, interface1/5 wired and32/1 Wi-Fi, advancing firmware counters throughout. Normalized all-core CPU busy on four-rule-active intervals mean0.251%, maximum0.855%. Samples include setup/teardown tails; not a controlled CPU-savings comparison.

MemAvailable samples538932..550552 KiB, first538932, last546936. Before/after SUnreclaim110436/110388 KiB. No monotonic memory loss observed; thirty minutes does not prove absence of leaks. Kernel before/after had no BUG/Oops/Call trace/firmware-crash/watchdog markers. CPUs0-3 online; WAN errors/dropped0 in both directions. Wi-Fi control ping10/10 under load, min/avg/max3.887/8.852/13.817ms.

Temporary p43 WAN-server /32 route removed by exit trap. Endpoint config and isolated Wi-Fi network cleanup documented in replacement-wifi report. Source and image unchanged during soak.
