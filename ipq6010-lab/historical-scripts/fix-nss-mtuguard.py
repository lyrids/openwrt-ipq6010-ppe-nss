from pathlib import Path
w=Path.home()/"projects/openwrt-dev";t=w/"src/openwrt-ppe-nss";p=t/"package/kernel/nss-wifi-drv/src/nss_flow.c";s=p.read_text()
s=s.replace("\tNSS_FLOW_REJECT_FIRMWARE,\n","\tNSS_FLOW_REJECT_FIRMWARE,\n\tNSS_FLOW_REJECT_MTU,\n",1).replace('\t"firmware",\n','\t"firmware", "mtu",\n',1)
a=s.index("/* The interface number names a physical/virtual NSS port");b=s.index("static int nss_flow_send_v4(",a)
s=s[:a]+'''/* Firmware enforcement of a routed MTU below the underlying link's IP
 * capacity is not established. Keep those flows in Linux, which owns PMTU
 * exceptions. Standard PPPoE capacity is deducted before this check.
 */
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
		scoped_guard(rcu)() {
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

'''+s[b:]
needle="\tret = e->v6 ? nss_flow_send_v6("
assert s.count(needle)==2
s=s.replace(needle,"\tnss_flow_mtu_limited = false;\n"+needle)
old='''		nss_flow_reject_at(NSS_FLOW_REJECT_FIRMWARE, ret, f,
				   fw_err ? fw_err : -ret);'''
new='''		nss_flow_reject_at(nss_flow_mtu_limited ? NSS_FLOW_REJECT_MTU :
				   NSS_FLOW_REJECT_FIRMWARE, ret, f,
				   fw_err ? fw_err : -ret);'''
assert old in s;s=s.replace(old,new,1)
needle='''	seq_printf(s, "bound %u pushed %u last-ifindex %d\\n",
'''
insert='''	seq_printf(s, "mtu_policy limited %u link %u/%u route %u/%u rule %u/%u l3if %d/%d\\\\n",
		   nss_flow_mtu_limited, nss_flow_mtu_link[0], nss_flow_mtu_link[1],
		   nss_flow_mtu_route[0], nss_flow_mtu_route[1],
		   nss_flow_mtu_rule[0], nss_flow_mtu_rule[1],
		   nss_flow_mtu_l3if[0], nss_flow_mtu_l3if[1]);
'''.replace('\\\\n','\\n')
assert needle in s;s=s.replace(needle,insert+needle,1)
p.write_text(s)
p=t/"files/etc/image-provenance";s=p.read_text().replace("iteration 4 (routed MTU and topology invalidation fix)","iteration 5 (live routed MTU guard with safe software fallback)").replace("MTU fix hardware validation pending","Reduced-MTU guard hardware validation pending");p.write_text(s)
old="nss-ethernet-mtufix-03803c78cd-20261025";new="nss-ethernet-mtuguard-03803c78cd-20261025"
for src,dst in [("build-nss-ethernet-mtufix","build-nss-ethernet-mtuguard"),("validate-nss-ethernet-mtufix","validate-nss-ethernet-mtuguard"),("validate-nss-ethernet-mtufix-extra.py","validate-nss-ethernet-mtuguard-extra.py")]:
 p=w/"bin"/dst;p.write_text((w/"bin"/src).read_text().replace(old,new));p.chmod(0o755)

