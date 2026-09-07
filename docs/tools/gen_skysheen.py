"""Generate textures/coop_fx/sky_sheen.tga - the sky-sheen sphere map for Omaha's open sea.

WHY THIS TOOL EXISTS [user 2026-09-06, bug-2508]
------------------------------------------------
docs/proposals/ocean_2026-09-06/README.md, section 4: Omaha's sun is vertical (worldspawn
`sundirection "270 360 0"`), so a sun glint sits at the nadir and is invisible from eye height, and
gl2's `alphaGen lightingSpecular` is lit by a hard-coded point anyway. What a grey overcast sea
actually catches at grazing angles is the SKY, so the deepbluesea block gets a `tcGen environment`
stage that maps a sphere map of the map's own sky (`textures/sky/d-day2` = `skyParms env/dday2`,
maintt/pak1 scripts/sky.shader). A shipped asset without its generator is a TRAPS T2 violation,
hence this file.

WHAT IT BAKES
-------------
A 256x256 32-bit TGA. The texel -> direction mapping is the one BOTH renderers use for
`tcGen environment` on a flat, +Z-normal sheet (gl1 RB_CalcEnvironmentTexCoords, gl2
generic_vp.glsl:149-155, algebraically identical for n = (0,0,1)):

    s = 0.5 + 0.5 * R.y        t = 0.5 - 0.5 * R.z        R = reflected view ray (unit)

so R.y = 2s - 1, R.z = 1 - 2t, and R.x = +/- sqrt(1 - R.y^2 - R.z^2) is NOT encoded (the classic
Quake sphere map is the orthographic photo of a mirror ball). Each texel therefore averages the sky
seen along (+R.x, R.y, R.z) and (-R.x, R.y, R.z). Rows t < 0.5 are reflections that point UP
(zenith at t = 0, horizon at t = 0.5) - the only rows a flat sea ever samples; rows t > 0.5 are
filled by mirroring so a bilinear fetch at the horizon row has sane neighbours.

The sky is read from the six cube faces the ENGINE would load, resolved with its own rules
(TRAPS T6): pak order main < mainta < maintt, later pak name wins inside a dir, loose files beat
paks, and R_LoadImage tries `.dds`, then `.jpg`, then `.tga` (renderergl2/tr_image.c:2481-2530).
On the dev install that is the 1024^2 `env/dday2_*.jpg` set from
maintt/zzzzz-AA_HD_Project_Pak1.pk3 (rt/bk/lf/ft/up) and retail main/Pak2.pk3's 8x8
`env/dday2_dn.jpg` (the HD project ships no down face). Face -> direction uses tr_sky.c's
`vec_to_st` / `MakeSkyVec` tables verbatim (renderergl2/tr_sky.c:73-140, 304-365), including the
`t = 1 - t` flip. If no face can be found at all the tool bakes a plausible overcast gradient from
the values measured on 2026-09-06 (zenith 90/98/108, horizon 176/172/169) and SAYS SO on stdout.

ALPHA = FRESNEL, BAKED
----------------------
The shader stage is `blendFunc GL_SRC_ALPHA GL_ONE` + `alphaGen const 0.25`, and the fragment alpha
is vertex alpha x texture alpha, so the texture's alpha channel is a free per-direction weight.
`alphaGen dot` / `oneMinusDot` are parsed-but-dead on gl2 (README section 0 item 7), so the
grazing-angle falloff a real water surface has is baked here instead:

    cos  = |R.z|                                  (= view elevation on a flat sea)
    a(t) = ALPHA_MIN + (1 - ALPHA_MIN) * (1 - cos) ** ALPHA_POW

which is 0.30 looking straight down (sheen 0.25 * 0.30 = 0.075) and 1.0 at the horizon (0.25).
It is per-vertex on the 8x8 drawn patch (README section 1), i.e. a smooth gradient, which at eye
height on a Higgins is the correct look.

NO FOG IS BAKED. The engine fogs every additive stage toward black with distance
(renderergl2/tr_shade.c:1450-1458), and the HD faces' horizon rows (176/172/169) already sit
within a few counts of the farplane colour (.62 .62 .61 = 158/158/156), so a static fog term would
be a second knob for no visible gain.

DETERMINISTIC: no randomness; the same source faces reproduce the file byte for byte, and --check
verifies that without writing. Run it from anywhere:

    python docs/tools/gen_skysheen.py            # write the texture
    python docs/tools/gen_skysheen.py --check    # exit 1 if the shipped file differs
    python docs/tools/gen_skysheen.py --preview out.png --paks G:/mohaa-gl2/main,G:/mohaa-gl2/mainta,G:/mohaa-gl2/maintt
"""

