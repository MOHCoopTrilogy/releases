"""[flguns] fit a disc gun onto its base gun's bone block and write the converted files (runs on the PLAYER's PC).

Port of the private discfit.py (H:\\hzm_work\\discguns\\p2) with every private input made a parameter:
  * the base gun from the player's install (flgunvfs / flgungeo: TIK -> SKD + idle frame 0, +X muzzle, up = the row's
    U, TIKI-scaled units), its raw bone block (copied VERBATIM: same names, order, tags)
  * its compiled sight row from discguns_baserows.json (our engine table cg_adssights.h, shipped with the converter)
  * the disc gun's own F / R solved on this PC (flgunsight.solve_key)
  * the disc gun clips decoded on this PC ({stream: wav path}, flguns.decode_sounds)
Fit: disc +y -> base +X, disc +z -> base U, uniform scale = true scale (52.49 u / m) nudged <= 5 % toward the base
sight radius, a small pitch / yaw (<= MAXTILT) so the disc R->F is parallel to the base R->F, the disc R laid ON the
base R, and the axial slide chosen by the best overlap of the two side silhouettes (the hands' grips). Every disc
vertex is rigidly weighted to one base bone (gun / bolt / pump / magazine roles), offsets against the base bone
frames at idle frame 0, so every stock and mod clip drives it as it drives the base mesh. Output is byte-identical
to the private pipeline for the same disc and install (no scipy: the silhouette dilation is the same cross-shaped
binary dilation in numpy)."""
import io
import json
import math
import os
import re
import struct
import sys
import wave

import numpy as np

import flgungeo as gungeo
import flgunskd as skdlib
import flgunvfs as vfs

HERE = os.path.dirname(os.path.abspath(getattr(sys, "_MEIPASS", None) or __file__))
ROWS_JSON = os.path.join(HERE, "discguns_baserows.json")
TRUE = 16.0 / 0.3048          # MOHAA units per metre (16 u / ft)

