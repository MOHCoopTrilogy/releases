#!/usr/bin/env python3
"""Frontline PROP models (Sealed Orders 1_1): the original's own Panzer IV - intact (live tank + its parked copy) and
destroyed - on the STOCK MOHAA entities, the European Assault recipe (docs/tools/ea/eaprops.py, user-approved Panzer
2026-11-15). Our own code, stdlib only; runs on the PLAYER's PC inside the converter, and its output (mesh, textures)
goes only into the player's own converted pak. Nothing disc-derived is shipped. Each prop is used by the mission script
only once the user approved it: fl_levels.json "props" per level (off or absent = nothing built, the pak unchanged).

Reverse-engineered 2026-11-15 on the user's own Xbox USA disc (1_1, level.viv):
  - the tank is a set of object meshes (.msh, flcore.Level.mesh): Tank_PIV_Body, _Turret01, _Cannon01, _Mg01,
    _Tread01 / _Tread02 (.mpk: the track's animation frames, #0 drawn), and the _Destroyed set;
  - each .msh carries its ATTACH POINTS: header word 10 = table offset, word 11 = count, 0x50 bytes each (a row-major
    4x4 with the translation at +0x30, then 16 bytes). Body: 0 hull MG (0.561 1.408 1.269), 1 right track
    (0.7785 -2.0727 0.5025), 2 left track (-0.7823 -2.0727 0.5025), 3 turret ring (0 -0.0005 1.508); Turret: 0 the gun
    (0 0.74 0.293); Cannon: 0 the muzzle (0 1.023 0); Mg01: 0 its muzzle (0 0.29 0). Metres, z up, forward +y.
Fitting (as eaprops): the soldiers' scale (52 u/m, flchar's), MOHAA axes; the hull moved so the ring lands on the
stock turret0 tag; turret + gun in the cannon model with our own SKAN (pitch at the gun's attach point, tag_barrel at
the muzzle, a short recoil on fire); the parked copy and the wreck as one model each on their stock skeletons.
Stock bone frames measured in the engine 2026-11-16 (gettagposition / gettagangles, world units at the tik scale).
"""
import math
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.join(HERE, "..", "ea"), os.path.join(HERE, "ea")):     # source tree / frozen _internal/ea
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.append(_p)
eaprops = None   # imported in build(), after the key check: a key-off run never needs the EA modules

SCALE = 52.0      # the converted soldiers' scale (u/m)

STOCK = {
    "vehicles/panzer_tank_europe.tik": {"scale": 0.52, "bones": {
        "panzer_IV": ((-12.30, 6.39, 6.16), (0.0, 90.0, 90.0)),
        "turret0": ((-0.61, 1.44, 102.02), (0.0, 0.0, 0.0))}},
    "vehicles/panzer_cannon_europe.tik": {"scale": 0.52, "bones": {
        "connect": ((-0.61, 1.44, 1.37), (0.0, 90.0, 0.0)),
        "pitch": ((45.87, 2.96, 17.70), (0.0, 90.0, 0.0)),
        "recoil": ((104.63, 1.54, 17.70), (0.0, 90.0, 0.0)),
        "tag_barrel": ((195.07, 1.54, 17.70), (0.0, 0.0, 0.0)),
        "Object03": ((53.72, -14.56, 18.55), (0.0, 90.0, 90.0)),
        "Object02": ((53.72, -14.56, 18.55), (0.0, 90.0, 90.0)),
        "Box01": ((1.52, 3.85, -1.02), (0.0, 90.0, 0.0))}},
    "vehicles/Panzer_destroyed_lowpoly_base.tik": {"scale": 0.52, "bones": {
        "origin": ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
        "panzer": ((53.09, -6.66, -0.17), (0.0, 90.0, 0.0)),
        "turret0": ((4.61, 0.0, 98.88), (0.0, 0.0, 0.0))}},
    "static/vehicle_panzer_iv_europe.tik": {"scale": 0.52, "bones": {
        "Box01": ((0.0, 0.0, 0.0), (0.0, 90.0, 0.0))}},
}
CANNON_PARENTS = {"connect": None, "pitch": "connect", "recoil": "pitch", "tag_barrel": "recoil", "Object03": "connect",
                  "Object02": "connect", "Box01": None}
