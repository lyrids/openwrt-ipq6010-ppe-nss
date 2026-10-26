# OpenWrt development workspace
All source checkouts, builds, and development belong on this Linux VM.
The user connects through ssh openwrt-dev@orb; the actual Linux account is ly.
Build as the unprivileged user. Use sudo only for host administration.
Keep source trees in src, shared downloads in downloads, ccache in ccache,
logs in logs, exported images/manifests in artifacts, and inventories in evidence.
Pin source and feed revisions for reproducible experiments.
Router inspection is authorized; flashing, rebooting, service changes and
partition repair are not part of environment setup.
