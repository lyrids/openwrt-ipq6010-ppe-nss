#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Extract a checksum-verified JDCloud RAM FIT; never load or execute a kernel."""
import argparse,gzip,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("fit",type=Path);p.add_argument("output",type=Path)
p.add_argument("--sha256",required=True,help="Independently verified SHA256 of the FIT")
a=p.parse_args()
assert hashlib.sha256(a.fit.read_bytes()).hexdigest()==a.sha256.lower(),"FIT SHA256 mismatch"
def fdt(file,node,prop):
 return subprocess.check_output(["fdtget","-t","s",str(file),node,prop],text=True).strip()
nodes=subprocess.check_output(["fdtget","-l",str(a.fit),"/images"],text=True).split()
config=fdt(a.fit,"/configurations","default")
kernel=fdt(a.fit,"/configurations/"+config,"kernel")
dtb=fdt(a.fit,"/configurations/"+config,"fdt")
assert fdt(a.fit,"/images/"+kernel,"arch")=="arm64"
assert fdt(a.fit,"/images/"+kernel,"type")=="kernel"
assert fdt(a.fit,"/images/"+dtb,"type")=="flat_dt"
assert not a.output.exists(),"Output already exists"
a.output.mkdir(parents=True)
for name,dest in [(kernel,"kernel.payload"),(dtb,"target.dtb")]:
 subprocess.run(["dumpimage","-T","flat_dt","-p",str(nodes.index(name)),"-o",str(a.output/dest),str(a.fit)],check=True,stdout=subprocess.DEVNULL)
compression=fdt(a.fit,"/images/"+kernel,"compression")
data=(a.output/"kernel.payload").read_bytes()
if compression=="gzip":data=gzip.decompress(data)
else:assert compression=="none","Unsupported kernel compression"
assert data[56:60]==b"ARM\x64","Not an ARM64 Image"
(a.output/"Image").write_bytes(data)
(a.output/"kernel.payload").unlink()
compat=fdt(a.output/"target.dtb","/","compatible")
assert "jdcloud,re-cs-02" in compat,"Wrong target DTB"
manifest={"source_sha256":a.sha256.lower(),"configuration":config,"compatible":compat,"kernel_compression":compression,"initramfs":"built into source kernel; no separate initrd","files":{}}
for name in ["Image","target.dtb"]:
 b=(a.output/name).read_bytes();manifest["files"][name]={"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
(a.output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
print(json.dumps(manifest,indent=2))
