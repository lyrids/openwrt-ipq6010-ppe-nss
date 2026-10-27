#!/usr/bin/env python3
"""Force peer unmap at unlock in the actual TX-completion source tail."""
import argparse,difflib,hashlib,pathlib,subprocess,tempfile
p=argparse.ArgumentParser()
p.add_argument("--source",type=pathlib.Path,required=True)
p.add_argument("--archive",type=pathlib.Path,required=True)
p.add_argument("--patch",type=pathlib.Path,required=True)
p.add_argument("--output",type=pathlib.Path,required=True)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
old=a.source.read_text()
needle="\tspin_unlock_bh(&ab->base_lock);\n\n\tstatus.sta = peer->sta;"
assert old.count(needle)==1
pristine=subprocess.check_output(["tar","--zstd","-xOf",str(a.archive),"backports-7.2/drivers/net/wireless/ath/ath11k/dp_tx.c"],text=True)
assert needle in pristine,"Pattern is not in pristine backports"
(a.output/"origin.txt").write_text("Pristine OpenWrt backports7.2 contains the race before community patches.\nArchive SHA256: "+hashlib.sha256(a.archive.read_bytes()).hexdigest()+"\n")
new=old.replace(needle,"\tstatus.sta = peer->sta;\n\tspin_unlock_bh(&ab->base_lock);")
diff="".join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile="a/drivers/net/wireless/ath/ath11k/dp_tx.c",tofile="b/drivers/net/wireless/ath/ath11k/dp_tx.c"))
a.patch.write_text("""From: Yong Liu <lyrids@me.com>
Subject: [PATCH] wifi: ath11k: copy TX status station before releasing peer lock

Peer unmap frees struct ath11k_peer while holding ab->base_lock. Copy the
station pointer before releasing that lock so a concurrent unmap cannot
free the peer before the subsequent dereference. The existing mac80211
station lifetime rules and status callback context are unchanged.

Signed-off-by: Yong Liu <lyrids@me.com>

"""+diff)
prefix=r"""
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
struct sta { int alive; };
struct peer { struct sta *sta; };
struct ab { int base_lock; };
struct ar { void *hw; };
struct ts { int peer_id; };
struct status { struct sta *sta; void *info, *skb; };
static struct sta station = { 1 };
static struct peer *live;
#define ATH11K_DBG_DATA 0
#define ath11k_dbg(...) ((void)0)
static void spin_lock_bh(int *p) { (void)p; }
static void spin_unlock_bh(int *p) {
 (void)p;
 /* Legal competing unmap after the lock is released, before the next load. */
 __asm__ __volatile__("" ::: "memory");
 free(live); live = NULL;
 __asm__ __volatile__("" ::: "memory");
}
static struct peer *ath11k_peer_find_by_id(struct ab *a, int id) {
 (void)a; (void)id; return live;
}
static void ieee80211_free_txskb(void *hw, void *skb) {
 (void)hw; (void)skb; abort();
}
static void ieee80211_tx_status_ext(void *hw, struct status *status) {
 (void)hw; assert(status->sta == &station); assert(status->sta->alive);
}
static void exercise(void) {
 struct ab base = {0}, *ab = &base;
 struct ar radio = {0}, *ar = &radio;
 struct ts event = {1}, *ts = &event;
 struct status status = {0};
 struct peer *peer;
 void *info = NULL, *msdu = NULL;
 live = malloc(sizeof(*live)); assert(live); live->sta = &station;
"""
suffix="\n}\nint main(void) { exercise(); puts(\"source-tail interleaving passed\"); return 0; }\n"
for name,src in [("before",old),("after",new)]:
 start=src.index("\tspin_lock_bh(&ab->base_lock);",src.index("ath11k_dp_tx_htt_tx_complete_buf("))
 end=src.index("\n}\n",start)
 c=a.output/(name+".c");c.write_text(prefix+src[start:end]+suffix)
 binary=a.output/name
 subprocess.run(["cc","-O1","-g","-fsanitize=address","-fno-omit-frame-pointer",str(c),"-o",str(binary)],check=True)
 result=subprocess.run([str(binary)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env={"ASAN_OPTIONS":"detect_leaks=0"})
 (a.output/(name+".log")).write_text(result.stdout)
 if name=="before":
  assert result.returncode!=0 and "heap-use-after-free" in result.stdout,result.stdout
 else:assert result.returncode==0,result.stdout
 print(name,result.returncode,"expected failure" if name=="before" else "passed")
print((a.output/"origin.txt").read_text())
