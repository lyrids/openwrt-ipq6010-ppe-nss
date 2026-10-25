from pathlib import Path
w=Path.home()/"projects/openwrt-dev";t=w/"src/openwrt-ppe-nss"
p=t/"package/kernel/nss-wifi-drv/src/nss_flow.c";s=p.read_text()
s=s.replace('''	if (o->pppoe == r->pppoe) {
		/* ponytail: VLAN without PPPoE is not offloaded yet */
		return (o->pppoe || o->vtpid || r->vtpid) ? -EOPNOTSUPP : 0;
	}
''','''	/* VLAN tags are carried by the IPv4/IPv6 rule independently of a
	 * PPPoE session. Only PPPoE on both sides is unsupported here.
	 */
	if (o->pppoe == r->pppoe)
		return o->pppoe ? -EOPNOTSUPP : 0;
''')
needle='static bool nss_ethernet_offload;'
assert needle in s
s=s.replace(needle,'''/* One-shot failure injection for paired-rule rollback validation. */
static unsigned int nss_ethernet_fail_create;
module_param_named(ethernet_fail_create, nss_ethernet_fail_create, uint, 0644);
MODULE_PARM_DESC(ethernet_fail_create, "fail this many complete Ethernet rule offers");

'''+needle)
needle='''	ret = nss_flow_pppoe_take(core, e);
'''
assert s.count(needle)==1
s=s.replace(needle,'''	if (ethernet && nss_ethernet_fail_create) {
		nss_ethernet_fail_create--;
		ret = -EIO;
		goto drop;
	}

'''+needle)
needle='''	*owned = true;
	nss_ethernet_offers++;
'''
s=s.replace(needle,'''	*owned = true;
	if (!test_bit(NF_FLOW_HW_BIDIRECTIONAL, &flow->flags))
		return -EOPNOTSUPP;
	nss_ethernet_offers++;
''')
needle='''		if (e->installed && !installed)
			nss_ethernet_pushed++;
	}
	return 0;
reject:
'''
assert needle in s
s=s.replace(needle,'''		if (e->installed && !installed)
			nss_ethernet_pushed++;
	}
	/* Do not let PPE steer either half until the firmware accepted the
	 * complete connection. The caller saves the first offer for later.
	 */
	return e && e->installed ? 0 : -EAGAIN;
reject:
''')
p.write_text(s)
p=t/"target/linux/qualcommax/files/drivers/net/ethernet/qualcomm/qca_ppe.h";s=p.read_text()
s=s.replace('\tbool fw_flow_reserved;','''	struct mutex fw_pending_lock;
	struct list_head fw_pending;
	bool fw_flow_reserved;''')
