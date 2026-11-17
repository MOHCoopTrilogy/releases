"""[eaguns] European Assault disc guns - the converter stage (runs on the PLAYER's PC). The EA twin of frontline/flguns.py.

The Frontline gun converter is reused as is: flgunsight solves the sight points from the ship-safe spec table
(frontline/discguns_sights.json, keys ea_*), flgunfit fits the disc mesh onto the base gun's bone block and writes the
skd / tik / shader / tga / wav files, flgunup upscales the textures. This module only adds what is EA-specific:

  * the cut: each gun's best copy (the level whose LEVEL_A.STR carries its highest-resolution textures) read with
    eaprops.read. An EA gun is one rigid mesh with SKIN WEIGHTS on a small per-gun skeleton (bone ids 0..7, no names on
    the disc): the moving parts (bolt, magazine, pump, rocket) ride their own bone. ROLES below says, per gun, which
    bone id is which part (read off the disc's own bind pose by position: a magazine is the bone hanging under the
    receiver, a bolt / cocking handle the one beside or on it). Every triangle goes whole to the bone carrying most of
    its corners, so a part is never torn.
  * the sounds: EA keys every sound by an alias id in SOUND/Audio.ubr (records: sample index, bank, alias); a sample is
    decoded from its bank (scr.abk / L1..L8.abk) with the converter's own vgmstream (subsong = index + 1).
  * GUNS / SOUNDS rows registered into flgunfit (the same row shapes as the Frontline rows).

Output: ONE pak in the home, zzzzzzzzzzzzzzzzzzzz_byo_guns_ea.pk3 with scripts/hzm_adssights_byo_ea.txt (the sight
rows; the engine's guns_ea ownership token). Same determinism rules as flguns (sorted entries, fixed timestamp).

    convert(image, home, mohaa, progress, opts) -> [pak path] or []
    opts: vgm (vgmstream-cli.exe), esrgan (realesrgan-ncnn-vulkan.exe), upscale (default True), keys"""
import os
import shutil
import struct
import tempfile
import zlib

import numpy as np

PAK = "zzzzzzzzzzzzzzzzzzzz_byo_guns_ea.pk3"
ROWS_FILE = "scripts/hzm_adssights_byo_ea.txt"

