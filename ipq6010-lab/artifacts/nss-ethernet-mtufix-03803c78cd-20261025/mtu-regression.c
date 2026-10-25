
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
typedef uint32_t u32;
enum flow_offload_tuple_dir {FLOW_OFFLOAD_DIR_ORIGINAL=0,FLOW_OFFLOAD_DIR_REPLY=1};
struct flow_offload_tuple {unsigned short mtu;};
struct flow_offload {struct {struct flow_offload_tuple tuple;} tuplehash[2];};
struct nss_flow_entry {bool bridged;unsigned long flow;};
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
static u32 nss_flow_effective_mtu(const struct nss_flow_entry *e,
				enum flow_offload_tuple_dir side, u32 mtu)
{
	const struct flow_offload *flow;

	if (e->bridged)
		return mtu;
	flow = (const void *)e->flow;
	return min_t(u32, mtu, flow->tuplehash[!side].tuple.mtu);
}


int main(void) {
 struct flow_offload flow={.tuplehash={{{1400}},{{1500}}}};
 struct nss_flow_entry e={.bridged=false,.flow=(unsigned long)&flow};
 assert(nss_flow_effective_mtu(&e,FLOW_OFFLOAD_DIR_ORIGINAL,1500)==1500);
 assert(nss_flow_effective_mtu(&e,FLOW_OFFLOAD_DIR_REPLY,1500)==1400);
 puts("PASS: routed bridge MTU clamps the correct direction");
 flow.tuplehash[0].tuple.mtu=1492;
 assert(nss_flow_effective_mtu(&e,FLOW_OFFLOAD_DIR_REPLY,1500-8)==1492);
 puts("PASS: PPPoE MTU1492 has no double subtraction");
 flow.tuplehash[0].tuple.mtu=9000;
 assert(nss_flow_effective_mtu(&e,FLOW_OFFLOAD_DIR_REPLY,1500)==1500);
 flow.tuplehash[0].tuple.mtu=0;
 assert(nss_flow_effective_mtu(&e,FLOW_OFFLOAD_DIR_REPLY,1500)==0);
 puts("PASS: physical ceiling preserved; missing routed MTU stays invalid");
 e.bridged=true;e.flow=0;
 assert(nss_flow_effective_mtu(&e,FLOW_OFFLOAD_DIR_REPLY,1500)==1500);
 puts("PASS: bridged connections never dereference a routed-flow pointer");
 return 0;
}
