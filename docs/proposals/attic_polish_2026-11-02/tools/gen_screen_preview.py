"""gen_screen_preview.py <out add dir> [clip name] [--sheet out.jpg] - v1.10.68 (c): the pull-down screen's looping, muted preview.

User plan (2026-11-09): "(c) later: a looping muted preview on the pull-down screen". The recipe that exists for a moving picture ON a
3D surface is the GL2 renderer's shader videoMap (renderergl2/tr_shader.c: CIN_PlayCinematic(.., CIN_loop | CIN_silent | CIN_shader)
- loops, silent, decoded by the engine's RoQ player); the loading-clip player (cl_loadcine.cpp) only draws 2D (DrawStretchRaw).
So: one of the mod's own loading clips (loadclips/*.hzlc - JPEG frames of in-game footage, already shipped in the loadclips paks)
is cut to 10 s, cropped to the picture's aspect, graded like a 1940s print (black and white, a warm silver tone, grain, a gate
vignette, a little weave and flicker) and written as video/hzm_screen_preview.roq (256 x 256, ffmpeg's roqvideo encoder). The
picture surface of hzm_projector_lit (shown while the projector runs) maps it with videoMap, additive (light on the fabric).
"""
import io, os, struct, subprocess, sys, tempfile, zipfile
import numpy as np
from PIL import Image, ImageFilter

out = sys.argv[1]
clip = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "m1l1"
G = r"G:\GOG\Medal of Honor - Allied Assault War Chest\maintt"
SECS, FPS, N = 10.0, 30, 256
PIC_ASPECT = 16.0 / 9.0                      # = gen_attic68_props SCR_PICW / SCR_PICH: the whole clip frame (its caption box sits at the left edge)


def frames_of(name):
    for pk in ("zzzzzzzzzz_coop_loadclips.pk3", "zzzzzzzzzz_coop_loadclips_2.pk3"):
        z = zipfile.ZipFile(os.path.join(G, pk))
        if "loadclips/%s.hzlc" % name in z.namelist():
            b = z.read("loadclips/%s.hzlc" % name)
            magic, ver, w, h, fps, nf, asp = struct.unpack_from("<4s6I", b, 0)
            assert magic == b"HZLC", magic
            # v1: the offset table follows the 28-byte header; v2/v3 add fields before it - find the table: offsets[0] points
            # just past the table, so scan for the first u32 that equals (its position + 4 * (nf + 1))
            for p0 in range(28, 512, 4):
                if struct.unpack_from("<I", b, p0)[0] == p0 + 4 * (nf + 1):
                    break
            else:
                raise SystemExit("no offset table in %s" % name)
            off = struct.unpack_from("<%dI" % (nf + 1), b, p0)
            return fps, asp / 1000.0, [b[off[k]:off[k + 1]] for k in range(nf)]
    raise SystemExit("no clip %s" % name)


fps, asp, J = frames_of(clip)
take = min(len(J), int(SECS * fps))
rng = np.random.default_rng(1944)
yy, xx = np.mgrid[-1:1:N * 1j, -1:1:N * 1j]
vig = np.clip(1.0 - 0.55 * (np.abs(xx) ** 3 + np.abs(yy) ** 3), 0, 1)
gate = np.clip((1 - np.maximum(np.abs(xx), np.abs(yy)) ** 12) * 4, 0, 1)
tmp = tempfile.mkdtemp(prefix="hzmprev_")
sheet = []
for k in range(int(SECS * FPS)):
    src = Image.open(io.BytesIO(J[int(k * fps / FPS) % take])).convert("L")
    W, H = src.size
    cw = int(H * PIC_ASPECT * (W / H) / asp)               # the crop width in stored pixels for the picture's aspect
    cw = min(W, cw)
    x0 = (W - cw) // 2
    dx = int(rng.normal(0, 0.6))                           # weave
    im = src.crop((x0 + dx, 0, x0 + dx + cw, H)).resize((N, N), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255
    a = np.clip((a - 0.06) * 1.18, 0, 1) ** 1.05            # print contrast
    a = a * vig * gate * (0.93 + 0.07 * rng.random())       # vignette, gate, flicker
    g = np.asarray(Image.fromarray((rng.random((N // 2, N // 2)) * 255).astype(np.uint8)).resize((N, N)), np.float32) / 255
    a = np.clip(a + (g - 0.5) * 0.06, 0, 1)                 # grain
    rgb = np.dstack([a * 1.0, a * 0.96, a * 0.86])          # warm silver
    Image.fromarray((rgb * 255).astype(np.uint8)).save(os.path.join(tmp, "f%04d.png" % k))
    if k % 60 == 0:
        sheet.append(Image.fromarray((rgb * 255).astype(np.uint8)))
vd = os.path.join(out, "video")
os.makedirs(vd, exist_ok=True)
dst = os.path.join(vd, "hzm_screen_preview.roq")
subprocess.check_call(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(tmp, "f%04d.png"),
                       "-an", "-c:v", "roqvideo", "-r", str(FPS), dst])
print("screen preview: %s %.1f s -> %s (%.1f MB)" % (clip, SECS, dst, os.path.getsize(dst) / 1e6))
if "--sheet" in sys.argv:
    s_ = Image.new("RGB", (N * len(sheet), N))
    for i, im in enumerate(sheet):
        s_.paste(im, (i * N, 0))
    s_.save(sys.argv[sys.argv.index("--sheet") + 1], quality=88)
