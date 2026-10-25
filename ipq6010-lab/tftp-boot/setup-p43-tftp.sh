set -eu
work="$HOME/openwrt-ramboot/tftp-server"
mkdir -p "$work"
sudo -n install -d -m 755 /etc/systemd/network/10-netplan-eth0.network.d /etc/systemd/system/tftpd-hpa.service.d /srv/tftp/openwrt
sudo -n cp -n /etc/default/tftpd-hpa "$work/tftpd-hpa.before"
sudo -n tee /etc/systemd/network/10-netplan-eth0.network.d/50-openwrt-tftp.conf >/dev/null <<'EOF'
[Link]
RequiredForOnline=no

[Network]
Address=192.168.1.2/24

[DHCPv4]
UseRoutes=no
UseDNS=no

[DHCPv6]
UseDNS=no

[IPv6AcceptRA]
UseDNS=no
UseGateway=no
EOF
sudo -n tee /etc/default/tftpd-hpa >/dev/null <<'EOF'
TFTP_USERNAME="tftp"
TFTP_DIRECTORY="/srv/tftp"
TFTP_ADDRESS="192.168.1.2:69"
TFTP_OPTIONS="--secure --verbose"
EOF
sudo -n tee /etc/systemd/system/tftpd-hpa.service.d/50-openwrt-tftp.conf >/dev/null <<'EOF'
[Service]
Restart=on-failure
RestartSec=2s
EOF
sudo -n networkctl reload
sudo -n networkctl reconfigure eth0
sudo -n systemctl daemon-reload
sudo -n install -m 644 "$HOME/openwrt-ramboot/nss-ethernet-mtuguard-initramfs.itb" /srv/tftp/openwrt/.jdcloud-re-cs-02.itb.new
sudo -n mv /srv/tftp/openwrt/.jdcloud-re-cs-02.itb.new /srv/tftp/openwrt/jdcloud-re-cs-02.itb
sudo -n systemctl enable --now tftpd-hpa
sudo -n systemctl restart tftpd-hpa
sudo -n ip route del default via 192.168.21.1 dev wlan0 metric 50
ip -br addr show eth0
ip route show default
sudo -n ss -lunp | grep ':69 '
cd "$work"
tftp 192.168.1.2 -m binary -c get openwrt/jdcloud-re-cs-02.itb downloaded.itb
printf '%s  %s\n' b2b63a339a3e6496a198de3d39a14ca21d19214dc08c047f00a8da1953795c56 downloaded.itb | sha256sum -c -