p.write_text(s)
p=t/"target/linux/qualcommax/files/drivers/net/ethernet/qualcomm/qca_ppe_flow_offload.c";s=p.read_text()
start=s.index('static int ppe_flow_block_cb(');end=s.index('/* Firmware halt must not leave',start)
s=s[:start]+'''/* A firmware rule needs both directional offers. Keep an owned copy of
 * the first, never pointers into nf_flow_rule memory freed by the caller.
 * Only netfilter flowtable rules reach this callback.
 */
struct ppe_fw_pending {
	struct list_head list;
	struct flow_block *block;
	unsigned long flow;
	struct flow_cls_offload cls;
	struct nf_flow_rule saved;
};

static struct flow_offload *ppe_fw_connection(unsigned long cookie)
{
	const struct flow_offload_tuple *tuple = (const void *)cookie;
	struct flow_offload_tuple_rhash *th;

	th = container_of(tuple, struct flow_offload_tuple_rhash, tuple);
	return container_of(th - tuple->dir, struct flow_offload, tuplehash[0]);
}

static void ppe_fw_pending_free(struct ppe_fw_pending *pending)
{
	struct flow_action_entry *act;
	int i;

	flow_action_for_each(i, act, &pending->saved.rule->action)
		if (act->id == FLOW_ACTION_REDIRECT)
			dev_put(act->dev);
	list_del(&pending->list);
	kfree(pending->saved.rule);
	kfree(pending);
}

/* fw_pending_lock serializes offers, rollback and firmware-stop cleanup. */
static void ppe_fw_pending_drop(struct qca_ppe_priv *priv,
			       struct flow_block *block, unsigned long flow)
{
	struct ppe_fw_pending *pending, *tmp;

	list_for_each_entry_safe(pending, tmp, &priv->fw_pending, list)
		if ((!block || pending->block == block) &&
		    (!flow || pending->flow == flow))
			ppe_fw_pending_free(pending);
}

static int ppe_fw_pending_save(struct ppe_flow_block *fb,
			       struct flow_cls_offload *cls)
{
	struct flow_rule *rule = flow_cls_offload_flow_rule(cls);
	struct ppe_fw_pending *pending, *old, *tmp;
	struct flow_action_entry *act;
	int i;

	pending = kzalloc(sizeof(*pending), GFP_KERNEL);
	if (!pending)
		return -ENOMEM;
	pending->saved.rule = flow_rule_alloc(rule->action.num_entries);
	if (!pending->saved.rule) {
		kfree(pending);
		return -ENOMEM;
	}
	pending->saved.match.dissector = *rule->match.dissector;
	memcpy(&pending->saved.match.key, rule->match.key,
	       sizeof(pending->saved.match.key));
	memcpy(&pending->saved.match.mask, rule->match.mask,
	       sizeof(pending->saved.match.mask));
	pending->saved.rule->match.dissector = &pending->saved.match.dissector;
	pending->saved.rule->match.key = &pending->saved.match.key;
	pending->saved.rule->match.mask = &pending->saved.match.mask;
	memcpy(pending->saved.rule->action.entries, rule->action.entries,
	       sizeof(rule->action.entries[0]) * rule->action.num_entries);
	flow_action_for_each(i, act, &pending->saved.rule->action)
		if (act->id == FLOW_ACTION_REDIRECT)
			dev_hold(act->dev);
	pending->cls = *cls;
	pending->cls.common.extack = NULL;
	pending->cls.rule = pending->saved.rule;
	pending->block = fb->block;
	pending->flow = (unsigned long)ppe_fw_connection(cls->cookie);

	list_for_each_entry_safe(old, tmp, &fb->priv->fw_pending, list)
		if (old->block == fb->block && old->cls.cookie == cls->cookie)
			ppe_fw_pending_free(old);
	list_add_tail(&pending->list, &fb->priv->fw_pending);
	return 0;
}

static void ppe_fw_pair_rollback(struct ppe_flow_block *fb,
				 struct flow_cls_offload *cls)
{
	struct flow_offload *flow = ppe_fw_connection(cls->cookie);
	struct qca_ppe_priv *priv = fb->priv;
	struct ppe_flow_entry *entry, *tmp;
	unsigned long original = (unsigned long)&flow->tuplehash[0].tuple;
	unsigned long reply = (unsigned long)&flow->tuplehash[1].tuple;

	ppe_fw_pending_drop(priv, fb->block, (unsigned long)flow);
	guard(mutex)(&priv->flow_lock);
	guard(mutex)(&priv->vlan_lock);
	list_for_each_entry_safe(entry, tmp, &priv->flow_list, list)
		if (entry->block == fb->block && entry->steer &&
		    (entry->cookie == original || entry->cookie == reply))
			ppe_flow_free(priv, entry);
}

static int ppe_flow_block_cb(enum tc_setup_type type, void *type_data,
			     void *cb_priv)
{
	struct flow_cls_offload *cls = type_data;
	struct ppe_flow_block *fb = cb_priv;
	struct qca_ppe_priv *priv = fb->priv;
	struct ppe_fw_pending *pending;
	unsigned long flow;
	bool owned;
	int ret;

	if (type != TC_SETUP_CLSFLOWER)
		return -EOPNOTSUPP;

	guard(mutex)(&priv->fw_pending_lock);
	ret = ppe_fw_flow_offload(priv, cls, fb->block, &owned);
	if (!owned && READ_ONCE(priv->fw_flow_reserved) &&
	    cls->command == FLOW_CLS_REPLACE &&
	    ppe_flow_ethernet_pair(priv, cls)) {
		ppe_fw_pair_rollback(fb, cls);
		return -EOPNOTSUPP;
	}
	if (owned) {
		switch (cls->command) {
		case FLOW_CLS_REPLACE:
			if (ret && ret != -EAGAIN)
				goto rollback;
			/* No hardware entry is installed for a pending offer,
			 * and -EAGAIN prevents a false HW_OFFLOAD indication.
			 */
			{
				int save_ret = ppe_fw_pending_save(fb, cls);

				if (save_ret) {
					ret = save_ret;
					goto rollback;
				}
			}
			if (ret == -EAGAIN)
				return ret;

			flow = (unsigned long)ppe_fw_connection(cls->cookie);
			list_for_each_entry(pending, &priv->fw_pending, list) {
				if (pending->block != fb->block ||
				    pending->flow != flow)
					continue;
				ret = ppe_flow_offload_replace(fb, &pending->cls, true);
				if (ret)
					goto rollback;
			}
			ppe_fw_pending_drop(priv, fb->block, flow);
			return 0;
		case FLOW_CLS_DESTROY:
			ppe_fw_pair_rollback(fb, cls);
			return ret;
		case FLOW_CLS_STATS:
			return ret;
		default:
			return -EOPNOTSUPP;
		}
	}

	switch (cls->command) {
	case FLOW_CLS_REPLACE:
		return ppe_flow_offload_replace(fb, cls, false);
	case FLOW_CLS_DESTROY:
		ppe_fw_pending_drop(priv, fb->block,
				    (unsigned long)ppe_fw_connection(cls->cookie));
		return ppe_flow_offload_destroy(priv, cls);
	case FLOW_CLS_STATS:
		return ppe_flow_offload_stats(priv, cls);
	default:
		return -EOPNOTSUPP;
	}

rollback:
	/* Remove both PPE directions, then withdraw the shared NSS rule.
	 * This also handles the second PPE insertion failing after the first.
	 */
	ppe_fw_pair_rollback(fb, cls);
	{
		struct flow_cls_offload undo = *cls;

		undo.command = FLOW_CLS_DESTROY;
		ppe_fw_flow_offload(priv, &undo, fb->block, &owned);
	}
	return ret;
}

'''+s[end:]
s=s.replace('''	guard(mutex)(&priv->flow_lock);
	guard(mutex)(&priv->vlan_lock);
	list_for_each_entry_safe(entry, tmp, &priv->flow_list, list)
		if (entry->steer)
''','''	guard(mutex)(&priv->fw_pending_lock);
	ppe_fw_pending_drop(priv, NULL, 0);
	guard(mutex)(&priv->flow_lock);
	guard(mutex)(&priv->vlan_lock);
	list_for_each_entry_safe(entry, tmp, &priv->flow_list, list)
		if (entry->steer)
''')
s=s.replace('''	/* Withdraw firmware rules before freeing their steering entries. */
	ppe_fw_flow_offload(priv, NULL, fb->block, &owned);''','''	/* Withdraw firmware rules before freeing their steering entries. */
	guard(mutex)(&priv->fw_pending_lock);
	ppe_fw_pending_drop(priv, fb->block, 0);
	ppe_fw_flow_offload(priv, NULL, fb->block, &owned);''')
