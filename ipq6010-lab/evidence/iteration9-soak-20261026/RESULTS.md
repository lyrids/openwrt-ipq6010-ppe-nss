# Iteration9 wired NAT soak

30-minute simultaneous TCP, p43 source1.2 ->DUT LAN1 ->WAN21.138 ->WRT32X WAN21.154:5201. Temporary p43 /32 route forces DUT traversal. iperf3 returned0, no JSON error, interval1800.008s. Receiver rates899.229 Mbit/s outbound,924.329 inbound. Sender retransmissions2333 and2321. About202.3/208.0 GB received. Not a loss-free claim.

NSS HW_OFFLOAD present in180/182 samples. Aggregate normalized CPU busy on HW-active intervals averaged0.208%, max7.210%, including deliberate AP-cycle activity. Available-memory samples541748..544948 KiB (first542192, last541748). Before/after SUnreclaim109004/109616 KiB. Small observed differences do not show an unbounded leak; this is only30-minute qualification. No BUG/Oops/Call trace/firmware-crash/watchdog markers in captured kernel logs; all CPUs0-3 remained online, WAN RX/TX errors0.

One AP down/up cycle deliberately occurred during active wired TCP: automatic flowtable removal/readdition, TCP continued without iperf failure. Under-load WAN ping10/10, min/avg/max1.751/2.463/3.273ms. Test route removed after completion. Monitor extends beyond the traffic interval; CPU criterion is HW-active sampled intervals, not exact boundary synchronization.
