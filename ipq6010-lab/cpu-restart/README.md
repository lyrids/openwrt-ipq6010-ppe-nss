# CPU restart investigation

Iteration6 restores all CPUs after an ordinary U-Boot RAM boot, but CPU3
failed to re-online after CPU_OFF. Both kexec load/unload paths passed before
this event. No actual kexec transition has been attempted.

The temporary diagnostic kernel patch logs PSCI CPU_ON function ID, MPIDR,
entry physical address, raw firmware result and translated errno; affinity
state before/after the request; two secondary-C checkpoints; and both startup
status words on timeout. It adds logging/read-only affinity queries, retaining
CPU power/start behavior and the stuck-CPU safety guard. It does not establish
or apply a fix.

Variants use the same instrumented kernel:
- host-control: NSS offload0 and Ethernet offload0, host Wi-Fi path.
- nss-enabled: NSS offload1 and Ethernet offload1 as iteration6.

Test the host-control first on a fresh boot, verify exactly which firmware
and modules are active, then perform one CPU3 offline/re-online attempt and
save all logs. Do not use a restoration trap to retry a failed CPU_ON request:
the previous iteration's trap added a second failing attempt. If re-online
fails, record the state, do not offline other CPUs, and return to recovery
for the next variant. A normal reboot needs physical SCREEN coordination.

Compare initial cold CPU bring-up with the post-CPU_OFF request. Raw return0
does not prove successful Linux startup. Affinity and C-entry markers narrow
the failure boundary. Missing C-entry markers do not prove that the assembly
entry was never reached.

SCM warm-vector registration and CPU clock/power handling are investigation
leads only. Add a correction only after diagnostic evidence and platform
source support it. A CPU remaining offline and kexec EBUSY must be reported.