s=s.replace('''	INIT_LIST_HEAD(&priv->flow_list);

	ret = rhashtable_init''','''	INIT_LIST_HEAD(&priv->flow_list);
	INIT_LIST_HEAD(&priv->fw_pending);
	mutex_init(&priv->fw_pending_lock);

	ret = rhashtable_init''')
s=s.replace('''	cancel_delayed_work_sync(&priv->sparse_work);

	mutex_lock(&priv->flow_lock);''','''	cancel_delayed_work_sync(&priv->sparse_work);

	guard(mutex)(&priv->fw_pending_lock);
	ppe_fw_pending_drop(priv, NULL, 0);
	mutex_lock(&priv->flow_lock);''')
p.write_text(s)
p=t/"files/etc/image-provenance";s=p.read_text().replace("iteration 2 (kmodloader options fix)","iteration 3 (VLAN and paired steering transaction fix)");p.write_text(s)
old="nss-ethernet-bootfix-03803c78cd-20261025";new="nss-ethernet-vlanfix-03803c78cd-20261025"
for src,dst in [("build-nss-ethernet-bootfix","build-nss-ethernet-vlanfix"),("validate-nss-ethernet-bootfix","validate-nss-ethernet-vlanfix"),("validate-nss-ethernet-bootfix-extra.py","validate-nss-ethernet-vlanfix-extra.py")]:
 p=w/"bin"/dst;p.write_text((w/"bin"/src).read_text().replace(old,new));p.chmod(0o755)

