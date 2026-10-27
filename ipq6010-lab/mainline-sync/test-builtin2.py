#!/usr/bin/env python3
"""Run on p43. Exercise built-in 2.4 GHz through a wired-managed WRT client."""
import argparse,datetime,json,os,pathlib,re,shlex,socket,subprocess,time
parser=argparse.ArgumentParser()
parser.add_argument("--sta-only",action="store_true")
parser.add_argument("--short",action="store_true")
parser.add_argument("--mode",choices=["nss","ppe"],default="nss")
a=parser.parse_args()
assert socket.gethostname().split('.')[0]=='p43'
home=pathlib.Path.home()/'openwrt-ramboot'
out=home/'mainline-qualification'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+a.mode+'-builtin2-wifi-bridge-retest'+('-sta-only' if a.sta_only else ''))
out.mkdir(parents=True)
known=pathlib.Path(os.environ.get('DUT_KNOWN_HOSTS',str(home/'iteration15-known-hosts')))
base=['ssh','-n','-o','BatchMode=yes','-o','ConnectTimeout=5','-o','StrictHostKeyChecking=yes']
dut=base+['-o','UserKnownHostsFile='+str(known),'root@192.168.1.1']
wbase=base+['-b','192.168.1.132','-o','UserKnownHostsFile='+str(home/'replacement154-lan-known-hosts'),'root@192.168.1.3']
external_control=os.environ.get('WRT_CONTROL_SOCKET')
sock=external_control or '/tmp/builtin2-'+str(os.getpid())+'.sock'
wrt=wbase[:-1]+['-S',sock,wbase[-1]]
def run(v,check=True,timeout=40):
 r=subprocess.run(v,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
 if check and r.returncode:raise RuntimeError(r.stdout or 'Remote operation failed')
 return r
def remote(h,s,**kw):return run(h+[s],**kw).stdout
def save(n,s):(out/n).write_text(s)
def stat(s):
 return {l.split()[0]:list(map(int,l.split()[1:9])) for l in s.splitlines() if re.match(r'^cpu[0-9]* ',l)}
def cpu(a,b,seconds):
 c={}
 for k,v in stat(a).items():
  d=[y-x for x,y in zip(v,stat(b)[k])];t=sum(d)
  if t:c[k]=dict(busy_pct=100*(t-d[3]-d[4])/t,softirq_pct=100*d[6]/t,irq_pct=100*d[5]/t)
 return dict(window_seconds=seconds,cores=c)
def snapshot(name):
 save(name+'.txt',remote(dut,'date -u; cat /proc/uptime; cat /proc/sys/kernel/random/boot_id; cat /sys/devices/system/cpu/online; cat /sys/module/ath11k/parameters/nss_offload; cat /sys/kernel/debug/39000000.nss/wifili_rx; cat /sys/kernel/debug/39000000.nss/flows; iw dev phy1-ap0 station dump; dmesg',check=False))
backups=[];server=None;receiver=None;control=False;rows=[]
token='/tmp/builtin2-retest-'+str(os.getpid())
try:
 if external_control:
  run(wbase[:-1]+['-S',sock,'-O','check',wbase[-1]])
 else:
  run(wbase[:-1]+['-M','-S',sock,'-o','ControlPersist=900','-fNT',wbase[-1]],timeout=20);control=True
 identity=remote(dut,'ubus call system board; cat /etc/image-provenance')
 assert 'jdcloud,re-cs-02' in identity and 'iteration 15' in identity
 save('identity.txt',identity)
 save('harness.py',pathlib.Path(__file__).read_text())
 save('test-settings.json',json.dumps(dict(mode=a.mode,sta_only=a.sta_only,short=a.short)))
 boot=remote(dut,'cat /proc/sys/kernel/random/boot_id').strip()
 assert (remote(dut,'cat /sys/module/ath11k/parameters/nss_offload').strip()=='Y')==(a.mode=='nss')
 assert remote(dut,'cat /sys/devices/system/cpu/online').strip()=='0-3'
 for host,label in [(dut,'dut'),(wrt,'client')]:
  backup=token+'-'+label
  remote(host,'set -e; test -z "$(uci changes wireless)"; umask 077; cp /etc/config/wireless '+backup)
  backups.append((host,backup))
 if not run(['ss','-H','-lun','sport','=',':6666']).stdout.strip():
  log=(out/'receiver.log').open('w')
  receiver=subprocess.Popen(['python3',str(home/'mainline-tools/netconsole-receiver.py'),'--seconds','1200','--output',str(out/'netconsole.log')],stdout=log,stderr=subprocess.STDOUT);log.close()
  time.sleep(1);assert receiver.poll() is None
 remote(dut,'echo BUILTIN2_RETEST_BEGIN >/dev/kmsg; uci set wireless.radio1.disabled=0; uci set wireless.radio1.country=US; uci set wireless.radio1.channel=11; uci set wireless.radio1.htmode=HE20; uci set wireless.default_radio1.disabled=0; uci commit wireless; wifi reload radio1')
 time.sleep(6)
 if a.sta_only:
  stations=remote(wrt,'for d in wlan1-1 wlan1-2; do iw dev "$d" station dump 2>/dev/null; done')
  assert not re.search(r'^Station ',stations,re.M),'Client AP has associated stations'
  remote(wrt,"""set -e
for s in default_radio1 wifinet3 wifinet4; do
 if [ "$(uci -q get wireless.$s.mode)" = ap ] && [ "$(uci -q get wireless.$s.device)" = radio1 ]; then
  uci set wireless.$s.disabled=1
 fi
done
uci commit wireless
wifi reload""")
  time.sleep(3)
 save('ap.txt' ,remote(dut,'iw dev phy1-ap0 info; ip -4 addr show dev br-lan'))
 env=os.environ.copy();env['WRT_CONTROL_SOCKET']=sock;env['DUT_KNOWN_HOSTS']=str(known)
 result=subprocess.run(['python3',str(home/'mainline-tools/select-client-radio.py'),'builtin2'],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=110)
 save('association.txt',result.stdout);assert result.returncode==0,result.stdout
 state=remote(wrt,'iw dev wlan0-sta link; ip -4 -o addr show dev wlan0-sta')
 save('client-link.txt',state)
 address=re.search(r'inet (192\.168\.1\.\d+)/',state);assert address
 address=address[1]
 save('ping.txt',remote(wrt,'ping -I wlan0-sta -c 3 -W 2 192.168.1.1; ping -I wlan0-sta -c 3 -W 2 192.168.1.2'))
 assert not run(['ss','-H','-lnt','sport','=',':5362']).stdout.strip()
 snapshot('before')
 seconds_tcp=10 if a.short else 15
 tests=[('tcp-up',[],seconds_tcp),('tcp-down',['-R'],seconds_tcp)]
 for rate in ([1] if a.short else [1,5,20]):
  tests += [(f'udp{rate}-up',['-u','-b',str(rate)+'M','-l','1200','-w','1M'],10),(f'udp{rate}-down',['-u','-b',str(rate)+'M','-l','1200','-w','1M','-R'],10)]
 for name,opts,seconds in tests:
  if name.startswith('udp20') and any(r.get('error') or r.get('receiver',{}).get('bits_per_second',0)<10e6 for r in rows if r['case'].startswith('tcp')):
   continue
  assert not run(['ss','-H','-lnt','sport','=',':5362']).stdout.strip(),'Test server port busy'
  log=(out/(name+'-server.log')).open('w');server=subprocess.Popen(['iperf3','-s','-1','-B','192.168.1.2','-p','5362'],stdout=log,stderr=subprocess.STDOUT);log.close()
  time.sleep(1);assert server.poll() is None
  snapshot(name+'-before');before=remote(dut,'cat /proc/stat')
  argv=['iperf3','-c','192.168.1.2','-p','5362','-B',address,'--bind-dev','wlan0-sta','-J','-t',str(seconds),'--connect-timeout','5000']+(['--rcv-timeout','10000'] if '-R' in opts else [])+opts
  started=time.monotonic()
  try:r=run(wrt+[shlex.join(argv)],check=False,timeout=seconds+25)
  except subprocess.TimeoutExpired:r=subprocess.CompletedProcess(argv,124,'test process timed out')
  wall=time.monotonic()-started;after=remote(dut,'cat /proc/stat')
  save(name+'.json',r.stdout)
  if server.poll() is None:server.terminate()
  server.wait(timeout=5);server=None
  try:data=json.JSONDecoder().raw_decode(r.stdout[r.stdout.index('{'):])[0]
  except (ValueError,json.JSONDecodeError):data={'error':r.stdout[:200]}
  end=data.get('end',{})
  row=dict(case=name,mode=a.mode,radio='builtin2',path='wifi-bridge',seconds=seconds,requested_2g_retest=True,client_sta_only=a.sta_only,exit=r.returncode,error=data.get('error'),dut_cpu=cpu(before,after,wall),receiver=end.get('sum_received',end.get('sum',{})),sender=end.get('sum_sent',{}))
  rows.append(row);save('results.json',json.dumps(rows,indent=2))
  print(name,json.dumps(dict(mbps=row['receiver'].get('bits_per_second',0)/1e6,loss_pct=row['receiver'].get('lost_percent'),error=row['error'])),flush=True)
  assert remote(dut,'cat /proc/sys/kernel/random/boot_id').strip()==boot,'Router rebooted'
  assert remote(dut,'cat /sys/devices/system/cpu/online').strip()=='0-3'
 snapshot('after')
 save('status','Test sequence completed; inspect rates/loss and errors. Compare matching campaigns separately.\n')
finally:
 if server and server.poll() is None:server.terminate();server.wait(timeout=5)
 errors=[]
 for host,backup in reversed(backups):
  try:
   reload='wifi reload radio1' if host==dut else 'wifi reload'
   remote(host,'set -e; uci revert wireless; cp '+backup+' /etc/config/wireless; '+reload+'; rm -f '+backup)
  except Exception as e:errors.append(str(e))
 if control:
  try:run(wbase[:-1]+['-S',sock,'-O','exit',wbase[-1]],check=False)
  except Exception as e:errors.append(str(e))
 if receiver and receiver.poll() is None:
  time.sleep(2);receiver.terminate();receiver.wait(timeout=5)
 save('cleanup.json',json.dumps(dict(errors=errors)))
 print('EVIDENCE',out,flush=True)
 if errors:raise RuntimeError('Restoration failed; host-local backups retained')
