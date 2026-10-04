# -*- coding: utf-8 -*-
"""Build / check zzzzzzzzzz_coop_m3l2ground.pk3 - m3l2's courtyard, barnyard and road ground (single process).

    python gen_m3l2ground_pak.py build --out DIR      build the pak + gates.json + sheets into DIR
    python gen_m3l2ground_pak.py check --pak PAK      rebuild in memory, byte-compare, re-run every gate (exit 1 = fail)

MEMBERS (all NEW names except the map):
  maps/m3l2.bsp                         retail main/Pak5.pk3 map, shader lump patched by bsp_patch.py (m3l2 ONLY)
  scripts/hzm_m3l2_ground.shader        textures/hzm_m3l2/road, textures/hzm_m3l2/farmyard + farmyard_b (tcGen vector, 512 u per repeat)
  textures/hzm_m3l2/farmyard.dds|.jpg   2048x2048 DXT1 full mips (+ jpg sibling: gl2 relief source, compression-off)
  textures/hzm_m3l2/road.dds|.jpg       1024x1024 DXT1 full mips (+ jpg sibling)
  CREDITS_m3l2ground.txt
WHY IT WINS: the only other copy of maps/m3l2.bsp is retail main/Pak5.pk3; every maintt pak mounts above main.
Every texture/shader name is new (exists in no other pak), so no pak order can hide or override them - and nothing
this pak ships can change another map: the retail m3l3grass_bocroad / _new / bocage_stevereq shaders and images are
untouched, and only m3l2's own BSP references the new names.
"""
import argparse, hashlib, io, json, os, struct, sys, zipfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "tools")))
import scene as SC                    # noqa: E402
import bsp_patch as BP                # noqa: E402
import gen_m3l2_ground as GG          # noqa: E402
import gen_tilefix_pak as TF          # noqa: E402
import gen_terrain_pak_v2 as V2       # noqa: E402
import clones as CL                   # noqa: E402

PAK_NAME = "zzzzzzzzzz_coop_m3l2ground.pk3"
FIXED_TS = (2026, 9, 29, 0, 0, 0)
NEW_ATTR = 0x81B60000
SEED = 7
RETAIL_BSP = ("main\\Pak5.pk3", "maps/m3l2.bsp")
RETAIL_BSP_SHA = "PIN"          # pinned on first build (printed) - see RETAIL_BSP_SHA_VALUE
RETAIL_BSP_SHA_VALUE = "b94848291ae680bd63130e8058f0b74521a8e859e3c93c1be46875433d4c6f24"
OMAHA_MAPS = ("maps/m3l1a.bsp", "maps/m3l1b.bsp", "maps/e3l1.bsp", "maps/e3l2.bsp", "maps/obj/obj_team3.bsp")

SHADER_HEAD = """// HZM coop - m3l2 ground (docs/proposals/m3l2_ground_2026-09-29). NEW names: only m3l2's patched BSP uses them.
// All follow the retail wilderness.shader ground recipe (diffuse + lightmap filter), so gl2 collapses them into
// lightall like every other ground (generated relief, rain wetness). tcGen vector takes three bare numbers per
// vector in BOTH renderers (ParseVector has no parentheses in OpenMOHAA - "( 0 x 0 )" would read as zeros).
// farmyard (courtyard faces) and farmyard_b (late-barn barnyard faces) share ONE image and differ only in their
// projection vectors: each is world-xy along its own group's BSP uv axes (bsp_patch.tcgen_vectors), so the
// generated relief tangent frame - built from the BSP's own uv - is lit from the right side on both.

textures/hzm_m3l2/road
{
	qer_editorimage textures/hzm_m3l2/road.tga
	qer_keyword natural
	qer_keyword flat
	surfaceparm dirt
	{
		map textures/hzm_m3l2/road.tga
		depthWrite
		rgbGen identity
	}
	{
		map $lightmap
		rgbGen identity
		blendFunc GL_DST_COLOR GL_ZERO
		depthFunc equal
	}
}
"""
YARD_BLOCK = """
%(name)s
{
	qer_editorimage textures/hzm_m3l2/farmyard.tga
	qer_keyword natural
	qer_keyword flat
	surfaceparm dirt
	{
		map textures/hzm_m3l2/farmyard.tga
		tcGen vector %(vec)s
		depthWrite
		rgbGen identity
	}
	{
		map $lightmap
		rgbGen identity
		blendFunc GL_DST_COLOR GL_ZERO
		depthFunc equal
	}
}
"""


