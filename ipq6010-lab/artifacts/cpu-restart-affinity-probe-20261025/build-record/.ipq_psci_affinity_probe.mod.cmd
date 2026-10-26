savedcmd_ipq_psci_affinity_probe.mod := printf '%s\n'   ipq_psci_affinity_probe.o | awk '!x[$$0]++ { print("./"$$0) }' > ipq_psci_affinity_probe.mod
