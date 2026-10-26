# Build reproduction

Use Linux and an unprivileged account. The original host was Ubuntu25.10arm64 with eight build jobs. workspace/ENVIRONMENT.txt and historical-scripts/install-host-deps record prerequisites. Downloaded dependencies and firmware retain their upstream licensing.

From the committed repository root:
    bash ipq6010-lab/prepare-build.sh
    make download -j8
    make -j8 V=s

prepare-build.sh updates the pinned feeds, applies the selected-firmware patch once, restores the exact selected feed package list, copies the config seed and overlay, and runs defconfig. It refuses a differing pre-existing firmware patch. Configure optional CCACHE_DIR and OPENWRT_DL_DIR environment variables to override the original host paths. It does not flash, reboot, or start a build. Review the generated config first.

The original full config and build history were verified on Orb. The new preparation helper is syntax-checked but has not been exercised in a separate clean-room build; a fresh output still needs image validation and RAM-boot qualification.

Outputs: bin/targets/qualcommax/ipq60xx/. The initramfs FIT is the RAM-boot artifact; sysupgrade output is archived metadata only and was never flashed. Historical validators document FIT/config/profile/rootfs/firmware checks and the device kernel partition constraint. They assume their original workspace layout and base commit; use them as reference when validating future revisions.

Pins: feeds.conf.pinned; configuration: config.seed and artifacts/*/build-state/config.full; firmware adaptation: nss-firmware-selected-line.patch. The selected firmware line is12.5; no closed firmware binary is committed here.

Historical helper scripts are preserved unchanged and may not be idempotent. Do not run implement/fix scripts on this tree: their changes are already committed. The earlier stashed guard is archived only.

Latest validated integration build: wifi-lifecycle-49b3824932-20261026 (iteration9), FIT SHA256 1f1cc86103aa7ead9dcdaf8c4b814ed9450c56383eed0de310dee5c435637f4e. Exact .config, build-state/feed pins, firmware adaptation, dates and image checksums are in artifacts/wifi-lifecycle-49b3824932-20261026. The current overlay provenance is updated to iteration9; no Wi-Fi password is embedded. AP setup is opt-in through wifi-lifecycle/configure-test-ap.sh.

The workspace-specific wifi-lifecycle/build-wifi-lifecycle wrapper records the current source commit and build inputs; it assumes the pinned feeds/config/overlay have already been prepared. It does not install images. A successful incremental build and RAM boot are verified; a separate fresh-toolchain clean-room build remains untested.
