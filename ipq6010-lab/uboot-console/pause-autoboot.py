#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Pause the installed IPQ U-Boot from p43; does not reboot or change environment."""
import argparse,errno,json,select,socket,sys,threading,time
REQUEST=b"UBOOT:ABORT"
REPLY=b"UBOOT:ABORTED"

def request_pause(sock,destination,expected_peer,timeout,interval=.1):
    start=time.monotonic();deadline=start+timeout;next_send=start;sent=ignored=0
    while time.monotonic()<deadline:
        now=time.monotonic()
        if now>=next_send:
            try:
                sock.sendto(REQUEST,destination);sent+=1
            except OSError as error:
                if error.errno not in (errno.ENETDOWN,errno.ENETUNREACH,errno.EHOSTUNREACH,errno.ENOBUFS,errno.EAGAIN):
                    raise
            next_send=now+interval
        ready,_,_=select.select([sock],[],[],min(interval,max(0,deadline-time.monotonic())))
        if ready:
            data,peer=sock.recvfrom(256)
            if data==REPLY and peer==expected_peer:
                return {"acknowledged":True,"peer":list(peer),"packets_sent":sent,
                        "ignored_replies":ignored,"elapsed_seconds":round(time.monotonic()-start,3)}
            ignored+=1
    raise TimeoutError("No valid U-Boot abort acknowledgement before timeout")

def wait_telnet(host,port,timeout=12):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        try:
            with socket.create_connection((host,port),timeout=1) as tcp:
                tcp.settimeout(.5);data=bytearray()
                while time.monotonic()<deadline and len(data)<8192:
                    try:part=tcp.recv(4096)
                    except socket.timeout:continue
                    if not part:break
                    data.extend(part)
                    if b"U-Boot Telnet Console" in data and b"IPQ6018#" in data:
                        return {"telnet_ready":True,"address":host,"port":port}
        except OSError:pass
        time.sleep(.2)
    raise TimeoutError("Abort acknowledged, but U-Boot Telnet prompt was not verified")

def self_test():
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as server:
        server.bind(("127.0.0.1",0));peer=server.getsockname()
        def firmware():
            data,client=server.recvfrom(256)
            assert data==REQUEST
            server.sendto(b"WRONG-REPLY",client)
            server.sendto(REPLY,client)
        thread=threading.Thread(target=firmware);thread.start()
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as client:
            client.bind(("127.0.0.1",0))
            result=request_pause(client,peer,peer,2)
        thread.join(timeout=2)
        assert result["acknowledged"] and result["ignored_replies"]==1
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sink:
        sink.bind(("127.0.0.1",0))
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as client:
            client.bind(("127.0.0.1",0))
            try:request_pause(client,sink.getsockname(),sink.getsockname(),.15)
            except TimeoutError:pass
            else:raise AssertionError("Missing reply must time out")
    print("PASS: actual loopback UDP request/reply, invalid reply ignored, bounded timeout")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--interface",default="eth0")
    p.add_argument("--router",default="192.168.1.1")
    p.add_argument("--timeout",type=float,default=45)
    p.add_argument("--dry-run",action="store_true")
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:self_test();return
    if a.timeout<=0 or a.timeout>300:p.error("timeout must be in (0,300]")
    plan={"interface":a.interface,"broadcast":"255.255.255.255","destination_port":37541,
          "reply_port":37540,"router":a.router,"timeout":a.timeout,
          "behavior":"request on-demand failsafe/Telnet; does not reboot or resume"}
    if a.dry_run:print(json.dumps(plan,indent=2));return
    socket.if_nametoindex(a.interface)
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as udp:
        udp.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
        udp.setsockopt(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,a.interface.encode()+b"\0")
        udp.bind(("0.0.0.0",37540))
        result=request_pause(udp,("255.255.255.255",37541),(a.router,37540),a.timeout)
    result.update(wait_telnet(a.router,23))
    print(json.dumps(result,indent=2))
if __name__=="__main__":
    try:main()
    except (OSError,TimeoutError) as error:sys.exit(str(error))