# disc key -> base tik, stub name, display name, role overrides (disc bone prefix -> role)
GUNS = {
    "fl_th":    dict(base="thompsonsmg", stub="thompsonsmg_fl", name="Thompson (Frontline)"),
    "fl_bar":   dict(base="bar", stub="bar_fl", name="BAR (Frontline)"),
    "fl_mp40":  dict(base="mp40", stub="mp40_fl", name="MP40 (Frontline)"),
    "fl_stg44": dict(base="mp44", stub="mp44_fl", name="StG 44 (Frontline)"),
    # maxtilt 4: the disc sight line (virtual rear over the receiver -> barrel band) is 3.4 deg off the base bead line.
    # Turned only 1.5 deg, the per-frame sight solve pitched the whole view model the rest of the way and the pump
    # hand's fingers rose ~20 px above the sight line (the base shotgun's sit below its bead). Turned fully, the
    # sight picture matches the base gun's (2026-11-16 QA flag 3).
    "fl_sg":    dict(base="shotgun", stub="shotgun_fl", name="Shotgun (Frontline)",
                     roles={"bolt_03": "pump", "bolt_04": "pump"}, maxtilt=4.0),
    # batch 2 (2026-11-16): the FL pistols' slide is bone Bolt_02 (-> the base slide bone), the hammer rides the frame
    "fl_m1":    dict(base="m1_garand", stub="m1_garand_fl", name="M1 Garand (Frontline)"),
    "fl_colt":  dict(base="colt45", stub="colt45_fl", name="Colt 45 (Frontline)"),
    "fl_p38":   dict(base="p38", stub="p38_fl", name="Walther P38 (Frontline)"),
    "fl_silpis": dict(base="silencedpistol", stub="silencedpistol_fl", name="Hi-Standard Silenced (Frontline)"),
    # batch 3: the scoped rifles - true scale (no sight radius to match), a fitted glass disc on the disc ocular
    # (coop_scope_glass_<tint>, the base rifle's tint), the disc bolt on the base bolt bone
    "fl_spring": dict(base="springfield", stub="springfield_fl", name="Springfield '03 Sniper (Frontline)", glass="blue", slide=0.0,
                      bones={"bolt": "Object02"}),     # the base bolt handle rides Object02 (no BOLT_BONES name)
    # slide 0 on the scoped rifles: the ocular stays ON the base ocular (eye relief = the base row's). The silhouette slide
    # put the G43 ocular 2 u closer to the eye: the optic's exit-pupil vignette shrank the picture to a dot in the glass
    "fl_g43":   dict(base="g43", stub="g43_fl", name="G 43 (Frontline)", glass="blue", slide=0.0,
                     roles={"bolt_action": "bolt", "magazine": "mag"},
                     drop=[{"tex": "G43Sight", "hmax": -0.2}]),
    # batch 4: the launchers. Frontline modelled no separate rocket (no rocket bone, nothing outside the tube): the BASE
    # rocket surface is carried over so the reload still shows one going in (the base anims toggle it)
    # shift 14.5: the tube silhouette put the disc pistol grip 14.5 u behind the base grip (base parts under the tube at
    # x -4..4, the disc grip assembly at -18..-12; QA 2026-11-16 run 1116_2107) - the hand held bare tube. Grips matched,
    # the disc muzzle sits 14.5 u past tag_barrel (the flash / rocket spawn inside the tube mouth)
    "fl_bazooka": dict(base="bazooka", stub="bazooka_fl", name="Bazooka (Frontline)", keep_base=["bazookashell"],
                       fit="bore", k=1.0, slide=12.0, shift=14.5),
    "fl_panzer": dict(base="panzerschreck", stub="panzerschreck_fl", name="Panzerschreck (Frontline)", keep_base=["shell"],
                      fit="bore", k=1.0, slide=12.0),
    # batch 5: the grenades. No sight row; the disc grenade is centred on the base grenade (true scale) and ALL of it is the
    # surface the base anims hide after the throw (frag: `grenade` +nodraw -> every disc part takes the "mag" role; the
    # stick grenade's anims use `surface all`, the TIKI keyword for every surface, so its parts keep the plain names)
    "fl_markIIgrenade": dict(base="m2frag_grenade_sp_start", stub="m2frag_grenade_sp_start_fl",
                             name="Frag Grenade (Frontline)", roles={"weapon": "mag"}),
    "fl_stickgrenade": dict(base="steilhandgranate_start", stub="steilhandgranate_start_fl",
                            name="Stielhandgranate (Frontline)"),
}
# disc sound per base alias slot (FL: the GunBnk stream index of level 7_1, identified by level presence + envelope).
# Slots not listed keep the base sound. Server-side slots (pickup / ammo pickup / no-ammo) are always base.
SOUNDS = {
    "fl_th": {"thompson_snd_fire": 16},
    "fl_bar": {"bar_snd_fire": 19},
    "fl_sg": {"shotgun_snd_fire": 13, "shotgun_snd_rechamber": 34, "shotgun_snd_reload_single": 97},
    # the fire stream of every gun is DATA on the disc: halfword 36 (byte 72) of its 84-byte weapbul row = its 1-based
    # slot in the GunBnk's first ref run, which is the vgmstream stream index on 7_1 (it reproduces every presence match:
    # Colt 2, Hi-Standard 3, G43 9, Springfield 11, shotgun 13, Thompson 16, BAR 19, bazooka 22) - 2026-11-16, bug-11348
    "fl_mp40": {"mp40_snd_fire": 15},
    "fl_stg44": {"mp44_snd_fire": 18},
    # M1: 95 = the clip ping (a single strike, ringing 0.34 s; run 7 of the bank = the per-gun stage clips, M1 = 0 / 1)
    "fl_m1": {"m1_snd_fire": 7, "snd_ping": 95},
    "fl_colt": {"colt45_snd_fire": 2},
    "fl_p38": {"P38_snd_fire": 4},
    "fl_silpis": {"silencer_snd_fire": 3},
    "fl_spring": {"springfield_snd_fire": 11},
    "fl_g43": {"gewehr43_snd_fire": 9},          # the SP GewehrSniper row (the MP G43 row is 8)
    "fl_bazooka": {"bazooka_snd_fire": 22},
    "fl_panzer": {"panzerschreck_snd_fire": 23},
}
# base wav each slot is loudness-matched to, and its soundparms (copied from the effective ubersound alias)
BASE_SND = {
    "thompson_snd_fire": ("sound/weapons/fire/ThompsonFire1.wav", "1.82 0.01 0.95 0.1 480 8000 weapon"),
    "bar_snd_fire": ("sound/weapons/fire/BARFire2.wav", "1.82 0.1 0.8 0.1 480 8000 weapon"),
    "shotgun_snd_fire": ("sound/weapons/fire/ShotgunFire1.wav", "1.95 0.0 0.8 0.1 480 8000 weapon"),
    "shotgun_snd_rechamber": ("sound/weapons/foley/ShotgunRechamber1.wav", "1.5 0.0 0.95 0.1 160 1000 item"),
    "shotgun_snd_reload_single": ("sound/weapons/foley/ShotgunFill1.wav", "1.2 0.01 0.95 0.1 160 1000 item"),
    "mp40_snd_fire": ("sound/weapons/fire/MP40Fire2.wav", "1.32 0.01 0.95 0.1 480 8000 weapon"),
    "mp44_snd_fire": ("sound/weapons/fire/MP44Fire1.wav", "1.32 0.05 0.95 0.1 480 8000 weapon"),
    "m1_snd_fire": ("sound/weapons/fire/M1GarandFire2a.wav", "1.69 0.2 0.8 0.2 480 8000 weapon"),
    "snd_ping": ("sound/weapons/foley/M1_Ping.WAV", "1.5 0.3 0.95 0.1 160 1000 auto"),
    "colt45_snd_fire": ("sound/weapons/fire/Colt45Fire1.wav", "1.70 0.05 1.0 0.03 480 8000 weapon"),
    "P38_snd_fire": ("sound/weapons/fire/P38Fire2.wav", "1.42 0.1 0.8 0.1 480 8000 weapon"),
    "silencer_snd_fire": ("sound/weapons/fire/SilencedFire2.wav", "1.10 0.1 0.95 0.1 480 8000 weapon"),
    "springfield_snd_fire": ("sound/weapons/fire/SpringfieldFire2.WAV", "1.69 0.2 0.95 0.1 480 8000 weapon"),
    "gewehr43_snd_fire": ("sound/weapons/fire/gewehr43fire2.WAV", "1.52 0.2 1.0 0.05 480 8000 weapon"),
    "bazooka_snd_fire": ("sound/weapons/fire/BazookaFire2.wav", "1.95 0.0 0.92 0.15 500 9000 weapon"),
    "panzerschreck_snd_fire": ("sound/weapons/fire/PanzershrekFire2.wav", "1.95 0.0 0.92 0.15 500 9000 weapon"),
}
MAPS = 'always maps "m e t dm lib obj train c b"'