INTACT = {"body": "Tank_PIV_Body.msh", "turret": "Tank_PIV_Turret01.msh", "cannon": "Tank_PIV_Cannon01.msh",
          "mg": "Tank_PIV_Mg01.msh", "tread_r": "Tank_PIV_Tread01.mpk#0", "tread_l": "Tank_PIV_Tread02.mpk#0"}
WRECK = {"body": "Tank_PIV_Body_Destroyed.msh", "turret": "Tank_PIV_Turret01_Destroyed.msh",
         "cannon": "Tank_PIV_Cannon01_Destroyed.msh", "tread_r": "Tank_PIV_Tread01_Destroyed.msh",
         "tread_l": "Tank_PIV_Tread02_Destroyed.msh"}
RECOIL = (0.0, -9.0, -6.0, -3.5, -1.5, 0.0)      # the gun's travel back along its axis on a shot (u), 0.05 s frames


def attach_points(buf):
    """the .msh attach table: [(x, y, z)] translations (metres)"""
    if not buf or len(buf) < 48:
        return []
    h = struct.unpack_from("<12I", buf, 0)
    out = []
    for i in range(h[11]):
        o = h[10] + 0x50 * i
        if o + 0x40 > len(buf):
            break
        out.append(struct.unpack_from("<3f", buf, o + 0x30))
    return out


def _file_of(L, name):
    return L.files.get(name.split("#")[0])


def to_map(p, off=(0.0, 0.0, 0.0)):
    return ((p[1] + off[1]) * SCALE, -(p[0] + off[0]) * SCALE, (p[2] + off[2]) * SCALE)


def to_map_w(p, off=(0.0, 0.0, 0.0)):
    """the hand-held / small objects (mg42gun, MG42GunTripod, the pickups, the phone) face -y on the disc (the tank +y):
    turned 180 degrees about z, then to_map"""
    return to_map((-(p[0] + off[0]), -(p[1] + off[1]), p[2] + off[2]))


def _alpha_mode(rgba):
    """False = opaque, True = cut-out (alpha ~0/255), "blend" = soft alpha (the pickups' drop-shadow cards)"""
    a = rgba[3::4]
    if min(a) >= 250:
        return False
    soft = sum(1 for v in a if 16 <= v <= 239)
    return "blend" if soft > len(a) * 0.15 else True


def _mesh(L, name, off, texkey, files, tdir, xf=None, small=False):
    """a disc object mesh as eaprops 'meshes' entries [(pos, uv, tris, shape)] (pos already in MOHAA map space, units),
    textures written as TGA under tdir (keyed by the decoded image's hash: the same image in two meshes is one file).
    small: the small-prop rules - untextured sub-meshes dropped (they would draw as the engine's notexture grid),
    soft-alpha cards marked "blend" """
    import hashlib
    out = []
    for d in L.mesh(name):
        if not d["tris"]:
            continue
        shape = None
        t = L.texture(d["tex"]) if d["tex"] else None
        if t and t.get("rgba") is not None:
            shape = hashlib.md5(bytes(t["rgba"])).hexdigest()[:8]
            tp = "%s/%s.tga" % (tdir, shape)
            if tp not in files:
                files[tp] = eaprops._tga(t)
            rgba = bytes(t["rgba"])
            texkey[shape] = (tp, _alpha_mode(rgba) if small else min(rgba[3::4]) < 250)
        elif small:
            continue
        pos = [(xf or to_map)(v, off) for v in d["verts"]]
        out.append((pos, d["uvs"], list(d["tris"]), shape))
    return out


def enabled(level, prop):
    """fl_levels.json "props": {"<prop>": true} - flipped by the SO fixer only once the user approved the model. Off or
    absent: nothing is written, and the converted pak is byte-identical to a build without this module"""
    try:
        import flpack
        return bool((flpack.spec(level).get("props") or {}).get(prop))
    except Exception:
        return False