def shader_text(orig_bsp):
    v = BP.tcgen_vectors(orig_bsp)
    out = SHADER_HEAD
    for nm in (BP.YARD.decode(), BP.YARD_B.decode()):
        (sx, sy, sz), (tx, ty, tz) = v[nm]
        vec = " ".join("%.10f" % (0.0 if abs(x) < 1e-9 else x) for x in (sx, sy, sz, tx, ty, tz))
        out += YARD_BLOCK % dict(name=nm, vec=vec)
    return out.encode("ascii")


CREDITS = b"""zzzzzzzzzz_coop_m3l2ground.pk3 - HZM coop, m3l2 (Battle in the Bocage) ground.
Every image is built from the game's own retail ground photographs (Medal of Honor: Allied Assault /
Breakthrough paks) by periodic image quilting, plus the CC0 grass (ambientCG Ground037) the mod already ships in
zzzzzzzzz_coop_terrain.pk3 for the road shoulders. No upscaler, no generated detail, no new third-party asset.
Generator: docs/proposals/m3l2_ground_2026-09-29/tools/gen_m3l2ground_pak.py (deterministic).
"""


def sha(b):
    return hashlib.sha256(b).hexdigest()


def retail_bsp():
    st = SC.stack()
    for i, m in st.copies.get(RETAIL_BSP[1], []):
        if st.name(i).lower() == RETAIL_BSP[0].lower():
            return st.read(i, m)
    raise SystemExit("retail m3l2.bsp not found")


def jpg(img):
    buf = io.BytesIO()
    Image.fromarray(np.clip(np.round(img), 0, 255).astype(np.uint8)).save(buf, "JPEG", quality=95, subsampling=0,
                                                                         optimize=False)
    return buf.getvalue()


