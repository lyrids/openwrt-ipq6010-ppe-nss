#!/usr/bin/env python3
import socket,sys,time,json
from pathlib import Path
mode,addr,port=sys.argv[1:4];port=int(port)
s=socket.socket(socket.AF_INET6,socket.SOCK_DGRAM);s.settimeout(.25)
# Verified from this VM's Linux UAPI headers: IPV6_MTU_DISCOVER=23,
# IP_PMTUDISC_PROBE=3. Ignore cached PMTU so oversized probes keep testing
# the router; every packet still fits the 1500-byte ingress link MTU.
s.setsockopt(socket.IPPROTO_IPV6,23,3)
if mode=="server":
 s.bind((addr,port));end=time.monotonic()+180
 while time.monotonic()<end:
  try:data,peer=s.recvfrom(4096)
  except socket.timeout:continue
  s.sendto(len(data).to_bytes(4,"big")+data[:80],peer)
  print(json.dumps({"received_bytes":len(data),"label":data[:80].decode(errors="replace").split("|")[:2]}),flush=True)
else:
 phasefile=Path(sys.argv[4]);s.bind((sys.argv[5],0));s.connect((addr,port))
 end=time.monotonic()+75;seq=0
 while time.monotonic()<end:
  phase=phasefile.read_text().strip()
  if phase=="stop":break
  seq+=1;label=f"{phase}|{seq}|".encode();size=256 if phase.startswith("warm") else 1400;data=label+b"x"*(size-len(label))
  rec={"phase":phase,"seq":seq,"sent_bytes":0,"acked":False}
  try:
   rec["sent_bytes"]=s.send(data);reply=s.recv(256)
   rec["acked"]=int.from_bytes(reply[:4],"big")==len(data) and reply[4:].startswith(label)
  except (OSError,socket.timeout) as exc:rec["error"]=str(exc)
  print(json.dumps(rec),flush=True);time.sleep(.1)

