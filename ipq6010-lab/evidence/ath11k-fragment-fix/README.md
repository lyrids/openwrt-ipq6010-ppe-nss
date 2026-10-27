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