def _wav_read(b):
    w = wave.open(io.BytesIO(b))
    ch, sw, n = w.getnchannels(), w.getsampwidth(), w.getnframes()
    sr = w.getframerate()
    fr = w.readframes(n)
    if sw == 1:
        a = (np.frombuffer(fr, np.uint8).astype(np.float64) - 128) * 256
    else:
        a = np.frombuffer(fr, "<i2").astype(np.float64)
    a = a.reshape(-1, ch).mean(1)
    return a, sr


def _active_rms(a):
    """RMS over the loud part (frames within 20 dB of the peak frame): a long tail does not dilute the match"""
    n = 441
    fr = np.array([np.sqrt(np.mean(a[i:i + n] ** 2)) for i in range(0, len(a) - n, n)] or [0.0])
    keep = fr[fr >= fr.max() * 0.1]
    return float(np.sqrt(np.mean(keep ** 2))) if len(keep) else 0.0


def sound_files(key, stub, snd_paths):
    """-> ({pak path: wav bytes}, [aliascache lines]); disc clip loudness-matched to the base alias's wav. A clip the
    disc did not yield keeps the base sound (no alias line)."""
    files, lines = {}, []
    for alias, idx in SOUNDS.get(key, {}).items():
        if idx not in snd_paths:
            continue
        a, sr = _wav_read(open(snd_paths[idx], "rb").read())
        bpath, parms = BASE_SND[alias]
        bb = vfs.read(bpath)
        if bb is not None:
            ba, _ = _wav_read(bb)
            g = _active_rms(ba) / max(1e-6, _active_rms(a))
            a = a * g
        pk = np.abs(a).max()
        if pk > 32000:
            a = a * (32000 / pk)
        fi, fo = int(sr * 0.004), int(sr * 0.03)       # 4 ms fade-in / 30 ms fade-out: no click at the clip edges
        a[:fi] *= np.linspace(0, 1, fi)
        a[-fo:] *= np.linspace(1, 0, fo)
        out = io.BytesIO()
        w = wave.open(out, "wb")
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(np.clip(a, -32768, 32767).astype("<i2").tobytes())
        w.close()
        p = "sound/weapons/byo/%s/%s.wav" % (stub, alias)
        files[p] = out.getvalue()
        lines.append("\t\taliascache %s %s soundparms %s loaded %s" % (alias, p, parms, MAPS))
    return files, lines


# coop_slide before chamber: the mod's P38 / Hi-Standard slides ride coop_slide (the Hi-Standard's chamber bone carries no
# vertex at all). A candidate counts only when base vertices are weighted to it.
BOLT_BONES = ("coop_bolt", "coop_slide", "bolt", "box02", "chamber", "m1garandchamber")
# the magazine surface = the one the base anims toggle (`surface <name> +/-nodraw`, gen_disc_stubs.clip_surface - the
# shipped body wildcards exactly that name): M1 material8 (the en-bloc clip), G43 g43_Clip, bazooka bazookashell
CLIP_RX = re.compile(r"(?mi)^[^/\n]*\bsurface\s+(\S+)\s+[+-]\w+")
PUMP_BONES = ("object01",)


def role_of(bone, over):
    b = bone.lower()
    for k, v in (over or {}).items():
        if b.startswith(k):
            return v
    if b.startswith("magazine") or b.startswith("clip") or b.startswith("mag_release"):
        return "mag" if b.startswith(("magazine", "clip")) else "gun"
    if b.startswith("bolt"):
        return "bolt"
    return "gun"


_ROWS = {}


