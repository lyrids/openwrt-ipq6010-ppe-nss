# Iteration9 RAM boot and lifecycle validation

Normal reboot loaded FIT1f1cc86103aa7ead9dcdaf8c4b814ed9450c56383eed0de310dee5c435637f4e through p43 TFTP, initramfs root, revisionr37715-49b3824932, kernel6.18.55, CPUs0-3. Procd wireless-completion trigger present automatically from image; no live init-script patch needed.

AP enabled after boot, phy2-ap0 appeared in offload flowtable automatically. Two AP down/up cycles removed/readded it without manual firewall reload. AP US/channel36 HE80. Previous iteration5 FIT preserved on p43 as previous.itb; boot environment and DUT eMMC unchanged. Kexec remains disabled.

Earlier preparation reboot likely accidental power interruption per user, not demonstrated firmware failure. Original m4m failed, so Linksys WRT32X replacement was authorized. Development VM access stalled; dedicated machine restart requested, SSH recovered and disk/source artifacts intact. No global OrbStack force-stop used.

Automated lifecycle assertion harness also passed one post-soak AP down/up cycle (automated-lifecycle.txt), without manual firewall reload. Source script in wifi-lifecycle/test-lifecycle.sh. Dedicated Orb VM command access later recovered; artifacts intact and evidence archived before publication.
