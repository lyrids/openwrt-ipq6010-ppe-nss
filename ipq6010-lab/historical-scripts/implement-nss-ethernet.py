from pathlib import Path
w=Path.home()/"projects/openwrt-dev"
t=w/"src/openwrt-ppe-nss"
def edit(name,old,new):
 p=t/name;s=p.read_text()
 assert s.count(old)==1,(name,old[:100],s.count(old))
 p.write_text(s.replace(old,new))
base="target/linux/qualcommax/files/"
pub=base+"include/linux/soc/qcom/qca_ppe.h"
edit(pub,"int qca_ppe_fw_booted", """struct flow_cls_offload;
struct flow_block;

/* Optional firmware route backend. A NULL rule withdraws a released block.
 * owned=true means PPE may only steer this connection, never route/NAT it.
 * The callback may sleep; unregister waits for in-flight callbacks.
 */
int qca_ppe_fw_flow_set(struct net_device *conduit,
        int (*handler)(struct flow_cls_offload *, const struct flow_block *,
                       bool *));
int qca_ppe_fw_booted""")
h=base+"drivers/net/ethernet/qualcomm/qca_ppe.h"
edit(h,"\tbool (__rcu *fw_carries)(int ifindex);",
"""\tbool (__rcu *fw_carries)(int ifindex);
\tint (__rcu *fw_flow)(struct flow_cls_offload *,
\t\t\t    const struct flow_block *, bool *);""")
edit(h,"void ppe_flow_init(struct qca_ppe_priv *priv);",
"""int ppe_fw_flow_offload(struct qca_ppe_priv *priv,
\t\t       struct flow_cls_offload *f,
\t\t       const struct flow_block *block, bool *owned);
void ppe_flow_purge_steer(struct qca_ppe_priv *priv);
void ppe_flow_init(struct qca_ppe_priv *priv);""")
main=base+"drivers/net/ethernet/qualcomm/qca_ppe_main.c"
edit(main,'#include <linux/reset.h>','#include <linux/reset.h>\n#include <linux/srcu.h>')
edit(main,'#define PPE_MIB_FOLD_INTERVAL',
"""/* Firmware messages can sleep; regular RCU is not sufficient here. */
DEFINE_STATIC_SRCU(ppe_fw_flow_srcu);

int ppe_fw_flow_offload(struct qca_ppe_priv *priv,
\t\t       struct flow_cls_offload *f,
\t\t       const struct flow_block *block, bool *owned)
{
\tint (*handler)(struct flow_cls_offload *, const struct flow_block *,
\t\t       bool *);
\tint idx, ret = 0;

\t*owned = false;
\tidx = srcu_read_lock(&ppe_fw_flow_srcu);
\thandler = srcu_dereference(priv->fw_flow, &ppe_fw_flow_srcu);
\tif (handler)
\t\tret = handler(f, block, owned);
\tsrcu_read_unlock(&ppe_fw_flow_srcu, idx);
\treturn ret;
}

int qca_ppe_fw_flow_set(struct net_device *conduit,
\t\tint (*handler)(struct flow_cls_offload *,
\t\t\t       const struct flow_block *, bool *))
{
\tstruct qca_ppe_priv *priv;

\tif (!conduit || !netdev_uses_dsa(conduit) ||
\t    conduit->dsa_ptr->ds->ops != &qca_ppe_ops)
\t\treturn -ENODEV;
\tpriv = ds_to_priv(conduit->dsa_ptr->ds);
\tif (handler && rcu_access_pointer(priv->fw_flow) &&
\t    rcu_access_pointer(priv->fw_flow) != handler)
\t\treturn -EBUSY;
\trcu_assign_pointer(priv->fw_flow, handler);
\tif (!handler) {
\t\tsynchronize_srcu(&ppe_fw_flow_srcu);
\t\tppe_flow_purge_steer(priv);
\t}
\treturn 0;
}
EXPORT_SYMBOL_GPL(qca_ppe_fw_flow_set);

#define PPE_MIB_FOLD_INTERVAL""")
# qca_ppe_ops is defined below; add a forward declaration.
edit(main,'#include "qca_ppe.h"','#include "qca_ppe.h"\n\nstatic const struct dsa_switch_ops qca_ppe_ops;')
flow=base+"drivers/net/ethernet/qualcomm/qca_ppe_flow_offload.c"
edit(flow,"static int ppe_flow_offload_replace(struct ppe_flow_block *fb,\n\t\t\t\t    struct flow_cls_offload *f)",
"""static int ppe_flow_offload_replace(struct ppe_flow_block *fb,
\t\t\t\t    struct flow_cls_offload *f,
\t\t\t\t    bool firmware_owned)""")
edit(flow,"\tsteer = ppe_flow_fw_carries(priv, data.odev);",
"\tsteer = firmware_owned || ppe_flow_fw_carries(priv, data.odev);")
start="""\tswitch (cls->command) {
\tcase FLOW_CLS_REPLACE:
\t\treturn ppe_flow_offload_replace(fb, cls);
\tcase FLOW_CLS_DESTROY:
\t\treturn ppe_flow_offload_destroy(priv, cls);
\tcase FLOW_CLS_STATS:
\t\treturn ppe_flow_offload_stats(priv, cls);
\tdefault:
\t\treturn -EOPNOTSUPP;
\t}
}"""
replacement="""\t{
\t\tbool owned;
\t\tint ret, ppe_ret;

\t\tret = ppe_fw_flow_offload(priv, cls, fb->block, &owned);
\t\tif (owned) {
\t\t\tswitch (cls->command) {
\t\t\tcase FLOW_CLS_REPLACE:
\t\t\t\tif (ret)
\t\t\t\t\treturn ret;
\t\t\t\t/* Firmware performs L3/NAT. PPE delivers the
\t\t\t\t * original packet to its CPU port unchanged.
\t\t\t\t */
\t\t\t\tppe_ret = ppe_flow_offload_replace(fb, cls, true);
\t\t\t\tif (ppe_ret) {
\t\t\t\t\tstruct flow_cls_offload undo = *cls;

\t\t\t\t\tundo.command = FLOW_CLS_DESTROY;
\t\t\t\t\tppe_fw_flow_offload(priv, &undo, fb->block,
\t\t\t\t\t\t\t    &owned);
\t\t\t\t}
\t\t\t\treturn ppe_ret;
\t\t\tcase FLOW_CLS_DESTROY:
\t\t\t\tppe_ret = ppe_flow_offload_destroy(priv, cls);
\t\t\t\treturn ret ? ret : ppe_ret == -ENOENT ? 0 : ppe_ret;
\t\t\tcase FLOW_CLS_STATS:
\t\t\t\treturn ret;
\t\t\tdefault:
\t\t\t\treturn -EOPNOTSUPP;
\t\t\t}
\t\t}
\t}

\tswitch (cls->command) {
\tcase FLOW_CLS_REPLACE:
\t\treturn ppe_flow_offload_replace(fb, cls, false);
\tcase FLOW_CLS_DESTROY:
\t\treturn ppe_flow_offload_destroy(priv, cls);
\tcase FLOW_CLS_STATS:
\t\treturn ppe_flow_offload_stats(priv, cls);
\tdefault:
\t\treturn -EOPNOTSUPP;
\t}
}"""
edit(flow,start,replacement)
edit(flow,"static LIST_HEAD(ppe_block_cb_list);",
"""/* Firmware halt must not leave connections steered at a dead core. */
void ppe_flow_purge_steer(struct qca_ppe_priv *priv)
{
\tstruct ppe_flow_entry *entry, *tmp;

\tguard(mutex)(&priv->flow_lock);
\tguard(mutex)(&priv->vlan_lock);
\tlist_for_each_entry_safe(entry, tmp, &priv->flow_list, list)
\t\tif (entry->steer)
\t\t\tppe_flow_free(priv, entry);
}

static LIST_HEAD(ppe_block_cb_list);""")
edit(flow,"""\tstruct ppe_flow_entry *entry, *tmp;

\tmutex_lock(&priv->flow_lock);""",
"""\tstruct ppe_flow_entry *entry, *tmp;
\tbool owned;

\t/* Withdraw firmware rules before freeing their steering entries. */
\tppe_fw_flow_offload(priv, NULL, fb->block, &owned);
\tmutex_lock(&priv->flow_lock);""")
n="package/kernel/nss-wifi-drv/src/"
# The feature is boot-selected; no live ownership switch.
edit(n+"nss_flow.c","static struct nss_core *nss_flow_core;",
"""static struct nss_core *nss_flow_core;
static bool nss_ethernet_offload;
module_param_named(ethernet_offload, nss_ethernet_offload, bool, 0444);
MODULE_PARM_DESC(ethernet_offload,
\t"Experimental Ethernet routed/NAT flow backend; select at module load");
static u32 nss_ethernet_offers, nss_ethernet_pushed;
static u32 nss_ethernet_rejected;
""")
edit(n+"nss_flow.c","#include <linux/mutex.h>","#include <linux/mutex.h>\n#include <linux/module.h>")
edit(n+"nss_flow.c","struct nss_flow_entry {",
"""struct nss_flow_entry {
\tconst struct flow_block *ppe_block;
\tbool ethernet;""")
edit(n+"nss_flow.c","static int nss_flow_replace(struct nss_core *core, struct flow_cls_offload *f)",
"""static int nss_flow_replace(struct nss_core *core, struct flow_cls_offload *f,
\t\t\t    bool ethernet)""")
edit(n+"nss_flow.c","""\t\tif (!nss_flow_is_ours(meta.key->ingress_ifindex) &&
\t\t    !nss_flow_is_ours(flow->tuplehash[!dir].tuple.iifidx)) {""",
"""\t\tif (!ethernet &&
\t\t    !nss_flow_is_ours(meta.key->ingress_ifindex) &&
\t\t    !nss_flow_is_ours(flow->tuplehash[!dir].tuple.iifidx)) {""")
edit(n+"nss_flow.c","\t\te->flow = key;",
"\t\te->flow = key;\n\t\te->ethernet = ethernet;")
edit(n+"nss_flow.c","return nss_flow_replace(core, f);","return nss_flow_replace(core, f, false);")
# Header declarations for core startup.
edit(n+"nss_drv.h","int nss_flow_init(void);",
"""int nss_flow_init(void);
int nss_ethernet_setup(struct net_device *conduit);
void nss_ethernet_stop(struct net_device *conduit);""")
edit(n+"nss_flow.c","#include <linux/soc/qcom/nss_wifi.h>",
'#include <linux/soc/qcom/nss_wifi.h>\n#include <linux/soc/qcom/qca_ppe.h>')
anchor="/* Withdraw every routed rule through @dev."
helper="""/* This path is offered through the PPE's own DSA block, so no
 * netfilter patch or second device-level classifier is needed.
 */
static bool nss_ethernet_port(struct nss_core *core, int ifindex)
{
\tstruct net_device *dev;
\tu32 mtu;

\tguard(rcu)();
\tdev = dev_get_by_index_rcu(&init_net, ifindex);
\treturn dev && dsa_user_dev_check(dev) &&
\t       nss_flow_ifnum(core, ifindex, &mtu) >= 0;
}

static int nss_ethernet_flow(struct flow_cls_offload *f,
\t\t\t     const struct flow_block *block, bool *owned)
{
\tstruct nss_flow_entry *e;
\tstruct nss_core *core;
\tstruct flow_offload *flow;
\tstruct flow_rule *rule;
\tunsigned long key;
\tbool installed;
\tint ret;

\t*owned = false;
\tguard(mutex)(&nss_flow_lock);
\tcore = nss_flow_core;
\tif (!nss_ethernet_offload || !core || !core->running)
\t\treturn 0;

\tif (!f) {
\t\tstruct rhashtable_iter iter;

\t\t/* Blocks disappear before their flows get DESTROY offers. */
\t\tdo {
\t\t\trhashtable_walk_enter(&nss_flow_table, &iter);
\t\t\trhashtable_walk_start(&iter);
\t\t\twhile ((e = rhashtable_walk_next(&iter)) != NULL)
\t\t\t\tif (!IS_ERR(e) && e->ethernet &&
\t\t\t\t    e->ppe_block == block)
\t\t\t\t\tbreak;
\t\t\trhashtable_walk_stop(&iter);
\t\t\trhashtable_walk_exit(&iter);
\t\t\tif (e)
\t\t\t\tnss_flow_forget(core, e);
\t\t} while (e);
\t\treturn 0;
\t}

\tflow = nss_flow_of(f->cookie);
\tkey = (unsigned long)flow;
\te = rhashtable_lookup_fast(&nss_flow_table, &key, nss_flow_ht_params);
\tif (e && e->ethernet) {
\t\t*owned = true;
\t\tif (f->command == FLOW_CLS_DESTROY)
\t\t\treturn nss_flow_destroy(core, f);
\t\tif (f->command == FLOW_CLS_STATS)
\t\t\treturn nss_flow_stats(core, f);
\t}
\tif (f->command != FLOW_CLS_REPLACE)
\t\treturn 0;

\t/* Both ends must be physical ports that this core has armed. */
\tif (!nss_ethernet_port(core, flow->tuplehash[0].tuple.iifidx) ||
\t    !nss_ethernet_port(core, flow->tuplehash[1].tuple.iifidx))
\t\treturn 0;
\t*owned = true;
\tnss_ethernet_offers++;
\trule = flow_cls_offload_flow_rule(f);
\tif (flow_rule_match_key(rule, FLOW_DISSECTOR_KEY_CVLAN)) {
\t\tret = -EOPNOTSUPP;
\t\tgoto reject;
\t}
\tif (flow_rule_match_key(rule, FLOW_DISSECTOR_KEY_VLAN)) {
\t\tstruct flow_match_vlan vlan;

\t\tflow_rule_match_vlan(rule, &vlan);
\t\tif (vlan.key->vlan_tpid != htons(ETH_P_8021Q)) {
\t\t\tret = -EOPNOTSUPP;
\t\t\tgoto reject;
\t\t}
\t}
\tinstalled = e && e->installed;
\tret = nss_flow_replace(core, f, true);
\tif (ret)
\t\tgoto reject;
\te = rhashtable_lookup_fast(&nss_flow_table, &key, nss_flow_ht_params);
\tif (e) {
\t\te->ppe_block = block;
\t\tif (e->installed && !installed)
\t\t\tnss_ethernet_pushed++;
\t}
\treturn 0;
reject:
\tnss_ethernet_rejected++;
\treturn ret;
}

int nss_ethernet_setup(struct net_device *conduit)
{
\tif (!nss_ethernet_offload)
\t\treturn 0;
\treturn qca_ppe_fw_flow_set(conduit, nss_ethernet_flow);
}

void nss_ethernet_stop(struct net_device *conduit)
{
\tqca_ppe_fw_flow_set(conduit, NULL);
}

"""
edit(n+"nss_flow.c",anchor,helper+anchor)
edit(n+"nss_flow.c",'\tseq_printf(s, "bound %u pushed %u last-ifindex %d\\n",',
"""\tseq_printf(s, "ethernet enabled %u offers %u pushed %u rejected %u\\\\n",
\t\t   nss_ethernet_offload, nss_ethernet_offers,
\t\t   nss_ethernet_pushed, nss_ethernet_rejected);
\tseq_printf(s, "bound %u pushed %u last-ifindex %d\\n",""".replace('\\\\n','\\n'))
# Add explicit Ethernet identification to the existing flow display.
edit(n+"nss_flow.c",'e->bridged ? " bridged" : "",','e->bridged ? " bridged" : e->ethernet ? " ethernet" : "",')
edit(n+"nss_core.c","\tqca_ppe_fw_carrier_set(core->conduit, NULL);",
"\tnss_ethernet_stop(core->conduit);\n\tqca_ppe_fw_carrier_set(core->conduit, NULL);")
edit(n+"nss_core.c","\tnss_pool_configure(core);",
"""\tret = nss_ethernet_setup(core->conduit);
\tif (ret) {
\t\tdev_err(core->dev, "Ethernet backend setup failed: %d\\\\n", ret);
\t\tnss_core_halt(core);
\t\treturn ret;
\t}

\tnss_pool_configure(core);""".replace('\\\\n','\\n'))
init="package/kernel/nss-wifi-drv/files/nss-wifi.init"
edit(init,"\tmodprobe nss-wifi-drv 2>/dev/null",
"""\tif [ "$(uci -q get nss-wifi.general.ethernet_offload)" = "1" ]; then
\t\tmodprobe nss-wifi-drv ethernet_offload=1 2>/dev/null
\telse
\t\tmodprobe nss-wifi-drv 2>/dev/null
\tfi""")
cfg="package/kernel/nss-wifi-drv/files/nss-wifi.config"
p=t/cfg;p.write_text(p.read_text()+"\n\t# Experimental Ethernet-only routed/NAT backend, chosen at boot.\n\toption ethernet_offload '0'\n")
print("Experimental Ethernet backend source changes applied.")

