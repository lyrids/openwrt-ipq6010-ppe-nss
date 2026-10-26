#!/bin/sh
set -eu
# Opt-in lab AP. Credentials are generated on the router, never built into images.
key_file=/tmp/wifi-lifecycle-test.key
umask 077
[ -s "$key_file" ] || dd if=/dev/urandom bs=32 count=1 2>/dev/null | sha256sum | cut -c1-32 > "$key_file"
uci set wireless.radio2.country=US
uci set wireless.radio2.channel=36
uci set wireless.radio2.htmode=HE80
uci set wireless.default_radio2.network=lan
uci set wireless.default_radio2.ssid=OpenWrt-RAM-test-QCN9074
uci set wireless.default_radio2.encryption=psk2
uci set wireless.default_radio2.key="$(cat "$key_file")"
uci set wireless.default_radio2.disabled=0
uci commit wireless
wifi reload radio2
