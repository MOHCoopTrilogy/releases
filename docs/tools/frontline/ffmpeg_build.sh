#!/bin/bash
# Minimal LGPL ffmpeg for the HZM bring-your-own-disc film step (Frontline briefings: EA MPCh -> id RoQ;
# European Assault intros: EA SCHl/MVhd VP6 + ADPCM R2 -> id RoQ, v1.10.69).
# Only what that step uses; no GPL or nonfree parts (no --enable-gpl / --enable-nonfree / external libs).
set -e
SRC=/h/hzm_work/frontline_tools/ffmpeg_src
cd $SRC
[ -d ffmpeg-8.1 ] || tar xf ffmpeg-8.1.tar.xz
mkdir -p build && cd build
CONF="--disable-everything --disable-autodetect --disable-doc --disable-network --disable-debug \
 --disable-ffplay --disable-ffprobe --enable-ffmpeg --enable-small --enable-static --disable-shared \
 --enable-swscale --enable-swresample --enable-avfilter \
 --enable-protocol=file,pipe \
 --enable-demuxer=ea,roq \
 --enable-parser=mpegvideo \
 --enable-decoder=mpeg2video,adpcm_ea_r1,adpcm_ea_r2,adpcm_ea_r3,vp6,vp6a,vp6f,roq,roq_dpcm \
 --enable-encoder=roq,roq_dpcm,pcm_s16le \
 --enable-muxer=roq,wav \
 --enable-filter=scale,crop,format,aresample,fps,null,anull,setpts,asetpts \
 --extra-ldflags=-static"
echo "$CONF" > ../CONFIGURE_LINE.txt
../ffmpeg-8.1/configure $CONF
make -j2
ls -la ffmpeg.exe
./ffmpeg.exe -hide_banner -L | head -3
./ffmpeg.exe -hide_banner -encoders | grep -i roq
./ffmpeg.exe -hide_banner -decoders | grep -i "mpeg2video\|adpcm_ea_r\|vp6"
./ffmpeg.exe -hide_banner -demuxers | grep -w ea
