# Opt-in SCM warm-entry experiment (iteration8)

The NSS-disabled iteration7 control reproduced the CPU3 restart failure.
The first CPU_ON returns raw0 (success), requests the same physical secondary
entry used on initial boot, and reports affinity2 (ON_PENDING). Neither
secondary-C checkpoint appears. A one-shot read-only module queried the
firmware several minutes later: CPU0/1/2 ON, CPU3 still ON_PENDING.
The module was unloaded afterward; its out-of-tree taint was introduced only
after the CPU failure. The entry, __cpu_setup, __enable_mmu and __secondary_switched code
symbols are outside freed init memory. This rules out NSS being required for the reproducer; it does
not yet establish a specific firmware or kernel defect.

The Linux QCOM SCM API qcom_scm_set_warm_boot_addr() documents its role for
CPU power-down/hotplug return. Patch0991 tests whether registering the normal
secondary entry before a post-boot CPU_ON helps this board. It is compiled
off by default, restricted to jdcloud,re-cs-02, and skipped during initial
SMP startup. If registration fails, CPU_ON is not attempted by this path.
No stuck-CPU check is removed, and no bootloader/secure firmware flash
or environment write is performed. A successful registration changes
volatile firmware state; resetting the opt-in flag does not undo it.

Candidate: host-control (NSS offload0, Ethernet offload0),18960156-byte FIT,
SHA2565e072483cefb5558c59da01d351d4bf47bfb50c294b34a36df9f4d7ce3ed968c.
Staged on p43:/home/ubuntu/openwrt-ramboot/cpu-warm-entry-experiment.itb.
Offline image validation and the zero-initialized parameter-symbol check
passed. It has not been RAM booted or runtime tested.

After a fresh recovery RAM boot:
1. Verify all four CPUs and the default N value at
   /sys/module/kernel/parameters/ipq_cpu_warm_vector.
2. Preserve the cold-boot trace. Copy test-one-cpu3-cycle.sh and
   test-warm-entry-once.sh to /tmp.
3. Run test-warm-entry-once.sh once. It explicitly enables the experiment,
   then attempts CPU3 offline/re-online. There is no retry after failure.
4. Collect SCM return, raw PSCI result, affinity, C checkpoints, CPU online
   mask, module parameter state and final connectivity.
5. Success requires actual CPU3 online again; SCM return0 alone is not a pass.
   A failure requires a normal recovery reboot before further hotplug tests.

Even if this restores hotplug within one kernel, cross-kernel kexec remains
unqualified: a subsequent kernel must have correct secondary entry handling
after relocation. Do not infer safe warm replacement from one CPU cycle.
The NSS-enabled configuration and repeated CPU cycles would also need tests.
Default source-preparation overlay stays NSS-enabled; the candidate builder
explicitly makes a host-control image for this experiment.
