#!/usr/bin/env python3
"""gen_loadclip.py - turn a folder of captured frames into a loading-screen clip (loadclips/<name>.hzlc), and pack clips
into a pk3 for the fixes pak.  Engine side: openmohaa-hzm code/client/cl_loadcine.cpp (docs/ENGINE.md "Loading cinematic").

  python docs/tools/gen_loadclip.py clip FRAMES_DIR NAME [--out DIR] [--fps 30] [--src-fps 30] [--size 1024x512]
                                         [--quality 62] [--loop-blend 15] [--max-secs 0] [--aspect 1.7778]
  python docs/tools/gen_loadclip.py pak OUT.pk3 CLIP.hzlc [CLIP.hzlc ...] [--rules ui/loadclips.txt]
  python docs/tools/gen_loadclip.py info CLIP.hzlc

FRAMES_DIR: any numbered image sequence (png/jpg/tga/bmp, sorted by name), e.g. the engine `screenshot` captures.
  --src-fps  the capture rate; frames are picked to resample to --fps (default 30; the engine plays at the file's rate).
  --size     power-of-two pixel size of the stored picture (the source is squeezed into it; the engine stretches it back at
             --aspect).  1024x512 is the default; 512x256 is half the bytes and visibly soft on a 1080p screen.
  --loop-blend N  cross-fades the last N frames into the first N so the clip loops without a seam: N frames of the footage
             are spent on the blend, the clip is N frames shorter than the capture.  Capture a little more than you want.
  --max-secs S   keep only the first S seconds of the (resampled) footage before the blend.

File format (little endian), written here and read by cl_loadcine.cpp:
  u32 'HZLC', u32 1, u32 width, u32 height, u32 fps, u32 frames, u32 aspect*1000, u32 offset[frames+1], JPEG frames.
Size rule of thumb at 1024x512 q62, 4:2:0: 25-45 KB a frame = 0.75-1.4 MB per second of clip (a 10 s clip is 8-14 MB), so
share clips between maps (ui/loadclips.txt lists several clips per rule and picks one per load) rather than one per map.

Needs Pillow (PIL).  No other dependency.  Run python with -I (the folder may be untrusted).
"""
import argparse, io, os, struct, sys, zipfile

MAGIC = 0x434C5A48


def _need_pil():
    try:
        from PIL import Image  # noqa
        return Image
    except ImportError:
        sys.exit("gen_loadclip.py needs Pillow: python -m pip install pillow")


def cmd_clip(a):
    Image = _need_pil()
    exts = (".png", ".jpg", ".jpeg", ".tga", ".bmp")
    files = sorted(f for f in os.listdir(a.frames) if f.lower().endswith(exts))
    if len(files) < 8:
        sys.exit("need at least 8 frames in %s" % a.frames)
    w, h = (int(v) for v in a.size.lower().split("x"))
    for v in (w, h):
        if v < 16 or v > 2048 or (v & (v - 1)):
            sys.exit("--size must be powers of two (16..2048), got %s" % a.size)
    # resample the capture rate to the clip rate by picking source frames
    n_src = len(files)
    n_out = int(n_src * a.fps / a.src_fps)
    if a.max_secs:
        n_out = min(n_out, int(a.max_secs * a.fps))
    pick = [min(n_src - 1, int(round(i * a.src_fps / a.fps))) for i in range(n_out)]
    blend = a.loop_blend
    if blend and n_out < blend * 3:
        sys.exit("clip of %d frames is too short for --loop-blend %d" % (n_out, blend))
    length = n_out - blend

    def load(i):
        im = Image.open(os.path.join(a.frames, files[pick[i]])).convert("RGB")
        return im.resize((w, h), Image.LANCZOS)

    out = []
    for i in range(length):
        im = load(i)
        if blend and i < blend:
            tail = load(length + i)
            # i = 0 is the tail's own next frame (continues the clip's last frame); the blend reaches the head at i = blend
            im = Image.blend(tail, im, i / float(blend))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=a.quality, subsampling=2, optimize=False, progressive=False)
        out.append(buf.getvalue())
    hdr = 28 + 4 * (length + 1)
    offs, pos = [], hdr
    for b in out:
        offs.append(pos)
        pos += len(b)
    offs.append(pos)
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, a.name + ".hzlc")
    with open(path, "wb") as f:
        f.write(struct.pack("<7I", MAGIC, 1, w, h, a.fps, length, int(round(a.aspect * 1000))))
        f.write(struct.pack("<%dI" % (length + 1), *offs))
        for b in out:
            f.write(b)
    print("%s: %d frames, %dx%d, %d fps = %.1f s, %.2f MB (%.1f KB/frame avg, max %.1f KB)" % (
        path, length, w, h, a.fps, length / float(a.fps), pos / 1048576.0, pos / length / 1024.0, max(map(len, out)) / 1024.0))


def cmd_info(a):
    d = open(a.clip, "rb").read()
    m, v, w, h, fps, n, asp = struct.unpack_from("<7I", d, 0)
    offs = struct.unpack_from("<%dI" % (n + 1), d, 28)
    ok = m == MAGIC and v == 1 and offs[-1] == len(d)
    print("%s: %s %dx%d %dfps %d frames (%.1f s) aspect %.3f, %.2f MB, avg %.1f KB/frame" % (
        a.clip, "ok" if ok else "BAD", w, h, fps, n, n / float(fps), asp / 1000.0, len(d) / 1048576.0, len(d) / n / 1024.0))


def cmd_pak(a):
    # ZIP_STORED: JPEG does not deflate, and the engine reads the whole entry in one go either way
    with zipfile.ZipFile(a.out, "w", zipfile.ZIP_STORED) as z:
        for c in a.clips:
            z.write(c, "loadclips/" + os.path.basename(c))
        if a.rules:
            z.write(a.rules, "ui/loadclips.txt")
    print("%s: %d entries, %.2f MB" % (a.out, len(a.clips) + (1 if a.rules else 0), os.path.getsize(a.out) / 1048576.0))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("clip")
    c.add_argument("frames")
    c.add_argument("name")
    c.add_argument("--out", default=".")
    c.add_argument("--fps", type=int, default=30)
    c.add_argument("--src-fps", type=float, default=30.0)
    c.add_argument("--size", default="1024x512")
    c.add_argument("--quality", type=int, default=62)
    c.add_argument("--loop-blend", type=int, default=15)
    c.add_argument("--max-secs", type=float, default=0)
    c.add_argument("--aspect", type=float, default=16.0 / 9.0)
    c.set_defaults(fn=cmd_clip)
    i = sp.add_parser("info")
    i.add_argument("clip")
    i.set_defaults(fn=cmd_info)
    p = sp.add_parser("pak")
    p.add_argument("out")
    p.add_argument("clips", nargs="+")
    p.add_argument("--rules")
    p.set_defaults(fn=cmd_pak)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
