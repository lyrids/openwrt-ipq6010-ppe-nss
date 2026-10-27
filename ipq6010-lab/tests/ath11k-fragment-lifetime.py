#!/usr/bin/env python3
"""Exercise actual patched timer/peer helpers with a pthread timer/work shim.

This checks helper ordering and lifetime contracts, not firmware or the Linux
timer implementation. It does not send crafted wireless traffic.
"""
import argparse
import pathlib
import subprocess

ap = argparse.ArgumentParser()
ap.add_argument("--source", required=True, type=pathlib.Path)
ap.add_argument("--output", required=True, type=pathlib.Path)
args = ap.parse_args()
args.output.mkdir(parents=True, exist_ok=True)

def extract(file, name):
    text = (args.source / file).read_text()
    start = text.index(name + "(")
    start = text.rfind("\n", 0, start) + 1
    brace = text.index("{", start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end] + "\n"

functions = "\n".join(extract(f, n) for f, n in [
    ("dp_rx.c", "ath11k_peer_frags_flush"),
    ("dp_rx.c", "ath11k_dp_rx_frag_timer"),
    ("dp_rx.c", "ath11k_peer_rx_frag_init"),
    ("peer.c", "ath11k_peer_delete_work"),
    ("peer.c", "ath11k_peer_free"),
])

# Check the integration properties not covered by helper-level execution.
rx = extract("dp_rx.c", "ath11k_dp_rx_frag_h_mpdu")
handoff = rx[rx.index("rx_tid = &peer->rx_tid[tid];"):rx.index("out_unlock:")]
assert "spin_unlock_bh" not in handoff
assert "timer_delete_sync" not in handoff
dp = extract("dp.c", "ath11k_dp_peer_cleanup")
assert dp.index("peer->dp_setup_done = false") < dp.index("ath11k_peer_rx_tid_cleanup")
for f in ["peer.c", "mac.c"]:
    text = (args.source / f).read_text()
    expected = 1 if f == "peer.c" else 0
    assert text.count("kfree(peer);") == expected, f
for name in ["ath11k_peer_frags_flush", "ath11k_peer_rx_tid_cleanup"]:
    body = extract("dp_rx.c", name)
    assert "spin_unlock_bh" not in body and "timer_delete_sync" not in body

