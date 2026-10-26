# QCN9074 UDP NAT at 300 Mbit/s

20-second sequential runs, 1200-byte payload. Outbound sender 300 Mbit/s /625055 datagrams; receiver 299 Mbit/s, jitter 0.032 ms, loss 2/624648 (0.00032%). Reverse sender 300 Mbit/s /625184 datagrams; receiver 300 Mbit/s, jitter 0.038 ms, loss 0/625027.

Active installed NSS interface 32/5 UDP rules captured. Forward last captured high count 556247 RX/TX; final sender total not captured, so no exact count-match assertion. Reverse firmware RX/TX reached 625184, matching sender count. HW_OFFLOAD records also present. Both directions hardware-accelerated, outbound not strictly loss-free. Endpoint totals differ as reported. No source of the two lost datagrams established.

This completes the planned 100/200/300 Mbit/s sweep; stop increasing load and proceed to station reconnect/flow-cleanup validation. No saturation ceiling or endurance guarantee inferred.
