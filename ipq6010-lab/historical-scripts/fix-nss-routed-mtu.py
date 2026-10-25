from pathlib import Path
w=Path.home()/"projects/openwrt-dev";t=w/"src/openwrt-ppe-nss";p=t/"package/kernel/nss-wifi-drv/src/nss_flow.c";s=p.read_text()
needle="static int nss_flow_send_v4("
helper='''/* The interface number names a physical/virtual NSS port, but routing may
 * impose a smaller MTU on an upper device. Each side's receive interface is
 * reached by the other direction's route. Clamp after any PPPoE deduction,
 * since the flowtable tuple already carries the effective IP MTU.
 */
static u32 nss_flow_effective_mtu(const struct nss_flow_entry *e,
				enum flow_offload_tuple_dir side, u32 mtu)
{
	const struct flow_offload *flow;

	if (e->bridged)
		return mtu;
	flow = (const void *)e->flow;
	return min_t(u32, mtu, flow->tuplehash[!side].tuple.mtu);
}

'''
assert helper not in s;s=s.replace(needle,helper+needle,1)
for name,minimum in [("nss_flow_send_v4",68),("nss_flow_send_v6",1280)]:
 a=s.index("static int "+name+"(");b=s.index("\n\tif (e->protocol == IPPROTO_TCP)",a)
 insert='''\n	c->conn_rule.flow_mtu = nss_flow_effective_mtu(e,
			FLOW_OFFLOAD_DIR_ORIGINAL, c->conn_rule.flow_mtu);
	c->conn_rule.return_mtu = nss_flow_effective_mtu(e,
			FLOW_OFFLOAD_DIR_REPLY, c->conn_rule.return_mtu);
	if (c->conn_rule.flow_mtu < MINIMUM || c->conn_rule.return_mtu < MINIMUM)
		return -EOPNOTSUPP;
'''.replace("MINIMUM",str(minimum))
 s=s[:b]+insert+s[b:]
needle='''	if (!test_bit(NF_FLOW_HW_BIDIRECTIONAL, &flow->flags))
		return -EOPNOTSUPP;
	nss_ethernet_offers++;'''
assert needle in s
s=s.replace(needle,'''	if (!test_bit(NF_FLOW_HW_BIDIRECTIONAL, &flow->flags))
		return -EOPNOTSUPP;
	/* A queued offer may outlive a topology invalidation. */
	if (test_bit(NF_FLOW_TEARDOWN, &flow->flags)) {
		ret = -EOPNOTSUPP;
		goto reject;
	}
	nss_ethernet_offers++;''')
a=s.index("static int nss_ethernet_netdev_event(");b=s.index("static struct notifier_block nss_ethernet_netdev_nb",a)
part=s[a:b];needle='''			if (e)
				nss_flow_forget(core, e);'''
assert needle in part
part=part.replace(needle,'''			if (e) {
				/* Drop the kernel's cached route/MTU as well as
				 * the firmware rule; the next flow must resolve
				 * the topology again through the normal stack.
				 */
				flow_offload_teardown((void *)e->flow);
				nss_flow_forget(core, e);
			}''')
s=s[:a]+part+s[b:];p.write_text(s)
p=t/"files/etc/image-provenance";s=p.read_text().replace("iteration 3 (VLAN and paired steering transaction fix)","iteration 4 (routed MTU and topology invalidation fix)").replace("Hardware validation pending; QCN9074 upload problem unresolved","MTU fix hardware validation pending; Wi-Fi upload issue resolved by user retest (client adapter)")
p.write_text(s)
old="nss-ethernet-vlanfix-03803c78cd-20261025";new="nss-ethernet-mtufix-03803c78cd-20261025"
for src,dst in [("build-nss-ethernet-vlanfix","build-nss-ethernet-mtufix"),("validate-nss-ethernet-vlanfix","validate-nss-ethernet-mtufix"),("validate-nss-ethernet-vlanfix-extra.py","validate-nss-ethernet-mtufix-extra.py")]:
 p=w/"bin"/dst;p.write_text((w/"bin"/src).read_text().replace(old,new));p.chmod(0o755)

