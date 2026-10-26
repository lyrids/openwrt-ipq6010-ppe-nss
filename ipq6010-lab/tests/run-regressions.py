#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Run source-derived control-flow tests with mock kernel/firmware dependencies."""
from pathlib import Path
import subprocess, tempfile
repo=Path(__file__).resolve().parents[2]
lab=repo/"ipq6010-lab"
with tempfile.TemporaryDirectory(prefix="ipq6010-regression-") as tmp:
    out=Path(tmp)
    for name in ("test-nss-mtuguard-transaction.py","test-nss-mtuguard-vlan-rule.py"):
        s=(lab/"historical-scripts"/name).read_text()
        lines=s.splitlines()
        index=next(i for i,line in enumerate(lines) if line.startswith('w=Path.home()'))
        lines[index]="w=Path("+repr(str(out))+");t=Path("+repr(str(repo))+");r=w;r.mkdir(exist_ok=True)"
        script=out/name
        script.write_text("\n".join(lines)+"\n")
        subprocess.run(["python3",str(script)],check=True)
    snapshot=lab/"artifacts/nss-ethernet-mtuguard-03803c78cd-20261025/mtu-guard-regression.c"
    actual=(repo/"package/kernel/nss-wifi-drv/src/nss_flow.c").read_text()
    saved=snapshot.read_text()
    def function(s):
        start=s.index("static u32 nss_flow_effective_mtu(")
        opening=s.index("{",start);level=1;end=opening+1
        while level:
            level += (s[end]=="{")-(s[end]=="}");end+=1
        return s[start:end]
    assert function(actual)==function(saved),"MTU source changed: regenerate the saved test harness"
    binary=out/"mtu-guard-regression"
    subprocess.run(["gcc","-std=gnu17","-Wall","-Wextra","-Werror","-g","-O1","-fsanitize=address,undefined",str(snapshot),"-o",str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
print("PASS: all three regression harnesses")
