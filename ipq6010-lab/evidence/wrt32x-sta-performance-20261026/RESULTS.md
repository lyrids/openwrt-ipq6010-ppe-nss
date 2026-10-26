# WRT32X persistent STA Wi-Fi performance, 2026-10-26

Follow-up: the UDP upload plateau was removed by increasing the WRT sender-buffer budget; see ../udp-isolation-20261026/RESULTS.md. Original measurements below remain unchanged.

Accepted full matrix: run-234158; sender controls: run-234951. Other run directories retain interrupted/missing-agent launcher attempts; they are not performance qualifications. Data uses endpoint-reported durations; raw endpoint timestamps are preserved.

Path: WRT32X wlan0-sta192.168.1.207 (MAC62:38:e0:c1:c5:23) ->QCN9074 US channel36 HE80 AP ->DUT LAN1 ->p43 Ethernet192.168.1.2:5360. WRT uses three-stream802.11ac VHT80, not an HE client. Both iperf3 endpoints version3.20. All cases explicitly bind source1.207 and SO_BINDTODEVICE wlan0-sta. Ordinary route would use WRT br-lan/LAN4; explicit binding and server neighbor matching STA MAC prevent bypass. NSS installed bridged31/1 rules and advancing firmware counters captured (291 installed-rule observations in accepted matrix).

| Test | Wi-Fi upload received Mbit/s | Wi-Fi download received Mbit/s | Sender TCP retransmissions up/down |
| --- | ---: | ---: | ---: |
| Single-stream TCP,20s each |432.259|834.828|0/0|
| Four-stream TCP,20s each |522.697|920.704|0/130|
| Simultaneous TCP,30s |290.554|470.225|0/1|

UDP1200-byte payload,10s each: requested100M upload sender6.069/receiver6.067 Mbit/s, zero reported loss, jitter0.251ms. Requested300M upload sender6.053/receiver6.051, zero reported loss, jitter0.251ms. These are not100/300M load passes: source under-delivers.

UDP download requested100M: received100.008 Mbit/s, loss12/104198 (0.01151%), jitter0.119ms. Requested300M: received298.113 Mbit/s, loss2029/312596 (0.64885%), jitter0.0266ms. Loss location not isolated; do not call the path loss-free.

Pacing controls: upload -b0 sender6.235/receiver6.233 Mbit/s, loss0; -b100M/64 burst sender7.665/receiver7.662, loss0. Neither removes the upload plateau. During advancing UDP upload firmware counts, sampled AP RX PHY rates877.5..975 Mbit/s; low offered application rate is not explained simply by a fixed low PHY rate. Root cause remains unisolated. Prior routed software-forwarding control also under-delivered, while NSS Wi-Fi datapath remained active; that earlier result does not isolate the entire Wi-Fi firmware/client path.

DUT normalized all-core CPU busy over accepted matrix samples mean0.555%, max2.363%. No BUG/Oops/Call trace/firmware-crash/watchdog markers in captured pre/post kernel logs. This is not a controlled CPU-savings comparison. Current station stays associated; default wired WAN route remains21.1. Dedicated p43 server5360 stopped automatically; no DUT/STA routing changes were made by this matrix.

Reproduction: launch wifi-lifecycle/wrt32x-sta-performance.sh on p43 through ssh -A (for nested WRT authentication). Default runs full matrix; udp-extra runs only sender controls. Check path-check.txt before interpreting results. Runtime setup is documented in wifi-lifecycle/wrt32x-persistent-sta.md. Current DUT iteration9 image unchanged.
