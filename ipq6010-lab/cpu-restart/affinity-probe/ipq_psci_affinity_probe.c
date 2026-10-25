// SPDX-License-Identifier: GPL-2.0-only
#include <linux/arm-smccc.h>
#include <linux/init.h>
#include <linux/module.h>
#include <uapi/linux/psci.h>

/* One-shot read-only queries. No CPU_ON, CPU_OFF or SCM writes. */
static int __init ipq_psci_affinity_probe_init(void)
{
 struct arm_smccc_res res;
 unsigned long mpidr;

 for (mpidr = 0; mpidr < 4; mpidr++) {
  arm_smccc_smc(PSCI_0_2_FN64_AFFINITY_INFO, mpidr, 0, 0, 0, 0, 0, 0, &res);
  pr_info("ipq-affinity-probe: mpidr=%#lx affinity=%ld (0=ON 1=OFF 2=ON_PENDING)\n",
          mpidr, (long)res.a0);
 }
 return 0;
}
static void __exit ipq_psci_affinity_probe_exit(void) {}
module_init(ipq_psci_affinity_probe_init);
module_exit(ipq_psci_affinity_probe_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Temporary read-only IPQ6010 PSCI affinity probe");