PROPS = ("panzer", "mg42", "health", "phone")     # the fl_levels.json "props" keys, one per approval


def build(L, level, mohaa_base, files, log=print):
    """write the props' models into the converted pak; returns data-script lines (level.fl_prop_tik / fl_prop_own)"""
    lines = []
    want = [p for p in PROPS if enabled(level, p)]
    if not mohaa_base or not want:
        return lines
    global eaprops
    import eaprops as _ep      # write_skd / write_skc / local_channels / axes / surfaces_for / effective_file
    eaprops = _ep
    for p in want:
        try:
            if p == "panzer":
                _panzer(L, level, mohaa_base, files, lines, log)
            elif p == "mg42":
                _mg42(L, level, mohaa_base, files, lines, log)
            else:
                for kind, spec in SMALL.items():
                    if spec["prop"] == p:
                        _small(L, level, mohaa_base, files, lines, log, kind, spec)
        except Exception as e:      # never fail the conversion: that prop keeps the stock model
            log("flprops: %s skipped (%s)" % (p, e))
    return lines


def _shader_text(pre, texkey):
    """the stock tank's / items' lighting (lightingSpherical); cut-outs alpha-tested, soft cards blended"""
    sh = []
    for key, (tp, mode) in sorted(texkey.items()):
        if mode == "blend":
            st = "\t\tblendFunc blend\n"
            head = "\tcull none\n\tpolygonOffset\n"
        else:
            st = "\t\talphaFunc GE128\n" if mode else ""
            head = "\tcull none\n"
        sh.append("%s_%s\n{\n%s\t{\n\t\tmap %s\n%s\t\trgbGen lightingSpherical\n\t}\n}\n" % (pre, key, head, tp, st))
    return "\n".join(sh)


def _add_shaders(files, level, text):
    sp = "scripts/fl_%s_props.shader" % level
    old = files.get(sp, b"")
    files[sp] = (old + b"\n" + text.encode()) if old else text.encode()


def _surf_lines(ss, pre):
    seen, out = set(), []
    for s in ss:
        if s[0] not in seen and s[3]:
            seen.add(s[0])
            out.append("\tsurface %s shader %s_%s" % (s[0], pre, s[3]))
    return out


# the small props: the disc mesh on the stock entity's own (single) bone, frames measured in engine
# (gettagposition / gettagangles, probe_flitems 2026-11-16). prop = the fl_levels.json "props" key that switches it on.
# health10 / health50: Frontline's Health10 (MedicinalCanteen) and Health50 (MedicalKit) on the map's stand-ins
# (amount < 50 -> item_25_healthbox, >= 50 -> item_50_healthbox). Health25's model is not settled from the disc data
# (the class script names a powerup id, not a mesh) - it keeps the stock box until a reference still shows it
SMALL = {
    "health10": {"prop": "health", "mesh": "MedicinalCanteen.msh",
                 "tik": "items/item_25_healthbox.tik", "bone": ("Box01", (0.0, 90.0, 90.0))},
    "health50": {"prop": "health", "mesh": "MedicalKit.msh",
                 "tik": "items/item_50_healthbox.tik", "bone": ("Box01", (0.0, 90.0, 0.0))},
    "phone": {"prop": "phone", "mesh": "Field_Phone_1_1.msh",
              "tik": "miscobj/phone_squarebase.tik", "bone": ("Box03", (0.0, 90.0, 90.0))},
}


def _stock(mohaa_base, tik):
    t = eaprops.effective_file(mohaa_base, "models/" + tik)
    if not t:
        return None, None, None
    t = t.decode("latin-1")
    path = re.search(r"(?im)^\s*path\s+(\S+)", t).group(1)
    skd = re.search(r"(?im)^\s*skelmodel\s+(\S+)", t).group(1)
    sk = eaprops.effective_file(mohaa_base, path + "/" + skd)
    return (t,) + (eaprops.skd_bones(sk) if sk else (None, None))