def base_row(tik, rows_json=None):
    p = rows_json or ROWS_JSON
    if p not in _ROWS:
        _ROWS[p] = json.load(open(p))
    r = _ROWS[p][tik]
    return dict(name=r["name"], F=np.array(r["F"]), R=np.array(r["R"]), delta=float(r["delta"]), U=np.array(r["U"]),
                relief=float(r["relief"]))


def _row_or_none(tik, rows_json=None):
    try:
        return base_row(tik, rows_json)
    except KeyError:                      # a grenade: no sight row in the engine table
        return None


def fit_center(fr, base, disc):
    """a grenade: disc +y -> base +X, disc +z -> base up (-Z, the weapon frame every row uses), true scale, the disc mesh's
    bounding-box centre on the base mesh's"""
    M = np.array(fr["M"])
    X = np.array([1.0, 0, 0])
    up = np.array([0, 0, -1.0])
    B0 = np.vstack([np.cross(X, up), X, up])
    T = B0 * TRUE
    Vd = np.vstack([p["V"] @ M.T for p in disc["parts"]]) @ T
    PB = gungeo.all_points(base["g"])
    t = (PB.min(0) + PB.max(0)) / 2 - (Vd.min(0) + Vd.max(0)) / 2
    info = dict(scale_k=1.0, slide=0.0, iou=None, tilt_deg=0.0, turned_deg=0.0, muzzle_disc=None, tag_barrel=None,
                size_base=np.round(np.ptp(PB, 0), 2).tolist(), size_disc=np.round(np.ptp(Vd, 0), 2).tolist())
    return T, t, M, None, None, info


def skd_bones(b):
    """the raw bone block of an SKD and its bone names (eaprops.skd_bones)"""
    nsurf, nbones, ofsb = struct.unpack_from("<3i", b, 72)
    o, names = ofsb, []
    for _ in range(nbones):
        names.append(b[o:o + 32].split(b"\0")[0].decode("latin-1"))
        o += struct.unpack_from("<i", b, o + 80)[0]
    return b[ofsb:o], names


def write_skd(name, bone_block, nbones, surfaces):
    """SKMD v6 (scale 1), eaprops.write_skd. surfaces: [(surface name, [(pos, nrm, uv, [(bone, weight, offset)])], tris)]"""
    blobs = []
    for sn, verts, tris in surfaces:
        vb = bytearray()
        for p, n, uv, ws in verts:
            vb += struct.pack("<3f2f2i", n[0], n[1], n[2], uv[0], uv[1], len(ws), 0)
            for bi, w, o in ws:
                vb += struct.pack("<if3f", bi, w, o[0], o[1], o[2])
        tb = b"".join(struct.pack("<3i", *t) for t in tris)
        nV, nT = len(verts), len(tris)
        ofsTri = 100
        ofsVerts = ofsTri + len(tb)
        ofsColl = ofsVerts + len(vb)
        ofsCollIdx = ofsColl + 4 * nV
        ofsEnd = ofsCollIdx + 4 * nV
        hdr = struct.pack("<4s64s8i", b"SKL ", sn.encode().ljust(64, b"\0"), nT, nV, 0, ofsTri, ofsVerts, ofsColl,
                          ofsEnd, ofsCollIdx)
        blobs.append(hdr + tb + bytes(vb) + struct.pack("<%di" % nV, *range(nV)) + bytes(4 * nV))
    body = b"".join(blobs)
    H = 152
    total = H + len(bone_block) + len(body)
    head = struct.pack("<4si64s5i10i4if", b"SKMD", 6, name.encode()[:63].ljust(64, b"\0"), len(blobs), nbones,
                       H, H + len(bone_block), total, *([0] * 10), 0, total, 0, total, 1.0)
    return head + bone_block + body


class MissingBase(Exception):
    """the player's install lacks the base gun (or the shipped body): that gun is skipped, never a failed conversion"""


