"""[flguns] Frontline disc guns - the converter stage (runs on the PLAYER's PC, after the level loop of `hzmconv add`).

The player's own disc gives the first-person gun meshes, their textures and the gun clips; the player's MOHAA install
gives the base guns (bone blocks, rows, wavs). Everything that is computed from the disc is computed HERE, never
shipped: the cut (level 7_1 level.viv weapon DMFs), the sight solve (flgunsight + the ship-safe spec table
discguns_sights.json), the sound decode (7_1GunBnk.abk through the converter's own vgmstream), the fit (flgunfit + the
ship-safe discguns_baserows.json) and the upscale (flgunup, the converter's own realesrgan).

Output: ONE pak in the home, zzzzzzzzzzzzzzzzzzzz_byo_guns_fl.pk3 (models, sounds, shaders, textures and
scripts/hzm_adssights_byo_fl.txt - the sight rows, which are also the ownership marker the engine looks for). The
level paks are never touched. Entries are sorted with a fixed timestamp, so the same disc and install give the same
pak bytes. A gun whose base is missing from the install (an older mod build) is skipped, never a failed conversion;
no gun at all -> no pak (an old one is removed).

    convert(image, home, mohaa, progress, opts) -> [pak path] or []
    opts: vgm (vgmstream-cli.exe), esrgan (realesrgan-ncnn-vulkan.exe), upscale (default True), keys"""
import os
import shutil
import struct
import tempfile
import zipfile

import numpy as np

PAK = "zzzzzzzzzzzzzzzzzzzz_byo_guns_fl.pk3"
ROWS_FILE = "scripts/hzm_adssights_byo_fl.txt"
KEYS = ["fl_th", "fl_bar", "fl_mp40", "fl_stg44", "fl_sg",                      # batch 1
        "fl_m1", "fl_colt", "fl_p38", "fl_silpis",                                  # batch 2 (2026-11-16)
        "fl_spring", "fl_g43",                                                      # batch 3: scoped
        "fl_bazooka", "fl_panzer",                                                  # batch 4: launchers
        "fl_markIIgrenade", "fl_stickgrenade"]                                      # batch 5: grenades
LEVEL = "7_1"                       # the level whose level.viv carries every Frontline first-person gun + GunBnk
ZIP_TIME = (2026, 1, 1, 0, 0, 0)
DMF = {"th": "th_weapon.dmf", "bar": "bar_weapon.dmf", "mp40": "mp40_weapon.dmf", "stg44": "stg44_weapon.dmf",
       "sg": "sg_weapon.dmf", "m1": "m1_weapon.dmf", "colt": "colt_weapon.dmf", "p38": "p38_weapon.dmf",
       "silpis": "silpis_weapon.dmf", "spring": "spring_weapon.dmf", "g43": "g43_weapon.dmf",
       "bazooka": "bazooka_weapon.dmf", "panzer": "panzer_weapon.dmf",
       "markIIgrenade": "markIIgrenade_weapon.dmf", "stickgrenade": "stickgrenade_weapon.dmf"}
GUNBONES = ("weapon", "bolt", "mag", "clip", "hammer", "handgrip", "bipod", "weapon_0")


# ------------------------------------------------------------------ the disc cut (private fldisc.py / fl_gunpart.py)
def read_dmf(b):
    """flchar.read_dmf with the bind rotations at their real offset: right after the bone names, 16-aligned
    (0x5c + 16 * bones). flchar reads 0x4c0, which is that offset only for the 70-bone character bodies; a weapon
    .dmf has 47-55 bones (bug-11285, the floating Thompson magazine)."""
    import flchar
    d = flchar.read_dmf(b)
    nb = struct.unpack_from("<I", b, 0x48)[0]
    o = (0x5c + 16 * nb + 15) & ~15
    d["rot"] = [struct.unpack_from("<3h", b, o + 6 * i) for i in range(nb)]
    return d


def is_gun(b):
    b = b.lower()
    return any(b.startswith(g) for g in GUNBONES)


