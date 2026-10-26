/* SPDX-License-Identifier: GPL-2.0-only */
/* What the qca-ppe DSA driver offers the host driver of the NSS firmware,
 * which shares the switch with it.
 */

#ifndef __LINUX_SOC_QCOM_QCA_PPE_H__
#define __LINUX_SOC_QCOM_QCA_PPE_H__

#include <linux/netdevice.h>

struct flow_cls_offload;
struct flow_block;

/* Optional firmware route backend. A NULL rule withdraws a released block.
 * owned=true means PPE may only steer this connection, never route/NAT it.
 * The callback may sleep; unregister waits for in-flight callbacks.
 */
int qca_ppe_fw_flow_set(struct net_device *conduit,
        int (*handler)(struct flow_cls_offload *, const struct flow_block *,
                       bool *));
int qca_ppe_fw_booted(struct net_device *conduit);
int qca_ppe_fw_ports_set(struct net_device *conduit);
int qca_ppe_fw_carrier_set(struct net_device *conduit,
			   bool (*carries)(int ifindex));

#endif /* __LINUX_SOC_QCOM_QCA_PPE_H__ */
