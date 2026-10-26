# QCN9074 simultaneous WAN TCP, 2026-10-26

User command iperf3 -c 192.168.21.154 -p 5201 --bidir -t 60. Client 192.168.1.163 on QCN9074 channel 36 HE80, NAT through WAN 192.168.21.138.

User summaries: outgoing receiver 250 Mbit/s (sender 250, 100 retransmissions); incoming receiver 166 Mbit/s (sender 166, 636 retransmissions). Aggregate simultaneous received rate 416 Mbit/s. Shared Wi-Fi airtime means these rates should not be expected to equal two independent one-way rates.

Captured 75 HW_OFFLOAD records for client/server TCP tuples within first 61 samples. Active NSS interface 32/5 rules advanced firmware counts, including flow RX 1285117 and reverse RX 851999 on respective flows. Monitoring includes background connections; maxima are not exact iperf byte accounting.

Router aggregate CPU busy across HW-active sampled intervals: mean 0.65%, maximum 1.25%, normalized over all four CPUs, computed /proc/stat deltas (first eight fields, idle+iowait counted idle). Monitoring itself adds load; active criterion may include background flows and is not exact test boundary alignment. No unaccelerated CPU control collected, so no quantitative savings claim.

Sampled signal -73 to -66 dBm. Router remained reachable, CPUs 0-3 online, no new errors in inspected kernel tail. Historical LAN4 down event predates this run. One-minute functional accelerated simultaneous forwarding passes; not a long-duration or loss-free qualification. AP remains enabled.
