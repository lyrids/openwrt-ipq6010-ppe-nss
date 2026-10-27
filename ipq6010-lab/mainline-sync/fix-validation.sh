#!/usr/bin/env bash
# Run on p43; image deployment and AP setup are separate authorized operations.
set -euo pipefail
exec python3 - "$@" <<'PY'
import argparse, datetime, json, os, pathlib, re, shlex, socket, subprocess, time
p=argparse.ArgumentParser()
p.add_argument('--helpers',type=pathlib.Path,default=pathlib.Path.cwd())
p.add_argument('--seconds',type=int,default=8)
p.add_argument('--peer-cycles',type=int,default=3)
p.add_argument('--resume',type=pathlib.Path)
p.add_argument('--mode',choices=['nss','ppe'],default='nss')
p.add_argument('--profile',choices=['full','core'],default='full')
a=p.parse_args()
assert 3<=a.seconds<=30 and 1<=a.peer_cycles<=8
assert socket.gethostname().split('.')[0]=='p43','Run on p43 only'
assert os.environ.get('WRT_CONTROL_SOCKET') or os.environ.get('SSH_AUTH_SOCK'),'Provide the existing SSH control socket or forwarded agent'
known=pathlib.Path(os.environ['DUT_KNOWN_HOSTS']).expanduser()
assert known.is_file()
a.helpers=a.helpers.resolve()
for f in ['benchmark.py','select-client-radio.py']: assert (a.helpers/f).is_file()
base=['ssh','-n','-o','BatchMode=yes','-o','ConnectTimeout=5','-o','StrictHostKeyChecking=yes']
dut=base+['-o','UserKnownHostsFile='+str(known),'root@192.168.1.1']
wrt=base+['-b','192.168.1.132','-o','UserKnownHostsFile='+str(pathlib.Path.home()/'openwrt-ramboot/replacement154-lan-known-hosts'),'root@192.168.1.3']
if os.environ.get('WRT_CONTROL_SOCKET'):wrt=wrt[:-1]+['-S',os.environ['WRT_CONTROL_SOCKET'],wrt[-1]]
out=pathlib.Path.home()/'openwrt-ramboot/mainline-qualification'/datetime.datetime.now(datetime.timezone.utc).strftime('fix-validation-%Y%m%dT%H%M%SZ')
out=a.resume.resolve() if a.resume else out
out.mkdir(parents=True,exist_ok=bool(a.resume))
def run(v,timeout=35,check=True):
 r=subprocess.run(v,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
 if check and r.returncode: raise RuntimeError(r.stdout)
 return r
def remote(h,s,**kw): return run(h+[s],**kw).stdout
def save(n,s): (out/n).write_text(s)
def snapshot(n):
 save(n+'.txt',remote(dut,'date -u; cat /proc/uptime; cat /sys/devices/system/cpu/online; tc -s qdisc show; nft list ruleset; for f in /sys/kernel/debug/*.nss/boot /sys/kernel/debug/*.nss/flows /sys/kernel/debug/*.nss/wifili_rx; do echo FILE-$f; cat "$f"; done; dmesg',check=False))
def fw(flag):
 remote(dut,'set -e; uci set firewall.@defaults[0].flow_offloading='+str(flag)+'; uci set firewall.@defaults[0].flow_offloading_hw='+str(flag)+'; /etc/init.d/firewall reload')
def station(ap):
 bssid=remote(dut,'cat /sys/class/net/'+ap+'/address').strip().lower()
 link=remote(wrt,'iw dev wlan0-sta link; ip -4 -o addr show dev wlan0-sta')
 assert 'connected to '+bssid in link.lower()
 m=re.search(r'inet (192\.168\.1\.\d+)/',link); assert m
 mac=remote(wrt,'cat /sys/class/net/wlan0-sta/address').strip().lower()
 assert re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}',mac)
 return m[1],mac
rows=json.loads((out/'results.json').read_text()) if a.resume and (out/'results.json').exists() else []
server=None
qdiscs=set()
backups=[]
token='/tmp/fix-validation-'+str(os.getpid())
def traffic(label,ap):
 sta,mac=station(ap)
 paths=[('bridge','192.168.1.2',5362)] if a.profile=='core' else [('bridge','192.168.1.2',5362),('nat','198.18.21.154',5366)]
 for path,target,port in paths:
  if path=='nat': remote(wrt,'ip route add 198.18.21.154/32 via 192.168.1.1 dev wlan0-sta')
  try:
   for proto in ['tcp','udp']:
    for direction in ['up','down']:
     name=label+'-'+path+'-'+proto+'-'+direction
     if any(r['case']==name and r.get('ok') for r in rows):continue
     opts=['iperf3','-c',target,'-p',str(port),'-B',sta,'--bind-dev','wlan0-sta','-J','-t',str(a.seconds),'--connect-timeout','5000']
     if proto=='udp': opts+=['-u','-b','30M','-l','1200']
     if direction=='down': opts+=['-R']
     r=run(wrt+[shlex.join(opts)],timeout=a.seconds+20,check=False);save(name+'.json',r.stdout)
     d=json.loads(r.stdout); end=d.get('end',{});rx=end.get('sum_received',end.get('sum',{}))
     ok=r.returncode==0 and not d.get('error') and rx.get('bytes',0)>0
     rows.append(dict(case=name,mode=a.mode,ok=ok,exit=r.returncode,receiver=rx,error=d.get('error')))
     save('results.json',json.dumps(rows,indent=2));assert ok,name
     print(name,round(rx.get('bits_per_second',0)/1e6,2),'Mbit/s',flush=True)
  finally:
   if path=='nat':remote(wrt,'ip route del 198.18.21.154/32 via 192.168.1.1 dev wlan0-sta',check=False)
 assert remote(dut,'cat /proc/sys/kernel/random/boot_id').strip()==boot
 assert remote(dut,'cat /sys/devices/system/cpu/online').strip()=='0-3'
 snapshot(label)