def _bounds(surfs, scale, pad=0.0):
    allv = [v[0] for s in surfs for v in s[1]]
    lo = tuple(min(v[i] for v in allv) / scale - pad for i in range(3))
    hi = tuple(max(v[i] for v in allv) / scale + pad for i in range(3))
    return lo, hi, math.sqrt(max(eaprops._dot(lo, lo), eaprops._dot(hi, hi)))


def _small(L, level, mohaa_base, files, lines, log, kind, spec):
    if spec["mesh"] not in L.files:
        log("flprops: %s not on this level; %s keeps the stock model" % (spec["mesh"], kind))
        return
    tik, bb, bn = _stock(mohaa_base, spec["tik"])
    if not tik or not bn or spec["bone"][0] not in bn:
        log("flprops: stock %s not found; %s keeps the stock model" % (spec["tik"], kind))
        return
    scale = float(re.search(r"(?im)^\s*scale\s+([\d.]+)", tik).group(1))
    sub = spec["tik"].split("/")[0]
    mdir = "models/%s/fl_%s" % (sub, level)
    tdir = "textures/fl_%s_props" % level
    pre = "fl_%s_%s" % (level, kind)
    texkey = {}
    ms = _mesh(L, spec["mesh"], (0, 0, 0), texkey, files, tdir, xf=to_map_w, small=True)
    bone, ang = spec["bone"]
    fr = ((0.0, 0.0, 0.0), eaprops.axes(ang))
    ib = bn.index(bone)
    ss = _surf_tris(ms, "fl%s" % kind, lambda k, j: (ib, fr, scale))
    files["%s/%s.skd" % (mdir, kind)] = eaprops.write_skd("fl_" + kind, bb, len(bn), [s[:3] for s in ss])
    lo, hi, rad = _bounds(ss, scale)
    ch = eaprops.local_channels([bone], {bone: None}, {bone: fr}, scale)
    files["%s/%s.skc" % (mdir, kind)] = eaprops.write_skc(0.05, [bone + " pos", bone + " rot"], [ch], (lo, hi), rad)
    _add_shaders(files, level, _shader_text(pre, texkey))
    t = eaprops._retarget_tik(tik, mdir, "%s.skd" % kind, _surf_lines(ss, pre))
    t = re.sub(r"(?im)^(\s*idle\s+)\S+\.skc", lambda mm: mm.group(1) + "%s.skc" % kind, t)
    name = "models/%s/fl_%s_%s.tik" % (sub, level, kind)
    files[name] = t.encode("latin-1")
    lines.append('\tlevel.fl_prop_tik["%s"] = "%s"' % (kind, name))
    lines.append('\tlevel.fl_prop_own["%s"] = 1' % kind)
    log("flprops: %s -> %s (%d surfaces, %d textures, %.0f x %.0f x %.0f u)" % (
        spec["mesh"], name, len(ss), len(texkey), (hi[0] - lo[0]) * scale, (hi[1] - lo[1]) * scale, (hi[2] - lo[2]) * scale))


# the nest guns: the disc's tripod-mount gun (MG42GunTripod.msh: no bipod, pivot at its origin in the receiver; attach
# point 0 = muzzle, 2 = ejection port) on the stock statweapons/mg42_gun.tik (TurretGun: seat, clips, cone unchanged).
# Its pistol grip goes where the stock gunner's hands are (eaprops STOCK grip, the EA 'grip' recipe), on the centreline
MG_MESH = "MG42GunTripod.msh"