class DiscGuns:
    """the 7_1 level.viv of the player's disc, opened once: load(key) -> {"parts": [...], "tex": {name: (w, h, rgba)}}"""

    def __init__(self, disc, lv=LEVEL):
        import flcore
        import flchar
        self.files = disc.viv_members(flcore.level_dir(lv) + "level.viv")
        self.tpk = {}
        for k in self.files:
            if k.lower().endswith(".tpk"):
                self.tpk.update(flchar.read_tpk(self.files[k]))

    def load(self, key):
        import flchar
        dmf = DMF[key]
        d = read_dmf(self.files[dmf])
        skl = flchar.read_skl(self.files[dmf.split("_weapon")[0] + "_weapon.skl"])
        B = flchar.bind(skl, d)
        parts, texs = [], {}
        for me in d["meshes"]:
            if not me["tex"] or me["tex"].upper() not in self.tpk:
                continue
            V, UV, T, BN = [], [], [], []
            for pal, P, U in me["batches"]:
                base = len(V)
                for p, u in zip(P, U):
                    a, b, w = d["wts"][pal[min(int(round(u[2] / 3.0)), len(pal) - 1)]]
                    J, R = B[d["names"][a]]
                    V.append(flchar._add(flchar._mv(R, p[:3]), J))
                    UV.append((u[0], u[1]))
                    BN.append(d["names"][a])
                T += [(base + x, base + y, base + z) for x, y, z in flchar.strip_tris([tuple(p[:3]) for p in P])]
            keep = [t for t in T if all(is_gun(BN[i]) for i in t)]
            if not keep:
                continue
            used = sorted({i for t in keep for i in t})
            remap = {i: k for k, i in enumerate(used)}
            tn = me["tex"]
            texs[tn] = self.tpk[tn.upper()]
            parts.append({"tex": tn, "V": np.array([V[i] for i in used]), "UV": np.array([UV[i] for i in used]),
                          "T": np.array([[remap[i] for i in t] for t in keep]), "bone": [BN[i] for i in used]})
        return {"parts": parts, "tex": texs}


# ------------------------------------------------------------------ the gun clips (private snd_from_disc.py)
def decode_sounds(disc, streams, tmp, vgm, lv=LEVEL):
    """-> {stream: wav path} decoded from <lv>GunBnk.abk with the converter's vgmstream; {} without one"""
    import flcore
    import flaudio
    if not vgm or not os.path.exists(vgm):
        return {}
    ab = disc.read(flcore.level_dir(lv) + lv.replace("_", "") + "GunBnk.abk")
    bnk, ents = flaudio.bnk_entries(ab)
    src = os.path.join(tmp, "gun.bnk")
    open(src, "wb").write(bnk)
    have = {e["stream"] for e in ents}
    out = {}
    for s in streams:
        if s not in have:
            continue
        dst = os.path.join(tmp, "%s_%03d.wav" % (lv, s))
        if flaudio.vgm_decode(vgm, src, dst, s):
            out[s] = dst
    return out


# ------------------------------------------------------------------ the stage
def build_files(image, home, mohaa, progress=lambda **kv: None, opts=None):
    """-> ({pak path: bytes}, {key: fit info}) - everything the guns pak holds, nothing written yet"""
    import flcore
    import flgunvfs
    import flgunfit
    import flgunsight
    opts = opts or {}
    flgunvfs.setup(mohaa, home)
    disc = flcore.Disc(image)
    guns = DiscGuns(disc)
    specs = flgunsight.load_specs(opts.get("specs"))
    tmp = tempfile.mkdtemp(prefix="flguns_")
    files, rows, report = {}, [], {}
    try:
        keys = opts.get("keys", KEYS)
        streams = sorted({i for k in keys for i in flgunfit.SOUNDS.get(k, {}).values()})
        snd = decode_sounds(disc, streams, tmp, opts.get("vgm"))
        if streams and not snd:
            progress(step="guns_sounds", skipped="no vgmstream: the base sounds stay")
        for k in keys:
            progress(step="guns", gun=k)
            try:
                d = guns.load(k[3:])
                fr = flgunsight.solve_key(k, d, specs[k])
                f, info = flgunfit.write_gun(k, d, fr, snd, opts.get("rows"))
            except flgunfit.MissingBase as e:
                progress(step="guns", gun=k, skipped="not in this mod build: %s" % e)
                continue
            if "_row" in f:                  # a grenade has no sight row
                rows.append(f.pop("_row").decode())
            files.update(f)
            report[k] = info
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not files:                       # nothing converted (a grenade-only key list still writes the marker)
        return {}, report
    files[ROWS_FILE] = ("// HZM coop discguns: converted on this PC (sight rows of the fitted disc meshes)\n"
                        + "\n".join(sorted(rows, key=lambda r: r.split()[1])) + "\n").encode()
    if opts.get("upscale", True):
        try:
            import flgunup
            report["_upscale"] = flgunup.upscale_files(files, opts.get("esrgan"), progress)
        except Exception as e:           # never fails the conversion: the disc originals stay
            progress(step="guns_upscale", skipped=str(e))
    return files, report


def write_pak(files, out):
    tmp = out + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for n in sorted(files):
            zi = zipfile.ZipInfo(n, ZIP_TIME)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, files[n])
    os.replace(tmp, out)
    return out


def convert(image, home, mohaa, progress=lambda **kv: None, opts=None):
    out = os.path.join(home, PAK)
    try:
        files, report = build_files(image, home, mohaa, progress, opts)
    finally:
        if os.path.exists(out + ".tmp"):
            os.remove(out + ".tmp")
    if not files:
        if os.path.exists(out):
            os.remove(out)
        return []
    return [write_pak(files, out)]