def base_gun(tik, rows_json=None):
    path = "models/weapons/%s.tik" % tik
    if vfs.read(path) is None:
        raise MissingBase(path)
    g = gungeo.load_gun(path)
    t = g["tik"]
    raw = vfs.read(g["skd"])
    skd = skdlib.read_skd(raw)
    skc = skdlib.read_skc(vfs.read(t["skc"])) if t.get("skc") else None
    mats, world = gungeo.bone_world(skd, skc, 0)
    block, names = skd_bones(raw)
    assert names == [b.name for b in skd.bones], (names, [b.name for b in skd.bones])
    cnt = {}
    for s, ss in zip(g["surfs"], skd.surfaces):
        for v in ss.verts:
            for bi, w, o in v[2]:
                cnt.setdefault(s["name"], {}).setdefault(bi, 0)
                cnt[s["name"]][bi] += 1
    eff = vfs.read(path).decode("latin-1")
    for _ in range(4):                  # the grenade tiks are include-only: inline them (gen_disc_stubs.inline_includes)
        inc = re.search(r"(?mi)^[ \t]*\$include[ \t]+(\S+)[ \t\r]*$", eff)
        if not inc:
            break
        sub = vfs.read(inc.group(1))
        eff = eff[:inc.start()] + (sub.decode("latin-1") if sub else "") + eff[inc.end():]
    sn = [s["name"] for s in g["surfs"]]
    clip = [s for s in sorted(set(CLIP_RX.findall(eff))) if s in sn] or [s for s in sn if "clip" in s.lower()]
    gunb = {}
    for sn, c in cnt.items():
        if sn not in clip:
            for bi, n in c.items():
                gunb[bi] = gunb.get(bi, 0) + n
    # the frag grenade's only surface IS the hidden-after-throw one: its bone is the gun bone too
    gun_bone = max(gunb, key=gunb.get) if gunb else max(cnt[clip[0]], key=cnt[clip[0]].get)
    lname = [n.lower() for n in names]
    used = {bi for c in cnt.values() for bi in c}
    bolt = next((lname.index(b) for b in BOLT_BONES if b in lname and lname.index(b) in used), None)
    pump = next((lname.index(b) for b in PUMP_BONES if b in lname), None)
    mag_bone = max(cnt[clip[0]], key=cnt[clip[0]].get) if clip else gun_bone
    return dict(tik=path, g=g, skd=skd, raw=raw, block=block, names=names, mats=mats, scale=t["scale"],
                clip=clip[0] if clip else None, roles={"gun": gun_bone, "bolt": bolt if bolt is not None else gun_bone,
                                                        "pump": pump if pump is not None else gun_bone,
                                                        "mag": mag_bone},
                row=_row_or_none(path, rows_json), eff=eff, skdpath=g["skd"], path=t["path"])


def _rotm(a, b):
    """rotation taking unit a onto unit b (row form: v @ R)"""
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = float(a @ b)
    if np.linalg.norm(v) < 1e-9:
        return np.eye(3)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    M = np.eye(3) + K + K @ K * (1 / (1 + c))
    return M.T


MAXTILT = 1.5


def _slerp_dir(a, b, f):
    w = math.acos(min(1.0, float(a @ b)))
    return (math.sin((1 - f) * w) * a + math.sin(f * w) * b) / math.sin(w)


def silhouette(P, x0, x1, z0, z1, n=240, m=60):
    img = np.zeros((m, n), bool)
    xi = np.clip(((P[:, 0] - x0) / (x1 - x0) * n).astype(int), 0, n - 1)
    zi = np.clip(((P[:, 2] - z0) / (z1 - z0) * m).astype(int), 0, m - 1)
    img[zi, xi] = True
    return img


def _dilate(m, iterations=2):
    """scipy.ndimage.binary_dilation(m, iterations=N) with its default cross structure and a zero border"""
    for _ in range(iterations):
        o = m.copy()
        o[1:] |= m[:-1]
        o[:-1] |= m[1:]
        o[:, 1:] |= m[:, :-1]
        o[:, :-1] |= m[:, 1:]
        m = o
    return m


