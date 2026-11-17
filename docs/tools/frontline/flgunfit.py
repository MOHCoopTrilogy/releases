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
}
# disc sound per base alias slot (FL: the GunBnk stream index of level 7_1, identified by level presence + envelope).
# Slots not listed keep the base sound. Server-side slots (pickup / ammo pickup / no-ammo) are always base.
SOUNDS = {
    "fl_th": {"thompson_snd_fire": 16},
    "fl_bar": {"bar_snd_fire": 19},
    "fl_sg": {"shotgun_snd_fire": 13, "shotgun_snd_rechamber": 34, "shotgun_snd_reload_single": 97},
}
# base wav each slot is loudness-matched to, and its soundparms (copied from the effective ubersound alias)
BASE_SND = {
    "thompson_snd_fire": ("sound/weapons/fire/ThompsonFire1.wav", "1.82 0.01 0.95 0.1 480 8000 weapon"),
    "bar_snd_fire": ("sound/weapons/fire/BARFire2.wav", "1.82 0.1 0.8 0.1 480 8000 weapon"),
    "shotgun_snd_fire": ("sound/weapons/fire/ShotgunFire1.wav", "1.95 0.0 0.8 0.1 480 8000 weapon"),
    "shotgun_snd_rechamber": ("sound/weapons/foley/ShotgunRechamber1.wav", "1.5 0.0 0.95 0.1 160 1000 item"),
    "shotgun_snd_reload_single": ("sound/weapons/foley/ShotgunFill1.wav", "1.2 0.01 0.95 0.1 160 1000 item"),
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


BOLT_BONES = ("coop_bolt", "bolt", "box02", "chamber", "m1garandchamber")
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
    clip = [s["name"] for s in g["surfs"] if "clip" in s["name"].lower()]
    gunb = {}
    for sn, c in cnt.items():
        if sn not in clip:
            for bi, n in c.items():
                gunb[bi] = gunb.get(bi, 0) + n
    gun_bone = max(gunb, key=gunb.get)
    lname = [n.lower() for n in names]
    bolt = next((lname.index(b) for b in BOLT_BONES if b in lname), None)
    pump = next((lname.index(b) for b in PUMP_BONES if b in lname), None)
    mag_bone = max(cnt[clip[0]], key=cnt[clip[0]].get) if clip else gun_bone
    eff = vfs.read(path).decode("latin-1")
    return dict(tik=path, g=g, skd=skd, raw=raw, block=block, names=names, mats=mats, scale=t["scale"],
                clip=clip[0] if clip else None, roles={"gun": gun_bone, "bolt": bolt if bolt is not None else gun_bone,
                                                        "pump": pump if pump is not None else gun_bone,
                                                        "mag": mag_bone},
                row=base_row(path, rows_json), eff=eff, skdpath=g["skd"], path=t["path"])


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


def fit(fr, base, disc, maxtilt=None):
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
    k = float(np.clip(sr_b / sr_d, 0.95, 1.05))
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
    P0 = Vd @ T + t0
    PB = gungeo.all_points(base["g"])
    x0 = min(PB[:, 0].min(), P0[:, 0].min()) - 25
    x1 = max(PB[:, 0].max(), P0[:, 0].max()) + 25
    z0 = min(PB[:, 2].min(), P0[:, 2].min()) - 2
    z1 = max(PB[:, 2].max(), P0[:, 2].max()) + 2
    SB = _dilate(silhouette(PB, x0, x1, z0, z1))
    best = None
    dirn = dB / np.linalg.norm(dB)
    for dx in np.arange(-8.0, 8.01, 0.25):
        SD = _dilate(silhouette(P0 + dirn * dx, x0, x1, z0, z1))
        iou = (SB & SD).sum() / max(1, (SB | SD).sum())
        if best is None or iou > best[0]:
            best = (iou, dx)
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


def write_gun(key, disc, fr, snd_paths, rows_json=None):
    """-> ({pak path: bytes, "_row": sight row bytes}, info). Raises MissingBase when the install lacks the base gun
    or the shipped body the converted tik includes (an old mod build): the caller skips that gun."""
    from PIL import Image
    cfg = GUNS[key]
    if vfs.read("models/weapons/byo/body/%s.txt" % cfg["base"]) is None:
        raise MissingBase("models/weapons/byo/body/%s.txt" % cfg["base"])
    base = base_gun(cfg["base"], rows_json)
    T, t, M, Ff, Rf, info = fit(fr, base, disc, cfg.get("maxtilt"))
    stub = cfg["stub"]
    mdir = "models/weapons/byo/%s" % stub
    surfs = build_surfaces(base, disc, T, t, M, cfg.get("roles"), "disc")
    files = {}
    files["%s/%s.skd" % (mdir, stub)] = write_skd("byo_" + stub, base["block"], len(base["names"]),
                                                  [(s[0], s[1], s[2]) for s in surfs])
    # textures + shaders (the disc pixels as they are; flgunup replaces the tgas with the upscale)
    tdir = "textures/byo_guns/%s" % stub
    shader_txt, sl, done = [], [], set()
    punch = fr.get("punch") or {}
    for s in surfs:
        tn = s[3]
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