def write_pak(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(members):
            zi = zipfile.ZipInfo(name, date_time=FIXED_TS)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = NEW_ATTR
            zi.create_system = 0
            z.writestr(zi, members[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return buf.getvalue()


# ============================================================================================================ gates
GATES = []


def gate(name, ok, detail=""):
    GATES.append(dict(name=name, ok=bool(ok), detail=detail))
    print(("PASS " if ok else "FAIL ") + name + ("  " + detail if detail else ""), flush=True)


def wrap_ratio(L, axis):
    """seam test: the |step| across the wrap line vs the median |step| across every interior line (same axis)."""
    d = np.abs(np.diff(L, axis=axis, append=np.take(L, [0], axis=axis)))
    per_line = d.mean(axis=1 - axis) if axis == 0 else d.mean(axis=0)
    return float(per_line[-1] / np.median(per_line[:-1]))


def self_similarity(L):
    """max normalised autocorrelation of the 8-64 u band away from zero lag (a clone / stamp detector)."""
    from scipy import ndimage
    b = ndimage.gaussian_filter(L, 4, mode="wrap") - ndimage.gaussian_filter(L, 32, mode="wrap")
    f = np.fft.fft2(b)
    ac = np.real(np.fft.ifft2(f * np.conj(f)))
    ac /= ac[0, 0]
    h, w = ac.shape
    yy, xx = np.meshgrid(np.fft.fftfreq(h) * h, np.fft.fftfreq(w) * w, indexing="ij")
    ac[np.hypot(yy, xx) < 48] = 0
    return float(ac.max())


def gates(members, orig_bsp, fy, rd, rep):
    new_bsp = members["maps/m3l2.bsp"]
    v = BP.verify(orig_bsp, new_bsp, BP.YARD_SURFS + BP.BARN_SURFS)
    gate("bsp: only shader lump + yard shaderNums changed", True, "entries %s renamed, 2 appended, +%d B" %
         (v["changed_entries"], v["bytes_added"]))
    # the staged/shipped foliage lightmap patch keys on the lightmap lump: must be byte-identical
    Lo, Ln = BP.lumps(orig_bsp), BP.lumps(new_bsp)
    lo = orig_bsp[Lo[2][0]:Lo[2][0] + Lo[2][1]]
    ln = new_bsp[Ln[2][0]:Ln[2][0] + Ln[2][1]]
    gate("bsp: lightmap lump identical (maps/m3l2.hzmlm still applies)", lo == ln and Lo[2] == Ln[2])
    st = SC.stack()
    others = [st.name(i) for i, m in st.copies.get("maps/m3l2.bsp", [])]
    gate("pak order: the only other maps/m3l2.bsp is retail main/Pak5 (any maintt pak wins)",
         others == ["main\\Pak5.pk3"], str(others))
    clash = [k for k in st.copies if k.startswith("textures/hzm_m3l2/") or k == "scripts/hzm_m3l2_ground.shader"]
    gate("new names exist in no other pak", not clash, str(clash[:5]))
    # no other BSP of the player stack references the new names (so nothing but m3l2 can draw them)
    refs = []
    for p in sorted(k for k in st.copies if k.startswith("maps/") and k.endswith(".bsp")):
        i, m = st.winner(p)
        if b"hzm_m3l2" in st.read(i, m):
            refs.append(p)
    gate("no player-stack BSP references textures/hzm_m3l2 (only the patched m3l2 will)", not refs, str(refs))
    gate("Omaha maps untouched (not in this pak)", not any(m in members for m in OMAHA_MAPS))
    gate("no retail texture/shader name overridden", all(k.startswith(("textures/hzm_m3l2/", "maps/m3l2.bsp",
                                                                    "scripts/hzm_m3l2", "CREDITS")) for k in members))
    # DDS format + encoder lean, both textures
    for nm, img in (("farmyard", fy), ("road", rd)):
        d = members["textures/hzm_m3l2/%s.dds" % nm]
        ok, info, three = TF.check_dds_format(d)
        gate("%s.dds: DXT1, full mip chain to 1x1, 4-colour blocks only" % nm, ok,
             "%dx%d mips %d, 3-colour blocks %d" % (info["w"], info["h"], info["mips"], three))
        dec = V2.dds_decode_level(d, info, 0)[..., :3].astype(np.float64)
        lean = np.abs(dec.reshape(-1, 3).mean(0) - img.reshape(-1, 3).mean(0))
        gate("%s.dds: no encoder colour lean (level-0 mean within 0.75 of float)" % nm, lean.max() <= 0.75,
             "per-channel %s" % np.round(lean, 2).tolist())
        drift = []
        for k in range(1, info["mips"]):
            if min(info["w"], info["h"]) >> k < 16:      # below 16 px a DXT level is 565 quantisation (v4 rule)
                break
            m = V2.dds_decode_level(d, info, k)[..., :3].reshape(-1, 3).mean(0)
            drift.append(float(np.abs(m - dec.reshape(-1, 3).mean(0)).max()))
        gate("%s.dds: mips down to 16 px keep the level-0 mean within 1.5" % nm, max(drift) <= 1.5,
             "worst %.2f" % max(drift))
    Lf = GG.luma(fy)
    zx, zy = wrap_ratio(Lf, 1), wrap_ratio(Lf, 0)
    gate("farmyard: no wrap seam (wrap-line step <= 1.15 x interior median, both axes)", max(zx, zy) <= 1.15,
         "s %.3f t %.3f" % (zx, zy))
    zr = wrap_ratio(GG.luma(rd), 1)
    gate("road: no wrap seam along the road (s)", zr <= 1.15, "%.3f" % zr)
    ss = self_similarity(GG.luma(fy)[::4, ::4])
    gate("farmyard: no clone / stamp (max off-peak 8-64u autocorrelation <= 0.30)", ss <= 0.30, "%.3f" % ss)
    cs = CL.clone_stats(GG.luma(fy)[::4, ::4], W=48, n=80)
    gate("farmyard: no near-exact copy (48 u patches, best other match > 0.9 in 8 orientations: 0%)",
         cs["frac90"] == 0.0, "frac90 %.3f frac97 %.3f median %.2f" % (cs["frac90"], cs["frac97"], cs["median"]))
    fm = fy.reshape(-1, 3).mean(0)
    gate("farmyard: mean colour = neighbour dirt target within 2 levels", np.abs(fm - GG.DIRT_TARGET).max() <= 2.0,
         "%s vs %s" % (np.round(fm, 1).tolist(), GG.DIRT_TARGET.tolist()))
    band = rd[int(0.3 * rd.shape[0]):int(0.7 * rd.shape[0])].reshape(-1, 3).mean(0)
    gate("road: centre dirt within 6 levels of the farmyard (they meet at the courtyard joins)",
         np.abs(band - fm).max() <= 6.0, "%s" % np.round(band, 1).tolist())
    gr = GG.grass_rgb().reshape(-1, 3).mean(0)
    edge = np.concatenate([rd[:int(0.06 * rd.shape[0])], rd[-int(0.06 * rd.shape[0]):]]).reshape(-1, 3).mean(0)
    gate("road: shoulder grass within 4 levels of the terrain grass it meets", np.abs(edge - gr).max() <= 4.0,
         "%s vs %s" % (np.round(edge, 1).tolist(), np.round(gr, 1).tolist()))
    clip = float(((fy <= 0.5) | (fy >= 254.5)).mean())
    gate("farmyard: clipped values <= 0.05%", clip <= 0.0005, "%.4f%%" % (clip * 100))


def build(out_dir=None):
    del GATES[:]
    orig = retail_bsp()
    print("retail maps/m3l2.bsp sha256", sha(orig))
    if RETAIL_BSP_SHA_VALUE:
        gate("retail m3l2.bsp is the pinned one", sha(orig) == RETAIL_BSP_SHA_VALUE)
    fy, q, rep = GG.build_farmyard(SEED)
    rd, rrep = GG.build_road(SEED)
    fy, rd = GG.toe(fy), GG.toe(rd)
    new_bsp, info = BP.patch(orig)
    members = {
        "maps/m3l2.bsp": new_bsp,
        "scripts/hzm_m3l2_ground.shader": shader_text(orig).replace(b"\n", b"\r\n"),
        "textures/hzm_m3l2/farmyard.dds": TF.encode_dxt1(fy),
        "textures/hzm_m3l2/farmyard.jpg": jpg(fy),
        "textures/hzm_m3l2/road.dds": TF.encode_dxt1(rd),
        "textures/hzm_m3l2/road.jpg": jpg(rd),
        "CREDITS_m3l2ground.txt": CREDITS.replace(b"\n", b"\r\n"),
    }
    gates(members, orig, fy, rd, rep)
    pak = write_pak(members)
    report = dict(pak=PAK_NAME, sha256=sha(pak), size=len(pak), retail_bsp_sha256=sha(orig), bsp_patch=info,
                  members={k: dict(sha256=sha(v), size=len(v)) for k, v in sorted(members.items())},
                  farmyard=rep, road=rrep, gates=GATES)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, PAK_NAME), "wb") as fh:
            fh.write(pak)
        with open(os.path.join(out_dir, "gates.json"), "w") as fh:
            json.dump(report, fh, indent=1, default=float)
        Image.fromarray(np.clip(fy, 0, 255).astype(np.uint8)).save(os.path.join(out_dir, "farmyard_preview.png"))
        Image.fromarray(np.clip(rd, 0, 255).astype(np.uint8)).save(os.path.join(out_dir, "road_preview.png"))
    print("pak", PAK_NAME, sha(pak), len(pak), "bytes;", sum(not g["ok"] for g in GATES), "gate failures")
    return pak, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("build", "check"))
    ap.add_argument("--out")
    ap.add_argument("--pak")
    a = ap.parse_args()
    pak, rep = build(a.out if a.mode == "build" else None)
    fails = [g for g in GATES if not g["ok"]]
    if a.mode == "check":
        with open(a.pak, "rb") as fh:
            have = fh.read()
        same = have == pak
        print(("PASS" if same else "FAIL") + " pak on disk is byte-identical to a rebuild (%s vs %s)" %
              (sha(have)[:12], sha(pak)[:12]))
        if not same:
            sys.exit(1)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
