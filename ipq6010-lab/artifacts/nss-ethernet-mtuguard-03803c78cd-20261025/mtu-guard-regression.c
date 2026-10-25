
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
typedef uint32_t u32;
enum flow_offload_tuple_dir {FLOW_OFFLOAD_DIR_ORIGINAL=0,FLOW_OFFLOAD_DIR_REPLY=1};
enum {FLOW_OFFLOAD_XMIT_DIRECT=1,FLOW_OFFLOAD_XMIT_NEIGH=2};
struct flow_offload_tuple {unsigned short mtu;int xmit_type;union {struct {int ifidx;}out;int ifidx;};};
struct flow_offload {struct {struct flow_offload_tuple tuple;}tuplehash[2];};
struct nss_flow_entry {bool bridged;unsigned long flow;};
struct net_device {u32 mtu;};
static int init_net,lookups;
static struct net_device devices[4];
static struct net_device *dev_get_by_index_rcu(void *net,int i){(void)net;lookups++;return i>0&&i<4?&devices[i]:0;}
#define READ_ONCE(x) (x)
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define scoped_guard(type,...) mock_scope()
#define mock_scope(...) for(int once=1;once;once=0)
static bool nss_flow_mtu_limited;
static u32 nss_flow_mtu_link[2], nss_flow_mtu_route[2], nss_flow_mtu_rule[2];
static int nss_flow_mtu_l3if[2];

static u32 nss_flow_effective_mtu(const struct nss_flow_entry *e,
				enum flow_offload_tuple_dir side, u32 mtu)
{
	const struct flow_offload_tuple *tuple;
	const struct flow_offload *flow;
	struct net_device *dev;
	u32 routed = mtu;
	int ifindex = 0;

	if (!e->bridged) {
		flow = (const void *)e->flow;
		/* The opposite direction routes back towards this NSS side. */
		tuple = &flow->tuplehash[!side].tuple;
		routed = READ_ONCE(tuple->mtu);
		switch (tuple->xmit_type) {
		case FLOW_OFFLOAD_XMIT_DIRECT:
			ifindex = tuple->out.ifidx;
			break;
		case FLOW_OFFLOAD_XMIT_NEIGH:
			ifindex = tuple->ifidx;
			break;
		default:
			routed = 0;
			break;
		}
		/* The direct path retains the original routed upper device
		 * separately from its physical hardware output interface.
		 * A bridge/VLAN MTU must not be replaced by the DSA port MTU.
		 */
		scoped_guard(rcu) {
			dev = dev_get_by_index_rcu(&init_net, ifindex);
			routed = dev ? min_t(u32, routed, READ_ONCE(dev->mtu)) : 0;
		}
	}
	nss_flow_mtu_link[side] = mtu;
	nss_flow_mtu_route[side] = routed;
	nss_flow_mtu_l3if[side] = ifindex;
	if (routed < mtu) {
		nss_flow_mtu_limited = true;
		nss_flow_mtu_rule[side] = 0;
		return 0;
	}
	nss_flow_mtu_rule[side] = mtu;
	return mtu;
}


int main(void){
 struct flow_offload f={0};struct nss_flow_entry e={false,(unsigned long)&f};
 f.tuplehash[0].tuple=(struct flow_offload_tuple){1500,FLOW_OFFLOAD_XMIT_DIRECT,.out={1}};
 f.tuplehash[1].tuple=(struct flow_offload_tuple){1500,FLOW_OFFLOAD_XMIT_DIRECT,.out={2}};
 devices[1].mtu=devices[2].mtu=1500;
 assert(nss_flow_effective_mtu(&e,0,1500)==1500);
 assert(nss_flow_effective_mtu(&e,1,1500)==1500);
 devices[1].mtu=1400;nss_flow_mtu_limited=false;
 assert(nss_flow_effective_mtu(&e,1,1500)==0&&nss_flow_mtu_limited);
 assert(nss_flow_mtu_route[1]==1400&&nss_flow_mtu_link[1]==1500&&nss_flow_mtu_l3if[1]==1);
 assert(f.tuplehash[0].tuple.mtu==1500);
 puts("PASS: normal1500 stays eligible; live bridge1400 overrides stale cached1500 and declines NSS");

 devices[1].mtu=1500;f.tuplehash[0].tuple.mtu=1400;
 assert(nss_flow_effective_mtu(&e,1,1500)==0);
 f.tuplehash[0].tuple.mtu=1500;devices[2].mtu=1350;
 assert(nss_flow_effective_mtu(&e,0,1500)==0);
 puts("PASS: both directional route limits and asymmetric MTUs are checked");

 devices[2].mtu=1500;devices[1].mtu=1492;f.tuplehash[0].tuple.mtu=1492;nss_flow_mtu_limited=false;
 assert(nss_flow_effective_mtu(&e,1,1500-8)==1492&&!nss_flow_mtu_limited);
 devices[1].mtu=1400;f.tuplehash[0].tuple.mtu=1400;
 assert(nss_flow_effective_mtu(&e,1,1492)==0);
 puts("PASS: standard PPPoE1492 retained without double subtraction; custom PPPoE1400 falls back");

 devices[1].mtu=9000;f.tuplehash[0].tuple.mtu=9000;
 assert(nss_flow_effective_mtu(&e,1,1500)==1500);
 f.tuplehash[0].tuple.out.ifidx=0;
 assert(nss_flow_effective_mtu(&e,1,1500)==0);
 f.tuplehash[0].tuple.xmit_type=FLOW_OFFLOAD_XMIT_NEIGH;f.tuplehash[0].tuple.ifidx=1;
 f.tuplehash[0].tuple.mtu=1500;devices[1].mtu=1500;
 assert(nss_flow_effective_mtu(&e,1,1500)==1500);
 e.bridged=true;e.flow=0;lookups=0;
 assert(nss_flow_effective_mtu(&e,1,1500)==1500&&lookups==0);
 puts("PASS: physical cap, missing device, neighbour route and bridged pointer safety");
 return 0;
}