prefix = r"""
#include <assert.h>
#include <pthread.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <stdio.h>
#define timer_delete test_timer_delete
#define skb_queue_head_init(p) (*(p) = 0)
#define IEEE80211_NUM_TIDS 16
#define GENMASK(h,l) (((1U << ((h) + 1)) - 1) & ~((1U << (l)) - 1))
#define container_of(p,t,m) ((t *)((char *)(p) - offsetof(t,m)))
#define timer_container_of(v,t,m) container_of(t,struct dp_rx_tid,m)
#define spin_lock_bh(p) assert(pthread_mutex_lock(p) == 0)
#define spin_unlock_bh(p) assert(pthread_mutex_unlock(p) == 0)
#define lockdep_assert_held(p) ((void)(p))
struct ath11k_peer;
struct timer_list {
    bool pending, running, shutdown;
    pthread_mutex_t lock;
    pthread_cond_t done;
    void (*fn)(struct timer_list *);
};
struct work_struct { void (*fn)(struct work_struct *); };
struct ath11k_base { pthread_mutex_t base_lock; void *workqueue; };
struct dp_rx_tid {
    struct ath11k_base *ab;
    struct timer_list frag_timer;
    unsigned last_frag_no, rx_frag_bitmap, fragments, rx_frags;
};
struct ath11k_peer {
    struct work_struct delete_work;
    struct dp_rx_tid rx_tid[IEEE80211_NUM_TIDS + 1];
    bool dp_setup_done;
};
static atomic_int freed, shutdowns, callbacks;
static pthread_t worker, callback;
static pthread_mutex_t gate_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t gate = PTHREAD_COND_INITIALIZER;
static bool callback_started, shutdown_waiting;

static void timer_setup(struct timer_list *t, void (*fn)(struct timer_list *), int flags)
{
    (void)flags;
    assert(!pthread_mutex_init(&t->lock, NULL));
    assert(!pthread_cond_init(&t->done, NULL));
    t->fn = fn;
}
static int timer_delete(struct timer_list *t)
{
    pthread_mutex_lock(&t->lock);
    int ret = t->pending;
    t->pending = false;
    pthread_mutex_unlock(&t->lock);
    return ret;
}
static bool timer_pending(struct timer_list *t)
{
    pthread_mutex_lock(&t->lock);
    bool ret = t->pending;
    pthread_mutex_unlock(&t->lock);
    return ret;
}
static void timer_shutdown_sync(struct timer_list *t)
{
    pthread_mutex_lock(&t->lock);
    t->shutdown = true;
    t->pending = false;
    while (t->running) {
        pthread_mutex_lock(&gate_lock);
        shutdown_waiting = true;
        pthread_cond_broadcast(&gate);
        pthread_mutex_unlock(&gate_lock);
        pthread_cond_wait(&t->done, &t->lock);
    }
    pthread_mutex_unlock(&t->lock);
    atomic_fetch_add(&shutdowns, 1);
}
static void ath11k_dp_rx_frags_cleanup(struct dp_rx_tid *t, bool release)
{
    (void)release;
    t->last_frag_no = 0;
    t->rx_frag_bitmap = 0;
    t->fragments = 0;
}
static void kfree(struct ath11k_peer *p)
{
    for (int i = 0; i <= IEEE80211_NUM_TIDS; i++) {
        struct timer_list *t = &p->rx_tid[i].frag_timer;
        assert(t->shutdown && !t->running && !t->pending);
        assert(!p->rx_tid[i].fragments);
        pthread_mutex_destroy(&t->lock);
        pthread_cond_destroy(&t->done);
    }
    assert(!p->dp_setup_done);
    atomic_fetch_add(&freed, 1);
    free(p);
}
static void *run_work(void *arg)
{
    struct work_struct *w = arg;
    w->fn(w);
    return NULL;
}
static bool queue_work(void *queue, struct work_struct *w)
{
    (void)queue;
    assert(!pthread_create(&worker, NULL, run_work, w));
    return true;
}
"""
suffix = r"""
static struct ath11k_base ab;
static struct ath11k_peer *new_peer(void)
{
    struct ath11k_peer *p = calloc(1, sizeof(*p));
    assert(p);
    p->delete_work.fn = ath11k_peer_delete_work;
    ath11k_peer_rx_frag_init(&ab, p);
    p->dp_setup_done = true;
    return p;
}
static void *run_callback(void *arg)
{
    struct timer_list *t = arg;
    pthread_mutex_lock(&t->lock);
    t->running = true;
    t->pending = false;
    pthread_mutex_unlock(&t->lock);
    pthread_mutex_lock(&gate_lock);
    callback_started = true;
    pthread_cond_broadcast(&gate);
    pthread_mutex_unlock(&gate_lock);
    t->fn(t);
    atomic_fetch_add(&callbacks, 1);
    pthread_mutex_lock(&t->lock);
    t->running = false;
    pthread_cond_broadcast(&t->done);
    pthread_mutex_unlock(&t->lock);
    return NULL;
}
static void start_callback(struct timer_list *t)
{
    callback_started = false;
    shutdown_waiting = false;
    assert(!pthread_create(&callback, NULL, run_callback, t));
    pthread_mutex_lock(&gate_lock);
    while (!callback_started)
        pthread_cond_wait(&gate, &gate_lock);
    pthread_mutex_unlock(&gate_lock);
}
static void retire(struct ath11k_peer *p)
{
    spin_lock_bh(&ab.base_lock);
    ath11k_peer_free(&ab, p);
    spin_unlock_bh(&ab.base_lock);
    pthread_join(worker, NULL);
}
int main(void)
{
    assert(!pthread_mutex_init(&ab.base_lock, NULL));
    /* A callback waiting for base_lock must not clean a newer expiry. */
    struct ath11k_peer *p = new_peer();
    spin_lock_bh(&ab.base_lock);
    start_callback(&p->rx_tid[0].frag_timer);
    pthread_mutex_lock(&p->rx_tid[0].frag_timer.lock);
    p->rx_tid[0].frag_timer.pending = true;
    pthread_mutex_unlock(&p->rx_tid[0].frag_timer.lock);
    p->rx_tid[0].fragments = 7;
    spin_unlock_bh(&ab.base_lock);
    pthread_join(callback, NULL);
    assert(p->rx_tid[0].fragments == 7);
    retire(p);
    puts("PASS: stale expiry preserves rearmed fragment sequence");

    /* Deletion holds allocation while a callback waits on base_lock. */
    p = new_peer();
    spin_lock_bh(&ab.base_lock);
    start_callback(&p->rx_tid[0].frag_timer);
    p->rx_tid[0].fragments = 3;
    int before = atomic_load(&freed);
    ath11k_peer_free(&ab, p);
    pthread_mutex_lock(&gate_lock);
    while (!shutdown_waiting)
        pthread_cond_wait(&gate, &gate_lock);
    pthread_mutex_unlock(&gate_lock);
    assert(atomic_load(&freed) == before);
    spin_unlock_bh(&ab.base_lock);
    pthread_join(callback, NULL);
    pthread_join(worker, NULL);
    assert(atomic_load(&freed) == before + 1);
    puts("PASS: peer free waits for callback completion without lock deadlock");

    /* Key flush cancels pending timeout and purges all TID queues. */
    p = new_peer();
    spin_lock_bh(&ab.base_lock);
    for (int i = 0; i <= IEEE80211_NUM_TIDS; i++) {
        p->rx_tid[i].frag_timer.pending = true;
        p->rx_tid[i].fragments = 2;
    }
    ath11k_peer_frags_flush(&ab, p);
    for (int i = 0; i <= IEEE80211_NUM_TIDS; i++) {
        assert(!p->rx_tid[i].fragments);
        assert(!timer_pending(&p->rx_tid[i].frag_timer));
    }
    spin_unlock_bh(&ab.base_lock);
    retire(p);
    puts("PASS: key flush cancels pending timers and clears every TID");
    assert(atomic_load(&freed) == 3);
    assert(atomic_load(&shutdowns) == 3 * (IEEE80211_NUM_TIDS + 1));
    assert(atomic_load(&callbacks) == 2);
    pthread_mutex_destroy(&ab.base_lock);
    return 0;
}
"""
source = args.output / "fragment-lifetime.c"
source.write_text(prefix + functions + suffix)
binary = args.output / "fragment-lifetime"
subprocess.run(["cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror", "-g",
                "-fsanitize=address,undefined", "-pthread",
                str(source), "-o", str(binary)], check=True)
result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
(args.output / "result.log").write_text(result.stdout + result.stderr)
print(result.stdout, end="")
print(result.stderr, end="")
result.check_returncode()
print("PASS: source integration checks; ASAN/UBSAN fixed-helper tests")
