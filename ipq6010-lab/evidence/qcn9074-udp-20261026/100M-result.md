# QCN9074 UDP NAT at 100 Mbit/s

20 seconds per direction, 1200-byte UDP payload, client 192.168.1.163 to 192.168.21.154:5201 through router NAT.

User summaries: outbound receiver 99.9 Mbit/s, jitter 0.086 ms, loss 0/208342; sender 208343 datagrams. Reverse receiver 100 Mbit/s, jitter 0.179 ms, loss 0/208385; sender 208440 datagrams. Preserve differing sender/receiver counts as reported; zero loss refers to receiver's reported loss calculation, not equality of totals.

Captured 52 client UDP HW_OFFLOAD records and installed NSS interface 32/5 UDP rules. Firmware forward RX reached 208343 packets and reverse RX reached 208440 packets, matching respective sender totals and corroborating both accelerated directions. Functional accelerated UDP NAT passed at this offered rate and duration. Higher rates and endurance remain unqualified.