# key (= the sight spec key, "ea_" + the model name without _gun_geo / _geo) -> the disc model, its best copy, the base gun
# and the bone roles. Bone ids are the disc skin's; a bone not listed rides the gun body. hide: bones left out (a
# reload-pose part posed over the gun in the bind pose).
G = {
    "ea_smg_thompson": dict(model="smg_thompson_gun_geo", level="1_1", base="thompsonsmg", name="Thompson (European Assault)",
                            roles={"b1": "bolt", "b2": "mag"}),
    "ea_mg_bar": dict(model="mg_bar_gun_geo", level="1_21", base="bar", name="BAR (European Assault)",
                      roles={"b1": "bolt", "b2": "mag"}),
    "ea_smg_mp40": dict(model="smg_mp40_gun_geo", level="1_1", base="mp40", name="MP40 (European Assault)",
                        roles={"b1": "bolt", "b3": "mag"}),
    "ea_mg_stg": dict(model="mg_stg_gun_geo", level="1_15", base="mp44", name="StG 44 (European Assault)",
                      roles={"b3": "bolt", "b4": "mag"}),
    "ea_SMG_PPSH": dict(model="SMG_PPSH_gun_geo", level="1_11", base="ppsh_smg", name="PPSh-41 (European Assault)",
                        roles={"b5": "bolt", "b3": "mag"}),
    "ea_smg_mp28": dict(model="smg_mp28_gun_geo", level="2_59", base="coop_bergmann", name="MP28 (European Assault)",
                        roles={"b2": "bolt", "b1": "mag"}),
    "ea_smg_sten": dict(model="smg_sten_gun_geo", level="2_57", base="sten", stub="sten_mk2s_ea", body="sten_mk2s_ea",
                        name="Sten Mk II(S) (European Assault)", roles={"b1": "bolt", "b2": "mag"}),
    "ea_rifle_m1": dict(model="rifle_m1_gun_geo", level="1_1", base="m1_garand", name="M1 Garand (European Assault)",
                        roles={"b1": "bolt", "b2": "bolt", "b3": "mag", "b4": "mag"}),
    "ea_rifle_karabiner": dict(model="rifle_karabiner_gun_geo", level="1_1", base="kar98", name="Kar98k (European Assault)",
                               roles={"b2": "bolt", "b3": "bolt", "b4": "mag"}),
    "ea_rifle_gewehr": dict(model="rifle_gewehr_gun_geo", level="1_11", base="coop_g43_irons", name="G 43 (European Assault)",
                            roles={"b1": "bolt", "b2": "mag"}),
    "ea_rifle_mn1891": dict(model="rifle_mn1891_gun_geo", level="1_15", base="mosin_nagant_rifle",
                            name="Mosin-Nagant 1891 (European Assault)", roles={"b1": "bolt", "b2": "bolt", "b5": "bolt"}),
    "ea_rifle_shotgun": dict(model="rifle_shotgun_gun_geo", level="1_22", base="shotgun", name="Shotgun (European Assault)",
                             roles={"b1": "pump"}, maxtilt=4.0),     # as Frontline's: the pump fingers stay under the bead
    "ea_PISTOL_45auto": dict(model="PISTOL_45auto_gun_geo", level="1_2", base="colt45", name="Colt 45 (European Assault)",
                             roles={"b1": "bolt", "b2": "mag"}),
    # the scoped rifles: true scale, the fitted glass disc on the disc ocular (the base rifle's tint), slide 0 (eye relief = base)
    "ea_rifle_gewehrScoped": dict(model="rifle_gewehrScoped_gun_geo", level="1_21", base="g43",
                                  name="G 43 Sniper (European Assault)", roles={"b1": "bolt", "b2": "mag"}, glass="blue",
                                  slide=0.0),
    "ea_rifle_m1Scoped": dict(model="rifle_m1Scoped_gun_geo", level="1_22", base="garand_scoped",
                              name="M1 Garand Sniper (European Assault)",
                              roles={"b1": "bolt", "b2": "bolt", "b3": "mag", "b4": "mag"}, glass="blue", slide=0.0),
    # b7: the 5-round charger posed OVER the scope in the bind pose (a reload part) - left out
    "ea_rifle_enfieldScoped": dict(model="rifle_enfieldScoped_gun_geo", level="1_8", base="enfieldsniper",
                                   name="Lee-Enfield No.4 (T) (European Assault)", roles={"b3": "bolt", "b4": "bolt", "b5": "bolt"},
                                   hide=[7], glass="blue", slide=0.0),
    "ea_rifle_mnvp": dict(model="rifle_mnvp_gun_geo", level="2_52", base="nagant_sniper",
                          name="Mosin-Nagant Sniper (European Assault)", roles={"b1": "bolt", "b2": "bolt", "b3": "bolt"},
                          glass="blue", slide=0.0),
    # the launchers: the disc bore on the base bore (sight line VIRTUAL, see discguns_sights.json); the disc ROCKET is the
    # reload shell (role mag -> the base's toggled surface, bazookashell: hidden except while it goes in)
    "ea_misc_M1bazooka": dict(model="misc_M1bazooka_gun_geo", level="1_11", base="bazooka", name="M1 Bazooka (European Assault)",
                              roles={"b2": "mag"}, fit="bore", k=1.0, slide=12.0, snap_mag=True),
    "ea_misc_M9bazooka": dict(model="misc_M9bazooka_gun_geo", level="1_21", base="bazooka", stub="bazooka_ea2",
                              body="bazooka_ea2", name="M9 Bazooka (European Assault)", roles={"b4": "mag"}, fit="bore", k=1.0, snap_mag=True,
                              slide=12.0),
    # the grenades: no sight row, centred on the base grenade (true scale); the frag's whole mesh is the surface the base
    # anims hide after the throw (as Frontline's), the stick grenade's anims use `surface all`
    "ea_grenade_frag": dict(model="grenade_frag_gun_geo", level="1_21", base="m2frag_grenade_sp_start",
                            name="Frag Grenade (European Assault)", roles={"b": "mag"}),
    "ea_grenade_mills": dict(model="grenade_mills_geo", level="1_1", base="mills_grenade_sp_start",
                             name="Mills Bomb (European Assault)", roles={"b": "mag"}),
    "ea_grenade_stick": dict(model="grenade_stick_geo", level="1_15", base="steilhandgranate_start",
                             name="Stielhandgranate (European Assault)"),
}
KEYS = list(G)
ZIP_TIME = (2026, 1, 1, 0, 0, 0)
BANKS = {0x40000000: "SCR.ABK", 1: "L1.ABK", 2: "L2.ABK", 4: "L3.ABK", 8: "L4.ABK", 16: "L5.ABK", 32: "L6.ABK",
         64: "L7.ABK", 128: "L8.ABK"}