def _mg42(L, level, mohaa_base, files, lines, log):
    if MG_MESH not in L.files:
        log("flprops: %s not on this level; the nest guns keep the stock model" % MG_MESH)
        return
    tik, bb, bn = _stock(mohaa_base, "statweapons/mg42_gun.tik")
    if not tik or not bn:
        log("flprops: stock MG42 turret not found; the nest guns keep the stock model")
        return
    SG = eaprops.STOCK["statweapons/mg42_gun.tik"]
    ap = attach_points(L.files.get(MG_MESH))
    verts = [v for d in L.mesh(MG_MESH) for v in d["verts"]]
    gv = [v for v in verts if 0.12 < v[1] < 0.27 and v[2] < 0.0]
    if len(ap) < 3 or not gv:
        log("flprops: MG42 grip / attach points not found; the nest guns keep the stock model")
        return
    grip = (sum(v[0] for v in gv) / len(gv), sum(v[1] for v in gv) / len(gv), min(v[2] for v in gv) / 2)
    g = to_map_w(grip)
    off = (SG["grip"][0] - g[0], 0.0, SG["grip"][2] - g[2])
    mdir = "models/statweapons/fl_%s" % level
    tdir = "textures/fl_%s_props" % level
    pre = "fl_%s_mg" % level
    texkey = {}
    ms = [([eaprops._add(p, off) for p in pos], uv, tris, sh) for pos, uv, tris, sh in
          _mesh(L, MG_MESH, (0, 0, 0), texkey, files, tdir, xf=to_map_w, small=True)]

    def frame(b):
        p, a = SG["bones"][b]
        return p, eaprops.axes(a)
    ib = bn.index("MG42")
    ss = _surf_tris(ms, "flmg", lambda k, j: (ib, frame("MG42"), SG["scale"]))
    files["%s/mg42.skd" % mdir] = eaprops.write_skd("fl_mg42", bb, len(bn), [s[:3] for s in ss])
    w = {b: frame(b) for b in SG["bones"]}
    w["tag_barrel"] = (eaprops._add(to_map_w(ap[0]), off), w["tag_barrel"][1])
    w["tag_eject"] = (eaprops._add(to_map_w(ap[2]), off), w["tag_eject"][1])
    par = {"origin": None, "tag_barrel": "origin", "MG42": "origin", "tag_eject": "origin"}
    names = list(SG["bones"])
    ch = eaprops.local_channels(names, par, w, SG["scale"])
    lo, hi, rad = _bounds(ss, SG["scale"])
    chans = [c for b in names for c in (b + " pos", b + " rot")]
    files["%s/mg42.skc" % mdir] = eaprops.write_skc(0.05, chans, [ch], (lo, hi), rad)
    nf = max(1, int(round(SG["fire_len"] / 0.05)))
    files["%s/mg42fire.skc" % mdir] = eaprops.write_skc(0.05, chans, [ch] * nf, (lo, hi), rad)
    _add_shaders(files, level, _shader_text(pre, texkey))
    t = eaprops._retarget_tik(tik, mdir, "mg42.skd", _surf_lines(ss, pre))
    name = "models/statweapons/fl_%s_mg42.tik" % level
    files[name] = t.encode("latin-1")
    lines.append('\tlevel.fl_prop_tik["mg42"] = "%s"' % name)
    lines.append('\tlevel.fl_prop_own["mg42"] = 1')
    log("flprops: %s -> %s (%d surfaces; grip %s -> offset %s; muzzle %s)" % (
        MG_MESH, name, len(ss), tuple(round(v, 1) for v in g), tuple(round(v, 1) for v in off),
        tuple(round(v, 1) for v in w["tag_barrel"][0])))


def _normals(pos, tris):
    """vertex normals from the faces, turned outward: the disc's strips are wound one way and the map conversion
    mirrors y, so the sign is decided per mesh by the faces' facing against the mesh centre"""
    n = [[0.0, 0.0, 0.0] for _ in pos]
    c = [sum(p[i] for p in pos) / max(1, len(pos)) for i in range(3)]
    score = 0.0
    for a, b, cc in tris:
        f = eaprops._cross(eaprops._sub(pos[b], pos[a]), eaprops._sub(pos[cc], pos[a]))
        mid = [(pos[a][i] + pos[b][i] + pos[cc][i]) / 3 - c[i] for i in range(3)]
        score += eaprops._dot(f, mid)
        for x in (a, b, cc):
            for i in range(3):
                n[x][i] += f[i]
    s = 1.0 if score >= 0 else -1.0
    return [eaprops._norm((v[0] * s, v[1] * s, v[2] * s)) if any(v) else (0.0, 0.0, 1.0) for v in n]


