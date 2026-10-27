#!/usr/bin/env python3
"""Receive kernel-only diagnostic UDP on the isolated controller Ethernet IP."""
import argparse,datetime,pathlib,socket,time
p=argparse.ArgumentParser()
p.add_argument("--address",default="192.168.1.2")
p.add_argument("--port",type=int,default=6666)
p.add_argument("--seconds",type=int,default=1800)
p.add_argument("--output",type=pathlib.Path,required=True)
a=p.parse_args()
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind((a.address,a.port));s.settimeout(1)
a.output.parent.mkdir(parents=True,exist_ok=True)
deadline=time.monotonic()+a.seconds
with a.output.open("a",buffering=1) as f:
 while time.monotonic()<deadline:
  try:data,peer=s.recvfrom(65535)
  except socket.timeout:continue
  f.write(datetime.datetime.now(datetime.timezone.utc).isoformat()+" "+str(peer)+" "+data.decode("utf-8","replace").rstrip()+"\n")