# disc sound per base alias slot: (level, alias id in that level's Audio.ubr, pick) - pick = which of the alias's samples
# (an EA alias is a random set; the first is taken). Slots not listed keep the base sound.
# Read off the running original (2026-11-16, bug-11367): a gdb break on the DirectSound voice start (0x2F0FEA) gives each
# voice's data pointer ([[voice+0x70]+0xbc]); those bytes sit in the level's SCR.ABK, and the BNKl PT table maps the offset to
# the sample index. Only the player's own trigger pulls were counted (voices within 0.25 s of each pull, every pull).
#   PPSh (1_11): main shot = sample 230 (stereo, 0.32 s, twice per burst step) + mech layer 79 + random tail 306 / 308.
#   M1 (1_1): shots alternate 155 / 156 (stereo), layer 157 ~0.14 s later, the 8th shot adds 158 (ping) then 159 (reload).
# One MOHAA alias = one clip, so the main shot is wired; the layers are listed as deviations.
SOUNDS = {
    "ea_SMG_PPSH": {"ppsh41_snd_fire": ("1_11", 0x6ae7dee1)},                         # alias = [230, 230]
    "ea_rifle_m1": {"m1_snd_fire": ("1_1", 0x2cf5ecd1),                               # alias = [155, 156, 157, 158, ...]
                    "snd_ping": ("1_1", 0x2cf5ecd1, 3)},                              # its 4th sample = 158, the ping
}
BASE_SND = {
    "ppsh41_snd_fire": ("sound/weapons/fire/wpnfire_PPSH_SMG02.wav", "1.82 0.01 0.95 0.1 480 8000 weapon"),
}


def stub_of(key):
    c = G[key]
    return c.get("stub") or "%s_ea" % c["base"]


def register():
    """the EA rows into flgunfit's tables (the fit / write code reads them by key)"""
    import flgunfit
    for k, c in G.items():
        row = dict(base=c["base"], stub=stub_of(k), name=c["name"], roles=c.get("roles"))
        for o in ("glass", "slide", "fit", "k", "shift", "maxtilt", "keep_base", "drop", "bones", "body", "snap_mag"):
            if o in c:
                row[o] = c[o]
        if "body" not in row:
            row["body"] = stub_of(k)
        flgunfit.GUNS[k] = row
    for k, s in SOUNDS.items():
        flgunfit.SOUNDS[k] = {a: "%s:%08x" % v[:2] + (":%d" % v[2] if len(v) > 2 and v[2] else "") for a, v in s.items()}
    flgunfit.BASE_SND.update(BASE_SND)


# ------------------------------------------------------------------ the disc cut
def level_stream(disc, lv):
    return disc.read("DATA/%s/%s/LEVEL_A.STR" % (lv.split("_")[0], lv))


class DiscGuns:
    """the player's EA disc: load(key) -> {"parts": [...], "tex": {name: (w, h, rgba)}} (flguns.DiscGuns shape; part bones
    are "b<disc bone id>")"""

    def __init__(self, disc):
        self.disc = disc
        self._lv = None
        self._d = None

    def _stream(self, lv):
        if self._lv != lv:
            self._d, self._lv = level_stream(self.disc, lv), lv
        return self._d

    def load(self, key):
        import eachar
        import eaprops
        c = G[key]
        d = self._stream(c["level"])
        at = d.find(("__Model:::%s.mesh" % c["model"]).encode())
        typ = None
        for p, cid, t, sz in eachar._chunks(d):
            if p <= at < p + sz:
                typ = t
                break
        m = eaprops.read(d, c["model"], typ) if typ is not None else None
        if not m:
            raise KeyError("%s: %s not on level %s" % (key, c["model"], c["level"]))
        dom = eaprops.dominant_bones(m)
        hide = set(c.get("hide", []))
        parts, texs = [], {}
        for k, (pos, uv, tris, shape) in enumerate(m["meshes"]):
            sh = (shape or "none").split("#")[0]
            im = m["textures"].get(sh)
            if im is None:
                continue
            db = dom[k] or [0] * len(pos)
            V, UV, BN, T, vmap = [], [], [], [], {}
            for tr in tris:
                bs = [db[i] for i in tr]
                b = max(set(bs), key=lambda x: (bs.count(x), -bs.index(x)))
                if b in hide:
                    continue
                t = []
                for i in tr:
                    if (i, b) not in vmap:
                        vmap[(i, b)] = len(V)
                        V.append(pos[i])
                        UV.append(uv[i])
                        BN.append("b%d" % b)
                    t.append(vmap[(i, b)])
                T.append(t)
            if not T:
                continue
            texs[sh] = (im["w"], im["h"], bytes(im["rgba"]))
            parts.append({"tex": sh, "V": np.array(V, float), "UV": np.array(UV, float), "T": np.array(T),
                          "bone": BN})
        return {"parts": parts, "tex": texs}