import argparse
import io
import os
import struct
import sys
import zipfile

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
TEX = os.path.join(MOD, "textures", "coop_fx", "sky_sheen.tga")

SIZE = 256
SUPERSAMPLE = 3                 # 3x3 jitter per texel
SKY_BASENAME = "env/dday2"      # skyParms env/dday2 (textures/sky/d-day2, maintt/pak1 sky.shader)
DEFAULT_PAKS = ["G:/mohaa-gl2/main", "G:/mohaa-gl2/mainta", "G:/mohaa-gl2/maintt"]

ALPHA_MIN = 0.30
ALPHA_POW = 3.0

# measured 2026-09-06 on the HD faces, used only when no face resolves
FALLBACK_ZENITH = (90.0, 98.0, 108.0)
FALLBACK_HORIZON = (176.0, 172.0, 169.0)

# renderergl2/tr_shader.c:2308 - face i of skyParms is <name>_<SUF[i]>
SUF = ["rt", "bk", "lf", "ft", "up", "dn"]
# renderergl2/tr_sky.c:73 (AddSkyPolygon): s = [0]/[2], t = [1]/[2]; sign = negate, value-1 = axis
VEC_TO_ST = [
    [-2, 3, 1],
    [2, 3, -1],
    [1, 3, 2],
    [-1, 3, -2],
    [-2, -1, 3],
    [-2, 1, -3],
]


# ----------------------------------------------------------------------------------------------
# engine-rule asset resolution (TRAPS T6)
# ----------------------------------------------------------------------------------------------
def resolve_engine_file(pak_dirs, qpath_noext):
    """Return (bytes, description) for the copy of qpath_noext.{dds,jpg,tga} the engine loads.

    R_LoadImage: .dds first (compressed textures on), then the .jpg alternative, then the named
    extension - and within one extension, loose file > later pak name > earlier pak name > later
    dir > earlier dir. Returns (None, None) when nothing matches."""
    for ext in ("dds", "jpg", "tga"):
        rel = qpath_noext + "." + ext
        # dirs are mounted main -> mainta -> maintt; the LAST mount wins, so scan in reverse
        for d in reversed(pak_dirs):
            loose = os.path.join(d, rel.replace("/", os.sep))
            if os.path.isfile(loose):
                with open(loose, "rb") as fh:
                    return fh.read(), "loose %s" % loose
            paks = sorted(
                f for f in os.listdir(d) if f.lower().endswith(".pk3")
            ) if os.path.isdir(d) else []
            for pak in reversed(paks):
                try:
                    z = zipfile.ZipFile(os.path.join(d, pak))
                except zipfile.BadZipFile:
                    continue
                names = {n.lower(): n for n in z.namelist()}
                if rel.lower() in names:
                    return z.read(names[rel.lower()]), "%s/%s :: %s" % (os.path.basename(d), pak, rel)
    return None, None


def load_faces(pak_dirs):
    faces = []
    for suf in SUF:
        data, where = resolve_engine_file(pak_dirs, "%s_%s" % (SKY_BASENAME, suf))
        if data is None:
            print("  face %s: NOT FOUND" % suf)
            faces.append(None)
            continue
        if where.lower().endswith(".dds"):
            # no DDS decoder here; a .dds sky face would need one - report and fall back
            print("  face %s: %s is a .dds (no decoder) - treated as missing" % (suf, where))
            faces.append(None)
            continue
        im = Image.open(io.BytesIO(data)).convert("RGB")
        arr = np.asarray(im).astype(np.float64)
        print("  face %s: %s  %dx%d  mean %s" % (suf, where, im.size[0], im.size[1],
                                                 tuple(arr.mean(axis=(0, 1)).round(1).tolist())))
        faces.append(arr)
    return faces


# ----------------------------------------------------------------------------------------------
# cube sampling, vectorised, following tr_sky.c exactly
# ----------------------------------------------------------------------------------------------
def _pick(v, j):
    """vec_to_st sign/axis decode: j>0 -> v[j-1], j<0 -> -v[-j-1]."""
    if j > 0:
        return v[:, j - 1]
    return -v[:, -j - 1]


