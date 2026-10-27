#!/usr/bin/env python3
"""Run on wired-managed p43; Wi-Fi client to the wired WRT iperf endpoint."""
import argparse,datetime,json,os,pathlib,re,shlex,socket,subprocess,time
p=argparse.ArgumentParser();p.add_argument('--mode',choices=['nss','ppe'],default='nss');a=p.parse_args()
assert socket.gethostname().split('.')[0]=='p43'
home=pathlib.Path.home()/'openwrt-ramboot'
out=home/'mainline-qualification'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+a.mode+'-builtin2-wifi-bridge-p43')
out.mkdir(parents=True)
base=['ssh','-n','-o','BatchMode=yes','-o','ConnectTimeout=5','-o','StrictHostKeyChecking=yes']
known=pathlib.Path(os.environ.get('DUT_KNOWN_HOSTS',str(home/'iteration15-known-hosts')))
dut=base+['-o','UserKnownHostsFile='+str(known),'root@192.168.1.1']
wrt=base+['-b','192.168.1.132','-S',os.environ['WRT_CONTROL_SOCKET'],'-o','UserKnownHostsFile='+str(home/'replacement154-lan-known-hosts'),'root@192.168.1.3']
def run(v,check=True,timeout=35):
 r=subprocess.run(v,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
 if check and r.returncode:raise RuntimeError('Operation failed: '+r.stdout)
 return r
def remote(h,s,**kw):return run(h+[s],**kw).stdout
def save(n,s):(out/n).write_text(s)
def wpa(*v):return run(['sudo','wpa_cli','-i','wlan0',*map(str,v)]).stdout
def counters(s):return {x.split()[0]:list(map(int,x.split()[1:9])) for x in s.splitlines() if re.match(r'^cpu\d* ',x)}
def cpu(s0,s1,wall):
 after=counters(s1);c={}
 for k,v in counters(s0).items():
  d=[y-x for x,y in zip(v,after[k])];t=sum(d)
  if t:c[k]=dict(busy_pct=100*(t-d[3]-d[4])/t,softirq_pct=100*d[6]/t,irq_pct=100*d[5]/t)
 return dict(window_seconds=wall,cores=c)
def snapshot(label):
 save(label+'.txt',remote(dut,'date -u; cat /proc/uptime; cat /proc/sys/kernel/random/boot_id; cat /sys/devices/system/cpu/online; cat /sys/kernel/debug/39000000.nss/wifili_rx; iw dev phy1-ap0 station dump; dmesg',check=False))
 save(label+'-client.txt',run(['sudo','iw','dev','wlan0','link']).stdout+run(['ip','-4','addr','show','dev','wlan0']).stdout)
server=None;server_file=None;network=None;original=None;backup=None;sysctls={};rows=[]
pidfile='/tmp/p43-wifi-server-'+str(os.getpid())+'.pid'
def stop_server():
 global server,server_file
 if server is not None:
  remote(wrt,'if [ -s '+pidfile+' ]; then p=$(cat '+pidfile+'); case "$p" in ""|*[!0-9]*) exit 1;; esac; if [ -r /proc/$p/cmdline ] && tr "\\000" " " < /proc/$p/cmdline | grep -q "iperf3 -s -1 -B 192.168.1.3 -p 5362"; then kill "$p" 2>/dev/null || true; fi; rm -f '+pidfile+'; fi',check=False)
  try:server.wait(timeout=5)
  except subprocess.TimeoutExpired:server.terminate();server.wait(timeout=5)
  server=None
 if server_file:server_file.close();server_file=None
try:
 route=run(['ip','-4','route','get','192.168.21.157','from','192.168.21.130']).stdout
 assert 'dev enx000ec6beaaf2' in route,'Wired management route missing'
 save('management-route.txt',route)
 identity=remote(dut,'ubus call system board; cat /etc/image-provenance')
 assert 'iteration 15' in identity and 'jdcloud,re-cs-02' in identity
 assert (remote(dut,'cat /sys/module/ath11k/parameters/nss_offload').strip()=='Y')==(a.mode=='nss')
 save('identity.txt',identity);save('harness.py',pathlib.Path(__file__).read_text())
 boot=remote(dut,'cat /proc/sys/kernel/random/boot_id').strip()
 state=wpa('status');original=re.search(r'^id=(\d+)$',state,re.M)
 assert original;original=int(original[1]);save('original-client-status.txt',state)
 power=run(['sudo','iw','dev','wlan0','get','power_save']).stdout
 save('original-power-save.txt',power)
 for key in ['net.ipv4.conf.eth0.arp_ignore','net.ipv4.conf.wlan0.rp_filter']:
  sysctls[key]=run(['sysctl','-n',key]).stdout.strip()
 run(['sudo','sysctl','-w','net.ipv4.conf.eth0.arp_ignore=1','net.ipv4.conf.wlan0.rp_filter=2'])
 run(['sudo','iw','dev','wlan0','set','power_save','off'])
 backup='/tmp/p43-wifi-test-'+str(os.getpid())+'-wireless'
 remote(dut,'set -e; test -z "$(uci changes wireless)"; umask 077; cp /etc/config/wireless '+backup)
 remote(dut,'uci set wireless.radio1.disabled=0; uci set wireless.radio1.country=US; uci set wireless.radio1.channel=11; uci set wireless.radio1.htmode=HE20; uci set wireless.default_radio1.disabled=0; uci commit wireless; wifi reload radio1')
 time.sleep(5)
 bssid=remote(dut,'cat /sys/class/net/phy1-ap0/address').strip()
 ssid=remote(dut,'uci -q get wireless.default_radio1.ssid').strip()
 network=int(wpa('add_network').strip())
 assert 'OK' in wpa('set_network',network,'ssid',json.dumps(ssid))
 assert 'OK' in wpa('set_network',network,'bssid',bssid)
 assert 'OK' in wpa('set_network',network,'scan_freq','2462')
 # The existing test PSK is used only on the authorized Wi-Fi client.
 # Never log it, place it in argv, or send it to a developer host.
 credential=run(dut+['uci -q get wireless.default_radio1.key'],check=False)
 if credential.returncode:raise RuntimeError('Unable to obtain the existing test credential on the authorized client')
 key=credential.stdout.strip()
 del credential
 assert 8<=len(key)<=63
 response=subprocess.run(['sudo','wpa_cli','-i','wlan0'],input='set_network '+str(network)+' psk '+json.dumps(key)+'\nquit\n',text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 del key
 assert response.returncode==0 and 'FAIL' not in response.stdout,'Temporary test PSK configuration failed'
 del response
 assert 'OK' in wpa('select_network',network)
 started=time.monotonic();address=None
 while time.monotonic()-started<60:
  time.sleep(2);state=wpa('status')
  addr=run(['ip','-4','-o','addr','show','dev','wlan0']).stdout
  m=re.search(r'inet (192\.168\.1\.\d+)/',addr)
  if 'wpa_state=COMPLETED' in state and 'bssid='+bssid in state and m:address=m[1];break
 assert address,'Wi-Fi association/DHCP failed'
 save('client-status.txt',state+addr)
 save('client-capabilities.txt',run(['sudo','iw','phy','phy0','info']).stdout)
 save('ping.txt',run(['ping','-I','wlan0','-c','3','-W','2','192.168.1.3']).stdout)
 mac=pathlib.Path('/sys/class/net/wlan0/address').read_text().strip()
 neighbor=remote(wrt,'ip neigh show '+address+' dev br-lan')
 save('server-neighbor.txt',neighbor);assert mac.lower() in neighbor.lower(),'ARP points to the wired interface'
 save('test-settings.json',json.dumps(dict(mode=a.mode,client='p43 brcmfmac',client_address=address,server='LY-WRT32X wired LAN4 192.168.1.3:5362',bssid=bssid,channel=11,width_mhz=20,management='192.168.21.130 wired',boot_id=boot,power_save=False),indent=2))
 tests=[('tcp-up',[]),('tcp-down',['-R'])]
 for rate in [5,20]:
  tests += [(f'udp{rate}-up',['-u','-b',str(rate)+'M','-l','1200','-w','1M']),(f'udp{rate}-down',['-u','-b',str(rate)+'M','-l','1200','-w','1M','-R'])]
 snapshot('before')
 for name,opts in tests:
  assert not remote(wrt,"netstat -lnt | grep ':5362 '",check=False).strip(),'Server port busy'
  server_file=(out/(name+'-server.log')).open('w')
  server=subprocess.Popen(wrt+['exec iperf3 -s -1 -B 192.168.1.3 -p 5362 -I '+pidfile],stdout=server_file,stderr=subprocess.STDOUT)
  time.sleep(1);assert server.poll() is None
  snapshot(name+'-before');before=remote(dut,'cat /proc/stat');start=time.monotonic()
  cmd=['iperf3','-c','192.168.1.3','-p','5362','-B',address,'--bind-dev','wlan0','-J','-t','15','--connect-timeout','5000']+(['--rcv-timeout','10000'] if '-R' in opts else [])+opts
  try:r=run(cmd,check=False,timeout=40)
  except subprocess.TimeoutExpired:r=subprocess.CompletedProcess(cmd,124,'test process timed out')
  wall=time.monotonic()-start;after=remote(dut,'cat /proc/stat')
  save(name+'.json',r.stdout);stop_server()
  try:d=json.JSONDecoder().raw_decode(r.stdout[r.stdout.index('{'):])[0]
  except (ValueError,json.JSONDecodeError):d={'error':r.stdout[:200]}
  end=d.get('end',{})
  row=dict(case=name,mode=a.mode,radio='builtin2',path='wifi-bridge',seconds=15,requested_2g_retest=True,test_client='p43-brcmfmac',exit=r.returncode,error=d.get('error'),dut_cpu=cpu(before,after,wall),receiver=end.get('sum_received',end.get('sum',{})),sender=end.get('sum_sent',{}))
  rows.append(row);save('results.json',json.dumps(rows,indent=2))
  print(name,json.dumps(dict(mbps=row['receiver'].get('bits_per_second',0)/1e6,loss_pct=row['receiver'].get('lost_percent'),error=row['error'])),flush=True)
  assert remote(dut,'cat /proc/sys/kernel/random/boot_id').strip()==boot,'Unexpected reboot'
  assert remote(dut,'cat /sys/devices/system/cpu/online').strip()=='0-3'
 snapshot('after');save('status','Completed p43 2.4 GHz bridge campaign; inspect rates/loss/errors.\n')
finally:
 errors=[]
 try:stop_server()
 except Exception as e:errors.append('server: '+str(e))
 if original is not None:
  try:wpa('select_network',original)
  except Exception as e:errors.append('original Wi-Fi: '+str(e))
 if network is not None:
  try:wpa('remove_network',network)
  except Exception as e:errors.append('test network: '+str(e))
 if 'power' in locals():
  try:run(['sudo','iw','dev','wlan0','set','power_save','on' if 'on' in power else 'off'])
  except Exception as e:errors.append('power save: '+str(e))
 for key,value in sysctls.items():
  try:run(['sudo','sysctl','-w',key+'='+value])
  except Exception as e:errors.append('sysctl: '+str(e))
 if backup:
  try:remote(dut,'set -e; uci revert wireless; cp '+backup+' /etc/config/wireless; wifi reload radio1; rm -f '+backup)
  except Exception as e:errors.append('router AP: '+str(e))
 save('cleanup.json',json.dumps(dict(errors=errors)))
 print('EVIDENCE',out,flush=True)
 if errors:raise RuntimeError('Restoration failed; see host-local evidence')
