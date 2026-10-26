#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
from pathlib import Path
import ctypes,ctypes.util,gzip,hashlib,json,subprocess,tarfile
w=Path("/home/ly/projects/openwrt-dev")
t=w/"src/openwrt-ppe-nss";root=w/"artifacts/cpu-warm-entry-experiment-20261025"
z=ctypes.CDLL(ctypes.util.find_library("zstd"))
z.ZSTD_findFrameCompressedSize.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
z.ZSTD_findFrameCompressedSize.restype=ctypes.c_size_t
z.ZSTD_isError.argtypes=[ctypes.c_size_t];z.ZSTD_isError.restype=ctypes.c_uint
def cpio(data):
    entries={};pos=0
    while data[pos:pos+6] in (b"070701",b"070702"):
        h=data[pos:pos+110];size=int(h[54:62],16);ns=int(h[94:102],16)
        name=data[pos+110:pos+110+ns-1].decode()
        start=(pos+110+ns+3)&~3
        assert start+size<=len(data)
        entries[name.lstrip("./")]=data[start:start+size]
        pos=(start+size+3)&~3
        if name=="TRAILER!!!":return entries
    raise ValueError("Incomplete cpio")
reports=[]
for variant,enabled in [("host-control","0")]:
    r=root/variant;images=r/"images"
    profiles=json.loads((images/"profiles.json").read_text());profile=profiles["profiles"]["jdcloud_re-cs-02"]
    assert profiles["target"]=="qualcommax/ipq60xx" and "jdcloud,re-cs-02" in profile["supported_devices"]
    report={"variant":variant,"images":[],"hardware_boot_tested":False,"fix_applied":False}
    for item in profile["images"]:
        p=images/item["name"];b=p.read_bytes()
        assert len(b)==item["size"] and hashlib.sha256(b).hexdigest()==item["sha256"]
        entry=dict(item)
        if item["type"]=="sysupgrade":
            with tarfile.open(p) as a:
                kernel=next(m for m in a.getmembers() if m.name.endswith("/kernel"))
                assert kernel.size<=6144*1024
                entry["kernel_bytes"]=kernel.size;entry["kernel_headroom_bytes"]=6144*1024-kernel.size
        if "initramfs" in p.name:
            listing=subprocess.check_output(["dumpimage","-l",str(p)],text=True)
            assert "config@cp03-c3" in listing;(r/"fit-info.txt").write_text(listing)
            packed=r/"kernel.gz"
            subprocess.run(["dumpimage","-T","flat_dt","-p","0","-o",str(packed),str(p)],check=True,stdout=subprocess.DEVNULL)
            image=gzip.decompress(packed.read_bytes())
            for marker in [b"ipq-cpu-diag:",b"affinity-before=",b"affinity-after=",b"raw=%d errno=%d",b"reached secondary C",b"secondary-status=",b"ipq-cpu-warm-entry:",b"ipq_cpu_warm_vector"]:
                assert marker in image,marker
            pos=0;archives=[]
            while True:
                pos=image.find(b"\x28\xb5\x2f\xfd",pos)
                if pos<0:break
                tail=image[pos:];buf=ctypes.create_string_buffer(tail)
                size=z.ZSTD_findFrameCompressedSize(buf,len(tail))
                if not z.ZSTD_isError(size):
                    decoded=subprocess.run(["zstd","-dc"],input=tail[:size],capture_output=True,check=True).stdout
                    try:archives.append(cpio(decoded))
                    except (ValueError,UnicodeError):pass
                pos+=4
            candidates=[a for a in archives if "etc/config/nss-wifi" in a]
            assert len(candidates)==1,len(candidates)
            entries=candidates[0];config=entries["etc/config/nss-wifi"].decode()
            assert "option offload '"+enabled+"'" in config
            assert "option ethernet_offload '"+enabled+"'" in config
            assert "usr/sbin/kexec" in entries
            assert variant in entries["etc/image-provenance"].decode()
            assert any(n.endswith("qca-nss0-retail-12.5.bin") for n in entries)
            assert not any("qca-nss0-retail-11.4" in n for n in entries)
            (r/"embedded-nss-wifi.config").write_text(config)
            (r/"embedded-provenance.txt").write_bytes(entries["etc/image-provenance"])
            (r/"embedded-file-list.txt").write_text("\n".join(sorted(entries))+"\n")
        report["images"].append(entry)
    cfg=(r/"kernel.config").read_text().splitlines()
    for option in ["CONFIG_KEXEC=y","CONFIG_KEXEC_FILE=y","CONFIG_HOTPLUG_CPU=y","CONFIG_SUSPEND=y"]:
        assert option in cfg,option
    manifest=next(images.glob("*.manifest")).read_text()
    assert any(l.startswith("kexec - ") for l in manifest.splitlines())
    for name in ["kmod-qca-nss-drv","kmod-qca-nss-ecm","kmod-qca-ssdk"]:
        assert not any(l.startswith(name+" ") for l in manifest.splitlines())
    report["checks"]=["profile size/SHA256","FIT cp03-c3","6MiB kernel limit","diagnostic strings in actual kernel","actual embedded initramfs variant config and identity","selected NSS12.5 only","built-in kexec and effective kernel config","vendor NSS/ECM/SSDK packages absent"]
    (r/"validation.json").write_text(json.dumps(report,indent=2)+"\n");reports.append(report)
(root/"validation.json").write_text(json.dumps({"variants":reports,"opt_in_registration_default":False,"hardware_tested":False,"fix_applied":False},indent=2)+"\n")
for report in reports:
    print(report["variant"])
    for item in report["images"]:
        print(item["name"],item["size"],item["sha256"])
        if "kernel_headroom_bytes" in item:print("kernel headroom",item["kernel_headroom_bytes"])
print("PASS opt-in experiment; default disabled; actual CPU restart test pending")

kernel=t/"build_dir/target-aarch64_cortex-a53_musl/linux-qualcommax_ipq60xx/linux-6.18.55"
nm=t/"staging_dir/toolchain-aarch64_cortex-a53_gcc-14.4.0_musl/bin/aarch64-openwrt-linux-musl-nm"
symbols=subprocess.check_output([str(nm),"-n",str(kernel/"vmlinux")],text=True)
assert any(l.endswith(" b ipq_cpu_warm_vector") for l in symbols.splitlines()),"Opt-in must reside in zero-initialized BSS"
(root/"default-off-symbol.txt").write_text("\n".join(l for l in symbols.splitlines() if "ipq_cpu_warm_vector" in l)+"\n")
print("PASS opt-in bool is zero-initialized BSS")