def sample_cube(faces, v):
    """v: (N,3) unit directions -> (N,3) RGB floats 0..255 (bilinear on the winning face)."""
    av = np.abs(v)
    axis = np.where(
        (av[:, 0] > av[:, 1]) & (av[:, 0] > av[:, 2]),
        np.where(v[:, 0] < 0, 1, 0),
        np.where(
            (av[:, 1] > av[:, 2]) & (av[:, 1] > av[:, 0]),
            np.where(v[:, 1] < 0, 3, 2),
            np.where(v[:, 2] < 0, 5, 4),
        ),
    )
    out = np.zeros((v.shape[0], 3), dtype=np.float64)
    for a in range(6):
        m = axis == a
        if not m.any():
            continue
        face = faces[a]
        vv = v[m]
        js, jt, jd = VEC_TO_ST[a]
        dv = _pick(vv, jd)
        dv = np.maximum(dv, 1e-6)
        s = _pick(vv, js) / dv
        t = _pick(vv, jt) / dv
        # MakeSkyVec: s,t in -1..1 -> 0..1, then t = 1 - t; texcoord t=0 is image row 0 (top)
        u = (s + 1.0) * 0.5
        w = 1.0 - (t + 1.0) * 0.5
        H, W = face.shape[0], face.shape[1]
        px = np.clip(u * (W - 1), 0, W - 1)
        py = np.clip(w * (H - 1), 0, H - 1)
        x0 = np.floor(px).astype(int)
        y0 = np.floor(py).astype(int)
        x1 = np.minimum(x0 + 1, W - 1)
        y1 = np.minimum(y0 + 1, H - 1)
        fx = (px - x0)[:, None]
        fy = (py - y0)[:, None]
        c = (face[y0, x0] * (1 - fx) * (1 - fy) + face[y0, x1] * fx * (1 - fy)
             + face[y1, x0] * (1 - fx) * fy + face[y1, x1] * fx * fy)
        out[m] = c
    return out


def fallback_sky(v):
    """Overcast gradient by elevation: zenith colour at |z|=1, horizon colour at z=0."""
    e = np.clip(np.abs(v[:, 2]), 0.0, 1.0)[:, None]
    z = np.array(FALLBACK_ZENITH)[None, :]
    h = np.array(FALLBACK_HORIZON)[None, :]
    # the measured faces darken quickly above the horizon: weight by sqrt(elevation)
    return h + (z - h) * np.sqrt(e)


# ----------------------------------------------------------------------------------------------
# the bake
# ----------------------------------------------------------------------------------------------
def bake(faces):
    n = SIZE
    ss = SUPERSAMPLE
    # sub-texel jitter grid, deterministic
    off = (np.arange(ss) + 0.5) / ss
    cols, rows = np.meshgrid(np.arange(n), np.arange(n))          # rows = image row from top
    rgb_acc = np.zeros((n, n, 3), dtype=np.float64)
    have_faces = all(f is not None for f in faces)
    for oy in off:
        for ox in off:
            s = (cols + ox) / n
            t = (rows + oy) / n
            ry = 2.0 * s - 1.0
            rz = 1.0 - 2.0 * t
            rr = ry * ry + rz * rz
            outside = rr > 1.0
            norm = np.sqrt(np.maximum(rr, 1e-12))
            ry = np.where(outside, ry / norm, ry)
            rz = np.where(outside, rz / norm, rz)
            rx = np.sqrt(np.maximum(1.0 - ry * ry - rz * rz, 0.0))
            # rows t > 0.5 (downward reflections) mirror the upward hemisphere
            rz_up = np.abs(rz)
            vp = np.stack([rx.ravel(), ry.ravel(), rz_up.ravel()], axis=1)
            vm = np.stack([-rx.ravel(), ry.ravel(), rz_up.ravel()], axis=1)
            if have_faces:
                c = 0.5 * (sample_cube(faces, vp) + sample_cube(faces, vm))
            else:
                c = 0.5 * (fallback_sky(vp) + fallback_sky(vm))
            rgb_acc += c.reshape(n, n, 3)
    rgb = rgb_acc / (ss * ss)

    # alpha: baked Fresnel on the texel-centre direction
    t_c = (rows + 0.5) / n
    rz_c = np.abs(1.0 - 2.0 * t_c)
    ry_c = 2.0 * ((cols + 0.5) / n) - 1.0
    rr_c = ry_c * ry_c + rz_c * rz_c
    rz_c = np.where(rr_c > 1.0, rz_c / np.sqrt(rr_c), rz_c)
    cos = np.clip(rz_c, 0.0, 1.0)
    alpha = ALPHA_MIN + (1.0 - ALPHA_MIN) * (1.0 - cos) ** ALPHA_POW

    img = np.zeros((n, n, 4), dtype=np.uint8)
    img[..., :3] = np.clip(np.rint(rgb), 0, 255).astype(np.uint8)
    img[..., 3] = np.clip(np.rint(alpha * 255.0), 0, 255).astype(np.uint8)
    return img


