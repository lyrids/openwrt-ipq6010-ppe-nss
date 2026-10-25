# Reverse UDP repeat, 200 Mbit/s, 60 seconds

User reports sender 200 Mbit/s, 1250157 datagrams; receiver 200 Mbit/s, jitter 0.078 ms, loss 0/1250046 (0%). Preserve the different endpoint totals; receiver-reported zero loss does not mean identical totals.

NSS interface 32/5 installed UDP rule reverse RX/TX counters reached exactly 1250157, matching sender count. Hardware offload remains confirmed. Prior 20-second 0.1% loss was not reproduced in this longer run; cause remains unlocated and cannot be declared fixed. This is a zero-reported-loss result for the measured interval, not a universal guarantee. Next rate: sequential 300 Mbit/s each way, 1200-byte payload, 20 seconds.
