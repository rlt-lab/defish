#!/usr/bin/env bash
# Build the FFmpeg that ships inside defish: static, GPL, with only what the app needs (FFmpeg's own decoders,
# filters and AAC encoder, plus libx264, and zlib for PNG). Built from the pinned sources below so every release
# can ship the complete corresponding source: ffmpeg-source-<target>.tar.gz holds those sources and this script.
# Usage: ffmpeg/build.sh macos     (on macOS)
#        ffmpeg/build.sh windows   (on Linux, cross-compiling with mingw-w64)
# Output in ffmpeg/out/: ffmpeg or ffmpeg.exe, licenses/, ffmpeg-source-<target>.tar.gz
set -euo pipefail
target=$1

FFMPEG=7.1.5
FFMPEG_SHA256=de668509caf9e35e3cd162473441fdb29538c6d96ed080292b3cf9e6fc5d558f
X264=b35605ace3ddf7c1a5d67a2eb553f034aef41d55  # x264 "stable" branch
ZLIB=1.3.1
ZLIB_SHA256=9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23

here=$(cd "$(dirname "$0")" && pwd)
work=$here/work; out=$here/out; src=$work/src; pre=$work/prefix
rm -rf "$work" "$out"
mkdir -p "$src" "$pre" "$out/licenses"
cd "$work"

fetch() {  # url file sha256
  curl -fsSL "$1" -o "$src/$2"
  echo "$3  $src/$2" | shasum -a 256 -c -
}
fetch "https://ffmpeg.org/releases/ffmpeg-$FFMPEG.tar.xz" "ffmpeg-$FFMPEG.tar.xz" $FFMPEG_SHA256
fetch "https://github.com/madler/zlib/releases/download/v$ZLIB/zlib-$ZLIB.tar.gz" "zlib-$ZLIB.tar.gz" $ZLIB_SHA256
# x264 has no release tarballs: fetch the pinned commit and archive it, then build from that archive.
git init -q x264-git
git -C x264-git fetch -q --depth 1 https://code.videolan.org/videolan/x264.git $X264
git -C x264-git archive --prefix="x264-$X264/" -o "$src/x264-$X264.tar.gz" FETCH_HEAD
cp "$here/build.sh" "$src/"
for f in "$src"/*.tar.*; do tar xf "$f"; done

jobs=$(getconf _NPROCESSORS_ONLN)
export PKG_CONFIG_PATH=$pre/lib/pkgconfig
ffmpeg_flags=(--prefix="$pre" --enable-gpl --enable-libx264 --enable-zlib --disable-autodetect
              --disable-doc --disable-ffplay --disable-ffprobe --disable-network
              --pkg-config-flags=--static --extra-cflags="-I$pre/include" --extra-ldflags="-L$pre/lib")

case $target in
  macos)
    export MACOSX_DEPLOYMENT_TARGET=11.0
    (cd "x264-$X264" && ./configure --prefix="$pre" --enable-static --disable-cli --enable-pic && make -j$jobs && make install)
    (cd "ffmpeg-$FFMPEG" && ./configure "${ffmpeg_flags[@]}" && make -j$jobs && make install)  # zlib: macOS's own
    exe=ffmpeg ;;
  windows)
    cross=x86_64-w64-mingw32-
    (cd "zlib-$ZLIB" && make -f win32/Makefile.gcc PREFIX=$cross -j$jobs &&
       make -f win32/Makefile.gcc install BINARY_PATH="$pre/bin" INCLUDE_PATH="$pre/include" LIBRARY_PATH="$pre/lib")
    (cd "x264-$X264" && ./configure --host=x86_64-w64-mingw32 --cross-prefix=$cross --prefix="$pre" \
       --enable-static --disable-cli && make -j$jobs && make install)
    (cd "ffmpeg-$FFMPEG" && ./configure "${ffmpeg_flags[@]}" --arch=x86_64 --target-os=mingw32 \
       --cross-prefix=$cross --pkg-config=pkg-config --extra-ldflags=-static && make -j$jobs && make install)
    cp "zlib-$ZLIB/LICENSE" "$out/licenses/zlib.txt"
    cp /usr/share/doc/mingw-w64-common/copyright "$out/licenses/mingw-w64.txt"  # its runtime is linked in
    exe=ffmpeg.exe ;;
  *) echo "usage: $0 macos|windows" >&2; exit 1 ;;
esac

cp "$pre/bin/$exe" "$out/"
cp "ffmpeg-$FFMPEG/COPYING.GPLv2" "$out/licenses/GPL-2.0.txt"
tar czf "$out/ffmpeg-source-$target.tar.gz" -C "$work" src
