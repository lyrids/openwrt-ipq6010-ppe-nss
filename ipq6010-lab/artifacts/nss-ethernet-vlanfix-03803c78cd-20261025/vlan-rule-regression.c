
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <errno.h>
#include <stdio.h>
typedef uint32_t u32;
enum {FLOW_OFFLOAD_DIR_ORIGINAL=0,FLOW_OFFLOAD_DIR_REPLY=1};
struct nss_core {int unused;};
struct nss_flow_pppoe {int unused;};
struct nss_flow_dir {bool pppoe;unsigned short sid,vtpid,vid;unsigned char mac[6],smac[6];int ifnum;u32 mtu;};
struct nss_flow_entry {struct nss_flow_dir dir[2];struct nss_flow_pppoe *pppoe;int pppoe_dir;};
static int calls;static u32 observed_tag;static struct nss_flow_pppoe session;
static struct nss_flow_pppoe *nss_flow_pppoe_ref(struct nss_core *c,unsigned short sid,const unsigned char *mac,const unsigned char *smac,int port,u32 mtu,u32 tag){(void)c;(void)sid;(void)mac;(void)smac;(void)port;(void)mtu;calls++;observed_tag=tag;return &session;}
#define IS_ERR(p) ((intptr_t)(p)<0)
#define PTR_ERR(p) ((intptr_t)(p))
static int nss_flow_pppoe_take(struct nss_core *core, struct nss_flow_entry *e)
{
	struct nss_flow_dir *o = &e->dir[FLOW_OFFLOAD_DIR_ORIGINAL];
	struct nss_flow_dir *r = &e->dir[FLOW_OFFLOAD_DIR_REPLY];
	struct nss_flow_dir *push, *wan;
	struct nss_flow_pppoe *p;
	u32 tag;

	/* A rule pushed again keeps the session it already holds. */
	if (e->pppoe)
		return 0;

	/* VLAN tags are carried by the IPv4/IPv6 rule independently of a
	 * PPPoE session. Only PPPoE on both sides is unsupported here.
	 */
	if (o->pppoe == r->pppoe)
		return o->pppoe ? -EOPNOTSUPP : 0;

	push = o->pppoe ? o : r;
	wan = o->pppoe ? r : o;
	e->pppoe_dir = o->pppoe ? FLOW_OFFLOAD_DIR_REPLY :
				  FLOW_OFFLOAD_DIR_ORIGINAL;
	tag = push->vtpid ? (u32)push->vtpid << 16 | push->vid : 0;

	p = nss_flow_pppoe_ref(core, push->sid, push->mac, push->smac,
			       wan->ifnum, wan->mtu, tag);
	if (IS_ERR(p))
		return PTR_ERR(p);
	e->pppoe = p;

	return 0;
}


int main(void){
 struct nss_core core={0};struct nss_flow_entry e={0};
 e.dir[1].vtpid=0x8100;e.dir[1].vid=100;
 assert(nss_flow_pppoe_take(&core,&e)==0&&!e.pppoe&&calls==0);
 e.dir[0].vtpid=0x8100;e.dir[0].vid=200;
 assert(nss_flow_pppoe_take(&core,&e)==0&&calls==0);
 puts("PASS: VLAN100 on one side and VLAN100/VLAN200 routing do not require PPPoE");
 e.dir[0].pppoe=e.dir[1].pppoe=true;
 assert(nss_flow_pppoe_take(&core,&e)==-EOPNOTSUPP&&calls==0);
 e.dir[0].pppoe=false;
 assert(nss_flow_pppoe_take(&core,&e)==0&&calls==1&&observed_tag==0x81000064&&e.pppoe);
 puts("PASS: two PPPoE sides remain rejected; existing PPPoE+VLAN100 session path preserved");
 return 0;
}
