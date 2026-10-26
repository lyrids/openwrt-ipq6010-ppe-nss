#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Run explicit commands in the installed U-Boot Telnet console."""
import argparse,socket,time,sys
p=argparse.ArgumentParser();p.add_argument("--host",default="192.168.1.1");p.add_argument("--timeout",type=float,default=20);p.add_argument("--allow-disconnect",action="store_true");p.add_argument("commands",nargs="+");a=p.parse_args()
sock=socket.create_connection((a.host,23),timeout=4);sock.settimeout(.3)
def receive(allow_disconnect=False):
    deadline=time.monotonic()+a.timeout;out=bytearray()
    while time.monotonic()<deadline:
        try:b=sock.recv(65536)
        except socket.timeout:continue
        except ConnectionResetError:
            if allow_disconnect:return bytes(out)
            raise
        if not b:
            if allow_disconnect:return bytes(out)
            raise RuntimeError("Console closed before prompt")
        out.extend(b)
        # The installed console sends plain text; tolerate basic negotiations.
        for command in (251,252,253,254):
            for option in range(40):
                if bytes([255,command,option]) in b:
                    reply=254 if command in (251,252) else 252
                    sock.sendall(bytes([255,reply,option]))
        if b"IPQ6018# " in out or out.endswith(b"IPQ6018#"):return bytes(out)
    if allow_disconnect:return bytes(out)
    raise TimeoutError("U-Boot prompt timeout; no further command sent")
print(receive().decode("utf-8","replace"),end="",flush=True)
for command in a.commands:
    print("\n>>> "+command,flush=True)
    sock.sendall(command.encode()+b"\r\n")
    print(receive(a.allow_disconnect and command==a.commands[-1]).decode("utf-8","replace"),end="",flush=True)
sock.close()
