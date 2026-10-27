#!/usr/bin/env python3
"""Assemble a portable report from raw evidence. Run only on Orb."""
import argparse,csv,datetime,hashlib,json,pathlib,re,shutil
p=argparse.ArgumentParser();p.add_argument("--evidence",type=pathlib.Path,required=True);p.add_argument("--output",type=pathlib.Path,required=True);p.add_argument("--status",type=pathlib.Path);a=p.parse_args()
repo=pathlib.Path(__file__).resolve().parents[2]
meta=json.loads(a.status.read_text()) if a.status and a.status.exists() else {}
rows=[]
for f in sorted(a.evidence.glob("*/results.json")):
 try:items=json.loads(f.read_text())
 except json.JSONDecodeError:continue
 for r in items:
  if not isinstance(r,dict) or not all(k in r for k in ("radio","path","case","mode")):continue
  r["run"]=f.parent.name
  identity=(f.parent/"identity.txt").read_text() if (f.parent/"identity.txt").exists() else ""
  match=re.search(r"iteration\s+(\d+)",identity)
  r["image_iteration"]=match[1] if match else "11"
  if r["image_iteration"]!="11":
   r["diagnostic"]=True;r["note"]="Later diagnostic/fix image; excluded from iteration11 qualification pairs"
  r["run_complete"]=(f.parent/"status").exists()
  if not r["run_complete"]:
   r["diagnostic"]=True;r["note"]="Interrupted run; completed repeat is used for comparisons"
  if r.get("radio")=="builtin2":
   r["diagnostic"]=True;r["note"]="2.4GHz retries waived by user; performance/offload unqualified"
  if r.get("path")=="pppoe" and not r.get("server_mode")=="kernel":
   r["diagnostic"]=True;r["note"]="Userspace PPPoE server; use kernel-mode rerun for comparison"
  r["nss_flow_observations"]=r.get("nss_flow_observations",[])[:4]
  rows.append(r)
qdisc=[]
base="https://github.com/lyrids/openwrt-ipq6010-ppe-nss/blob/jdcloud-mainline-ppe-nss/ipq6010-lab/evidence/mainline-qualification-20261026/"
for mode in ["nss","ppe","software"]:
 for f in sorted((a.evidence/("qdisc-"+mode)).glob("run-*/*.json")):
  try:d=json.loads(f.read_text())
  except json.JSONDecodeError:continue
  if d.get("error") or "sum_received" not in d.get("end",{}):continue
  name=f.stem;mbps=d["end"]["sum_received"]["bits_per_second"]/1e6
  snap=f.with_name(name+"-active.txt")
  text=snap.read_text() if snap.exists() else ""
  hw=" offloaded " in text
  if "baseline" in name or "recovery" in name:interpretation="Reference / recovery"
  elif "tbf" in name and name.startswith("ethernet"):interpretation="Hardware cap enforced" if hw and mbps<(220 if "200" in name else 110) else "Inspect rate and hardware state"
  elif name=="ethernet-prio":interpretation="Hardware attachment; arbitration not tested" if hw else "Software attachment only"
  elif "100" in name:interpretation="Cap enforced" if 80<mbps<110 else "Configured100M cap bypassed"
  else:interpretation="Forwarding compatibility; inspect queue counters"
  qdisc.append({"mode":mode,"case":name,"mbps":mbps,"interpretation":interpretation,"href":base+str(f.relative_to(a.evidence)),"tc_excerpt":"\n".join(text.splitlines()[:7])})
fix_runs=[]
fragment=repo/"ipq6010-lab/evidence/ath11k-fragment-fix/runtime"
fix_files=list(a.evidence.glob("fix-validation-*/results.json"))+list(fragment.glob("fragment-*/results.json"))
for f in sorted(fix_files):
 try:items=json.loads(f.read_text())
 except json.JSONDecodeError:continue
 fix_runs.append({"run":f.parent.name,"complete":(f.parent/"status").exists(),"cases":items})
provenance={
 "Official OpenWrt":"6c9452a35b923d98bb26c85b5734a6058c02185e",
 "Community source":"03803c78cd3b6968c20dab239c0c2f688692be63 (88 replayed, 2 already upstream)",
 "Image source commit":"6aa8805fe5",
 "Branch":"jdcloud-mainline-ppe-nss",
 "Kernel":"6.18.55",
 "NSS firmware":"CP12.5; same pinned binaries in both variants",
 "NSS-on FIT SHA256":"c92f6f0aad3315b5f0962b5a56219ac3022ca411820336aba083cd0637269e36",
 "NSS-off FIT SHA256":"830795903fc522da9019b83dc9210af5997fd6819a1388e06115da76ffa09541",
 "Previous iteration10 FIT SHA256":"3efc36b646da67cd4c99563f97a39b7b787ad3a1a9821bd6231bba72d996a7c4"
}
provenance.update(meta.get("provenance",{}))
pairs={}
for r in rows:
 if r.get("error") or r.get("diagnostic") or not r.get("run_complete") or r.get("seconds")!=15:continue
 key=(r["radio"],r["path"],r["case"])
 pairs.setdefault(key,{})[r["mode"]]=r
comparisons=[{"radio":k[0],"path":k[1],"case":k[2],"modes":v} for k,v in sorted(pairs.items()) if "nss" in v and len(v)>1]
data={"fix_runs":fix_runs,"comparisons":comparisons,"generated":datetime.datetime.now(datetime.timezone.utc).isoformat(),"rows":rows,"qdisc":qdisc,"provenance":provenance,**{k:v for k,v in meta.items() if k!="provenance"}}
a.output.mkdir(parents=True,exist_ok=True)
(a.output/"results.json").write_text(json.dumps(data,indent=2))
with (a.output/"measurements.csv").open("w") as f:
 w=csv.writer(f);w.writerow(["run","mode","radio","path","case","qdisc","received_mbps","dut_mean_cpu_pct","dut_max_core_pct","dut_softirq_pct","udp_loss_pct","nss_packet_flow_observed","error","diagnostic"])
 for r in rows:
  c=r.get("dut_cpu",{}).get("cores",{});v=[x["busy_pct"] for k,x in c.items() if k!="cpu"]
  w.writerow([r["run"],r["mode"],r["radio"],r["path"],r["case"],r.get("qdisc"),r.get("receiver",{}).get("bits_per_second",0)/1e6,c.get("cpu",{}).get("busy_pct"),max(v) if v else None,c.get("cpu",{}).get("softirq_pct"),r.get("receiver",{}).get("lost_percent"),r.get("nss_packet_flow_observed"),r.get("error"),r.get("diagnostic",False)])
template=(pathlib.Path(__file__).parent/"report-template.html").read_text()
payload=json.dumps(data,separators=(",",":")).replace("</","<\\/")
html=template.replace("__REPORT_DATA__",payload)
assert "__REPORT_DATA__" not in html
(a.output/"ax6600-mainline-qualification.html").write_text(html)
if not (a.output/"evidence").exists(): (a.output/"evidence").symlink_to(a.evidence.resolve(),target_is_directory=True)
print("Report:",a.output/"ax6600-mainline-qualification.html","cases",len(rows),"queue checks",len(qdisc))
