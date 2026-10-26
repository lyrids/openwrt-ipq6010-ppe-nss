# UDP upload limit: endpoint socket-buffer diagnosis

DUT remains iteration9 with the same PPE/NSS driver/firmware. WRT32X STA wlan0-sta1.207 ->QCN9074 ->p43 LAN1.2:5360; both iperf3 3.20, payload1200 bytes. Ten seconds per case. Raw client results are under client/udp-isolation-20261026; p43 restoration and NSS monitor are at this directory root. Endpoint wall clocks differ; use per-test durations and kernel uptime rather than assuming synchronized timestamps.

## Isolating the path

| Default-buffer sender case | Sender Mbit/s | Receiver Mbit/s | Receiver loss |
| --- | ---: | ---: | ---: |
| Wired, requested100M |99.999|99.996|0%|
| Wi-Fi, requested100M |5.975|5.973|0%|
| Loopback, requested100M |100.000|99.999|0%|
| Loopback, unpaced |1091.384|1091.374|0%|
| Wired, unpaced |941.662|941.632|0%|

Same binary and host can send much faster without Wi-Fi. This is not a global application/CPU cap.

## Buffer controls

Original WRT wmem_default/wmem_max/rmem_max were180224 bytes (176KiB). p43 maxima were already4194304 bytes and remained at those values. Temporarily raised WRT maxima to4194304 to permit explicit larger test sockets. No JDCloud settings changed.

- iperf -w1M (actual Linux sndbuf/rcvbuf2MiB): Wi-Fi requested100M receiver99.962 Mbit/s, zero reported loss; unpaced receiver140.686 Mbit/s.
- Sender-only control: WRT wmem_default4MiB, no iperf -w; actual client sndbuf4194304 and rcvbuf180224. Wi-Fi requested100M receiver99.965 Mbit/s, zero loss. Receiver buffer was not requested larger. This isolates the local sender-memory budget as a causal constraint.
- iperf -w4M (actual Linux socket buffers8MiB): upload requested300M receiver299.878 Mbit/s, zero loss; reverse300.006 Mbit/s, zero loss; unpaced upload547.751 Mbit/s, zero loss.
- Restore original WRT values and rerun without -w: sender7.667/receiver7.663 Mbit/s, actual sndbuf180224. The low-rate plateau returns. Network/interface/firmware remained unchanged.

Larger send-buffer allowance removes the observed upload limitation. This is consistent with socket-memory backpressure on the WRT Wi-Fi transmit path. Exact driver queue/completion/ownership behavior was not traced; no driver bug or patch is claimed. Receive buffers were also larger in -w tests, so zero reverse loss is a conditional observation rather than an isolated receiver-drop diagnosis or endurance guarantee.

NSS remained active at the improved rates:85 captured bridged UDP rule observations on interface31/1; firmware flow RX reached571363 and reverse RX312766 packets. No new JDCloud image or kernel/NSS patch was required.

## Reproduction and restoration

Start dedicated p43 iperf3 server bound1.2:5360. Save original maxima on both endpoints; set net.core.wmem_max and net.core.rmem_max to4194304. Use the Wi-Fi client with -B1.207 --bind-dev wlan0-sta -u -b300M -l1200 -w4M -t10, then -R. Linux reports twice the requested -w buffer size. Avoid benchmarking against WRT's own21.154 local address.

Source helpers: wifi-lifecycle/udp-endpoint-controls.sh and udp-buffer-controls.sh. For the buffer helper, first create wmem-max.before/rmem-max.before from the current WRT values in /tmp/udp-isolation-20261026; it saves/restores wmem_default and restores maxima on exit. p43 maxima are restored separately. Use fresh backups on repeated experiments.

Verified final WRT wmem_default/wmem_max/rmem_max180224; p43 maxima4194304. Dedicated loopback and p43 servers stopped; STA stays connected and wired WAN default stays21.1. No sysctl defaults or maxima were persistently increased. Full-rate repeat tests require the temporary maxima and explicit -w setting again.
