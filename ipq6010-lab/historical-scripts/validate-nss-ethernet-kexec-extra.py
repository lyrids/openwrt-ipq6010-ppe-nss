from pathlib import Path
import subprocess,json,gzip
w=Path.home()/"projects/openwrt-dev";t=w/"src/openwrt-ppe-nss";r=w/"artifacts/nss-ethernet-kexec-20261025"
k=t/"build_dir/target-aarch64_cortex-a53_musl/linux-qualcommax_ipq60xx/linux-6.18.55";pkg=k.parent/"nss-wifi-drv"
import tarfile
uns=t/"staging_dir/host/bin/unsquashfs4"
with tarfile.open(next((r/"images").glob("*sysupgrade*"))) as archive:
 root=next(m for m in archive.getmembers() if m.name.endswith("/root"))
 (r/"rootfs.squashfs").write_bytes(archive.extractfile(root).read())
listing=subprocess.check_output([str(uns),"-ll",str(r/"rootfs.squashfs")],text=True)
(r/"rootfs-file-list.txt").write_text(listing)
for name in ["qca_ppe_main.c","qca_ppe_flow_offload.c","qca_ppe.h","qca_edma.c"]:
 assert (t/"target/linux/qualcommax/files/drivers/net/ethernet/qualcomm"/name).read_bytes()==(k/"drivers/net/ethernet/qualcomm"/name).read_bytes(),name
for name in ["nss_flow.c","nss_core.c","nss_drv.h"]:
 assert (t/"package/kernel/nss-wifi-drv/src"/name).read_bytes()==(pkg/name).read_bytes(),name
# Runtime source identity is checked above; documentation was added during the build.
for name in ["usr/sbin/kexec","usr/sbin/conntrack","usr/bin/tcpdump","usr/libexec/ip-full","usr/sbin/bridge","etc/image-provenance","qca-nss0-retail-12.5.bin"]:
 assert name in listing,name
assert "qca-nss0-retail-11.4.bin" not in listing
cfg=subprocess.check_output([str(uns),"-cat",str(r/"rootfs.squashfs"),"etc/config/nss-wifi"],text=True)
assert "option ethernet_offload '1'" in cfg and "option firmware '12.5'" in cfg
init=subprocess.check_output([str(uns),"-cat",str(r/"rootfs.squashfs"),"etc/init.d/nss-wifi"],text=True)
assert "options nss-wifi-drv ethernet_offload=%s" in init
assert "Ethernet mode mismatch" in init
manifest=next((r/"images").glob("*.manifest")).read_text()
for name in ["kmod-qca-nss-drv","kmod-qca-nss-ecm","kmod-qca-nss-dp","kmod-qca-ssdk"]:
 assert not any(l.startswith(name+" ") for l in manifest.splitlines()),name
assert "qca_ppe_fw_flow_set" in (k/"Module.symvers").read_text()
assert b"parmtype=ethernet_offload:bool" in (pkg/"nss-wifi-drv.ko").read_bytes()
data=(k/"usr/initramfs_data.cpio").read_bytes();pos=0;names=[];entries={}
while data[pos:pos+6] in (b"070701",b"070702"):
 h=data[pos:pos+110];size=int(h[54:62],16);ns=int(h[94:102],16)
 name=data[pos+110:pos+110+ns-1].decode();names.append(name)
 start=(pos+110+ns+3)&~3;entries[name]=data[start:start+size];pos=(start+size+3)&~3
 if name=="TRAILER!!!":break
assert any(n.endswith("qca-nss0-retail-12.5.bin") for n in names)
assert not any("qca-nss0-retail-11.4" in n for n in names)
assert b"option ethernet_offload '1'" in entries.get("etc/config/nss-wifi",entries.get("/etc/config/nss-wifi",b""))
(r/"initramfs-file-list.txt").write_text("\n".join(names)+"\n")
image=next((r/"images").glob("*initramfs*"))
subprocess.run(["dumpimage","-T","flat_dt","-p","0","-o",str(r/"initramfs-kernel.gz"),str(image)],check=True,stdout=subprocess.DEVNULL)
assert (k/"usr/initramfs_inc_data").read_bytes() in gzip.decompress((r/"initramfs-kernel.gz").read_bytes())
j=json.loads((r/"validation.json").read_text())
extra=["compiled PPE/NSS source matches final local patch","kernel exports firmware flow callback; module contains Ethernet boot parameter","actual SquashFS and embedded FIT initramfs contain selected firmware and enabled Ethernet mode","VLAN/conntrack/PPPoE diagnostic tools present","vendor NSS/ECM/SSDK packages absent"]
j["checks"]=list(dict.fromkeys(j["checks"]+extra))
j["feature_status"]="Experimental Ethernet NSS backend; hardware validation pending"
(r/"validation.json").write_text(json.dumps(j,indent=2)+"\n")
for i in j["images"]:
 print(i["name"],i["size"],i["sha256"])
 if "kernel_bytes" in i:print("Kernel headroom:",i["kernel_partition_bytes"]-i["kernel_bytes"])
print("Offline checks passed; hardware boot and acceleration remain untested.")


assert "usr/sbin/kexec" in entries or "/usr/sbin/kexec" in entries
assert "iteration 6 (kexec bootstrap" in entries["etc/image-provenance"].decode()
j=json.loads((r/"validation.json").read_text())
j["checks"] += ["KEXEC/KEXEC_FILE/HOTPLUG_CPU/SUSPEND effective kernel config", "packaged kexec present in actual embedded initramfs", "iteration-6 identity embedded", "compiled EDMA and NSS shutdown source matches working tree"]
j["feature_status"]="Kexec bootstrap; offline validated, no hardware boot or warm-transition test yet"
(r/"validation.json").write_text(json.dumps(j,indent=2)+"\n")
