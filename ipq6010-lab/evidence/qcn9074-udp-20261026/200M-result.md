# QCN9074 UDP NAT at 200 Mbit/s

User summaries, 20 seconds, 1200-byte payload. Outbound sender/receiver 200 Mbit/s, loss 0/416771, receiver jitter 0.118 ms. Reverse sender 200 Mbit/s /416949 datagrams; receiver 200 Mbit/s, loss 426/416835 (0.1%), jitter 0.047 ms.

Installed NSS interface 32/5 UDP rules captured, firmware forward RX/TX 416771/416771 and reverse RX/TX 416949/416949, matching sender counts at NSS accounting points. HW_OFFLOAD conntracks also captured. Both directions accelerated. Counters alone cannot locate receiver loss; radio delivery, host buffers, or other path components need isolation. End samples show station tx retries/failed 3/3 and signal -71 to -69 dBm, insufficient to attribute 426 datagrams to a particular cause. No loss-free inbound qualification at 200 Mbit/s. Repeat inbound at same rate for 60 seconds before increasing offered load.