# ------------------------------------------------------------------ the sounds
def ubr_aliases(ubr):
    """{alias id: [(bank, sample index)]} from a level's Audio.ubr (fields read by name, eapack.sounddefs)"""
    nf, nr, st = struct.unpack_from("<III", ubr, 16)
    off = {}
    for i in range(nf):
        c, t, o = struct.unpack_from("<III", ubr, 32 + 12 * i)
        off[c] = o
    fa = off[zlib.crc32(b"Alias") & 0xffffffff]
    fb = off[zlib.crc32(b"Bank Type") & 0xffffffff]
    fs = off[0xBC1069FF]
    base = 32 + 12 * nf
    out = {}
    for r in range(nr):
        rs = base + r * st
        if rs + st > len(ubr):
            break
        out.setdefault(struct.unpack_from("<I", ubr, rs + fa)[0], []).append(
            (struct.unpack_from("<I", ubr, rs + fb)[0], struct.unpack_from("<H", ubr, rs + fs)[0]))
    return out


def decode_sounds(disc, refs, tmp, vgm):
    """refs: {"<level>:<alias hex>[:<pick>]"} -> {ref: wav path} (the alias's sample <pick>, default the first); {} without
    vgmstream"""
    import subprocess
    if not vgm or not os.path.exists(vgm):
        return {}
    out, ubrs, banks = {}, {}, {}
    for ref in sorted(refs):
        lv, ah = ref.split(":")[:2]
        pick = int(ref.split(":")[2]) if ref.count(":") > 1 else 0
        d = "DATA/%s/%s/SOUND/" % (lv.split("_")[0], lv)
        if lv not in ubrs:
            try:
                ubrs[lv] = ubr_aliases(disc.read(d + "AUDIO.UBR"))
            except Exception:
                ubrs[lv] = {}
        smp = ubrs[lv].get(int(ah, 16))
        if not smp or len(smp) <= pick or smp[pick][0] not in BANKS:
            continue
        bk, idx = smp[pick]
        src = os.path.join(tmp, "%s_%s" % (lv, BANKS[bk]))
        if src not in banks:
            open(src, "wb").write(disc.read(d + BANKS[bk]))
            banks[src] = 1
        dst = os.path.join(tmp, "%s_%s_%d.wav" % (lv, ah, pick))
        r = subprocess.run([vgm, "-s", str(idx + 1), "-i", "-o", dst, src], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, creationflags=(0x08000000 | 0x00000040) if os.name == "nt" else 0)
        if r.returncode == 0 and os.path.exists(dst):
            out[ref] = dst
    return out


# ------------------------------------------------------------------ the stage
def build_files(image, home, mohaa, progress=lambda **kv: None, opts=None):
    """-> ({pak path: bytes}, {key: fit info}) - everything the EA guns pak holds, nothing written yet"""
    import flcore
    import flgunvfs
    import flgunfit
    import flgunsight
    opts = opts or {}
    register()
    flgunvfs.setup(mohaa, home)
    disc = flcore.Disc(image)
    guns = DiscGuns(disc)
    specs = flgunsight.load_specs(opts.get("specs"))
    tmp = tempfile.mkdtemp(prefix="eaguns_")
    files, rows, report = {}, [], {}
    try:
        keys = opts.get("keys", KEYS)
        refs = sorted({r for k in keys for r in flgunfit.SOUNDS.get(k, {}).values()})
        snd = decode_sounds(disc, refs, tmp, opts.get("vgm"))
        if refs and not snd:
            progress(step="guns_sounds", skipped="no vgmstream: the base sounds stay")
        for k in keys:
            progress(step="guns", gun=k)
            try:
                d = guns.load(k)
                fr = flgunsight.solve_key(k, d, specs[k])
                f, info = flgunfit.write_gun(k, d, fr, snd, opts.get("rows"))
            except flgunfit.MissingBase as e:
                progress(step="guns", gun=k, skipped="not in this mod build: %s" % e)
                continue
            if "_row" in f:
                rows.append(f.pop("_row").decode())
            files.update(f)
            report[k] = info
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not files:
        return {}, report
    files[ROWS_FILE] = ("// HZM coop discguns: converted on this PC (sight rows of the fitted European Assault meshes)\n"
                        + "\n".join(sorted(rows, key=lambda r: r.split()[1])) + "\n").encode()
    if opts.get("upscale", True):
        try:
            import flgunup
            report["_upscale"] = flgunup.upscale_files(files, opts.get("esrgan"), progress)
        except Exception as e:
            progress(step="guns_upscale", skipped=str(e))
    return files, report


def convert(image, home, mohaa, progress=lambda **kv: None, opts=None):
    import flguns
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
    return [flguns.write_pak(files, out)]
