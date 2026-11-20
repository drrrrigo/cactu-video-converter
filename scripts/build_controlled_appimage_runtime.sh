#!/bin/sh
# Run only inside the pinned isolated Alpine root, with /sources read-only.
# This experiment does not replace the selected packager runtime or approve it.
set -eu
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
export SOURCE_DATE_EPOCH=1795205905
cd /build
mkdir -p work relink
cd work
rm -rf fuse squash runtime
mkdir -p fuse squash runtime
tar xf /sources/libfuse-3.15.0.tar.xz --no-same-owner -C fuse --strip-components=1
tar xf /sources/squashfuse-0.5.2.tar.gz --no-same-owner -C squash --strip-components=1
tar xf /sources/appimage-runtime-fedfad51acc2860b2916a1eef32ba4a500ff31ef.tar.gz --no-same-owner -C runtime --strip-components=1
patch -d fuse -p1 < runtime/patches/libfuse/mount.c.diff
export CFLAGS='-Os -ffunction-sections -fdata-sections -ffile-prefix-map=/build/work=.'
meson setup fuse/build fuse --prefix=/usr --default-library=static -Dexamples=false -Dtests=false -Duseroot=false
ninja -C fuse/build -j2 install
cd squash
./autogen.sh
./configure --disable-shared --enable-static LDFLAGS=-static
make -j2
make install
install -d /usr/local/include/squashfuse
install -m644 ./*.h /usr/local/include/squashfuse/
cd ../runtime/src/runtime
clang -std=gnu99 $CFLAGS -D_FILE_OFFSET_BITS=64 \
  '-DGIT_COMMIT="fedfad51acc2860b2916a1eef32ba4a500ff31ef-cactu1"' \
  -I/usr/local/include/squashfuse -I/usr/include/fuse3 \
  -Wall -Werror -c runtime.c -o runtime.o
clang -static -static-pie -Wl,--gc-sections,-Map=runtime.map -T data_sections.ld \
  runtime.o -lsquashfuse -lsquashfuse_ll -lzstd -lz -lfuse3 -lmimalloc -o runtime
cp runtime.o runtime.map data_sections.ld /build/relink/
cp runtime /build/runtime-x86_64.unstripped
strip --strip-debug --strip-unneeded runtime
printf 'AI\002' | dd of=runtime bs=1 count=3 seek=8 conv=notrunc
cp runtime /build/runtime-x86_64
clang --version > /build/compiler-version.txt
readelf -d runtime > /build/runtime-dynamic.txt
readelf -p .comment runtime > /build/runtime-compiler-comments.txt
find /usr/lib /usr/local/lib -name '*.a' -o -name 'crt*.o' | sort > /build/relink-available-inputs.txt
/sbin/apk info -vv > /build/installed-packages.txt