def encode_tga(img):
    """Uncompressed true-colour TGA, 32 bpp, bottom-up rows, BGRA - the retail froth*.tga layout
    (Pak2: type 2, desc 8). FULL 18-byte header: the 13-byte header of bug-2493 omitted the
    colour-map spec and the engine would have read every row 5 bytes off."""
    h, w = img.shape[0], img.shape[1]
    header = struct.pack("<BBBHHBHHHHBB",
                         0,      # id length
                         0,      # colour map type
                         2,      # image type: uncompressed true-colour
                         0, 0, 0,  # colour map spec (first entry, length, entry size)
                         0, 0,   # x/y origin
                         w, h,
                         32,     # bits per pixel
                         8)      # descriptor: 8 alpha bits, bottom-left origin
    assert len(header) == 18, len(header)
    bgra = img[::-1, :, [2, 1, 0, 3]]   # bottom-up, BGRA
    body = np.ascontiguousarray(bgra).tobytes()
    data = header + body
    assert len(data) == 18 + w * h * 4, len(data)
    return data


def report(img):
    a = img.astype(np.float64)
    lum = a[..., :3].max(axis=2) / 255.0
    al = a[..., 3] / 255.0
    n = img.shape[0]
    print("  %dx%d RGBA, %d-byte TGA" % (n, n, 18 + n * n * 4))
    for row in (0, n // 8, n // 4, 3 * n // 8, n // 2 - 1):
        t = (row + 0.5) / n
        print("  row %3d (t=%.3f, R.z=%+.2f): rgb %s  alpha %.3f  add@0.25 = %.3f" % (
            row, t, 1 - 2 * t, tuple(a[row, :, :3].mean(axis=0).round(1).tolist()),
            al[row].mean(), 0.25 * (lum[row] * al[row]).mean()))
    print("  upper-hemisphere rows (t<0.5): max-channel mean %.3f, max %.3f; additive contribution"
          " at alphaGen const 0.25 = mean %.3f, max %.3f" % (
              lum[: n // 2].mean(), lum[: n // 2].max(),
              0.25 * (lum[: n // 2] * al[: n // 2]).mean(),
              0.25 * (lum[: n // 2] * al[: n // 2]).max()))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--paks", default=",".join(DEFAULT_PAKS),
                    help="comma-separated fs dirs in mount order (main,mainta,maintt)")
    ap.add_argument("--check", action="store_true", help="regenerate in memory and compare")
    ap.add_argument("--preview", default=None, help="also write a PNG preview here (not in the repo)")
    ap.add_argument("--out", default=TEX)
    args = ap.parse_args()

    pak_dirs = [p for p in args.paks.split(",") if p]
    print("sky faces for %s:" % SKY_BASENAME)
    faces = load_faces(pak_dirs)
    if not all(f is not None for f in faces):
        print("  -> one or more faces missing: baking the FALLBACK overcast gradient instead")

    img = bake(faces)
    data = encode_tga(img)
    report(img)

    if args.preview:
        Image.fromarray(img, "RGBA").save(args.preview)
        print("  preview: %s" % args.preview)

    if args.check:
        with open(args.out, "rb") as fh:
            cur = fh.read()
        if cur == data:
            print("OK: %s matches the generator" % args.out)
            return 0
        print("STALE: %s differs from the generator (%d vs %d bytes)" % (args.out, len(cur), len(data)))
        return 1

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "wb") as fh:
        fh.write(data)
    print("wrote %s (%d bytes)" % (args.out, len(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