def start_server():
 f=(out/'bridge-server.log').open('a')
 child=subprocess.Popen(['iperf3','-s','-B','192.168.1.2','-p','5362'],stdout=f,stderr=subprocess.STDOUT);f.close()
 time.sleep(1);assert child.poll() is None
 return child
try:
 assert '192.168.1.2/' in run(['ip','-4','addr','show','dev','eth0']).stdout
 assert '192.168.1.132/' in run(['ip','-4','addr','show','dev','eth0']).stdout
 routes=run(['ip','-4','route','show']).stdout;save('controller-routes-before.txt',routes)
 assert not remote(wrt,'ip route show 198.18.21.154/32').strip(),'Existing test route'
 assert not run(['ss','-H','-lnt','sport','=',':5362']).stdout.strip(),'Bridge port busy'
 assert remote(dut,'cat /sys/module/ath11k/parameters/nss_offload').strip()==('Y' if a.mode=='nss' else 'N')
 assert '198.18.21.1/' in remote(dut,'ip -4 addr show dev wan'),'Test WAN setup required'
 boot=remote(dut,'cat /proc/sys/kernel/random/boot_id').strip()
 for dev in ['wan','phy0-ap0','phy2-ap0']:
  q=remote(dut,'tc qdisc show dev '+dev);save('original-'+dev+'.txt',q)
  assert q.strip() and all('noqueue' in l for l in q.splitlines()),'Existing qdisc '+dev
 for host,config in [(wrt,'wireless'),(dut,'firewall')]:
  # PSK-containing snapshot stays on its original router and is never printed.
  backup=token+'-'+config
  remote(host,'set -e; test -z "$(uci changes '+config+')"; umask 077; cp /etc/config/'+config+' '+backup)
  backups.append((host,config,backup))
 save('test-settings.json',json.dumps(dict(mode=a.mode,profile=a.profile,seconds=a.seconds,peer_cycles=a.peer_cycles,boot_id=boot),indent=2))
 snapshot('before')
 for radio,ap in [('qcn','phy2-ap0'),('builtin5','phy0-ap0')]:
  save(radio+'-select.txt',run(['python3',str(a.helpers/'select-client-radio.py'),radio],timeout=140).stdout)
  station(ap)
  for path in ['wifi-bridge','wifi-nat']:
   name=radio+'-'+path+'-benchmark.log'
   if not (a.resume and (out/name).exists()):
    save(name,run(['python3',str(a.helpers/'benchmark.py'),'--mode',a.mode,'--path',path,'--radio',radio,'--balanced','--seconds',str(a.seconds)],timeout=4*(a.seconds+35)+60).stdout)
  server=start_server()
  for seq,flag in enumerate([0,1] if a.profile=='core' else [0,1,0,1]):
   fw(flag);traffic(radio+'-flow-'+str(seq)+'-'+str(flag),ap)
  for dev in ([ap] if a.profile=='core' else [ap,'wan']):
   for kind in (['tbf'] if a.profile=='core' else ['tbf','cake']):
    spec='tbf rate 100mbit burst 64kb latency 50ms' if kind=='tbf' else 'cake bandwidth 100mbit'
    qdiscs.add(dev);remote(dut,'tc qdisc replace dev '+dev+' root '+spec)
    # NSS may bypass host shaping; never assert a 100 Mbps cap.
    traffic(radio+'-'+dev+'-'+kind,ap)
    remote(dut,'tc qdisc del dev '+dev+' root');qdiscs.remove(dev)
    traffic(radio+'-'+dev+'-'+kind+'-removed',ap)
  for cycle in range(a.peer_cycles):
   sta,mac=station(ap);label=radio+'-peer-'+str(cycle+1)
   payload=shlex.quote(json.dumps(dict(addr=mac,reason=5,deauth=True,ban_time=0)))
   remote(dut,'ubus call hostapd.'+ap+' del_client '+payload)
   start=time.monotonic()
   while True:
    assert time.monotonic()-start<45,'Reassociation timeout '+label
    time.sleep(1)
    try:
     station(ap);peer=remote(dut,'iw dev '+ap+' station get '+mac)
     m=re.search(r'connected time:\s*(\d+)\s+seconds',peer)
     if m and int(m[1])<=time.monotonic()-start+2 and re.search(r'authorized:\s+yes',peer):save(label+'-reassociated.txt',peer);break
    except (RuntimeError,AssertionError):pass
   traffic(label+'-fresh',ap)
  server.terminate();server.wait(timeout=5);server=None
 snapshot('after')
 assert run(['ip','-4','route','show']).stdout==routes,'Controller route change'
 save('status','TRAFFIC PASS; 2.4 GHz waived. Review throughput, loss and kernel logs.\n')
finally:
 if server and server.poll() is None:server.terminate();server.wait(timeout=5)
 for dev in qdiscs:
  try:remote(dut,'tc qdisc del dev '+dev+' root',check=False)
  except Exception as e:save('cleanup-'+dev+'.error',str(e))
 errors=[]
 for host,config,backup in reversed(backups):
  try:
   reload='/etc/init.d/firewall reload' if config=='firewall' else 'wifi reload'
   remote(host,'set -e; uci revert '+config+'; cp '+backup+' /etc/config/'+config+'; '+reload+'; rm -f '+backup)
  except Exception as e:errors.append(config);save('cleanup-'+config+'.error',str(e))
 print('EVIDENCE',out,flush=True)
 if errors:raise RuntimeError('Restore failed; remote snapshots retained: '+','.join(errors))
PY