def _surf_tris(meshes, label, bone_of):
    m = {"meshes": meshes, "skin": [{"nrm": [_mirror_n(v) for v in _normals(pos, tris)]}
                                    for pos, uv, tris, sh in meshes]}
    return eaprops.surfaces_for(m, range(len(meshes)), lambda k, j, p: p, bone_of, label)


def _mirror_n(n):
    """surfaces_for maps disc normals to map space (x, y) -> (y, -x); ours are already map space: pre-invert that"""
    return (-n[1], n[0], n[2])


def _panzer(L, level, mohaa_base, files, lines, log):
    body_ap = attach_points(_file_of(L, INTACT["body"]))
    tur_ap = attach_points(_file_of(L, INTACT["turret"]))
    can_ap = attach_points(_file_of(L, INTACT["cannon"]))
    if len(body_ap) < 4 or not tur_ap or not can_ap:
        log("flprops: Panzer IV attach points not found; the tank keeps the stock model")
        return
    mg_at, tr_r, tr_l, ring = body_ap[0], body_ap[1], body_ap[2], body_ap[3]
    gun_at = tuple(ring[i] + tur_ap[0][i] for i in range(3))
    muzzle = tuple(gun_at[i] + can_ap[0][i] for i in range(3))
    tiks = {k: eaprops.effective_file(mohaa_base, "models/" + k) for k in STOCK}
    if not all(tiks.values()):
        log("flprops: stock Panzer IV (europe) files not found; the tank keeps the stock model")
        return
    tiks = {k: v.decode("latin-1") for k, v in tiks.items()}

    def skd_of(tik):
        t = tiks[tik]
        path = re.search(r"(?im)^\s*path\s+(\S+)", t).group(1)
        skd = re.search(r"(?im)^\s*skelmodel\s+(\S+)", t).group(1)
        return eaprops.skd_bones(eaprops.effective_file(mohaa_base, path + "/" + skd))
    mdir = "models/vehicles/fl_%s" % level
    tdir = "textures/fl_%s_props" % level
    pre = "fl_%s_pz" % level
    texkey = {}
    SB, SC = STOCK["vehicles/panzer_tank_europe.tik"], STOCK["vehicles/panzer_cannon_europe.tik"]
    SD, SS = STOCK["vehicles/Panzer_destroyed_lowpoly_base.tik"], STOCK["static/vehicle_panzer_iv_europe.tik"]

    def frame(spec, b):
        p, a = spec["bones"][b]
        return p, eaprops.axes(a)
    t0 = SB["bones"]["turret0"][0]
    rmap = to_map(ring)
    shift = (t0[0] - rmap[0], t0[1] - rmap[1], 0.0)        # the hull moves so the ring lands on turret0

    def shifted(ms):
        return [([eaprops._add(p, shift) for p in pos], uv, tris, sh) for pos, uv, tris, sh in ms]
    hull = shifted(_mesh(L, INTACT["body"], (0, 0, 0), texkey, files, tdir)
                   + _mesh(L, INTACT["tread_r"], tr_r, texkey, files, tdir)
                   + _mesh(L, INTACT["tread_l"], tr_l, texkey, files, tdir)
                   + _mesh(L, INTACT["mg"], mg_at, texkey, files, tdir))
    turret = _mesh(L, INTACT["turret"], ring, texkey, files, tdir)
    gun = _mesh(L, INTACT["cannon"], gun_at, texkey, files, tdir)
    # 1. hull on 'panzer_IV' (the lean animations move it; turret0 rides it)
    bb, bn = skd_of("vehicles/panzer_tank_europe.tik")
    ib = bn.index("panzer_IV")
    hull_s = _surf_tris(hull, "flpz_hull", lambda k, j: (ib, frame(SB, "panzer_IV"), SB["scale"]))
    files["%s/panzer_base.skd" % mdir] = eaprops.write_skd("fl_panzer_base", bb, len(bn), [s[:3] for s in hull_s])
    # 2. turret + gun: the cannon entity's own space = map space - turret0 (after the hull shift)
    cb, cn = skd_of("vehicles/panzer_cannon_europe.tik")
    off = (shift[0] - t0[0], shift[1] - t0[1], -t0[2])

    def to_can(ms):
        return [([eaprops._add(p, off) for p in pos], uv, tris, sh) for pos, uv, tris, sh in ms]
    cw = {b: frame(SC, b) for b in SC["bones"]}
    trn = eaprops._add(to_map(gun_at), off)
    muz = eaprops._add(to_map(muzzle), off)
    cw["pitch"] = (trn, cw["pitch"][1])
    cw["recoil"] = (trn, cw["recoil"][1])
    cw["tag_barrel"] = (muz, cw["tag_barrel"][1])
    ic, ir = cn.index("connect"), cn.index("recoil")
    tur_s = _surf_tris(to_can(turret), "flpz_turret", lambda k, j: (ic, cw["connect"], SC["scale"]))
    gun_s = _surf_tris(to_can(gun), "flpz_gun", lambda k, j: (ir, cw["recoil"], SC["scale"]))
    can_s = tur_s + gun_s
    files["%s/panzer_cannon.skd" % mdir] = eaprops.write_skd("fl_panzer_cannon", cb, len(cn), [s[:3] for s in can_s])
    names = list(SC["bones"])
    chans = [c for b in names for c in (b + " pos", b + " rot")]
    allv = [v[0] for s in can_s for v in s[1]]
    lo = tuple(min(v[i] for v in allv) / SC["scale"] - 10 for i in range(3))
    hi = tuple(max(v[i] for v in allv) / SC["scale"] + 10 for i in range(3))
    rad = math.sqrt(max(eaprops._dot(lo, lo), eaprops._dot(hi, hi)))
    idle = eaprops.local_channels(names, CANNON_PARENTS, cw, SC["scale"])
    files["%s/panzer_cannon.skc" % mdir] = eaprops.write_skc(0.05, chans, [idle], (lo, hi), rad)
    fr = []
    fwd = cw["tag_barrel"][1][0]              # the gun's own forward axis (the barrel tag's x row)
    for d in RECOIL:
        w = dict(cw)
        p, a = cw["recoil"]
        w["recoil"] = (tuple(p[i] + fwd[i] * d for i in range(3)), a)
        bp, ba = cw["tag_barrel"]
        w["tag_barrel"] = (tuple(bp[i] + fwd[i] * d for i in range(3)), ba)
        fr.append(eaprops.local_channels(names, CANNON_PARENTS, w, SC["scale"]))
    files["%s/panzer_cannon_fire.skc" % mdir] = eaprops.write_skc(0.05, chans, fr, (lo, hi), rad)
    # 3. the parked copy (static/vehicle_panzer_iv_europe): the whole intact tank on Box01, the same placement
    sb, sn = skd_of("static/vehicle_panzer_iv_europe.tik")
    whole = hull + shifted(turret) + shifted(gun)
    st_s = _surf_tris(whole, "flpz_static", lambda k, j: (sn.index("Box01"), frame(SS, "Box01"), SS["scale"]))
    files["%s/panzer_static.skd" % mdir] = eaprops.write_skd("fl_panzer_static", sb, len(sn), [s[:3] for s in st_s])
    # 4. the wreck: the destroyed set on 'panzer', the ring on the stock wreck's turret0 (its smoke rises there)
    wb, wn = skd_of("vehicles/Panzer_destroyed_lowpoly_base.tik")
    tw = SD["bones"]["turret0"][0]
    wshift = (tw[0] - rmap[0], tw[1] - rmap[1], 0.0)
    wreck = [([eaprops._add(p, wshift) for p in pos], uv, tris, sh) for pos, uv, tris, sh in
             _mesh(L, WRECK["body"], (0, 0, 0), texkey, files, tdir)
             + _mesh(L, WRECK["tread_r"], tr_r, texkey, files, tdir)
             + _mesh(L, WRECK["tread_l"], tr_l, texkey, files, tdir)
             + _mesh(L, WRECK["turret"], ring, texkey, files, tdir)
             + _mesh(L, WRECK["cannon"], gun_at, texkey, files, tdir)]
    wr_s = _surf_tris(wreck, "flpz_wreck", lambda k, j: (wn.index("panzer"), frame(SD, "panzer"), SD["scale"]))
    files["%s/panzer_wreck.skd" % mdir] = eaprops.write_skd("fl_panzer_wreck", wb, len(wn), [s[:3] for s in wr_s])
    # shaders: the stock tank's own lighting (lightingSpherical, mainta Tanks.shader); cut-outs alpha-tested
    sh = []
    for key, (tp, cut) in sorted(texkey.items()):
        sh.append("%s_%s\n{\n\tcull none\n\t{\n\t\tmap %s\n%s\t\trgbGen lightingSpherical\n\t}\n}\n" % (
            pre, key, tp, "\t\talphaFunc GE128\n" if cut else ""))
    _add_shaders(files, level, "\n".join(sh))

    def surf_lines(ss):
        seen, out = set(), []
        for s in ss:
            if s[0] not in seen and s[3]:
                seen.add(s[0])
                out.append("\tsurface %s shader %s_%s" % (s[0], pre, s[3]))
        return out
    tank = eaprops._retarget_tik(tiks["vehicles/panzer_tank_europe.tik"], mdir, "panzer_base.skd", surf_lines(hull_s),
                                 "models/vehicles/panzer_iv",
                                 replace=(("vehicles/panzer_cannon_europe.tik", "vehicles/fl_%s_panzer_cannon.tik" % level),))
    can = eaprops._retarget_tik(tiks["vehicles/panzer_cannon_europe.tik"], mdir, "panzer_cannon.skd", surf_lines(can_s))
    can = re.sub(r"(?im)^(\s*idle\s+)\S+\.skc", lambda mm: mm.group(1) + "panzer_cannon.skc", can)
    can = re.sub(r"(?im)^(\s*fire\s+)\S+\.skc", lambda mm: mm.group(1) + "panzer_cannon_fire.skc", can)
    stat = eaprops._retarget_tik(tiks["static/vehicle_panzer_iv_europe.tik"], mdir, "panzer_static.skd",
                                 surf_lines(st_s), "models/vehicles/panzer_iv")
    wr = eaprops._retarget_tik(tiks["vehicles/Panzer_destroyed_lowpoly_base.tik"], mdir, "panzer_wreck.skd",
                               surf_lines(wr_s), "models/vehicles/Panzer_destroyed_lowpoly")
    # the stock wreck's skin swaps (surface X +skin1) name the stock surfaces: harmless, they match nothing
    for k, t in (("", tank), ("_cannon", can), ("_static", stat), ("_wreck", wr)):
        files["models/vehicles/fl_%s_panzer%s.tik" % (level, k)] = t.encode("latin-1")
    lines.append('\tlevel.fl_prop_tik["panzer"] = "models/vehicles/fl_%s_panzer.tik"' % level)
    lines.append('\tlevel.fl_prop_tik["panzer_static"] = "models/vehicles/fl_%s_panzer_static.tik"' % level)
    lines.append('\tlevel.fl_prop_tik["panzer_wreck"] = "models/vehicles/fl_%s_panzer_wreck.tik"' % level)
    lines.append('\tlevel.fl_prop_own["panzer"] = 1')     # built only once approved (the fl_levels key)
    log("flprops: Panzer IV -> fl_%s_panzer.tik (hull %d / turret+gun %d / static %d / wreck %d surfaces, %d textures; "
        "ring shift %.1f %.1f; trunnion %s muzzle %s)" % (level, len(hull_s), len(can_s), len(st_s), len(wr_s),
                                                           len(texkey), shift[0], shift[1],
                                                           tuple(round(v, 1) for v in trn), tuple(round(v, 1) for v in muz)))