def fit(fr, base, disc, maxtilt=None, kfix=None, mode=None, slide=8.0, shift=None):
    maxtilt = MAXTILT if maxtilt is None else maxtilt
    M = np.array(fr["M"])
    Fd, Rd = np.array(fr["F"]), np.array(fr["R"])
    row = base["row"]
    Fb, Rb, U = row["F"], row["R"], row["U"] / np.linalg.norm(row["U"])
    X = np.array([1.0, 0, 0])
    up = U - (U @ X) * X
    up /= np.linalg.norm(up)
    a = np.cross(X, up)
    B0 = np.vstack([a, X, up])     # row form: v_base = v_disc @ B0
    sr_b = np.linalg.norm(Fb - Rb)
    sr_d = np.linalg.norm(Fd - Rd) * TRUE
    # a SCOPE row's F is synthetic (R + 12 u on the base, R + 0.3 m on the disc): no sight radius to match - true scale
    k = float(kfix) if kfix is not None else (1.0 if fr.get("kind") == "scope" else float(np.clip(sr_b / sr_d, 0.95, 1.05)))
    s = TRUE * k
    Vd = np.vstack([p["V"] @ M.T for p in disc["parts"]])
    dD = (Fd - Rd) @ B0
    dB = Fb - Rb
    # a disc sight line more than MAXTILT off the base one (a VIRTUAL rear over a receiver, e.g. the shotgun): turn the
    # gun only MAXTILT toward it - the hands keep the grips - and let the per-frame sight solve take the rest
    ang = math.acos(min(1.0, dD @ dB / np.linalg.norm(dD) / np.linalg.norm(dB)))
    if ang > math.radians(maxtilt):
        dBp = _slerp_dir(dD / np.linalg.norm(dD), dB / np.linalg.norm(dB), math.radians(maxtilt) / ang)
        Rs = _rotm(dD, dBp)
    else:
        Rs = _rotm(dD, dB)
    T = B0 @ Rs * s                 # v_base = v_canon @ T + t
    Rf = Rd @ T
    Ff = Fd @ T
    t0 = Rb - Rf
    if mode == "bore":
        # a launcher's sight line is VIRTUAL (no usable hardware on the disc): the tube is what the hands hold, so the
        # disc bore goes ON the base bore (muzzle point on tag_barrel, bore-parallel, no turn) and the row is measured
        # from the fitted disc - the per-frame sight solve centres it like any other row (twin = the base gun)
        T = B0 * s
        Rf = Rd @ T
        Ff = Fd @ T
        t0 = np.array(base["g"]["tags"]["tag_barrel"][0], float) - np.array(fr["O"]) @ T
        dB = np.array([1.0, 0.0, 0.0])
        ang = 0.0
    P0 = Vd @ T + t0
    PB = gungeo.all_points(base["g"])
    x0 = min(PB[:, 0].min(), P0[:, 0].min()) - 25
    x1 = max(PB[:, 0].max(), P0[:, 0].max()) + 25
    z0 = min(PB[:, 2].min(), P0[:, 2].min()) - 2
    z1 = max(PB[:, 2].max(), P0[:, 2].max()) + 2
    SB = _dilate(silhouette(PB, x0, x1, z0, z1))
    best = None
    dirn = dB / np.linalg.norm(dB)
    for dx in np.arange(-slide, slide + 0.01, 0.25):
        SD = _dilate(silhouette(P0 + dirn * dx, x0, x1, z0, z1))
        iou = (SB & SD).sum() / max(1, (SB | SD).sum())
        if best is None or iou > best[0]:
            best = (iou, dx)
    if shift is not None:            # a fixed axial shift (GUNS "shift"): the grips, not the silhouettes, decide
        best = (best[0], float(shift))
    t = t0 + dirn * best[1]
    info = dict(scale_k=round(k, 4), sr_base=round(sr_b, 2), sr_disc_true=round(sr_d, 2), slide=best[1],
                iou=round(best[0], 3), len_base=round(float(np.ptp(PB[:, 0])), 2),
                len_disc=round(float(np.ptp(P0[:, 0])), 2),
                tilt_deg=round(math.degrees(ang), 3), turned_deg=round(min(math.degrees(ang), maxtilt), 3),
                muzzle_disc=np.round(np.array(fr["O"]) @ T + t, 2).tolist(),
                tag_barrel=np.round(base["g"]["tags"]["tag_barrel"][0], 2).tolist())
    return T, t, M, Ff + t, Rf + t, info


def vnormals(V, Tr):
    N = np.zeros_like(V)
    f = np.cross(V[Tr[:, 1]] - V[Tr[:, 0]], V[Tr[:, 2]] - V[Tr[:, 0]])
    for i in range(3):
        np.add.at(N, Tr[:, i], f)
    n = np.linalg.norm(N, axis=1, keepdims=True)
    n[n == 0] = 1
    return N / n


MAXV, MAXT = 999, 1999
FLIP_WINDING = False


def build_surfaces(base, disc, T, t, M, over, prefix):
    """-> [(surface name, verts, tris, texname)] ; verts = (pos, nrm, uv, [(bone, 1.0, offset)])"""
    sc = base["scale"]
    mats = base["mats"]
    out, nclip = [], 0
    clipname = base["clip"] or "Clip"
    for p in disc["parts"]:
        V = (p["V"] @ M.T) @ T + t           # base frame, TIKI-scaled
        roles = np.array([role_of(b, over) for b in p["bone"]])
        for role in ("gun", "bolt", "pump", "mag"):
            sel = roles == role
            tri = p["T"][sel[p["T"]].all(1)]
            if not len(tri):
                continue
            bi = base["roles"][role]
            Mb = mats[bi]
            chunks, cur, cmap = [], [], {}
            for tr in tri:
                new = sum(1 for x in tr if x not in cmap)
                if cur and (len(cmap) + new > MAXV or len(cur) + 1 > MAXT):
                    chunks.append((cur, cmap))
                    cur, cmap = [], {}
                for x in tr:
                    if x not in cmap:
                        cmap[x] = len(cmap)
                cur.append(tr)
            if cur:
                chunks.append((cur, cmap))
            for ct, cmap in chunks:
                order = sorted(cmap, key=cmap.get)
                Vs = V[order]
                lt = np.array([[cmap[x] for x in tr] for tr in ct])
                lt = lt[:, ::-1] if FLIP_WINDING else lt
                N = vnormals(Vs, lt)
                verts = []
                for j in range(len(order)):
                    lp = Vs[j] / sc
                    off = (lp - Mb[3]) @ Mb[:3].T
                    n = N[j] @ Mb[:3].T
                    uv = p["UV"][order[j]]
                    verts.append((tuple(Vs[j]), tuple(n), (float(uv[0]), float(uv[1])), [(bi, 1.0, tuple(off))]))
                if role == "mag":
                    nm = clipname if nclip == 0 else "%s_%d" % (clipname, nclip + 1)
                    nclip += 1
                else:
                    nm = "%s%d" % (prefix, len(out))
                out.append((nm, verts, [tuple(map(int, x)) for x in lt], p["tex"]))
    return out


