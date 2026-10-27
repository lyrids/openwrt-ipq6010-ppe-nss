# Fragment lifetime fix: iteration 14

Patch 959 keeps fragment RX, key fragment flushing and RX TID cleanup under
base_lock. They cancel timers without waiting, while the callback uses the
same lock. A callback for an earlier expiry leaves a newly pending timer's
fragment sequence alone.

Every peer initializes all fragment timers before publication. All four
peer freeing sites now stop datapath RX, cancel pending fragment timers,
purge fragment state and queue final destruction. The worker calls
timer_shutdown_sync() on every embedded timer without base_lock before
kfree(). The existing core workqueue is drained before ath11k_base is freed.

This prevents unlocked embedded RX TID use, cancellation deadlocks, late
timer callback access to a freed peer, and timer rearming during TID teardown.
It does not establish that the historical router restarts had this cause.

Validation:
- Kernel checkpatch: zero errors/warnings/checks.
- Patch applies to the saved pre-959 prepared sources.
- Actual fixed helper bodies compiled and exercised with a pthread timer/work
  shim, ASAN and UBSAN: stale expiry after rearm, callback blocked by deletion,
  and pending timer cancellation across all 17 TIDs pass.
- Static integration checks: no unlock in fragment reassembly's RX TID lifetime;
  datapath disabled before TID cleanup; no direct peer frees outside the worker.
- The shim checks helper ordering, not firmware or the Linux timer subsystem.
- ARM64 build and hardware validation pending at this checkpoint.

Iteration 14 runtime results:
- Both 5 GHz radios: initial TCP/UDP bridge and NAT checks passed with NSS off.
- 40/40 additional native-driver traffic cases passed across flow-offload
  toggles, TBF install/remove and one authenticated peer reconnect per radio.
- Four CPUs remained online and the recorded boot ID was unchanged.
- No BUG/Oops/KASAN/panic/refcount/stall/lockup signature was found in netconsole.
- This did not generate or prove on-air 802.11 fragmentation. Fixed-helper
  tests cover pending/running timer orderings through a host shim.
- NSS-on QCN TCP control handshakes failed before the throughput phase.
  Iteration 13 passed the identical QCN test at about 355/806 Mbps.
  Therefore iteration 14 is rejected as an NSS deployment candidate.
- Iteration 15 preserves the offsets of existing peer fields. It is a
  controlled diagnostic variant; its NSS outcome must be measured before
  assigning a cause to the iteration 14 regression.

Final candidate: iteration 15, source d69ebcba83, ath11k release 13.
- Existing peer member offsets are preserved; the deletion work item is appended.
- Identical QCN NSS smoke test passed at about 391/760 Mbps.
- Both radios passed initial TCP/UDP bridge and NAT checks (16 cases).
- 40/40 further NSS-enabled traffic cases passed across flowtable toggles,
  TBF attach/remove and authenticated station reconnects.
- Both APs passed teardown/recreation and automatic flowtable-membership checks.
- Boot ID remained 5ff4134d-bb3a-4e20-8336-cf1c9299af47; CPUs0-3 stayed online.
- NAT runs recorded active NSS firmware packet-flow observations.
- No kernel fault signature was captured in the netconsole campaign log.
- The exact mechanism of iteration14's NSS failure is not established by this
  one layout-preserving comparison. Its rejected results are retained.
- Native runtime results are from iteration14; NSS runtime results are from15.
  They are diagnostic regressions, not matched long-duration CPU benchmarks.
- Original reset attribution and on-air802.11 fragmentation remain unqualified.
