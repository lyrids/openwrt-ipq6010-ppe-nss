from pathlib import Path
import subprocess
w=Path.home()/"projects/openwrt-dev";r=w/"artifacts/nss-ethernet-vlanfix-03803c78cd-20261025";t=w/"src/openwrt-ppe-nss"
s=(t/"package/kernel/nss-wifi-drv/src/nss_flow.c").read_text();a=s.index("static int nss_flow_pppoe_take(");b=s.index("/* What the rule says",a);actual=s[a:b]
stub=r'''
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
'''
main=r'''
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
'''
p=r/"vlan-rule-regression.c";p.write_text(stub+actual+main)
subprocess.run(["gcc","-std=gnu17","-Wall","-Wextra","-Werror","-g","-O1","-fsanitize=address,undefined",str(p),"-o",str(r/"vlan-rule-regression")],check=True)
out=subprocess.check_output([str(r/"vlan-rule-regression")],text=True);(r/"vlan-rule-regression.txt").write_text(out);print(out)