def drop_parts(disc, fr, rules):
    """mesh defects the disc ships (GUNS "drop"): a part whose texture contains rule["tex"] and that lies wholly below
    rule["hmax"] (height above the muzzle bore, in gun lengths, canonical frame) is left out - the FL G43's misassembled
    G43Sight bar floats 0.24 L under the gun. Returns (disc copy, [dropped part summaries])."""
    if not rules:
        return disc, []
    M, O, L = np.array(fr["M"]), np.array(fr["O"]), float(fr["L"])
    keep, gone = [], []
    for p in disc["parts"]:
        h = ((np.round(np.asarray(p["V"], float), 5) @ M.T)[:, 2] - O[2]) / L
        if any(r["tex"].lower() in p["tex"].lower() and h.max() < r["hmax"] for r in rules):
            gone.append((p["tex"], len(p["V"]), round(float(h.max()), 3)))
        else:
            keep.append(p)
    return dict(disc, parts=keep), gone


def base_surface(base, name):
    """a surface of the BASE mesh copied verbatim into the converted skd (GUNS "keep_base"): the bone block is the base's,
    so its weights / offsets stay valid. For a part the disc never modelled (the FL launchers have no separate rocket:
    the base rocket `bazookashell` / `shell` still rides in for the reload, as the base anims show it). -> surface tuple
    with ("base", <the base tik's shader for it>) as the texture."""
    import re as _re
    for ss in base["skd"].surfaces:
        if ss.name.lower() == name.lower():
            m = _re.search(r"(?mi)^\s*surface\s+%s\s+shader\s+(\S+)" % _re.escape(ss.name), base["eff"])
            tri = np.frombuffer(bytes(ss.tri_bytes), dtype="<i4").reshape(-1, 3)
            verts = [((0.0, 0.0, 0.0), tuple(n), tuple(tc), [(bi, w, tuple(o)) for bi, w, o in wl]) for n, tc, wl, ml in ss.verts]
            return (ss.name, verts, [tuple(map(int, x)) for x in tri], ("base", m.group(1) if m else "default"))
    raise MissingBase("%s: no surface %s" % (base["tik"], name))


def lens_surface(base, Rf, u, radius, bone):
    """a double-sided 24-gon glass disc on the fitted ocular, facing the eye (scope_mesh.py recipe: the renderer's PiP
    pass and coverage mask key on a view-model surface whose shader names glass / lens)"""
    sc, Mb = base["scale"], base["mats"][bone]
    e1 = np.cross(u, [0, 0, 1.0])
    e1 = e1 / np.linalg.norm(e1)
    e2 = np.cross(u, e1)
    n = 24
    pts = [Rf] + [Rf + radius * (math.cos(2 * math.pi * i / n) * e1 + math.sin(2 * math.pi * i / n) * e2) for i in range(n)]
    tri = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
    tri = tri + [(a, c, b) for (a, b, c) in tri]
    nb = -u @ Mb[:3].T
    verts = [(tuple(q), tuple(nb), (0.5, 0.5), [(bone, 1.0, tuple((q / sc - Mb[3]) @ Mb[:3].T))]) for q in pts]
    return ("lens", verts, tri, None)


