set -eu
workspace=/home/ly/projects/openwrt-dev
mkdir -p "$workspace/artifacts/kexec-tools-2.0.32-20261025"
run="$workspace/artifacts/kexec-tools-2.0.32-20261025"
cd "$workspace/downloads"
curl -fL --retry 2 -o kexec-tools-2.0.32.tar.xz https://www.kernel.org/pub/linux/utils/kernel/kexec/kexec-tools-2.0.32.tar.xz > "$run/download.log" 2>&1
echo '8f81422a5fd2362cf6cb001b511e535565ed0f32c2f4451fb5eb68fed6710a5d  kexec-tools-2.0.32.tar.xz' | sha256sum -c -
tar -xf kexec-tools-2.0.32.tar.xz -C "$workspace/src"
cd "$workspace/src/kexec-tools-2.0.32"
export STAGING_DIR="$workspace/src/openwrt-ppe-nss/staging_dir"
cross="$STAGING_DIR/toolchain-aarch64_cortex-a53_gcc-14.4.0_musl/bin/aarch64-openwrt-linux-musl-"
./configure --build=aarch64-linux-gnu --host=aarch64-openwrt-linux-musl --target=aarch64-openwrt-linux-musl --without-zlib --without-lzma --without-zstd CC="${cross}gcc" LD="${cross}ld" AR="${cross}ar" CFLAGS="-Os -std=gnu17" LDFLAGS="-static" > "$run/configure.log" 2>&1
make -j8 > "$run/build.log" 2>&1
cp build/sbin/kexec "$run/kexec"
"${cross}strip" "$run/kexec"
file "$run/kexec"
sha256sum "$run/kexec" > "$run/kexec.sha256"
"$run/kexec" --version > "$run/version.txt"
cat "$run/version.txt"
