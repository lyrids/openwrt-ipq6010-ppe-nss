# QCN9074 Wi-Fi/LAN bridge test

Reviewed 2026-10-26 Asia/Singapore; directory retains collection-host date. Client 192.168.1.163 (62:ba:80:c7:2d:19) -> QCN9074 phy2-ap0, US channel 36 HE80 -> LAN1 -> p43 192.168.1.2:5202. Two sequential 20-second TCP runs.

Wi-Fi to LAN: wired receiver 432 Mbit/s over 20.10 seconds. LAN to Wi-Fi: wired sender 503 Mbit/s over 20.02 seconds, 221 TCP retransmissions. Client-side receiver result for reverse direction was not supplied; 503 is explicitly sender throughput.

Active monitor captured proto 6 v4 bridged if 32/1 installed 1 rules, with advancing firmware counters (e.g. flow RX 32603 -> 186639 -> 342115 packets), and bridge active entries. Wi-Fi vdev 32 packet/byte counters also advanced. Four bridge entries cumulatively pushed, subsequently removed as gone. This is evidence for NSS bridge acceleration rather than inferring it from throughput or generic Wi-Fi counters alone.

Signal varied roughly -81 to -72 dBm between sampled endpoints; these results do not establish radio capacity. Vdev TX fail counter rose 0 -> 221 and desc_fail rose 5656046 -> 27447098; counter meaning and relation to retries require source review, so no loss-free qualification. Station tx retry/fail counters remained 16 in endpoint samples, illustrating why those alone are insufficient.

server.log begins with an address-in-use error from a duplicate listener startup attempt; the existing dedicated port-5202 listener accepted and completed both tests. The monitor captured both active runs. AP and dedicated listener remain available for subsequent user-driven tests. No firmware or boot configuration changed.