def write_gun(key, disc, fr, snd_paths, rows_json=None):
    """-> ({pak path: bytes, "_row": sight row bytes}, info). Raises MissingBase when the install lacks the base gun
    or the shipped body the converted tik includes (an old mod build): the caller skips that gun."""
    from PIL import Image
    cfg = GUNS[key]
    if vfs.read("models/weapons/byo/body/%s.txt" % cfg["base"]) is None:
        raise MissingBase("models/weapons/byo/body/%s.txt" % cfg["base"])
    base = base_gun(cfg["base"], rows_json)
    for role, bn in (cfg.get("bones") or {}).items():     # a base bone the generic role names do not find
        base["roles"][role] = base["names"].index(bn)
    disc, dropped = drop_parts(disc, fr, cfg.get("drop"))
    if fr["kind"] == "none":
        T, t, M, Ff, Rf, info = fit_center(fr, base, disc)
    else:
        T, t, M, Ff, Rf, info = fit(fr, base, disc, cfg.get("maxtilt"), cfg.get("k"), cfg.get("fit"), cfg.get("slide", 8.0),
                                    cfg.get("shift"))
    if dropped:
        info["dropped"] = dropped
    if fr["kind"] == "scope":      # the row keeps the base convention F = R + 12 u along the (disc) scope axis
        Ff = Rf + (Ff - Rf) / np.linalg.norm(Ff - Rf) * 12.0
    stub = cfg["stub"]
    mdir = "models/weapons/byo/%s" % stub
    surfs = build_surfaces(base, disc, T, t, M, cfg.get("roles"), "disc")
    for nm in cfg.get("keep_base", []):
        surfs.append(base_surface(base, nm))
    if fr["kind"] == "scope" and fr.get("lens_r"):
        u = (Ff - Rf) / np.linalg.norm(Ff - Rf)
        # 0.08 u toward the eye: the disc oculars carry a PAINTED glass cap in the rear-face plane - the glass disc sits
        # just in front of it (no z-fight), and the PiP picture covers the painting
        surfs.append(lens_surface(base, Rf - u * 0.08, u, fr["lens_r"] * TRUE * info["scale_k"] * 0.9, base["roles"]["gun"]))
        info["lens_r"] = round(fr["lens_r"] * TRUE * info["scale_k"] * 0.9, 3)
    files = {}
    files["%s/%s.skd" % (mdir, stub)] = write_skd("byo_" + stub, base["block"], len(base["names"]),
                                                  [(s[0], s[1], s[2]) for s in surfs])
    # textures + shaders (the disc pixels as they are; flgunup replaces the tgas with the upscale)
    tdir = "textures/byo_guns/%s" % stub
    shader_txt, sl, done = [], [], set()
    punch = fr.get("punch") or {}
    for s in surfs:
        tn = s[3]
        if isinstance(tn, tuple):     # a base surface carried over: the base gun's own shader
            sl.append("\tsurface %s shader %s" % (s[0], tn[1]))
            continue
        if tn is None:            # the fitted glass disc: the mod's shipped glass shader (scopes_1025 glass_tiks TINT)
            sl.append("\tsurface %s shader coop_scope_glass_%s" % (s[0], cfg.get("glass", "blue")))
            continue
        sh = "byo_%s_%s" % (stub, tn.lower())
        if tn not in done:
            w, h, rgba = disc["tex"][tn]
            im = Image.frombytes("RGBA", (w, h), rgba)
            if tn in punch:          # a peep aperture the disc only painted (discguns_sights.json "punch")
                A = np.array(im)
                A[..., 3][punch[tn]] = 0
                im = Image.fromarray(A)
                rgba = im.tobytes()
            cut = min(rgba[3::4]) < 250
            tga = "%s/%s.tga" % (tdir, tn.lower())
            files[tga] = _tga(im)
            shader_txt.append("%s\n{\n\tcull none\n\t{\n\t\tmap %s\n%s\t\trgbGen lightingSpherical\n\t}\n}\n" % (
                sh, tga, "\t\talphaFunc GE128\n\t\tdepthWrite\n" if cut else ""))
            done.add(tn)
        sl.append("\tsurface %s shader %s" % (s[0], sh))
    files["scripts/byo_guns_%s.shader" % stub] = "\n".join(shader_txt).encode()
    tik = ["TIKI", "// HZM coop discguns: CONVERTED on this PC from the player's own disc (never shipped). Overrides the",
           "// shipped stub at the same path; the body below is the shipped one (same anims, tags, stats).",
           "setup", "{", "\tscale %s" % _fmt(base["scale"]), "\tpath %s" % mdir, "\tskelmodel %s.skd" % stub] + sl + \
          ["}", ""]
    sf, al = sound_files(key, stub, snd_paths)
    files.update(sf)
    if al:
        tik += ["init", "{", "\tclient", "\t{", "\t\t// the disc's own clips, tiki-local: only this converted gun hears them"] \
            + al + ["\t}", "}", ""]
    tik += ["$include models/weapons/byo/body/%s.txt" % cfg["base"], ""]
    files["models/weapons/byo/%s.tik" % stub] = "\n".join(tik).encode()
    row = base["row"]
    if fr["kind"] == "none":
        info.update(surfaces=[(s[0], len(s[1]), len(s[2]), s[3]) for s in surfs],
                    sounds={a: i for a, i in SOUNDS.get(key, {}).items() if i in snd_paths})
        return files, info
    files["_row"] = ('sight models/weapons/byo/%s.tik "%s" %.4f %.4f %.4f %.4f %.4f %.4f %.6f %.3f %.3f %.3f %.3f %s "%s"'
                     % (stub, cfg["name"], *Ff, *Rf, row["delta"], *row["U"], row["relief"], fr["kind"],
                        row["name"])).encode()
    info.update(F=np.round(Ff, 3).tolist(), R=np.round(Rf, 3).tolist(), surfaces=[(s[0], len(s[1]), len(s[2]), s[3])
                                                                                    for s in surfs],
                sounds={a: i for a, i in SOUNDS.get(key, {}).items() if i in snd_paths})
    return files, info


def _fmt(x):
    return ("%.4f" % x).rstrip("0").rstrip(".")


def _tga(im):
    im = im.convert("RGBA")
    w, h = im.size
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 8)
    px = np.asarray(im)[::-1, :, [2, 1, 0, 3]].tobytes()
    return hdr + px
